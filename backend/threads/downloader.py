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
from threads import sbgenerator

class DownloaderThread:
    _running = True
    _mutex = threading.Lock() # lock with mutex every time self._queue is manipulated
    _queue = [] # queue of videos to download
    _currentVideo = None # current video that is downloading
    _lastUpdate = 0 # only update progress at specific intervals
    _step = 0 # 0 = video, 1 = audio
    _totalBytesEstimate = 0
    _currentFormat = None
    _previousWeight = 0
    _formats = []
    _simulate = False # set to True to simulate the animation and websocket updates of video downloading

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
        previousWeight = self._previousWeight
        weight = self._currentFormat['weight']
        
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
                self._totalBytesEstimate = 0
                self._step += 1
                if (self._step == 2):
                    print('---------- finished audio')
                    self._currentVideo.status = model.STATUS_ENCODING
                else:
                    print('---------- finished video')
                    self._currentVideo.status = model.STATUS_DOWNLOADING_AUDIO
            elif d['status'] == 'downloading':
                totalBytes = d.get("total_bytes")
                if (totalBytes == None):
                    est = int(d.get('total_bytes_estimate') or 0)
                    if (est > self._totalBytesEstimate):
                        self._totalBytesEstimate = est
                    totalBytes = self._totalBytesEstimate
                print('---------- progress_hook called threadId=' + str(threading.get_native_id()) + ', ' + str(d.get('downloaded_bytes')) + '/' + str(totalBytes) + ', status=' + d['status'] + 
                    ', filename=' + d['filename'] + ', weight=' + str(weight) + ', previousWeight=' + str(previousWeight) + ', speed=' + str(d.get('speed')))
                
                # determine progress
                self._currentVideo.status = model.STATUS_DOWNLOADING_VIDEO
                
                self._currentVideo.progress.downloadedBytes = d.get('downloaded_bytes')
                self._currentVideo.progress.totalBytes = totalBytes
                if (totalBytes > 0):
                    progress = previousWeight + (d.get('downloaded_bytes') / totalBytes * weight)
                    print('-- progress=' + str(progress))
                    self._currentVideo.progress.progress = progress
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
            self._previousWeight = 0
            url = self._currentVideo.url
            print('downloading next item from queue', self._currentVideo.videoId)
            id = self._currentVideo.id
            filename = self._currentVideo.filename
            
            # downgrade video quality setting until it matches maximum height of video
            videoQuality = model.settings.get('videoQuality')
            if (self._currentVideo.height < 2160 and videoQuality == '4K'):
                videoQuality = '1440p'
            if (self._currentVideo.height < 1440 and videoQuality == '1440p'):
                videoQuality = '1080p'
            if (self._currentVideo.height < 1080 and videoQuality == '1080p'):
                videoQuality = '720p'
            
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
        match (videoQuality):
            case '4K': 
                bestHeight = 2160
                self._formats = [
                    {
                        'weight': 0.625,
                        'height': 2160,
                        'name': '4K',
                    },
                    {
                        'weight': 0.25,
                        'height': 1440,
                        'name': '1440p',
                    },
                    {
                        'weight': 0.125,
                        'height': 1080,
                        'name': '1080p',
                    },
                ]
            case '1440p':
                bestHeight = 1440
                self._formats = [
                    {
                        'weight': 0.65,
                        'height': 1440,
                        'name': '1440p',
                    },
                    {
                        'weight': 0.35,
                        'height': 1080,
                        'name': '1080p',
                    },
                ]
            case '1080p':
                bestHeight = 1080
                self._formats = [
                    {
                        'weight': 1.0,
                        'height': 1080,
                        'name': '1080p',
                    },
                ]
            case '720p':
                bestHeight = 720
                self._formats = [
                    {
                        'weight': 1.0,
                        'height': 720,
                        'name': '720p',
                    },
                ]
                
        #print('/videos/' + str(self._currentVideo.id) + '-' + self._currentVideo.filename)

        for format in self._formats:
            self._lastUpdate = 0
            self._step = 0 # reset step back to video
            self._totalBytesEstimate = 0
            self._currentFormat = format            
            # https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py
            ydl_opts = {
                'verbose': True,
                'logger': dlp_logger(),
                'progress_hooks': [self._dlp_progress_hook],
                'outtmpl': '/videos/' + str(id) + '-' + format['name'] + '-' + filename, # was '%(title)s.%(ext)s'
                #'throttledratelimit': 1500,
                'format_sort': ['res:' + str(format['height'])], # force resolution
                'mark_watched': True, # the mark watched func is overridden by the piworkoutpluginie plugin and the data is saved to the video model
                'cookiefile': './db/cookies.txt',
                #'postprocessors': [ # sponsorblock now handled with player directly
                #    {'key': 'SponsorBlock'},
                #    {'key': 'ModifyChapters', 'remove_sponsor_segments': ['sponsor', 'preview']}
                #], #'sponsorblock_remove': ['sponsor', 'preview'],
            }

            # download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print('------------------------------- starting download')
                ydl.download(url)
                # post processing has finished and thread is about to close
                # mark video as completed
                print('------------------------------- completed')
                
            # set time of file to now
            now = time.time()
            fullFile = '/videos/' + str(id) + '-' + format['name'] + '-' + filename
            os.utime(fullFile, (now, now))
            
            self._previousWeight += format['weight']

        with model.video.dataMutex():
            # determine width and height from best format
            width = self._currentVideo.width
            height = self._currentVideo.height
            
            if (height > bestHeight):
                # resize
                ratio = height / bestHeight
                height = bestHeight
                width = width / ratio
            
            self._currentVideo.status = model.STATUS_COMPLETE
            fullFilename = '/videos/' + str(id) + '-' + self._formats[0]['name'] + '-' + filename
            self._currentVideo.filesize = os.path.getsize(fullFilename)
            self._currentVideo.progress = None
            self._currentVideo.width = width
            self._currentVideo.height = height
            model.video.save(self._currentVideo, False)
            
            # generate storyboard
            if (not os.path.exists('/videos/' + str(id) + '-' + filename + '.sbb')):
                sbgenerator.append(self._currentVideo)

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