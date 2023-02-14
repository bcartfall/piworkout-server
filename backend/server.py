"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import asyncio
import websockets
import json
import os
import threading

import model

from namespaces import settings, connect, videos, player, ping

CLIENTS = set()
MUTEX = threading.Lock()
MESSAGE_ID = 0

async def receive(event, queue):
    """
    Handle message from client
    """
    assert(event['namespace'])
    #print(event)

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
        case 'ping':
            ping.receive(event, queue)
        case _:
            print(f'  namespace {namespace} not handled.')

async def relay(queue, websocket):
    while True:
        # todo Implement custom logic based on queue.qsize() and
        # websocket.transport.get_write_buffer_size() here.
        message = await queue.get()
        await websocket.send(message)

async def handler(websocket):
    queue = asyncio.Queue()
    relay_task = asyncio.create_task(relay(queue, websocket))
    CLIENTS.add(queue)
    print('  client connected count=' + str(len(CLIENTS)))
    try:
        # send initial message
        obj = {
            'namespace': 'init',
            'data': {
                'settings': settings.data(),
                'connected': model.settings.get('youtubeApiToken', '') != '',
                'videos': videos.data(),
            },
        }

        send(queue, obj)

        # receive messages
        async for message in websocket:
            await receive(json.loads(message), queue)
    finally:
        CLIENTS.remove(queue)
        relay_task.cancel()
        print('  client disconnected count=' + str(len(CLIENTS)))

def send(queue, obj):
    global MESSAGE_ID
    with MUTEX:
        MESSAGE_ID += 1
        obj['messageId'] = MESSAGE_ID
        queue.put_nowait(json.dumps(obj))

def broadcast(obj, sender = None):
    """
    Send message to all users. If sender is specified do not send back to sender.
    """
    global MESSAGE_ID
    with MUTEX:
        MESSAGE_ID += 1
        obj['messageId'] = MESSAGE_ID
        for queue in CLIENTS:
            if (sender == queue):
                continue
            queue.put_nowait(json.dumps(obj))


async def main():
    host = os.environ['BACKEND_HOST']
    port = os.environ['BACKEND_PORT']
    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # run forever

def start():
    asyncio.run(main())