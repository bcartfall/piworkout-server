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
                    print('Error Refresh/Service: ' + str(re))
                except RetryError as e:
                    print('Error Retry: ' + str(re))
                except Exception as e:
                    print('Error exception: ' + str(e))
                    
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
        print('markWatched()')
        if (self.cj == None):
            print('cookiejar not set.')
            return
        
        # this is locked from run()
        with model.video.dataMutex():
            data = json.loads(video.watchedUrl)
            position = video.position

        keys = ['videostatsPlaybackUrl', 'videostatsWatchtimeUrl']
        for key in keys:
            item = data[key]
            is_full = item['is_full']
            
            # taken from yt_dlp
            parsed_url = urllib.parse.urlparse(item['url'])
            qs = urllib.parse.parse_qs(parsed_url.query)

            # cpn generation algorithm is reverse engineered from base.js.
            # In fact it works even with dummy cpn.
            CPN_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
            cpn = ''.join(CPN_ALPHABET[random.randint(0, 256) & 63] for _ in range(0, 16))

            qs.update({
                'ver': ['2'],
                'cpn': [cpn],
                'cmt': position,
                'el': 'detailpage',  # otherwise defaults to "shorts"
            })

            if is_full:
                # these seem to mark watchtime "history" in the real world
                # they're required, so send in a single value
                qs.update({
                    'st': 0,
                    'et': position,
                })
            
            url = urllib.parse.urlunparse(
                parsed_url._replace(query=urllib.parse.urlencode(qs, True)))
            requests.get(url, cookies=self.cj)
            #print(key, url)

    def garbageCollect(self):
        """
        Run garbage collection method
        """
        print('listfetch.garbageCollect()')
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
            for video in model.video.items():
                if (video.filename == a[l - 1]):
                    # found don't delete
                    found = True
                    break
            if (found):
                continue

            # check if old enough to delete
            days = (now - os.path.getmtime(dir + path)) / 86400
            if (days >= 7):
                print(f'Removing file {path}, days={days}')
                os.remove(dir + path)

THREAD = ListFetchThread()

def fetchOnNextCycle():
    print('Setting _shouldFetch=True')
    THREAD._shouldFetch = True

def _runThread():
    THREAD.run()

def run():
    print('listfetch run()')
    t = threading.Thread(target=_runThread)
    t.start()

def close():
    print('listfetch close()')
    THREAD.close()