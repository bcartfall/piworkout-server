"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import json
import google.oauth2.credentials
import googleapiclient.discovery
import googleapiclient.errors

from threads import listfetch
import model, server

def receive(event, queue):
    print('videos', event)
    if (event['action']):
        if (event['action'] == 'refresh'):
            # Update all clients with full video list
            broadcast()
            listfetch.fetchOnNextCycle()
        elif (event['action'] == 'order'):
            # Change order of videos
            print('TODO Change Order') 
        elif (event['action'] == 'playerInformation'):
            # Get more information about video from youtube and update model
            getPlayerInformation(event, queue)
        elif (event['action'] == 'rate'):
            # Submit rating change
            putRating(event, queue)

def data():
    res = []
    print('videos.data()')
    with model.video.dataMutex():
        for item in model.video.data(False, False):
            #print('  id=' + str(item.id) + ', videoId=' + item.videoId)
            res.append(item.toObject())
    return res

def getPlayerInformation(event, queue):
    print('Getting more information about video ' + str(event['id']))
    with model.video.dataMutex():
        video = model.video.byId(event['id'], False)
        videoId = video.videoId
        if (video == None):
            print(' Error: video not found.')
            return None
    
    youtube = model.video.getYouTube()
    if (youtube == None):
        # no credentials created yet
        print('  Error: no credentials created yet')
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

        model.video.save(video, False)
        
    #print('  done getting information')

    with model.video.dataMutex():
        server.send(queue, {
            'namespace': 'videos',
            'video': video.toObject(),
            'source': 'playerInformation',
        })

def putRating(event, queue):
    rating = event['rating']
    print('Submitting rating ' + str(event['id']) + ', rating=' + rating)
    
    apiKey = model.settings.get('googleAPIKey', '')
    with model.video.dataMutex():
        video = model.video.byId(event['id'], False)
        if (video == None):
            print(' Error: video not found.')
            return None
        videoId = video.videoId
        if (apiKey == ''):
            video.rating = rating
        model.video.save(video, False)
    
    youtube = model.video.getYouTube()
    if (youtube == None):
        # no credentials created yet
        print('  Error: no credentials created yet')
        
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