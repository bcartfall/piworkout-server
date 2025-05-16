"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import asyncio
import websockets
from websockets.legacy.server import serve
import json
import os
import sys
from queue import Queue, Empty
import yt_dlp
import yt_dlp.version

import model

from namespaces import settings, connect, videos, player, logs, routines, ping, file_upload, exercises

import logging
logger = logging.getLogger('piworkout-server')

CLIENTS = set()
MESSAGE_ID = 0

ytDlpVersion = yt_dlp.version.__version__
with yt_dlp.YoutubeDL() as ydl:
    ytDlpVersion = ytDlpVersion + ' (latest=' + yt_dlp.Updater(ydl)._get_version_info('latest')[0] + ')'


async def receiveJson(event, queue):
    """
    Handle message from client
    """
    if (not 'namespace' in event):
        logger.debug('namespace not found in message')
        return
    #if (event['namespace'] != 'up'):
    #    logger.debug(event)

    # handle message
    namespace = event['namespace']
    match namespace:
        case 'up':
            None # clients send frequently to get back messages
        case 'settings':
            settings.receive(event, queue)
        case 'connect':
            connect.receive(event, queue)
        case 'videos':
            videos.receive(event, queue)
        case 'player':
            player.receive(event, queue)
        case 'routines':
            routines.receive(event, queue)
        case 'logs':
            logs.receive(event, queue)
        case 'ping':
            ping.receive(event, queue)
        case 'exit':
            sys.exit() # restart application
        case _:
            logger.warning(f'  namespace {namespace} not handled.')

            
async def receiveBinary(binaryMessage, queue):
    # magic number (8), version (8), namespace (28) .... 
    magicNumber = binaryMessage[0:8]
    if (magicNumber != b'\x89webSOK\n'):
        logger.warn('Incoming binary message did not contain correct magicNumber.')
        return None
    
    #version = message[8:16].decode('ascii').rstrip('\x00')
    namespace = binaryMessage[16:44].decode('ascii').rstrip('\x00')
    match namespace:
        case 'file-upload':
            file_upload.binaryReceive(binaryMessage, queue)
        case 'exercises':
            exercises.binaryReceive(binaryMessage, queue)
        case _:
            logger.warning(f'  binary namespace {namespace} not handled.')


async def consumer_handler(websocket, queue):
    # receive messages
    try:
        async for message in websocket:
            jsonMessage = None
            binaryMessage = None
            try:
                # determine if a binary message
                if (message[0] == '{'):
                    # normal json message
                    jsonMessage = json.loads(message)
                else:
                    # binary message
                    binaryMessage = message
            except ValueError:
                logger.debug('Decoding json message has failed.')
                logger.debug(message)
            if (jsonMessage):
                await receiveJson(jsonMessage, queue)
            elif (binaryMessage):
                await receiveBinary(binaryMessage, queue)
                
            await asyncio.sleep(0.04)  # yield control to the event loop
    except websockets.exceptions.ConnectionClosed:
        logger.debug('  client disconnected early')

        
async def producer_handler(websocket, queue):
    # send messages
    try:
        while True:
            # get message from queue, block if not messages
            try:
                message = queue.get(False)
                await websocket.send(message)
                queue.task_done()
            except Empty:
                await asyncio.sleep(0.04)  # yield control to the event loop (tickrate 25fps)
    except websockets.exceptions.ConnectionClosed:
        logger.warning('Connecting closed while attempting to send.')

async def handler(websocket):
    logger.debug('Creating thread safe queue.')
    queue = Queue()
    CLIENTS.add(queue)
    logger.info('  client connected count=' + str(len(CLIENTS)))
    try:
        # send initial message
        obj = {
            'namespace': 'init',
            'data': {
                'settings': settings.data(),
                'connected': model.settings.get('youtubeApiToken', '') != '',
                'videos': videos.data(),
                'player': player.data(),
                'routines': routines.data(),
                'versions': {
                    'piworkoutServer': '1.0.0',
                    'ytDlp': ytDlpVersion,
                }
            },
        }
        
        try:
            queue.put(json.dumps(obj))
        except websockets.exceptions.ConnectionClosed:
            logger.debug('  client disconnected early')
        except:
            logger.error('  error sending init message')

        # receive messages / send messages
        consumer_task = asyncio.ensure_future(consumer_handler(websocket, queue))
        producer_task = asyncio.ensure_future(producer_handler(websocket, queue))
        done, pending = await asyncio.wait(
            [consumer_task, producer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        CLIENTS.remove(queue)
        logger.info('  client disconnected count=' + str(len(CLIENTS)))

def send(queue, obj):
    global MESSAGE_ID
    MESSAGE_ID += 1
    obj['messageId'] = MESSAGE_ID
    queue.put_nowait(json.dumps(obj))

def broadcast(obj, sender = None):
    """
    Send message to all users. If sender is specified do not send back to sender.
    """
    global MESSAGE_ID
    MESSAGE_ID += 1
    obj['messageId'] = MESSAGE_ID
    for queue in CLIENTS:
        if (sender == queue):
            continue
        queue.put_nowait(json.dumps(obj))


def start():
    host = os.environ['BACKEND_HOST']
    port = os.environ['BACKEND_PORT']
    
    start_server = serve(handler, host, port)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()