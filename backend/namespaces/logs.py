"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import json

import model, server

import logging
logger = logging.getLogger('piworkout-server')

def receive(event, queue):
    logger.debug('logs event=' + json.dumps(event))
    
    if ('method' in event and event['method'] == 'GET'):
        # load all logs for videoId
        server.send(queue, {
            'namespace': 'logs',
            'items': model.log.getItems(event['videoId']),
        })
    else:
        # create log entry
        model.log.create({
            'video_id': event['videoId'],
            'action': event['action'],
            'data': event['data'],
        })