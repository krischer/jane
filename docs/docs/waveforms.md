# Waveforms

Jane's second pillar besides its plugin-based document database is the ability
to deal with seismic waveforms. There is no reason to store that into a
document database as it is very well structured; something a relational
database is made for. Therefore waveform data is stored in a coupe of tables in
the underlying PostgreSQL database.

## Getting Waveforms Into the Database

The first step is always to get data into the database. For this purpose, Jane offers two complementary ways:

1. A command to index a certain path. Use this to index old data or campaign data.
2. A command to monitor a certain directory. Any detected changes will be
   picked up and reflected in the database.

All commands are implemented as Django management commands. Run these in the
`jane/src` directory.

### Index A Certain Path

The `index_waveforms` command can be used to recursively find and index all
waveforms files in a certain folder. It has the following options.

```bash
$ python manage.py index_waveforms --help

usage: manage.py index_waveforms [--celery] [--delete-files] [--queue QUEUE] path

Index waveforms

positional arguments:
  path                  The path to index.

optional arguments:
  --celery              Distribute jobs to Celery`s 'index_waveforms' queue.
                        By default all jobs will be run directly. Remember to
                        have celery workers with that queue running!
  --delete-files        Delete all files before indexing new ones. By default
                        the indexer will just crawl all files and add new or
                        changed ones. It will not delete anything. If true it
                        will remove all files at or below the given path from
                        the database before reindexing everything.
  --queue QUEUE         The name of the celery queue to use for the indexing.
                        Only important if --celery is used. Defaults to
                        "index_waveforms".

```

The `--celery` settings warrants a bit more explanation. If you only have
relatively little files to index, just run the command without it; all
waveforms will then be indexed one after another. If you run it with
`--celery`, the tasks will be sent to the queue specified by the `--queue`
argument. An instance with that queue thus has to be running. This scales much
better as you can run celery with a larger number of workers.

### Monitor a Directory

Directories can also continuously be monitored for any changes; the main use
for this is incoming waveform data that should be indexed fairly rapidly.

```bash
$ python manage.py filemon --help

usage: manage.py filemon [--debug] [--poll]
                         [--polling-interval POLLING_INTERVAL] [--queue QUEUE]
                         path

Monitor files.

positional arguments:
  path                  The path to monitor.

optional arguments:
  --debug, -d           Debug on
  --poll                Don`t use the OS filesystem monitors, but poll the
                        filesystem in intervals.
  --polling-interval POLLING_INTERVAL
                        Polling interval if --poll is used in seconds.
  --queue QUEUE         The name of the celery queue to use for the indexing.
                        Defaults to "monitor_waveforms".
```

This always requires active celery workers, working on the queue specified with
the `--queue` argument. By default this command will use the operating system's
capability to monitor file system changes. In some cases this does not work
(mainly if the kernel is not responsible for the storage, e.g. on a network
 drive). In these cases, please use the `--poll` argument which will result in
the file system being periodically scanned for changes; the scanning interval
is determined by the `--polling_interval` argument.
