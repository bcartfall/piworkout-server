"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import urllib.parse
from googleapiclient.errors import HttpError
import time
import requests
import json
from urllib.parse import urlparse, parse_qs
from contextlib import suppress

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
            changeOrder(event, queue)
        elif (event['action'] == 'playerInformation'):
            # Get more information about video from youtube and update model
            getPlayerInformation(event, queue)
        elif (event['action'] == 'rate'):
            # Submit rating change
            putRating(event, queue)
        elif (event['action'] == 'remove'):
            # Remove video
            remove(event, queue)
        elif (event['action'] == 'add'):
            # Add video
            add(event, queue)

def data():
    res = []
    logger.info('videos.data()')
    with model.video.dataMutex():
        for item in model.video.data(False, False):
            #logger.debug('  id=' + str(item.id) + ', videoId=' + item.videoId)
            res.append(item.toObject())
    return res

def changeOrder(event, queue):
    logger.info('Changing order of video id=' + str(event['id']) + ' to index=' + str(event['index']))
    
    with model.video.dataMutex():
        oVideos = model.video.getItems(lock=False)
        nVideos = oVideos.copy()
        fromVideo = model.video.byId(event['id'], lock=False)
        toVideo = nVideos[event['index']]
        
        fromIndex = fromVideo.order
        toIndex = toVideo.order
        
    if (fromIndex == toIndex):
        logger.info('  no change in order')
        return None
    
    # update youtube playlist
    youtube = model.video.getYouTube(readonly=False)
            
    if (youtube == None):
        logger.warning('  no oauth credentials')
    else:
        try:
            request = youtube.playlistItems().update(
                part='snippet',
                body={
                    'id': fromVideo.playlistItemId,
                    'snippet': {
                        'playlistId': model.video.getPlaylistId(),
                        'position': toIndex,
                        'resourceId': {
                            'kind': 'youtube#video',
                            'videoId': fromVideo.videoId,
                        }
                    }
                }
            )
            
            request.execute()
        except:
            logger.error('  error updating youtube playlist api')
    
    # update memory model
    with model.video.dataMutex():
        nVideos[toIndex] = fromVideo
        inc = -1 if toIndex < fromIndex else 1
        
        # moving video
        nVideos[toIndex] = fromVideo
        fromVideo.order = toIndex
        model.video.save(fromVideo, lock=False)
        logger.debug(f'  moving {fromVideo.id} to index {toIndex}')
        
        # slide other videos to fill space
        for i in range(fromIndex, toIndex, inc):
            video = oVideos[i + inc]
            nVideos[i] = video
            video.order = i
            model.video.save(video, lock=False)
            logger.debug(f'  moving {video.id} to index {i}')
            
        model.video.setItems(nVideos, lock=False)
        
    # update (all) clients
    broadcast()
    
def remove(event, queue):
    logger.info('Removing video id=' + str(event['id']))
    
    removeVideo = model.video.byId(event['id'])
    if (removeVideo == None):
        # no video found
        return None
    
    if (removeVideo.source == 'youtube'):
        # remove from youtube
        youtube = model.video.getYouTube(readonly=False)
        if (youtube == None):
            logger.warning('  no oauth credentials')
        else:
            try:
                request = youtube.playlistItems().delete(
                    id=removeVideo.playlistItemId,
                )
                
                request.execute()
            except:
                logger.error('  error removing video from youtube playlist api')
    
    # remove from DB and memory model
    with model.video.dataMutex():
        videos = model.video.getItems(lock=False)
        for index, video in enumerate(videos):
            if (video.id == removeVideo.id):
                del videos[index] # splice(index, 1)
                break
        model.video.remove(removeVideo, lock=False)
        
    # update (all) clients
    broadcast()

def add(event, queue):
    """
    Add video
    """
    source = event['source']
    url = event['url']
    position = event['order'] or 0
    if (position < 0):
        position = 0
    
    logger.info(f'Adding video url={url}, source={source}')
    
    if (source == ''):
        # determine source
        # currently only parse youtube
        source = 'youtube'
    
    if (source == 'youtube'):
        videoId = get_yt_id(url, ignore_playlist=True)
        if (videoId == '' or videoId == None):
            logger.error('videoId not set.')
            return None
            
        logger.info(f'  Adding youtube videoId={videoId} to position {position}')
        
        try:
            youtube = model.video.getYouTube(readonly=False)
            
            if (youtube == None):
                logger.warning('  no oauth credentials')
                return None
            
            request = youtube.playlistItems().insert(
                part='snippet',
                body={
                    'snippet': {
                        'playlistId': model.video.getPlaylistId(),
                        'position': position,
                        'resourceId': {
                            'kind': 'youtube#video',
                            'videoId': videoId,
                        }
                    }
                }
            )
            response = request.execute()
        
            nVideo = model.video.createYoutubeVideo(videoId=videoId, playlistItemId=response['id'])
            
        except HttpError as err:
            logger.error(f'  Error adding video err.code={err.status_code} err.reason={err.reason}')
        except:
            logger.error('  Error adding video')
            return None
            
        # update DB and memory
        with model.video.dataMutex():
            index = 0
            videos = model.video.getItems(lock=False)
            nVideos = []
            
            for video in videos:
                if (index == position):
                    nVideo.order = index
                    nVideos.append(nVideo)
                    model.video.save(nVideo, lock=False)
                    index += 1
                elif (nVideo.id == video.id): 
                    continue
                
                if (video.order != index):
                    video.order = index
                    model.video.save(video, lock=False)
                index += 1
            
            model.video.setItems(nVideos, lock=False)
            
        # update list of videos
        broadcast()
        
    else:
        logger.error('Video source not handled.')

def getPlayerInformation(event, queue):
    logger.info('Getting more information about video ' + str(event['id']))
    with model.video.dataMutex():
        video = model.video.byId(event['id'], False)
        videoId = video.videoId
        if (video == None):
            logger.warning(' Error: video not found.')
            return None
        sponsorblock = video.sponsorblock
        source = video.source
    
    if (source != 'youtube'):
        return None
    
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
    if (sponsorblock != None):
        logger.debug('sponsorblock=' + str(sponsorblock))
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

def get_yt_id(url, ignore_playlist=False):
    # Examples:
    # - http://youtu.be/SA2iWivDJiE
    # - http://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
    # - http://www.youtube.com/embed/SA2iWivDJiE
    # - http://www.youtube.com/v/SA2iWivDJiE?version=3&amp;hl=en_US
    query = urlparse(url)
    if query.hostname == 'youtu.be': return query.path[1:]
    if query.hostname in {'www.youtube.com', 'youtube.com', 'music.youtube.com'}:
        if not ignore_playlist:
        # use case: get playlist id not current video in playlist
            with suppress(KeyError):
                return parse_qs(query.query)['list'][0]
        if query.path == '/watch': return parse_qs(query.query)['v'][0]
        if query.path[:7] == '/watch/': return query.path.split('/')[1]
        if query.path[:7] == '/embed/': return query.path.split('/')[2]
        if query.path[:3] == '/v/': return query.path.split('/')[2]
   # returns None for invalid YouTube url

def broadcast(sender = None):
    server.broadcast(obj={
        'namespace': 'videos',
        'videos': data(),
    }, sender=sender)
