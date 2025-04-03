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
import yt_dlp
import subprocess

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
            logger.info('markWatched() id=' + str(video.id))
            if (video.watchedUrl == ''):
                logger.info('  -- already marked as watched.')
                # already marked as watched
                return
            youtubeUrl = video.url
            data = json.loads(video.watchedUrl)
            position = video.position
            video_length = video.duration
            
            if (self.cj == None):
                logger.warning('cookiejar not set.')
                return
            
        # unset watchedUrl so it doesn't run more than once
        with model.video.dataMutex():
            video.watchedUrl = ''
            model.video.save(video, False)
        
        # run command yt-dlp to mark as watched
        # disable yt-dlp --mark-watched. We now use embeded youtube player to sync played times
        #subprocess.run(["yt-dlp", youtubeUrl, "--mark-watched", "--simulate", "--cookies=./db/cookies.txt"])
        
        return     
        # just run yt-dlp to mark as watched
        ydl_opts = {
            'outtmpl': '/videos/test.mkv',
            'mark_watched': True, # the mark watched func is overridden by the piworkoutpluginie plugin
            'cookiefile': './db/cookies.txt',
            'simulate': True,
        }

        # download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info('------------------------------- starting simulated download')
            ydl.download(youtubeUrl)
            # post processing has finished and thread is about to close
            # mark video as completed
            logger.info('------------------------------- completed')
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
            """
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
            """
        else:
            # send position
            playbackUrl = 'https://www.youtube.com/api/stats/playback?ns=yt&ver=2&cmt=0&final=1'
            p = urllib.parse.urlparse(playbackUrl)
            pQs = urllib.parse.parse_qs(p.query)
            pQs.update({
                'docid': qs['docid'], # Video Id
                'len': video_length,
                'st': position,
                'et': position,
                'cpn': cpn, # Client Playback Nonce, unique hash code for each query
                'ei': qs['ei'], # Event Id
                'vm': qs['vm'], # Visitor Monitoring?
                'of': qs['of'],
            })
            url = urllib.parse.urlunparse(p._replace(query=urllib.parse.urlencode(pQs, True)))
            logger.debug(url)
            requests.get(url, cookies=self.cj)
            
            watchUrl = 'https://www.youtube.com/api/stats/watchtime?ns=yt&ver=2&cmt=0&final=1'
            p = urllib.parse.urlparse(watchUrl)
            pQs = urllib.parse.parse_qs(p.query)
            pQs.update({
                'docid': qs['docid'], # Video Id
                'len': video_length,
                'st': position,
                'et': position,
                'cpn': cpn, # Client Playback Nonce, unique hash code for each query
                'ei': qs['ei'], # Event Id
            })
            url = urllib.parse.urlunparse(p._replace(query=urllib.parse.urlencode(pQs, True)))
            logger.debug(url)
            requests.get(url, cookies=self.cj)

    def garbageCollect(self):
        """
        Run garbage collection method
        """
        logger.info('listfetch.garbageCollect()')
        dir = '/videos/'
        now = time.time()
        videos = model.video.getItems()

        for path in os.listdir(dir):
            if (not os.path.isfile(dir + path)):
                continue
            if (path[-9:] == 'README.md'):
                continue
            #logger.debug(f'Checking {path}.')

            # check if file exists in model
            a = path.split('-')

            found = False
            for video in videos:
                if (str(video.id) == a[0]):
                    # found don't delete
                    #logger.debug(f'Found video.id {video.id}. Keeping {path}.')
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