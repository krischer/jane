# -*- coding: utf-8 -*-

from celery import shared_task

from jane.waveforms import models


@shared_task
def process_query(networks, stations, locations, channels, starttime, endtime,
                  format='mseed', nodata='204', quality='B',
                  minimumlength=0, longestonly=False):
    """
    Process query and generate a combined waveform file
    """
    return 'OK'
