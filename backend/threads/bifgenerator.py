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

import model

INTERVAL=5000 # time between storyboard images in ms

class BifGeneratorThread:
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
                self._generate(video)
            time.sleep(1)
            
    def close(self):
        self._running = False
        
    def _generate(self, video):
        with model.video.dataMutex():
            id = video.id
            filename = video.filename
        print('generating bif for ' + filename)
        
        fullFilename = '/videos/' + str(id) + '-1080p-' + filename
        
        tmpFolder = '/tmp/biff/'
        
        self._clean()
            
        # generate jpg images every 10s
        cmd = ['ffmpeg', '-i', fullFilename, '-threads', '2', '-r', str(1 / (INTERVAL / 1000)), '-s', '320x180', tmpFolder + '%08d.jpg']
        print(cmd)
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
        
        self._clean()
        print('done generating bif: ' + bifFilename)
        
    def _clean(self):
        # clear tmp folder
        tmpFolder = '/tmp/biff/'
        
        if not os.path.exists(tmpFolder):
            os.makedirs(tmpFolder)
        
        for path in os.listdir(tmpFolder):
            if (not os.path.isfile(tmpFolder + path)):
                continue
            os.remove(tmpFolder + path)
        
THREAD = BifGeneratorThread()

def append(video):
    with THREAD.queueMutex:
        THREAD.generateQueue.append(video)

def _runThread():
    THREAD.run()

def run():
    print('bifgenerator run()')
    t = threading.Thread(target=_runThread)
    t.start()

def close():
    print('bifgenerator close()')
    THREAD.close()