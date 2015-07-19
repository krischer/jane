# -*- coding: utf-8 -*-
"""
Waveform indexer adapted from obspy.db.
"""

import fnmatch
import http
import logging
import multiprocessing
import os
import pprint
import select
import sys
import time

from django.core.management.base import BaseCommand

from ... import process_waveforms
from ... import models


# Available in Python 3.4+. Works with all BLAS implementations.
# multiprocessing.set_start_method("forkserver")

logger = logging.getLogger("jane-waveform-indexer")


class WaveformFileCrawler(object):
    """
    A waveform file crawler.

    This class scans periodically all given paths for waveform files and
    collects them into a watch list.
    """
    def _delete(self, path, file=None):
        """
        Remove a file or all files with a given path from the database.
        """
        if file:
            try:
                f = models.File.objects.get(path__name=path, name=file)
                f.delete()
                logger.debug("Deleted file '%s'." % os.path.join(path, file))
            except models.File.DoesNotExist:
                logger.error("Error deleting file '%s': Not part of the "
                             "database" % os.path.join(path, file))
        else:
            try:
                p = models.Path.objects.get(name=path)
                p.delete()
                logger.debug("Deleted path '%s'." % path)
            except models.Path.DoesNotExist:
                logger.error("Error deleting path '%s': Not part of the "
                             "database" % path)

    def _select(self, path=None):
        """
        Fetch entry from database.
        """
        if path:
            # check database for file entries in specific path
            return {_i[0]: _i[1] for _i in
                    models.File.objects
                        .filter(path__name=path)
                        .values_list("name", "mtime")}
        else:
            return models.Path.objects.values_list("name", flat=True)

    def _process_log_queue(self):
        try:
            msg = self.log_queue.pop(0)
        except:
            pass
        else:
            if msg.startswith('['):
                logger.error(msg)
            else:
                logger.debug(msg)

    @property
    def patterns(self):
        return self.paths[self._root][0]

    def has_pattern(self, file):
        """
        Checks if the file name fits to the preferred file pattern.
        """
        for pattern in self.patterns:
            if fnmatch.fnmatch(file, pattern):
                return True
        return False

    def _reset_walker(self):
        """
        Resets the crawler parameters.
        """
        # break if options run_once is set and a run was completed already
        if self.options["run_once"] and \
                getattr(self, 'first_run_complete', False):
            # before shutting down make sure all queues are empty!
            while self.work_queue:
                msg = 'Crawler stopped but waiting for empty queues to exit.'
                logger.debug(msg)
                if self.log_queue:
                    msg = 'log_queue still has %s item(s)'
                    logger.debug(msg % len(self.log_queue))
                    # Fetch items from the log queue
                    self._process_log_queue()
                    continue
                if self.work_queue:
                    msg = 'work_queue still has %s items'
                    logger.debug(msg % len(self.work_queue))
                time.sleep(10)
            logger.debug('Crawler stopped by option run_once.')
            sys.exit()
            return
        logger.debug('Crawler restarted.')
        # reset attributes
        self._current_path = None
        self._current_files = []
        self._db_files = {}
        # get search paths for waveform crawler
        self._roots = list(self.paths.keys())
        self._root = self._roots.pop(0)
        # create new walker
        self._walker = os.walk(self._root, topdown=True, followlinks=True)
        # clean up paths
        if self.options["cleanup"]:
            paths = self._select()
            for path in paths:
                if not os.path.isdir(path):
                    # no path in filesystem
                    self._delete(path)
                elif not self._select(path):
                    # empty path in database
                    self._delete(path)
        # logging
        logger.debug("Crawling root '%s' ..." % self._root)
        self.first_run_complete = True

    def _step_walker(self):
        """
        Steps current walker object to the next directory.
        """
        # try to fetch next directory
        try:
            root, dirs, files = next(self._walker)
        except StopIteration:
            # finished cycling through all directories in current walker
            # try get next crawler search path
            try:
                self._root = self._roots.pop()
            except IndexError:
                # a whole cycle has been done
                # reset everything
                self._reset_walker()
                return
            # reset attributes
            self._current_path = None
            self._current_files = []
            self._db_files = {}
            # create new walker
            self._walker = os.walk(self._root, topdown=True, followlinks=True)
            # logging
            logger.debug("Crawling root '%s' ..." % self._root)
            return
        # remove files or paths starting with a dot
        if self.options["skip_dots"]:
            for file in files:
                if file.startswith('.'):
                    files.remove(file)
            for dir in dirs:
                if dir.startswith('.'):
                    dirs.remove(dir)
        self._current_path = root
        self._current_files = files
        # logging
        logger.debug("Scanning path '%s' ..." % self._current_path)
        # get all database entries for current path
        self._db_files = self._select(self._current_path)

    def _prepare_paths(self, paths):
        out = {}
        for path in paths:
            path = os.path.expanduser(path)
            # strip features
            if '#' in path:
                parts = path.split('#')
                path = parts[0]
                features = parts[1:]
            else:
                features = []
            # strip patterns
            if '=' in path:
                path, patterns = path.split('=', 1)
                if ' ' in patterns:
                    patterns = patterns.split(' ')
                else:
                    patterns = [patterns.strip()]
            else:
                patterns = ['*.*']
            # normalize and absolute path name
            path = os.path.normpath(os.path.abspath(path))
            # check path
            if not os.path.isdir(path):
                logger.warn("Skipping inaccessible path '%s' ..." % path)
                continue
            out[path] = (patterns, features)
        return out

    def iterate(self):
        """
        Handles exactly one directory.
        """
        # skip if service is not running
        # be aware that the processor pool is still active waiting for work
        if not self.running:
            return
        # skip if input queue is full
        if len(self.input_queue) > self.options["number_of_cpus"]:
            return
        # Fetch items from the log queue
        self._process_log_queue()
        # walk through directories and files
        try:
            file = self._current_files.pop(0)
        except IndexError:
            # file list is empty
            # clean up not existing files in current path
            if self.options["cleanup"]:
                for file in self._db_files.keys():
                    self._delete(self._current_path, file)
            # jump into next directory
            self._step_walker()
            return
        # skip file with wrong pattern
        if not self.has_pattern(file):
            return
        # process a single file
        path = self._current_path
        filepath = os.path.join(path, file)
        # get file stats
        try:
            stats = os.stat(filepath)
            mtime = int(stats.st_mtime)
        except Exception as e:
            logger.error(str(e))
            return
        # check if recent
        if self.options["recent"]:
            # skip older files
            if time.time() - mtime > 60 * 60 * self.options["recent"]:
                try:
                    db_file_mtime = self._db_files.pop(file)
                except:
                    pass
                return

        # option force-reindex set -> process file regardless if already in
        # database or recent or whatever
        if self.options["force_reindex"]:
            self.input_queue[filepath] = (path, file)
            return
        # compare with database entries
        if file not in self._db_files.keys():
            # file does not exists in database -> add file
            self.input_queue[filepath] = (path, file)
            return
        # file is already in database
        # -> remove from file list so it won't be deleted on database cleanup
        try:
            db_file_mtime = self._db_files.pop(file)
        except:
            return
        # -> compare modification times of current file with database entry
        if mtime == db_file_mtime:
            return
        # modification time differs -> update file
        print("NEVE HERE!")
        self.input_queue[filepath] = (path, file)


def worker(_i, input_queue, work_queue, log_queue):
    try:
        # loop through input queue
        while True:
            # fetch a unprocessed item
            try:
                filepath = input_queue.popitem()[0]
            except:
                continue
            # skip item if already in work queue
            if filepath in work_queue:
                continue
            work_queue.append(filepath)

            # process the file.
            try:
                process_waveforms.process_file(filepath)
            except Exception as e:
                log_queue.append("Error reading '%s': '%s' - %s" % (
                    filepath, str(type(e)), str(e)))
            # ALways attempt to remove it from the worker queue.
            try:
                work_queue.remove(filepath)
            except:
                pass
    except KeyboardInterrupt:
        return


class MyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """
        Respond to a GET request.
        """
        out = """<html>
  <head>
    <title>obspy-indexer status</title>
    <meta http-equiv="refresh" content="10" />
    <style type="text/css">
      th { text-align: left; font-family:monospace; width: 150px;
           vertical-align: top; padding: 3px; }
      td { font-family:monospace; padding: 3px;}
      pre { margin: 0; }
    </style>
  </head>
  <body>
    <h1>obspy-indexer</h1>
    <h2>Options</h2>
"""
        out += '<table>'
        for key, value in sorted(self.server.options.items()):
            out += "<tr><th>%s</th><td>%s</td></tr>" % (key, value)
        out += '</table>'
        out += '<h2>Status</h2>'
        out += '<table>'
        out += "<tr><th>current path</th><td>%s</td></tr>" % \
               (self.server._current_path)
        out += "<tr><th>patterns</th><td><pre>%s</pre></td></tr>" % \
               ('\n'.join(self.server.patterns))
        out += "<tr><th>features</th><td><pre>%s</pre></td></tr>" % \
               ('\n'.join(self.server.features))
        out += "<tr><th>file queue</th><td><pre>%s</pre></td></tr>" % \
               ('\n'.join(self.server._current_files))
        out += '</table>'
        out += "</body></html>"
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(out)


class WaveformIndexer(http.server.HTTPServer, WaveformFileCrawler):
    """
    A waveform indexer server.
    """
    def serve_forever(self, poll_interval=0.5):
        self.running = True
        while self.running:
            r, _w, _e = select.select([self], [], [], poll_interval)
            if r:
                self._handle_request_noblock()
            self.iterate()


def _run_indexer(options):
    logger.info("Starting indexer %s:%s ..." % (options["host"],
                                                options["port"]))
    # initialize crawler
    service = WaveformIndexer((options["host"], options["port"]), MyHandler)
    try:
        # prepare paths
        if ',' in options["data"]:
            paths = options["data"].split(',')
        else:
            paths = [options["data"]]
        paths = service._prepare_paths(paths)
        if not paths:
            return

        # create file queue and worker processes
        manager = multiprocessing.Manager()
        in_queue = manager.dict()
        work_queue = manager.list()
        log_queue = manager.list()

        # spawn processes
        for i in range(options["number_of_cpus"]):
            args = (i, in_queue, work_queue, log_queue)
            p = multiprocessing.Process(target=worker, args=args)
            p.daemon = True
            p.start()

        service.options = options

        # set queues
        service.input_queue = in_queue
        service.work_queue = work_queue
        service.log_queue = log_queue
        service.paths = paths
        service._reset_walker()
        service._step_walker()
        service.serve_forever(options["poll_interval"])
    except KeyboardInterrupt:
        quit()
    logger.info("Indexer stopped.")


class Command(BaseCommand):
    help =  """Crawl directories and index waveforms contents to Jane.


Usage Examples
--------------
    orint("processing", filename)

(1) Run indexer as daemon continuously crawling the given paths but index only
    the last 24 hours (-r24) of a waveform archive::

       #!/bin/bash
       DATA=/path/to/archive/2010,/path/to/archive/2011,/path/to/arclink
       LOG=/path/to/indexer.log
       python manage.py index_waveforms --verbose -i0.0 -n1 -d$DATA \
           -r24 -l$LOG &

(2) Run only once and remove duplicates::

       python manage.py index_waveforms --verbose -i0.0 --run-once \
           --check-duplicates -n1 -d$DATA
"""

    def add_arguments(self, parser):
        parser.add_argument(
            '-d', '--data', default='data=*.*',
            help="""Path, search patterns and feature plug-ins of waveform files.
    The indexer will crawl recursively through all sub-directories within each
    given path. Multiple paths have to be separated with a comma, e.g.
    '/first/path=*.*,/second/path,/third/path=*.gse'.
    File patterns are given as space-separated list of wildcards after a equal
    sign, e.g.
    '/path=*.gse2 *.mseed,/second/path=*.*'.
    Feature plug-ins may be added using the hash (#) character, e.g.
    '/path=*.mseed#feature1#feature2,/second/path#feature2'.
    Be aware that features must be provided behind file patterns (if any)! There is
    no default feature enabled.
    Default path option is 'data=*.*'.""")
        parser.add_argument(
            '-n', type=int, dest='number_of_cpus',
            help="Number of CPUs used for the indexer.",
            default=multiprocessing.cpu_count())
        parser.add_argument(
            '-i', '--poll-interval', type=float, default=0.1,
            help="Poll interval for file crawler in seconds (default is 0.1).")
        parser.add_argument(
            '-r', '--recent', type=int, default=0,
            help="Index only recent files modified within the given "
                 "number of hours. This option is deactivated by default.")
        parser.add_argument(
            '-l', '--log', default='',
            help="Log file name. If no log file is given, stdout will be used.")
        parser.add_argument(
            '-a', '--all-files', action='store_false', dest='skip_dots',
            help="The indexer will automatically skip paths or "
                 "files starting with a dot. This option forces "
                 "parsing of all paths and files.")
        parser.add_argument(
            '-1', '--run-once', action='store_true',
            help="The indexer will parse through all given directories only "
                 "once and quit afterwards.")
        parser.add_argument(
            '--check-duplicates', action='store_true',
            help="Checks for duplicate entries within database. "
                 "This feature will slow down the indexer progress.")
        parser.add_argument(
            '--cleanup', action='store_true',
            help="Clean database from non-existing files or paths " +
                 "if activated, but will skip all paths marked as " +
                 "archived in the database.")
        parser.add_argument(
            '-f', '--force-reindex', action='store_true',
            help="Reindex existing index entry for every crawled file.")
        parser.add_argument(
            '-H', '--host', default='localhost',
            help="Server host name. Default is 'localhost'.")
        parser.add_argument(
            '-p', '--port', type=int, default=0,
            help="Port number. If not given a free port will be picked.")


    def handle(self, *args, **kwargs):
        # set level of verbosity
        if kwargs["verbosity"] > 1:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        # Prevent propagating to higher loggers.
        logger.propagate = 0

        if kwargs["log"] == "":
            # Console log handler.
            ch = logging.StreamHandler()
        else:
            ch = logging.FileHandler(kwargs["log"])

        # Add formatter
        FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"
        formatter = logging.Formatter(FORMAT)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        logger.info("Started with parameters:\n%s" % pprint.pformat(kwargs))

        _run_indexer(kwargs)
