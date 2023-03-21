"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import threading
import time
import model
import os
import http.cookiejar as cookielib
import requests
import urllib.error
import urllib.parse
import random
import json
from google.auth.exceptions import RefreshError
from google.api_core.exceptions import RetryError, ServiceUnavailable, NotFound

import logging
logger = logging.getLogger('piworkout-server')

class ListFetchThread:
    _running = True
    _shouldFetch = True
    _gcCounter = 60
    _wait = 60 # check every 60 seconds
    markWatchedQueue = []
    queueMutex = threading.Lock()
    cj = None

    def run(self):
        start = time.time()
        while (self._running):
            elapsed = time.time() - start
                
            if (elapsed > self._wait or self._shouldFetch):
                self._shouldFetch = False
                start = time.time() # reset timer

                try:
                    model.video.fetch()
                    self._gcCounter += 1
                    if (self._gcCounter >= 60):
                        self._gcCounter = 0
                        self.garbageCollect()
                except (RefreshError, ServiceUnavailable) as re:
                    logger.error('Error Refresh/Service: ' + str(re))
                except RetryError as e:
                    logger.error('Error Retry: ' + str(re))
                except Exception as e:
                    logger.error('Error exception: ' + str(e))
                    
            # determine if there is a video to mark watched in queue
            video = None
            with self.queueMutex:
                if (len(self.markWatchedQueue) > 0):
                    video = self.markWatchedQueue.pop(0)
            if (video != None):
                self.markWatched(video)
            
            time.sleep(1) 

    def close(self):
        self._running = False
        
    def markWatched(self, video):
        # this is locked from run()
        with model.video.dataMutex():
            data = json.loads(video.watchedUrl)
            position = video.position
            video_length = video.duration
            
            logger.info('markWatched() id=' + str(video.id))
            if (self.cj == None):
                logger.warning('cookiejar not set.')
                return
            
        # new way of marking watched smarttube-next
        
        # get url endpoints and query data. was taken from yt-dlp previously in piworkoutpluginie
        item = data['videostatsPlaybackUrl']
        parsed_url = urllib.parse.urlparse(item['url'])
        qs = urllib.parse.parse_qs(parsed_url.query)
        
        # cpn generation algorithm is reverse engineered from base.js.
            # In fact it works even with dummy cpn.
        CPN_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        cpn = ''.join(CPN_ALPHABET[random.randint(0, 256) & 63] for _ in range(0, 16))
        
        fullWatched = (position > video_length - 3)
        
        # fullWatched doesn't appear to be working so just set the watchtime to video_length - 3s
        if (fullWatched):
            fullWatched = False
            position = video_length - 3
        
        if (fullWatched):
            # @deprecated
            # send fully watched
            
            # create watched record
            nQs = {}
            nQs.update({
                'ns': 'yt',
                'ver': ['2'],
                'final': '1',
                'docid': qs['docid'],
                'cpn': cpn,
                'ei': qs['ei'],
                'vm': qs['vm'],
                'of': qs['of'],
            })
            
            url = urllib.parse.urlunparse(parsed_url._replace(path='/api/stats/playback', query=urllib.parse.urlencode(nQs, True)))
            logger.debug(url)
            requests.get(url, cookies=self.cj)
            
            # update watched time
            nQs = {}
            nQs.update({
                'ns': 'yt',
                'ver': ['2'],
                'final': '1',
                'docid': qs['docid'],
                'st': 0,
                'et': video_length - 3,
                'cpn': cpn,
                'ei': qs['ei'],
            })
            url = urllib.parse.urlunparse(parsed_url._replace(path='/api/stats/watchtime', query=urllib.parse.urlencode(nQs, True)))
            logger.debug(url)
            requests.get(url, cookies=self.cj)
        else:
            # send position
            
            # create watched record
            nQs = {}
            nQs.update({
                'ns': 'yt',
                'ver': ['2'],
                'cmt': '0',
                'final': '1',
                'docid': qs['docid'],
                'len': video_length,
                'st': '0',
                'et': position,
                'cpn': cpn,
                'ei': qs['ei'],
                'vm': qs['vm'],
                'of': qs['of'],
            })
            
            url = urllib.parse.urlunparse(parsed_url._replace(path='/api/stats/playback', query=urllib.parse.urlencode(nQs, True)))
            logger.debug(url)
            requests.get(url, cookies=self.cj)
            
            # update watched time
            nQs = {}
            nQs.update({
                'ns': 'yt',
                'ver': ['2'],
                'cmt': '0',
                'final': '1',
                'docid': qs['docid'],
                'len': video_length,
                'st': 0,
                'et': position,
                'cpn': cpn,
                'ei': qs['ei'],
            })
            url = urllib.parse.urlunparse(parsed_url._replace(path='/api/stats/watchtime', query=urllib.parse.urlencode(nQs, True)))
            logger.debug(url)
            requests.get(url, cookies=self.cj)

    def garbageCollect(self):
        """
        Run garbage collection method
        """
        logger.info('listfetch.garbageCollect()')
        dir = '/videos/'
        now = time.time()

        for path in os.listdir(dir):
            if (not os.path.isfile(dir + path)):
                continue
            if (path[-9:] == 'README.md'):
                continue
            if (path[-3:] == 'jpg'):
                continue

            # check if file exists in model
            a = path.split('-')
            l = len(a)

            found = False
            for video in model.video.getItems():
                if (video.filename == a[l - 1]):
                    # found don't delete
                    found = True
                    break
            if (found):
                continue

            # check if old enough to delete
            days = (now - os.path.getmtime(dir + path)) / 86400
            if (days >= 7):
                logger.info(f'Removing file {path}, days={days}')
                os.remove(dir + path)

THREAD = ListFetchThread()

def fetchOnNextCycle():
    logger.debug('Setting _shouldFetch=True')
    THREAD._shouldFetch = True

def _runThread():
    THREAD.run()

def run():
    logger.debug('listfetch run()')
    t = threading.Thread(target=_runThread)
    t.start()

def close():
    logger.debug('listfetch close()')
    THREAD.close()