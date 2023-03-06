"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import time

import model, server
from threads import listfetch

STATUS_STOPPED = 1
STATUS_PAUSED = 2
STATUS_PLAYING = 3
STATUS_ENDED = 4

class PlayerModel:
    time:float = 0
    videoId:int = 0
    status:int = 0
    client:str = '' # this client has control over the player, it will instruct other clients to play, pause, seek, etc
    action:str = ''
    
    #
    video = None
    lastWatched:int = 0
    
    def toString(self):
        return f'time={self.time},videoId={self.videoId},status={self.status},action={self.action}'

    def toObject(self):
        return {
            'time': self.time,
            'videoId': self.videoId,
            'status': self.status,
            'client': self.client,
            'action': self.action,
        }

MODEL = PlayerModel()

def data():
    return MODEL.toObject()    

def receive(event, queue):
    print('player', event)
    if (event['action']):
        MODEL.action = event['action']
        
        if (MODEL.video == None or MODEL.video.videoId != event['videoId']):
            # load video into memory
            MODEL.video = model.video.byId(event['videoId'], False)
            if (MODEL.video == None):
                print('Error: Video not found.')
                return
            
        
        if (event['action'] == 'progress' or event['action'] == 'seek'):
            MODEL.time = event['time']
            if (time.time() - MODEL.lastWatched >= 10):
                # 10 seconds have passed
                savePosition(event, updateDB=True, updateYT=True)
            elif (event['action'] == 'seek'):
                # just update position in memory
                savePosition(event, updateDB=False, updateYT=False)
        elif (event['action'] == 'play'):
            MODEL.client = event['source']
            MODEL.status = STATUS_PLAYING
            MODEL.videoId = event['videoId']
            MODEL.time = event['time']
        elif (event['action'] == 'pause'):
            savePosition(event, updateYT=True)
            MODEL.client = ''
            MODEL.status = STATUS_PAUSED
            MODEL.time = event['time']
        elif (event['action'] == 'ended'):
            savePosition(event, updateYT=True)
            MODEL.client = ''
            MODEL.status = STATUS_ENDED
        elif (event['action'] == 'stop'):
            savePosition(event, updateYT=True)
            MODEL.client = ''
            MODEL.status = STATUS_STOPPED
            MODEL.time = event['time']
            
        # broadcast player status to all other clients
        server.broadcast({
            'namespace': 'player',
            'player': data(),
        }, queue)

def savePosition(event, updateDB = True, updateYT = True):
    if (event['source'] == MODEL.client and MODEL.video != None):
        # update position for video in database
        with model.video.dataMutex():
            MODEL.video.position = event['time']
            if (event['action'] == 'ended'):
                MODEL.video.position = MODEL.video.duration
            if (updateDB):
                model.video.save(MODEL.video, False)
        # set watched position in youtube
        if (updateYT):
            markWatched()
        
def markWatched():
    MODEL.lastWatched = time.time()
    
    if (MODEL.video == None):
        return
    
    # send request to youtube
    if (model.settings.get('youtubeCookie', '') == ''):
        # no cookie set
        return
    
    # add to listfetch thread queue
    with listfetch.THREAD.queueMutex:
        listfetch.THREAD.markWatchedQueue.append(MODEL.video)
