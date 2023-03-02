"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import threading
import time
import model
import os
import glob

class ListFetchThread:
    _running = True
    _shouldFetch = True
    _gcCounter = 60
    _wait = 60 # check every 60 seconds
    _mutex = threading.Lock()

    def run(self):
        start = time.time()
        while (self._running):
            elapsed = time.time() - start
                
            if (elapsed > self._wait or self._shouldFetch):
                self._shouldFetch = False
                start = time.time() # reset timer

                model.video.fetch()
                self._gcCounter += 1
                if (self._gcCounter >= 60):
                    self._gcCounter = 0
                    self.garbageCollect()
            
            time.sleep(0.033) # 30hz

    def close(self):
        self._running = False

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
                os.remove(dir + path + '.jpg')

THREAD = ListFetchThread()

def fetchOnNextCycle():
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