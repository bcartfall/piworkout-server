"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import server

import logging
logger = logging.getLogger('piworkout-server')

def receive(event, queue):
    """
    Send a simple reply with same uuid provided so that a client knows how long it takes the server to respond over the network
    """
    logger.debug('ping', event)
    server.send(queue, {
        'namespace': 'ping',
        'uuid': event['uuid'],
    })
