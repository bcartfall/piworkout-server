"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import model
import json
import time
import datetime
import math
import http.cookiejar as cookielib

from threads import listfetch
import server

import logging
logger = logging.getLogger('piworkout-server')

# keys that can be saved from settings form
KEYS = ['audioDelay', 'networkDelay', 'videoQuality', 'playlistUrl', 'youtubeCookie', 'googleAPIKey']

def data():
    obj = {}
    data = model.settings.data()
    for key in KEYS:
        if (key in data):
            obj[key] = data[key]
        else:
            obj[key] = ''
    return obj

def receive(event, queue):
    if (event['method'] == 'PUT'):
        logger.info('updating settings')
        for key in event['data']:
            if key in KEYS:
                value = event['data'][key]
                model.settings.put(key, event['data'][key])

        # convert youtube copy and pasted cookie to a format yt-dlp understands
        if event['data']['youtubeCookie'].strip() != '':
            cookies = event['data']['youtubeCookie'].split('\n')
            f = open('./db/cookies.txt', 'w')

            f.write('# Netscape HTTP Cookie File\n')
            line = 0
            for cookie in cookies:
                line += 1
                try:
                    a = cookie.split('\t')
                    name = a[0]
                    value = a[1]
                    domain = a[2]
                    path = a[3]
                    expiration = a[4]
                    httpOnly = a[5]
                    if (name == ''):
                        continue
                    if (domain[0] != '.'):
                        domain = '.' + domain
                    if (httpOnly == '✓'):
                        httpOnly = 'TRUE'
                    else:
                        httpOnly = 'FALSE'
                    if (expiration == 'Session'):
                        date = datetime.datetime.today() + datetime.timedelta(days=1)
                    else:
                        date = datetime.datetime.fromisoformat(expiration)
                    expiration = math.floor(datetime.datetime.timestamp(date))
                    
                    f.write('\t'.join([domain, 'TRUE', path, httpOnly, str(expiration), name, value]) + '\n')
                except:
                    logger.warning(f'exception in converting cookie on line {line}')
            f.close()
            
            # update listfetch cookiejar
            cj = cookielib.MozillaCookieJar('./db/cookies.txt')
            cj.load()
            with listfetch.THREAD.queueMutex:
                listfetch.THREAD.cj = cj

        # send updating settings to all clients
        obj = {
            'namespace': 'settings',
            'settings': data(),
        }
        server.broadcast(obj, queue)
