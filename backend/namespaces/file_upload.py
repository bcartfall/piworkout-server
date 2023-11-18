"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-03-23
 * See README.md
"""

import struct
import os
import ffmpeg
import threading
import re
import ffmpeg
import tempfile
import time
import subprocess
from PIL import Image

import server
import model
from namespaces import videos

import logging
logger = logging.getLogger('piworkout-server')

fp = None
cUuid = ''

def binaryReceive(message, queue):
    """
    Handle file uploads from desktop client
    """
    global fp, cUuid
    
    I = struct.Struct('<I') # unsigned 4 bytes integer little-endian
    #Q = struct.Struct('<Q') # unsigned 8 bytes long little-endian
    
    uuid = message[44:80].decode('ascii').rstrip('\x00')
    action = message[80:88].decode('ascii').rstrip('\x00')
    
    path = '/videos/.' + uuid + '.video'
    
    if (action == 'cmpt'):
        # complete
        cUuid = ''
        fp.close()
        strLen = I.unpack(message[88:92])[0]
        videoName = message[92:(92 + strLen)].decode('ascii').rstrip('\x00')
        
        t = threading.Thread(target=threadCreateVideo, args=(videoName, uuid))
        t.start()
        return None
        
    elif (action != 'store'):
        logger.error('Unhandled action = ' + action)
    
    
    part = I.unpack(message[88:92])[0]
    #start = I.unpack(message[92:96])[0]
    length = I.unpack(message[96:100])[0]
    #total = Q.unpack(message[100:108])[0]
    
    logger.debug('file_upload len=' + str(len(message)) + ', action=' + action + ', part=' + str(part))
    
    #print(part, start, length, total)
    
    if (uuid != cUuid):
        # starting new upload
        fp = open(path, 'wb')
        cUuid = uuid
    
    buffer = message[108:(length + 108)]
    #print('writting ' + str(len(buffer)) + ' bytes')
    fp.write(buffer)    


def threadCreateVideo(videoName, uuid):
    """
    Create video and convert to correct format
    """
    # get information about video
    path = '/videos/.' + uuid + '.video'
    logger.info(path)
    streams = ffmpeg.probe(path)['streams']
    
    found = False
    for stream in streams:
        if (stream['codec_type'] == 'video'):
            found = True
            bit_rate = round(float(stream['bit_rate']) * 0.001) # KBit/s
            duration = round(float(stream['duration']))
            width = stream['width']
            height = stream['height']
            
            a = stream['avg_frame_rate'].split('/')
            fps = round(int(a[0]) / int(a[1]))
            break
        
    if (not found):
        logger.warning('ffprobe did not find video stream information')
        return None
    
    logger.info('Adding video ' + videoName + '.')
    
    newFilename = re.sub('[^a-zA-Z0-9]', '_', videoName) + '.mp4'
            
    video = model.Video(
        id=0, 
        order=0, 
        videoId='', 
        source='file-upload', 
        url='',
        title=videoName.rsplit('.', 1)[0], # strip extension from filename
        filename=newFilename,
        filesize=os.path.getsize(path),
        description='',
        duration=duration,
        position=0,
        width=width,
        height=height,
        tbr=bit_rate,
        fps=fps,
        vcodec='h264',
        status=model.STATUS_ENCODING,
        progress=None,
    )
    
    model.video.insert(video)
    model.video.save(video)
    
    newPath = '/videos/' + str(video.id) + '-upload-' + video.filename
    
    logger.debug('  Creating thumbnail image.')
    thumbPath = '/videos/' + str(video.id) + '-' + newFilename + '.jpg'
    if (os.path.exists(thumbPath)):
        os.remove(thumbPath)
    ffmpeg.input(path, ss='00:00:15').filter('scale', 320, -1).output(thumbPath, vframes=1).run()
    
    # add to list and update order of all videos
    with model.video.dataMutex():
        list = model.video.getItems(lock=False)
        nList = []
        nList.append(video)
        
        index = 1
        for tVideo in list:
            tVideo.order = index
            index += 1
            model.video.save(tVideo, lock=False)
            nList.append(tVideo)
        model.video.setItems(nList, lock=False)
    
    videos.broadcast()
    
    logger.debug('  Converting video to webm.')
    try:
        video.progress = model.VideoProgress()
        video.progress.totalBytes = video.filesize
        
        with ProgressFfmpeg(duration, on_progress, video) as progress:
            #-vcodec libx264 -acodec aac
            (ffmpeg
                .input(path)
                .output(newPath, **{'vcodec': 'libx264', 'acodec': 'aac'})
                .global_args('-progress', progress.output_file.name)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
    except ffmpeg.Error as e:
        logger.error(e.stderr)
        
    with model.video.dataMutex():
        video.status = model.STATUS_COMPLETE
        video.progress = None
        model.video.save(video, lock=False)
        
    videos.broadcast()
    
    # generate sb on every keyframe 160x90, BIG images should be 10 by 10 (1600x900)
    logger.debug('  Creating story board binary (sbb).')
    tmpFolder = '/tmp/sb-file-upload/'
    def cleanUp(tmpFolder):
        if not os.path.exists(tmpFolder):
            os.makedirs(tmpFolder)

        for tPath in os.listdir(tmpFolder):
            if (not os.path.isfile(tmpFolder + tPath)):
                continue
            os.remove(tmpFolder + tPath)
    cleanUp(tmpFolder)
    
    sbbWidth = 160
    sbbHeight = 90
    sbbRows = 10
    sbbColumns = 10
    sbbDelay = 10000
    cmd = ['ffmpeg', '-i', newPath, '-threads', '2', '-r', str(1 / (sbbDelay / 1000)), '-s', str(sbbWidth) + 'x' + str(sbbHeight), tmpFolder + '%08d.png']
    logger.debug(cmd)
    subprocess.call(cmd, stderr=subprocess.DEVNULL)
    
    # combine small images into BIG images
    files = []
    for tPath in os.listdir(tmpFolder):
        if (not os.path.isfile(tmpFolder + tPath)):
            continue
        files.append(tmpFolder + tPath)
    files.sort()
    images = []
    durations = []
    
    def createImage(buffer, tPath, width, height, rows, columns):
        bImage = Image.new('RGB', (width * columns, height * rows))
        x = 0
        y = 0
        for file in buffer:
            img = Image.open(file)
            bImage.paste(img, (x * width, y * height))
            x += 1
            if (x >= columns):
                x = 0
                y += 1
        bImage.save(tPath)
        return tPath
    
    buffer = []
    l = 0
    m = sbbRows * sbbColumns
    for file in files:
        buffer.append(file)
        l += 1
        
        if (l >= m):
            images.append(createImage(buffer, tmpFolder + str(len(images)) + '.jpg', sbbWidth, sbbHeight, sbbRows, sbbColumns))
            durations.append(l * sbbDelay / 1000)
            l = 0
            buffer = []
    if (l > 0):
        images.append(createImage(buffer, tmpFolder + str(len(images)) + '.jpg', sbbWidth, sbbHeight, sbbRows, sbbColumns))
        durations.append(l * sbbDelay / 1000)
    
    # build sbb file
    I = struct.Struct('<I') # unsigned 4 bytes integer little-endian
    d = struct.Struct('<d') # binary float double
    
    sbbPath = '/videos/' + str(video.id) + '-' + newFilename + '.sbb'
    if (os.path.exists(sbbPath)):
        os.remove(sbbPath)
    fp = open(sbbPath, 'wb')
    
    # magic number (0, 8 bytes)
    fp.write(bytearray([0x53, 0x54, 0x4F, 0x52, 0x59, 0x73, 0x62, 0x1a]))
    
    # version (8, 4 bytes)
    fp.write(I.pack(0))
    
    # image count (12, 4 bytes) (number of BIG storyboard images)
    count = len(images)
    fp.write(I.pack(count))
    
    # width (16, 4 bytes) (width of smaller images)
    fp.write(I.pack(sbbWidth))

    # height (20, 4 bytes) (height of smaller images)
    fp.write(I.pack(sbbHeight))

    # fps (24, 8 bytes) (fps for each image frame [smaller image]) (e.g. fps of 0.1 would mean a small image every 10s)
    sbbFps = 1000 / sbbDelay # 1 every 10s
    fp.write(d.pack(sbbFps))

    # rows (32, 4 bytes) (rows in a BIG storyboard image)
    rows = 10
    fp.write(I.pack(sbbRows))

    # columns (36, 4 bytes) (cols in a BIG storyboard image)
    columns = 10
    fp.write(I.pack(sbbColumns))
    
    # reserved for future expansion (40-64)
    ba = bytearray()
    for i in range(40, 64):
        ba.append(0x00)
    fp.write(ba)
    
    # write the index (64, 20 bytes per index)
    offset = 64 + (20 * count) + 20 # start of image data
    for index, imagePath in enumerate(images):
        #logger.debug('creating index ' + str(imagePath))
        fp.write(I.pack(index)) # 4 bytes (index of this BIG storyboard image)
        fp.write(I.pack(offset)) # 4 bytes (position of binary image data for BIG image)
        
        size = os.path.getsize(imagePath)
        offset += size
        
        fp.write(I.pack(size)) # 4 bytes, (length of bytes of BIG image data)
        fp.write(d.pack(durations[index])) # 8 bytes (64bit float for duration of this BIG story board image)
        
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
    cleanUp(tmpFolder)
    
    logger.debug('  Removing tmp file.')
    os.remove(path)
    
    
def on_progress(progress, video):
    logger.debug('encoding progress =' + str(progress))
    with model.video.dataMutex():
        video.progress.progress = progress
        
    # send progress to all clients
    server.broadcast({
        'namespace': 'videos',
        'video': video.toObject(),
        'source': 'fileUpload',
    })
    
## --------------------------- FFMpeg Progres ---------------------------
class ProgressFfmpeg(threading.Thread):
    def __init__(self, vid_duration_seconds, progress_update_callback, video):
        threading.Thread.__init__(self, name='ProgressFfmpeg')
        self.stop_event = threading.Event()
        self.output_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        self.vid_duration_seconds = vid_duration_seconds
        self.progress_update_callback = progress_update_callback
        self.video = video

    def run(self):

        while not self.stop_event.is_set():
            latest_progress = self.get_latest_ms_progress()
            if latest_progress is not None:
                completed_percent = latest_progress / self.vid_duration_seconds
                self.progress_update_callback(completed_percent, self.video)
            time.sleep(1)

    def get_latest_ms_progress(self):
        lines = self.output_file.readlines()

        if lines:
            for line in lines:
                if 'out_time_ms' in line:
                    out_time_ms = line.split('=')[1]
                    return int(out_time_ms) / 1000000.0
        return None

    def stop(self):
        self.stop_event.set()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.stop()    