"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import model, server

STATUS_STOPPED = 1
STATUS_PAUSED = 2
STATUS_PLAYING = 3
STATUS_ENDED = 4

MODEL = {
    'time': 0,
    'videoId': 0,
    'status': 0,
}

class PlayerModel:
    time:float = 0
    videoId:int = 0
    status:int = 0
    client:str = '' # this client has control over the player, it will instruct other clients to play, pause, seek, etc

    def toString(self):
        return f'time={self.time},videoId={self.videoId},status={self.status}'

    def toObject(self):
        return {
            'time': self.time,
            'videoId': self.videoId,
            'status': self.status,
        }

MODEL = PlayerModel()

def receive(event, queue):
    print('player', event)
    if (event['action']):
        if (event['action'] == 'progress'):
            MODEL.time = event['time']
        elif (event['action'] == 'play'):
            MODEL.client = event['source']
            MODEL.status = STATUS_PLAYING
            MODEL.videoId = event['videoId']
        elif (event['action'] == 'pause'):
            savePosition(event)
            MODEL.client = ''
            MODEL.status = STATUS_PAUSED
        elif (event['action'] == 'ended'):
            savePosition(event)
            MODEL.client = ''
            MODEL.status = STATUS_ENDED
        elif (event['action'] == 'stop'):
            savePosition(event)
            MODEL.client = ''
            MODEL.status = STATUS_STOPPED
            
        # broadcast player status to all other clients
        server.broadcast({
            'namespace': 'player',
            'player': MODEL.toObject(),
        }, queue)

def savePosition(event):
    if (event['source'] == MODEL.client):
        # update position for video in database
        with model.video.dataMutex():
            video = model.video.byId(event['videoId'], False)
            if (video == None):
                print('Error: Video not found.')
                return
            video.position = event['time']
            if (event['action'] == 'ended'):
                video.position = video.duration
            model.video.save(video, False)