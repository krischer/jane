# -*- coding: utf-8 -*-

import os

from celery.app import shared_task
from django.core.exceptions import ObjectDoesNotExist
from obspy.core import read

from jane.filearchive import models


@shared_task
def process_file(filename):
    """
    Process single file
    """
    # make sure path and file objects exists
    path_obj = models.Path.objects.get_or_create(
            name=os.path.dirname(os.path.abspath(filename)))[0]
    file_obj = models.File.objects.get_or_create(path=path_obj,
            name=os.path.basename(filename))[0]
    try:
        # check if waveform
        stream = read(filename)
        if len(stream) == 0:
            return
    except:
        return
    # set format
    file_obj.format = stream[0].stats._format
    file_obj.save()
    for trace in stream:
        waveform_obj = models.Waveform.objects.get_or_create(file=file_obj,
            starttime=trace.stats.starttime.datetime,
            endtime=trace.stats.endtime.datetime)[0]
        waveform_obj.network = trace.stats.network
        waveform_obj.station = trace.stats.station
        waveform_obj.location = trace.stats.location
        waveform_obj.channel = trace.stats.channel
        waveform_obj.calib = trace.stats.calib
        waveform_obj.sampling_rate = trace.stats.sampling_rate
        waveform_obj.npts = trace.stats.npts
        waveform_obj.preview_image = trace.plot(format='png')
        waveform_obj.save()
    return


@shared_task
def filemon_event(event):
    """
    Handle file monitor events
    """
    src_path = os.path.dirname(os.path.abspath(event['src_path']))
    src_file = os.path.basename(event['src_path'])
    event_type = event['event_type']
    is_directory = event['is_directory']

    # deleted path or file
    if event_type == 'deleted':
        try:
            if is_directory:
                models.Path.objects.get(name=src_path).delete()
            else:
                models.File.objects.get(path__name=src_path,
                                        name=src_file).delete()
        except ObjectDoesNotExist:
            pass
        return

    # get or create source objects
    path_obj = models.Path.objects.get_or_create(name=src_path)[0]
    # handle events
    if event_type in ['created', 'modified'] and not is_directory:
        # call processing
        process_file.delay(filename=event['src_path'])
    elif event_type == 'moved':
        if not is_directory:
            file_obj = models.File.objects.get_or_create(path=path_obj,
                                                         name=src_file)[0]
        # moved file
        dest_path = os.path.dirname(event['dest_path'])
        dest_file = os.path.basename(event['dest_path'])
        if is_directory:
            path_obj.name = dest_path
            path_obj.save()
        elif dest_path == src_path:
            file_obj.name = dest_file
            file_obj.save()
        else:
            dest_obj = models.Path.objects.get_or_create(name=dest_path)[0]
            file_obj.name = dest_file
            file_obj.path = dest_obj
            file_obj.save()
    else:
        raise NotImplementedError('Unknown event_type %s' % (event_type))


@shared_task
def index_path(path):
    """
    Index given path
    """
    # convert to absolute path
    path = os.path.abspath(path)
    try:
        # delete all paths and files which start with path
        models.Path.objects.filter(name__startswith=path).delete()
    except:
        return
    for root, _, files in os.walk(path):
        # index each file
        for file in files:
            process_file.delay(os.path.join(root, file))
