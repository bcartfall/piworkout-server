"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-03-03
 * See README.md
"""

import threading
import time
import os
import subprocess
import struct
import yt_dlp
import json
import requests
import shutil

import model

import logging
logger = logging.getLogger('piworkout-server')

INTERVAL=5000 # time between storyboard images in ms - used for deprecated bif generator

class SBGeneratorThread:
    _running = True
    generateQueue = []
    queueMutex = threading.Lock()

    def run(self):
        while (self._running):
            video = None
            with self.queueMutex:
                if (len(self.generateQueue) > 0):
                    video = self.generateQueue.pop(0)
            if (video != None):
                self._generateSB(video)
            time.sleep(1)
            
    def close(self):
        self._running = False
        
        
    def _generateSB(self, video):
        with model.video.dataMutex():
            id = video.id
            filename = video.filename
            url = video.url
            
        # check if sb file already exists
        sbbPath = '/videos/' + str(id) + '-' + filename + '.sbb'
        if (os.path.exists(sbbPath)):
            logger.debug('video ' + str(id) + ' already has sb file.')
            return
            
        logger.info('generating sb for id=' + str(id) + ', filename=' + filename)
        
        tmpFolder = '/tmp/sb/'
        
        self._clean('sb')
        
        # get information for sb0
        ydl_opts = {
            'verbose': False,
            'format': 'sb0',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.debug('getting information from ytdlp')
            info = ydl.extract_info(url, download = False)
            #logger.debug(json.dumps(ydl.sanitize_info(info)), file=open('yt_dlp_video.json', 'w'))
            
            found = False
            for format in info.get('formats'):
                if (format['format_id'] == 'sb0'):
                    found = True
                    # fetch all images in format['fragments'] to tmp
                    # and generate special .sb file.
                    #logger.debug(json.dumps(format),  file=open('yt_dlp_video.json', 'w'))
                    
                    width = int(format['width'])
                    height = int(format['height'])
                    fps = float(format['fps']) # double
                    rows = int(format['rows'])
                    columns = int(format['columns'])
                    
                    durations = []
                    images = []
                    fCount = len(format['fragments'])
                    for index, fragment in enumerate(format['fragments']):
                        durations.append(float(fragment['duration'])) # double
                        imagePath = tmpFolder + str(index + 1).zfill(8) + '.webp'
                        
                        logger.debug('Downloading fragment ' + str(index + 1) + '/' + str(fCount))
                        res = requests.get(fragment['url'], stream = True)
                        if res.status_code == 200:
                            images.append(imagePath)
                            with open(imagePath, 'wb') as f:
                                shutil.copyfileobj(res.raw, f)
                        else:
                            logger.error('Fragment download failed.')
                    
                    # create sbb file
                    with open(sbbPath, 'wb') as fp:
                        logger.info('Generating sbb file ' + sbbPath)
                        I = struct.Struct('<I') # unsigned 4 bytes integer little-endian
                        d = struct.Struct('<d') # binary float double
                        
                        # magic number (0, 8 bytes)
                        fp.write(bytearray([0x53, 0x54, 0x4F, 0x52, 0x59, 0x73, 0x62, 0x1a]))
                        
                        # version (8, 4 bytes)
                        fp.write(I.pack(0))
                        
                        # image count (12, 4 bytes)
                        count = len(images)
                        fp.write(I.pack(count))
                        
                        # width (16, 4 bytes)
                        fp.write(I.pack(width))
                
                        # height (20, 4 bytes)
                        fp.write(I.pack(height))

                        # fps (24, 8 bytes)
                        fp.write(d.pack(fps))

                        # rows (32, 4 bytes)
                        fp.write(I.pack(rows))

                        # columns (36, 4 bytes)
                        fp.write(I.pack(columns))
                        
                        # reserved for future expansion (40-64)
                        ba = bytearray()
                        for i in range(40, 64):
                            ba.append(0x00)
                        fp.write(ba)
                        
                        # write the index (64, 20 bytes per index)
                        offset = 64 + (20 * count) + 20 # start of image data
                        for index, imagePath in enumerate(images):
                            #logger.debug('creating index ' + str(imagePath))
                            fp.write(I.pack(index)) # 4 bytes
                            fp.write(I.pack(offset)) # 4 bytes
                            
                            size = os.path.getsize(imagePath)
                            offset += size
                            
                            fp.write(I.pack(size)) # 4 bytes
                            fp.write(d.pack(durations[index])) # 8 bytes
                            
                        # terminate index
                        fp.write(bytearray([0xff, 0xff, 0xff, 0xff])) # bytes
                        fp.write(I.pack(offset)) # 4 bytes
                        fp.write(I.pack(0)) # 4 bytes
                        fp.write(d.pack(0)) # 8 bytes
                        
                        # write the image data
                        for imagePath in images:
                            #logger.debug('writing data ' + str(imagePath))
                            with open(imagePath, 'rb') as imagefp:
                                while True:
                                    buffer = imagefp.read(65536)
                                    if (not buffer):
                                        break
                                    fp.write(buffer)
                        logger.debug('Done generating sbb file ' + sbbPath)
                    
            if (not found):
                logger.error('sb0 not found for video id ' + id)
                       
        # cleanup
        self._clean('sb')
    
    """ generate bif file
    @deprecated We just pull the story from yt-dlp and create a custom sbb filer
    """
    def _generateBif(self, video):
        with model.video.dataMutex():
            id = video.id
            filename = video.filename
        logger.info('generating bif for ' + filename)
        
        fullFilename = '/videos/' + str(id) + '-1080p-' + filename
        
        tmpFolder = '/tmp/biff/'
        self._clean('biff')
            
        # generate jpg images every 10s
        cmd = ['ffmpeg', '-i', fullFilename, '-threads', '2', '-r', str(1 / (INTERVAL / 1000)), '-s', '320x180', tmpFolder + '%08d.jpg']
        logger.debug(cmd)
        subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        files = []
        for path in os.listdir(tmpFolder):
            if (not os.path.isfile(tmpFolder + path)):
                continue
            files.append(tmpFolder + path)
        files.sort()
        
        # create a bif file from images
        # see https://developer.roku.com/en-ca/docs/developer-program/media-playback/trick-mode/bif-file-creation.md
        bifFilename = '/videos/' + str(id) + '-' + filename + '.bif'
        
        fp = open(bifFilename, 'wb')
        
        I = struct.Struct('<I') # unsigned 4 bytes integer little-endian
        
        # magic number (0, 8 bytes)
        fp.write(bytearray([0x89, 0x42, 0x49, 0x46, 0x0d, 0x0a, 0x1a, 0x0a]))
        
        # version (8, 4 bytes)
        fp.write(I.pack(0))
        
        # image count (12, 4 bytes)
        count = len(files)
        fp.write(I.pack(count))
        
        # framewise separation: interval in ms (16, 4 bytes)
        b = I.pack(INTERVAL)
        fp.write(I.pack(INTERVAL))
        
        # reserved for future expansion
        ba = bytearray()
        for i in range(20, 64):
            ba.append(0x00)
        fp.write(ba)
               
        # write the bif index (64)
        index = 0
        offset = 64 + (8 * count) + 8
        for file in files:
            fp.write(I.pack(index))
            fp.write(I.pack(offset))
            
            size = os.path.getsize(file)
            offset += size
            
            index += 1
            
        # terminate index
        fp.write(bytearray([0xff, 0xff, 0xff, 0xff]))
        fp.write(I.pack(offset))
               
        # data section: write all image data sequentially
        for file in files:
            with open(file, 'rb') as imagefp:
                while True:
                    buffer = imagefp.read(65536)
                    if (not buffer):
                        break
                    fp.write(buffer)
        
        fp.close()
        
        self._clean('biff')
        logger.info('done generating bif: ' + bifFilename)
        
    def _clean(self, folder):
        # clear tmp folder
        tmpFolder = '/tmp/' + folder + '/'
        
        if not os.path.exists(tmpFolder):
            os.makedirs(tmpFolder)
        
        for path in os.listdir(tmpFolder):
            if (not os.path.isfile(tmpFolder + path)):
                continue
            os.remove(tmpFolder + path)
        
THREAD = SBGeneratorThread()

def append(video):
    with THREAD.queueMutex:
        THREAD.generateQueue.append(video)

def _runThread():
    THREAD.run()

def run():
    logger.debug('sbgenerator run()')
    t = threading.Thread(target=_runThread)
    t.start()

def close():
    logger.debug('sbgenerator close()')
    THREAD.close()