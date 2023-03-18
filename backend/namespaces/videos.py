"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import json
import google.oauth2.credentials
import googleapiclient.discovery
import googleapiclient.errors
import time
import requests

from threads import listfetch
import model, server

import logging
logger = logging.getLogger('piworkout-server')

def receive(event, queue):
    logger.info('videos', event)
    if (event['action']):
        if (event['action'] == 'refresh'):
            # Update all clients with full video list
            broadcast()
            listfetch.fetchOnNextCycle()
        elif (event['action'] == 'order'):
            # Change order of videos
            logger.debug('TODO Change Order') 
        elif (event['action'] == 'playerInformation'):
            # Get more information about video from youtube and update model
            getPlayerInformation(event, queue)
        elif (event['action'] == 'rate'):
            # Submit rating change
            putRating(event, queue)

def data():
    res = []
    logger.info('videos.data()')
    with model.video.dataMutex():
        for item in model.video.data(False, False):
            #logger.debug('  id=' + str(item.id) + ', videoId=' + item.videoId)
            res.append(item.toObject())
    return res

def getPlayerInformation(event, queue):
    logger.info('Getting more information about video ' + str(event['id']))
    with model.video.dataMutex():
        video = model.video.byId(event['id'], False)
        videoId = video.videoId
        if (video == None):
            logger.warning(' Error: video not found.')
            return None
        sponsorblock = video.sponsorblock
    
    youtube = model.video.getYouTube()
    if (youtube == None):
        # no credentials created yet
        logger.warning('  Error: no credentials created yet')
        return None

    # get video information
    request = youtube.videos().list(
        part="snippet,statistics",
        id=videoId
    )
    response = request.execute()
    item = response['items'][0]

    views = item['statistics']['viewCount']
    likes = item['statistics']['likeCount']
    date = item['snippet']['publishedAt'][0:10]
    title = item['snippet']['title']
    description = item['snippet']['description']

    # get channel information
    request = youtube.channels().list(
        part="snippet,statistics",
        id=item['snippet']['channelId']
    )
    response = request.execute()
    item = response['items'][0]

    channelName = item['snippet']['title']
    channelImageUrl = item['snippet']['thumbnails']['default']['url']

    # get rating information
    apiKey = model.settings.get('googleAPIKey', '')
    
    if (apiKey != ''):
        # api key
        rating = 'none'
    else:
        # oauth
        request = youtube.videos().getRating(
            id=videoId
        )
        response = request.execute()
        item = response['items'][0]

        rating = item['rating'] # like / dislike / none
        
    # get sponsorblock information (cache for a few hours)
    logger.debug('sponsorblock=', str(sponsorblock))
    if (sponsorblock == None or (sponsorblock and sponsorblock['expires_at'] < time.time())):
        # cache expired or sponsorblock not set
        sponsorblock = {
            'status': 200,
            'expires_at': time.time() + 10800, # 3 hours
            'segments': []
        }
        url = f'https://sponsor.ajay.app/api/skipSegments?videoID={videoId}'
        logger.debug(f'sponsorblock downloading from {url}')
        try:
            response = requests.get(url)
            status_code = response.status_code
            sponsorblock['status'] = status_code
            if (status_code != 200):
                logger.error(f'error getting sponsorblock information from api, status_code={status_code}')
                if (status_code != 404):
                    # try again next request if code is not 404
                    sponsorblock = None
            else:
                # [{"category":"sponsor","actionType":"skip","segment":[18.069,78.36],"UUID":"...","videoDuration":4050.241,"locked":0,"votes":0,"description":""}]
                sponsorblock['segments'] = response.json()
        except requests.exceptions.RequestException as e:
            sponsorblock = None
            logger.error(f'error getting sponsorblock information from api, url={url}, e={e}')
        except:
            sponsorblock = None
            logger.error(f'error getting sponsorblock information from api, url={url}, e=except')

    # update
    with model.video.dataMutex():
        video.views = views
        video.likes = likes
        video.date = date
        video.title = title
        video.description = description

        video.channelName = channelName
        video.channelImageUrl = channelImageUrl

        video.rating = rating
        video.sponsorblock = sponsorblock

        model.video.save(video, False)
        
    #logger.debug('  done getting information')

    with model.video.dataMutex():
        server.send(queue, {
            'namespace': 'videos',
            'video': video.toObject(),
            'source': 'playerInformation',
            'uuid': event['uuid'],
        })

def putRating(event, queue):
    rating = event['rating']
    logger.info('Submitting rating ' + str(event['id']) + ', rating=' + rating)
    
    apiKey = model.settings.get('googleAPIKey', '')
    with model.video.dataMutex():
        video = model.video.byId(event['id'], False)
        if (video == None):
            logger.error(' Error: video not found.')
            return None
        videoId = video.videoId
        if (apiKey == ''):
            video.rating = rating
        model.video.save(video, False)
    
    youtube = model.video.getYouTube()
    if (youtube == None):
        # no credentials created yet
        logger.warning('  Warning: no credentials created yet')
        
        return None
    
    if (apiKey == ''):
        # api key can't set rating
        # send rating (oauth)
        request = youtube.videos().rate(
            id=videoId,
            rating=rating
        )
        request.execute()

def broadcast():
    server.broadcast({
        'namespace': 'videos',
        'videos': data(),
    })