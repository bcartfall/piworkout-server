"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import sqlite3
import threading
import time
import json
from dataclasses import dataclass
import google.oauth2.credentials
import googleapiclient.discovery
import googleapiclient.errors
from urllib.parse import urlparse, parse_qs
import requests
import yt_dlp
import re
import os
import http.cookiejar as cookielib

from threads import downloader, listfetch, sbgenerator
from namespaces import videos

#
STATUS_INIT = 1
STATUS_DOWNLOADING_VIDEO = 2
STATUS_DOWNLOADING_AUDIO = 3
STATUS_ENCODING = 4
STATUS_COMPLETE = 5
STATUS_DELETED = 6

db = sqlite3.connect('./db/database.sqlite3', check_same_thread=False) 
mutex = threading.Lock() # DB mutex

DEBUG = False # default False # set debug to true to delete the DB and redownload every video from the playlist

# initialize database
with mutex:
    if (DEBUG):
        db.execute('DROP TABLE videos')
    db.execute('CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY, `order` INT, videoId VARCHAR(255), source VARCHAR(255), url VARCHAR(255), filename VARCHAR(255), filesize INT, title VARCHAR(255), description TEXT, duration INT, position FLOAT, width INT, height INT, tbr INT, fps INT, vcodec VARCHAR(255), status INT, watchedUrl TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, name VARCHAR(255), value TEXT)')
    db.commit()
    
"""
# test downloading a specific video again
with mutex:
    db.execute('DELETE FROM videos WHERE id = 9')
    db.commit()
"""

# methods
def close():
    with mutex:
        db.close()

# models
class SettingsModel:
    _data = {
        'audioDelay': '0',
        'networkDelay': '0',
        'videoQuality': '1440p',
        'playlistUrl': 'https://',
        'youtubeCookie': '',
        'youtubeApiToken': '',
        'googleAPIKey': '',
    }
    _dataMutex = threading.Lock()

    def __init__(self, db, mutex):
        self._db = db
        self._mutex = mutex

        # load settings into memory
        with (self._mutex):
            cursor = self._db.cursor()
            cursor.execute('SELECT name, value FROM settings')
            rows = cursor.fetchall()
        with (self._dataMutex):
            for row in rows:
                self._data[row[0]] = row[1]
                
        # init: load cookie file (if exists)
        if (self.get('youtubeCookie', '') != ''):
            cj = cookielib.MozillaCookieJar('./db/cookies.txt')
            cj.load()
            with listfetch.THREAD.queueMutex:
                listfetch.THREAD.cj = cj

    def data(self, lock: bool = True):
        if (lock):
            self._dataMutex.acquire()
        res = self._data.copy()
        if (lock):
            self._dataMutex.release()
        return res

    def get(self, name: str, default: str = None):
        with self._dataMutex:
            if name in self._data:
                return self._data[name]
            else:
                return default

    def put(self, name: str, value: str):
        with self._dataMutex:
            if not name in self._data:
                return None
            self._data[name] = value

        with self._mutex:
            cursor = self._db.cursor()
            cursor.execute('SELECT id FROM settings WHERE name = ?', (name,))
            settingId = cursor.fetchone()
            if (settingId == None):
                cursor.execute('INSERT INTO settings (name, value) VALUES (?, ?)', (name, value,))
            else:
                cursor.execute('UPDATE settings SET value = ? WHERE id = ?', (value, settingId[0],))
            self._db.commit()
            return value

    def delete(self, name: str):
        with self._dataMutex:
            self._data[name] = ''
        with self._mutex:
            cursor = self._db.cursor()
            cursor.execute('DELETE FROM settings WHERE name = ?', (name,))
            self._db.commit()

settings = SettingsModel(db, mutex)

# videos
@dataclass
class VideoProgress:
    downloadedBytes: int = 0
    totalBytes: int = 0
    progress: float = 0
    eta: int = 0
    speed: float = 0
    elapsed: float = 0

    def toObject(self):
        return {
            'downloadedBytes': self.downloadedBytes,
            'totalBytes': self.totalBytes,
            'progress': self.progress,
            'eta': self.eta,
            'speed': self.speed,
            'elapsed': self.elapsed,
        }

@dataclass
class Video:
    id: int = 0
    order: int = 0
    videoId: str = ''
    source: str = '' # youtube or custom-upload
    url: str = ''
    filename: str = ''
    filesize: int = 0
    title: str = ''
    description: str = ''
    duration: int = 0
    position: float = 0
    width: int = 0
    height: int = 0
    tbr: int = 0
    fps: int = 0
    vcodec: str = ''
    status: int = 0
    watchedUrl: str = ''
    progress: VideoProgress = None

    # the following fields are only for cache and are only requested from YouTube when the video is played
    channelName: str = '',
    channelImageUrl: str = '',
    date: str = '',
    views: int = 0,
    likes: int = 0,
    rating: str = 'none',

    def toObject(self):
        if (self.progress):
            pObj = self.progress.toObject()
        else:
            pObj = None
        return {
            'id': int(self.id),
            'order': int(self.order),
            'videoId': str(self.videoId),
            'source': str(self.source),
            'url': str(self.url),
            'filename': str(self.filename),
            'filesize': int(self.filesize or 0),
            'title': str(self.title),
            'description': str(self.description),
            'duration': int(self.duration),
            'position': float(self.position),
            'width': int(self.width),
            'height': int(self.height),
            'tbr': int(self.tbr),
            'fps': int(self.fps),
            'vcodec': str(self.vcodec),
            'status': int(self.status),
            'progress': pObj,

            # additional
            'channelName': self.channelName,
            'channelImageUrl': self.channelImageUrl,
            'date': self.date,
            'views': self.views,
            'likes': self.likes,
            'rating': self.rating,
        }

class VideoModel:
    _items = []
    _dataMutex = threading.Lock()

    def __init__(self, db, mutex, settings):
        self._db = db
        self._mutex = mutex
        self._settings = settings

        if (DEBUG):
            with self._mutex:
                print('debug=True Deleting videos.')
                cursor = self._db.cursor()
                cursor.execute('DELETE FROM videos')
                self._db.commit()

        # load videos into memory
        with self._mutex:
            cursor = self._db.cursor()
            cursor.execute('SELECT id, `order`, videoId, source, url, filename, filesize, title, description, duration, position, width, height, tbr, fps, vcodec, status, watchedUrl FROM videos ORDER BY `order`')
            rows = cursor.fetchall()
        with self._dataMutex:
            for row in rows:
                video = Video(
                    id=int(row[0] or 0),
                    order=int(row[1] or 0),
                    videoId=row[2],
                    source=row[3],
                    url=row[4],
                    filename=row[5],
                    filesize=int(row[6] or 0),
                    title=row[7],
                    description=row[8],
                    duration=int(row[9] or 0),
                    position=float(row[10] or 0),
                    width=int(row[11] or 0),
                    height=int(row[12] or 0),
                    tbr=int(row[13] or 0),
                    fps=int(row[14] or 0),
                    vcodec=row[15],
                    status=int(row[16] or 0),
                    watchedUrl=str(row[17] or ''),
                    channelName='', 
                    channelImageUrl='', 
                    date='', 
                    likes=0, 
                    views=0, 
                    rating='None'
                )
                self._items.append(video)
                if (video.status == STATUS_INIT):
                    # add to downloader queue
                    downloader.THREAD.append(video)
                    
                if (not os.path.exists('/videos/' + str(video.id) + '-' + video.filename + '.sbb')):
                    # generate sb
                    sbgenerator.append(video)

                

    def data(self, copy:bool = True, lock:bool = True):
        if (lock):
            self._dataMutex.acquire()
        if (copy):
            res = self._items.copy()
        else:
            res = self._items
        if (lock):
            self._dataMutex.release()
        return res

    def dataMutex(self):
        return self._dataMutex

    def save(self, video: Video, lock: bool = True):
        """
        Save data to database
        """
        if (lock):
            self._dataMutex.acquire()
        with self._mutex:
            cursor = self._db.cursor()
            cursor.execute('UPDATE videos SET `order` = ?, videoId = ?, source=?, url = ?, filename = ?, filesize = ?, title = ?, description = ?, duration = ?, position = ?, width = ?, height = ?, tbr = ?, fps = ?, vcodec = ?, status = ?, watchedUrl = ? WHERE id = ?', (video.order, video.videoId, video.source, video.url, video.filename, video.filesize, video.title, video.description, video.duration, video.position, video.width, video.height, video.tbr, video.fps, video.vcodec, video.status, video.watchedUrl, video.id,))
            self._db.commit()
        if (lock):
            self._dataMutex.release()

    def remove(self, video: Video, lock: bool = True):
        if (lock):
            self._dataMutex.acquire()
        print('model.video().remove() removing id=' + str(video.id) + ', videoId=' + video.videoId)
        self._items.remove(video)
        for t in self._items:
            print('  id=' + str(t.id) + ', videoId=' + t.videoId)

        downloader.THREAD.remove(video) # remove from download queue

        with self._mutex:
            cursor = self._db.cursor()
            cursor.execute('DELETE FROM videos WHERE videoId = ?', (video.videoId,))
            self._db.commit()

        if (lock):
            self._dataMutex.release()


    def items(self):
        with self._dataMutex:
            return self._items.copy()

    def byVideoId(self, videoId: str, lock: bool = True):
        """
        Get video by videoId
        """
        if (lock):
            self._dataMutex.acquire()
        video = None
        for item in self._items:
            if (item.videoId == videoId):
                video = item
                break
        if (lock):
            self._dataMutex.release()
        return video

    def byId(self, id: int, lock: bool = True):
        """
        Get video by id
        """
        if (lock):
            self._dataMutex.acquire()
        video = None
        for item in self._items:
            if (item.id == id):
                video = item
                break
        if (lock):
            self._dataMutex.release()
        return video
    
    def getYouTube(self):
        """
        Get youtube API object
        """
        api_service_name = "youtube"
        api_version = "v3"
        youtube = None

        oauthToken = self._settings.get('youtubeApiToken', '')
        apiKey = self._settings.get('googleAPIKey', '')
        if (apiKey != ''):
            youtube = googleapiclient.discovery.build(
                api_service_name, api_version, developerKey=apiKey)
        elif (oauthToken != ''):
            # no credentials created yet
            data = json.loads(oauthToken)
            credentials = google.oauth2.credentials.Credentials(
                data['token'],
                refresh_token=data['refresh_token'],
                token_uri=data['token_uri'],
                client_id=data['client_id'],
                client_secret=data['client_secret'])
            youtube = googleapiclient.discovery.build(
                api_service_name, api_version, credentials=credentials)
        return youtube

    def fetch(self):
        """
        Fetch list from YouTube API.
        Throws: RefreshError, ServiceUnavailable, RetryError, Exception
        """
        print('model.video.fetch()')

        youtube = self.getYouTube()
            
        if (youtube == None):
            print('  no credentials created yet')
            return None

        # get playlistId
        playerlistUrl = self._settings.get('playlistUrl', '')
        if (playerlistUrl == ''):
            print('playlistUrl not set')
            return
            
        parsed = urlparse(playerlistUrl)
        if (parsed.scheme == ''):
            # just an ID
            playlistId = parsed.path
        else:
            qs = parse_qs(parsed.query)
            playlistId = qs['list'][0]

        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=50,
            playlistId=playlistId
        )
        response = request.execute()

        order = 0
        change = False
        # create video class
        # make sure youtube videos stay in order
        ytVideos = []

        for item in response['items']:
            #print(json.dumps(item))
            order = 0
            videoId = item['contentDetails']['videoId']
            url = f'https://www.youtube.com/watch?v={videoId}'

            with self._mutex:
                # check if exists in DB
                cursor = self._db.cursor()
                cursor.execute('SELECT id FROM videos WHERE videoId = ?', (videoId,))
                row = cursor.fetchone()
                if (row != None):
                    # found
                    print(f' Already exists videoId={videoId}')
                    ytVideos.append(self.byVideoId(videoId=videoId, lock=False))
                    continue

            # set video information
            with yt_dlp.YoutubeDL({}) as ydl:
                print('getting file information from youtube')
                info = ydl.extract_info(url, download = False)

                # ydl.sanitize_info makes the info json-serializable
                #print('------------------------------- dumping ydl info')
                # save info to file
                #print(json.dumps(ydl.sanitize_info(info)),  file=open('yt_dlp_video.json', 'w'))
                video = Video(
                    id=0, 
                    order=order, 
                    videoId=videoId, 
                    source='youtube', 
                    url=url, 
                    title=info.get('title'),
                    filename=re.sub('[^a-zA-Z0-9]', '_', info.get('title')) + '.' + info.get('ext'),
                    filesize=info.get('filesize_approx'),
                    description=info.get('description'),
                    duration=info.get('duration'),
                    position=0,
                    width=info.get('width'),
                    height=info.get('height'),
                    tbr=info.get('tbr'),
                    fps=info.get('fps'),
                    vcodec=info.get('vcodec'),
                    status=STATUS_INIT,
                    progress=None
                )

                thumbnailUrl = info.get('thumbnail')

            # save to DB
            ytVideos.append(video)
            change = True
            with self._mutex:
                # save to DB (if not exists)
                cursor = self._db.cursor()
                cursor.execute('INSERT INTO videos (videoId) VALUES (?)', (video.videoId,))
                video.id = cursor.lastrowid
                self._db.commit()
            self.save(video = video, lock = False)

            # save video thumbnail
            path = '/videos/' + str(video.id) + '-' + video.filename + '.jpg'
            if (not os.path.exists(path)):
                data = requests.get(thumbnailUrl).content
                f = open(path, 'wb')
                f.write(data)
                f.close()

            # add to items and add to downloader queue
            print(f' Adding videoId={video.videoId}')
            self._items.append(video)

            # add to downloader queue
            downloader.THREAD.append(video)

        # check for deleted youtube videos
        with self._dataMutex:
            for video in self._items.copy():
                if video.source != 'youtube':
                    continue
                found = False
                for cVideo in ytVideos:
                    if (cVideo.videoId == video.videoId):
                        found = True
                        break
                if (not found):
                    # delete
                    #print('  removing id=' + str(video.id) + ', videoId=' + video.videoId)
                    self.remove(video, False)
                    change = True
                
        # create a new array with all youtube source videos in order provided from playlist
        ytIndex = -1
        ytLength = len(ytVideos)
        nItems = []

        with self._dataMutex:
            for index, video in enumerate(self._items):
                if (video.source == 'youtube' and ytIndex < ytLength - 1):
                    ytIndex += 1

                    ytVideo = ytVideos[ytIndex]
                    nItems.append(ytVideo)
                    #print('yt add ' + str(ytVideo.id))
                    if (ytVideo.order != ytIndex):
                        # update order in DB
                        print(f'  Updating order of {ytVideo.videoId} to {ytIndex}.')
                        ytVideo.order = ytIndex
                        self.save(ytVideo, False)
                        change = True
                else:
                    nItems.append(video)
            self._items = nItems

        if (change):
            videos.broadcast()
        print('done fetch')

video = VideoModel(db, mutex, settings)