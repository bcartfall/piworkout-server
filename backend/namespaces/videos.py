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
    
    apiToken = model.settings.get('youtubeApiToken', '')
    if (apiToken == ''):
        # no credentials created yet
        print('  Error: no credentials created yet')
        return None
    data = json.loads(apiToken)

    credentials = google.oauth2.credentials.Credentials(
        data['token'],
        refresh_token=data['refresh_token'],
        token_uri=data['token_uri'],
        client_id=data['client_id'],
        client_secret=data['client_secret'])

    api_service_name = "youtube"
    api_version = "v3"

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

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
    request = youtube.videos().getRating(
        id=videoId
    )
    response = request.execute()
    item = response['items'][0]

    rating = item['rating']

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

    with model.video.dataMutex():
        server.send(queue, {
            'namespace': 'videos',
            'video': video.toObject(),
            'source': 'playerInformation',
        })

def putRating(event, queue):
    rating = event['rating']
    print('Submitting rating ' + str(event['id']) + ', rating=' + rating)
    with model.video.dataMutex():
        video = model.video.byId(event['id'], False)
        if (video == None):
            print(' Error: video not found.')
            return None
        videoId = video.videoId
        video.rating = rating
        model.video.save(video, False)
    
    apiToken = model.settings.get('youtubeApiToken', '')
    if (apiToken == ''):
        # no credentials created yet
        print('  Error: no credentials created yet')
        return None
    data = json.loads(apiToken)

    credentials = google.oauth2.credentials.Credentials(
        data['token'],
        refresh_token=data['refresh_token'],
        token_uri=data['token_uri'],
        client_id=data['client_id'],
        client_secret=data['client_secret'])

    api_service_name = "youtube"
    api_version = "v3"

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

    # send rating
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