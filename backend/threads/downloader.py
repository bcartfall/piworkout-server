"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import threading
import time
import requests
import threading
import time
import yt_dlp
import re
import random
import json
import os

import model, server
from namespaces import videos

class DownloaderThread:
    _running = True
    _mutex = threading.Lock() # lock with mutex every time self._queue is manipulated
    _queue = [] # queue of videos to download
    _currentVideo = None # current video that is downloading
    _lastUpdate = 0 # only update progress at specific intervals
    _step = 0 # 0 = video, 1 = audio
    _simulate = False

    def run(self):
        while (self._running):
            time.sleep(0.033) # 30hz

            # simulate file downloading
            if (self._simulate):
                videos = model.video.data()
                videos[1].position += 1
                if (videos[1].position > videos[1].duration):
                    videos[1].position = 1
                server.broadcast({
                        'namespace': 'videos',
                        'video': videos[1].toObject(),
                        'source': 'progressHook',
                    })

            with self._mutex:
                l = len(self._queue)

            if (l > 0):
                self._download()

    # progress_hook for yt-dlp
    # see progress_hooks at https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L191
    def _dlp_progress_hook(self, d):
        print('------------------------------- progress_hook called '+ str(d.get('downloaded_bytes')) + '/' + str(d.get('total_bytes')) + ', status=' + d['status'] + ', filename=' + d['filename'])
        # store progress in memory for other calls
        with model.video.dataMutex():
            shouldBroadcast = False
            now = time.time()
            elapsed = now - self._lastUpdate
            if (elapsed >= 0.1 and self._step < 1):
                shouldBroadcast = True
            
            #print('----' + d['status'])
            if d['status'] == 'finished':
                shouldBroadcast = True
                self._step += 1
                if (self._step == 2):
                    print('------------------------------- finished audio')
                    self._currentVideo.status = model.STATUS_ENCODING
                else:
                    print('------------------------------- finished video')
                    self._currentVideo.status = model.STATUS_DOWNLOADING_AUDIO
            elif d['status'] == 'downloading':
                self._currentVideo.status = model.STATUS_DOWNLOADING_VIDEO
                self._currentVideo.progress.downloadedBytes = d.get('downloaded_bytes')
                self._currentVideo.progress.totalBytes = d.get('total_bytes')
                self._currentVideo.progress.eta = d.get('eta')
                self._currentVideo.progress.speed = d.get('speed')
                self._currentVideo.progress.elapsed = d.get('elapsed')
                #print(self._currentVideo.progress)

            # send update
            if (shouldBroadcast):
                # 10 updates per second
                self._lastUpdate = now
                server.broadcast({
                    'namespace': 'videos',
                    'video': self._currentVideo.toObject(),
                    'source': 'progressHook',
                })

    def _download(self):
        # this will keep the thread busy until the video is downloaded
        with self._mutex:
            # remove top item from queue
            self._currentVideo = self._queue.pop(0)

        with model.video.dataMutex():
            self._currentVideo.progress = model.VideoProgress()
            url = self._currentVideo.url
            print('downloading next item from queue', self._currentVideo.videoId)
            id = self._currentVideo.id
            filename = self._currentVideo.filename

        # catch output
        class dlp_logger:
            def debug(self, msg):
                # For compatibility with youtube-dl, both debug and info are passed into debug
                # You can distinguish them by the prefix '[debug] '
                if msg.startswith('[debug] '):
                    self.info(msg)
                    pass
                else:
                    self.info(msg)
                    pass

            def info(self, msg):
                pass

            def warning(self, msg):
                pass

            def error(self, msg):
                print(msg)
                pass

        # prepare download options
        match (model.settings.get('videoQuality')):
            case '4K': 
                resolution = '2160'
            case '1440p':
                resolution = '1440'
            case '1080p':
                resolution = '1080'
            case '720p':
                resolution = '720'

        #print('/videos/' + str(self._currentVideo.id) + '-' + self._currentVideo.filename)

        self._lastUpdate = 0
        self._step = 0 # reset step back to video
        # https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py
        ydl_opts = {
            'verbose': True,
            'logger': dlp_logger(),
            'progress_hooks': [self._dlp_progress_hook],
            'outtmpl': '/videos/' + str(id) + '-' + filename, # was '%(title)s.%(ext)s'
            #'throttledratelimit': 1500,
            'format_sort': ['res:' + resolution], # force resolution
            'mark_watched': True,
            'cookiefile': './db/cookies.txt',
            'sponsorblock_remove': ['sponsor', 'preview'],
        }

        # download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print('------------------------------- starting download')
            ydl.download(url)
            # post processing has finished and thread is about to close
            # mark video as completed
            print('------------------------------- completed')

        with model.video.dataMutex():
            # set time of file to now
            now = time.time()
            fullFile = '/videos/' + str(id) + '-' + filename
            os.utime(fullFile, (now, now))

            self._currentVideo.status = model.STATUS_COMPLETE
            self._currentVideo.filesize = os.path.getsize(fullFile)
            self._currentVideo.progress = None
            model.video.save(self._currentVideo, False)

            # broadcast video complete
            server.broadcast({
                'namespace': 'videos',
                'video': self._currentVideo.toObject()
            })

        # download is done
        with self._mutex:
            self._currentVideo = None

    def append(self, video):
        """
        Add video to download queue
        """
        with self._mutex:
            self._queue.append(video)

    def remove(self, video):
        """
        Remove video from queue
        """
        with self._mutex:
            if (video in self._queue):
                self._queue.remove(video)

    def close(self):
        self._running = False

THREAD = DownloaderThread()

def _runThread():
    THREAD.run()

def run():
    print('downloader run()')
    t = threading.Thread(target=_runThread)
    t.start()

def close():
    print('downloader close()')
    THREAD.close()