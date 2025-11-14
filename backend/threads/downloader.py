"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import threading
import time
import threading
import time
import yt_dlp
import os
import shlex

import model, server
from threads import sbgenerator

import logging
logger = logging.getLogger('piworkout-server')

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
        progress = 0.0
        totalBytes = 0
        
        # store progress in memory for other calls
        shouldBroadcast = False
        now = time.time()
        elapsed = now - self._lastUpdate
        if (elapsed >= 0.1 and self._step < 1):
            shouldBroadcast = True
            
        #logger.debug('----' + d['status'])
        if d['status'] == 'finished':
            shouldBroadcast = True
            self._totalBytesEstimate = 0
            self._step += 1
            if (self._step == 2):
                logger.debug('---------- finished audio')
                self._currentVideo.status = model.STATUS_ENCODING # atomic
            else:
                logger.debug('---------- finished video')
                self._currentVideo.status = model.STATUS_DOWNLOADING_AUDIO # atomic
        elif d['status'] == 'downloading':
            totalBytes = d.get("total_bytes")
            if (totalBytes == None):
                est = int(d.get('total_bytes_estimate') or 0)
                if (est > self._totalBytesEstimate):
                    self._totalBytesEstimate = est
                totalBytes = self._totalBytesEstimate
            # determine progress
            self._currentVideo.status = model.STATUS_DOWNLOADING_VIDEO # atomic

        # send update
        if (shouldBroadcast):
            with model.video.dataMutex():
                self._currentVideo.progress.downloadedBytes = d.get('downloaded_bytes')
                self._currentVideo.progress.totalBytes = totalBytes
                if (totalBytes > 0):
                    progress = previousWeight + (d.get('downloaded_bytes') / totalBytes * weight)
                    #logger.debug('-- progress=' + str(progress))
                    self._currentVideo.progress.progress = progress
                self._currentVideo.progress.eta = d.get('eta')
                self._currentVideo.progress.speed = d.get('speed')
                self._currentVideo.progress.elapsed = d.get('elapsed')
                videoObject = self._currentVideo.toObject()
            
            logger.debug('---------- progress_hook called threadId=' + str(threading.get_native_id()) + ', progress=' + ("{:.4f}".format(progress)) + ', ' + str(d.get('downloaded_bytes')) + '/' + str(totalBytes) + ', status=' + d['status'] + ', filename=' + d['filename'] + ', weight=' + str(weight) + ', previousWeight=' + str(previousWeight) + ', speed=' + str(d.get('speed')))
            # n updates per second
            self._lastUpdate = now
            server.broadcast({
                'namespace': 'videos',
                'video': videoObject,
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
            logger.info('downloading next item from queue ' + str(self._currentVideo.videoId))
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
                logger.error(msg)
                pass

        # prepare download options
        match (videoQuality):
            case '4K': 
                bestHeight = 2160
                self._formats = [
                    {
                        'weight': 0.85,
                        'height': 2160,
                        'name': '4K',
                        'format_sort': ['res:2160'],
                    },
                    {
                        'weight': 0.15,
                        'height': 1080,
                        'name': '1080p',
                        'format_sort': ['vcodec:avc', 'res:1080', 'acodec:aac'], # support iOS
                    },
                ]
            case '1440p':
                bestHeight = 1440
                self._formats = [
                    {
                        'weight': 0.65,
                        'height': 1440,
                        'name': '1440p',
                        'format_sort': ['res:1440'],
                    },
                    {
                        'weight': 0.35,
                        'height': 1080,
                        'name': '1080p',
                        'format_sort': ['vcodec:avc', 'res:1080', 'acodec:aac'], # support iOS
                    },
                ]
            case '1080p':
                bestHeight = 1080
                self._formats = [
                    {
                        'weight': 1.0,
                        'height': 1080,
                        'name': '1080p',
                        'format_sort': ['vcodec:avc', 'res:1080', 'acodec:aac'], # support iOS
                    },
                ]
            case '720p':
                bestHeight = 720
                self._formats = [
                    {
                        'weight': 1.0,
                        'height': 720,
                        'name': '720p',
                        'format_sort': ['vcodec:avc', 'res:720', 'acodec:aac'], # support iOS
                    },
                ]
                
        #logger.debug('/videos/' + str(self._currentVideo.id) + '-' + self._currentVideo.filename)

        for format in self._formats:
            logger.debug('Downloading format ' + format['name'] + ', videoId=' + str(self._currentVideo.videoId))
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
                'format_sort': format['format_sort'],
                #'mark_watched': True, # the mark watched func is overridden by the piworkoutpluginie plugin and the data is saved to the video model
                'cookiefile': './db/cookies.txt',
                #'postprocessors': [ # sponsorblock now handled with player directly
                #    {'key': 'SponsorBlock'},
                #    {'key': 'ModifyChapters', 'remove_sponsor_segments': ['sponsor', 'preview']}
                #], #'sponsorblock_remove': ['sponsor', 'preview'],
            }

            # get user options
            ytDlpArgv = model.settings.get('ytDlpArgv').strip()
            if (ytDlpArgv):
                # Example: Parse options from a command-line-like string
                # Split the string into argv list (handle quoted strings if needed; simple split works for basic cases)
                argv = shlex.split(ytDlpArgv)

                # Parse the arguments
                user_opts = yt_dlp.parse_options(argv)

                # add to options
                ydl_opts = user_opts.ydl_opts | ydl_opts

            # download
            logger.debug('Downloading with options: ' + str(ydl_opts))
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info('------------------------------- starting download')
                ydl.download(url)

                # post processing has finished and thread is about to close
                # mark video as completed
                logger.info('------------------------------- completed')
                
            model.log.create({
                'video_id': id,
                'action': 'onDownloaded',
                'data': str(id) + '-' + format['name'] + '-' + filename
            })

            # yt-dlp will force .mp4 extension if container is an mp4 (e.g. filename.webm.mp4)
            # this conflicts with our database where each resolution needs to have the same filename format
            # rename mp4 to proper extension (yt-dlp)
            fullFile = '/videos/' + str(id) + '-' + format['name'] + '-' + filename
            if os.path.isfile(fullFile + '.mp4'):
                os.rename(fullFile + '.mp4', fullFile)
            if os.path.isfile(fullFile + '.webm'):
                os.rename(fullFile + '.webm', fullFile)
            if os.path.isfile(fullFile + '.mkv'):
                os.rename(fullFile + '.mkv', fullFile)
                
            # set time of file to now
            now = time.time()
            logger.debug('setting time of file ' + fullFile)
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
    logger.debug('downloader run()')
    t = threading.Thread(target=_runThread)
    t.start()

def close():
    logger.debug('downloader close()')
    THREAD.close()