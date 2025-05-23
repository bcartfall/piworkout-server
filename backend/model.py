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
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
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

import logging
logger = logging.getLogger('piworkout-server')

#
STATUS_INIT = 1
STATUS_DOWNLOADING_VIDEO = 2
STATUS_DOWNLOADING_AUDIO = 3
STATUS_ENCODING = 4
STATUS_COMPLETE = 5
STATUS_DELETED = 6

db = sqlite3.connect('./db/database.sqlite3', check_same_thread=False)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

db.row_factory = dict_factory

mutex = threading.Lock() # DB mutex

DEBUG = False # default False # set debug to true to delete the DB and redownload every video from the playlist

# initialize database
with mutex:
    #db.execute('DROP TABLE routines')
    if (DEBUG):
        db.execute('DROP TABLE videos')
    db.execute('CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY, `order` INT, videoId VARCHAR(255), source VARCHAR(255), url VARCHAR(255), filename VARCHAR(255), filesize INT, title VARCHAR(255), description TEXT, duration INT, position FLOAT, width INT, height INT, tbr INT, fps INT, vcodec VARCHAR(255), status INT, watchedUrl TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, name VARCHAR(255), value TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, video_id INTEGER, action VARCHAR(255), data TEXT, created_at INT)')
    db.execute('CREATE TABLE IF NOT EXISTS routines (id INTEGER PRIMARY KEY, `order` INTEGER, name VARCHAR(255), description TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS exercises (id INTEGER PRIMARY KEY, routineId INTEGER, `order` INT, name VARCHAR(255), tooltip TEXT, image VARCHAR(255), description TEXT, video_url TEXT)')
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
        'ytMarkWatchedHost': '',
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
                self._data[row['name']] = row['value']
                
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
                cursor.execute('UPDATE settings SET value = ? WHERE id = ?', (value, settingId['id'],))
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

# routines
@dataclass
class Exercise:
    id: int = 0
    rotuineId: int = 0,
    order: int = 0
    name: str = ''
    tooltip: str = ''
    image: str = ''
    description: str = ''
    video_url: str = ''
    
    def toObject(self):
        return {
            'id': int(self.id),
            'rotuineId': int(self.rotuineId),
            'order': int(self.order),
            'name': str(self.name),
            'tooltip': str(self.name),
            'image': str(self.name),
            'description': str(self.name),
            'video_url': str(self.name),
        }

@dataclass
class Routine:
    id: int = 0
    order: int = 0
    name: str = ''
    description: str = ''
    exercises: list[Exercise] = None
    
    def toObject(self):
        a = []
        for item in self.exercises:
            a.append(item.toObject())
        
        return {
            'id': int(self.id),
            'order': int(self.order),
            'name': str(self.name),
            'description': str(self.name),
            'exercises': a,
        }
        
class RoutineModel:
    _items = []
    _dataMutex = threading.Lock()

    def __init__(self, db, mutex, settings):
        self._db = db
        self._mutex = mutex
        self._settings = settings

        # load routines and exercises into memory
        with self._mutex:
            cursor = self._db.cursor()
            cursor.execute('SELECT id, `order`, name, description FROM routines ORDER BY `order`')
            rows = cursor.fetchall()
        with self._dataMutex:
            for row in rows:
                routine = Routine(
                    id=int(row['id'] or 0),
                    order=int(row['order'] or 0),
                    name=row['name'],
                    description=row['description'],
                    exercises=[],
                )
                self._items.append(routine)
                
            with self._mutex:
                rows2 = cursor.execute('SELECT id, `order`, name, tooltip, image, description, video_url FROM exercises ORDER BY `order`')
            for row in rows2:
                exercise = Exercise(
                    id=int(row['id'] or 0),
                    order=int(row['order'] or 0),
                    name=row['name'],
                    tooltip=row['tooltip'],
                    image=row['image'],
                    description=row['description'],
                    video_url=row['video_url']
                )
                routine.exercises.append(exercise)
            rows = cursor.fetchall()

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
    
    def insert(self, routine: Routine):
        with self._mutex:
            # save to DB (if not exists)
            cursor = self._db.cursor()
            cursor.execute('INSERT INTO routines (name) VALUES ("")')
            routine.id = cursor.lastrowid
            logger.debug('Inserted routine into DB id=' + str(routine.id))
            self._db.commit()
            self._items.append(routine)
            
    def insertExercise(self, routine: Routine, exercise: Exercise):
        with self._mutex:
            # save to DB (if not exists)
            cursor = self._db.cursor()
            cursor.execute('INSERT INTO exercises (rotuineId) VALUES (?)', (routine.id,))
            exercise.id = cursor.lastrowid
            logger.debug('Inserted exercise into DB id=' + str(exercise.id))
            routine.exercises.append(exercise)
            self._db.commit()

    def save(self, routine: Routine, lock: bool = True):
        """
        Save routine data to database
        """
        if (lock):
            self._dataMutex.acquire()
        with self._mutex:
            cursor = self._db.cursor()
            cursor.execute('UPDATE routines SET `order` = ?, name = ?, description = ? WHERE id = ?', (routine.order, routine.name, routine.description, routine.id,))
            self._db.commit()
        if (lock):
            self._dataMutex.release()
            
    def saveExercise(self, routine: Routine, exercise: Exercise, lock: bool = True):
        """
        Save exercise data to database
        """
        if (lock):
            self._dataMutex.acquire()
        with self._mutex:
            cursor = self._db.cursor()
            cursor.execute('UPDATE exercises SET routineId = ?, `order` = ?, name = ?, tooltip = ?, image = ?, description = ?, video_url = ? WHERE id = ?', (exercise.routineId, exercise.order, exercise.name, exercise.tooltip, exercise.image, exercise.description, exercise.video_url, exercise.id,))
            self._db.commit()
        if (lock):
            self._dataMutex.release()

    def remove(self, routine: Routine, lock: bool = True):
        if (lock):
            self._dataMutex.acquire()
        logger.debug('model.routine().remove() removing id=' + str(routine.id))
        try:
            self._items.remove(routine)
        except:
            pass
            
        for t in self._items:
            logger.debug('  id=' + str(t.id))

        with self._mutex:
            cursor = self._db.cursor()
            # delete routine and exercises records
            cursor.execute('DELETE FROM exercises WHERE routineId = ?', (routine.id,))
            cursor.execute('DELETE FROM routines WHERE id = ?', (routine.id,))
            self._db.commit()

        if (lock):
            self._dataMutex.release()

    def removeExercise(self, routine: Routine, exercise: Exercise, lock: bool = True):
        if (lock):
            self._dataMutex.acquire()
        logger.debug('model.routine().removeExercise() removing id=' + str(exercise.id))
        try:
            routine.remove(exercise)
        except:
            pass
            
        with self._mutex:
            cursor = self._db.cursor()
            # delete exercise record
            cursor.execute('DELETE FROM exercises WHERE id = ?', (exercise.id,))
            self._db.commit()

        if (lock):
            self._dataMutex.release()

    def getItems(self, lock: bool = True):
        if (lock):
            self._dataMutex.acquire()
        items = self._items.copy()
        if (lock):
            self._dataMutex.release()
        return items
    
    def setItems(self, items, lock: bool = True):
        """
        Update list of videos
        """
        if (lock):
            self._dataMutex.acquire()
        self._items = items
        if (lock):
            self._dataMutex.release()
            
    def debugItems(self):
        print('DEBUG printing all routines in memory')
        items = self.getItems(lock=False)
        for item in items:
            print('DEBUG', f'id={item.id}, url={item.name}')

    def byId(self, id: int, lock: bool = True):
        """
        Get routine by id
        """
        if (lock):
            self._dataMutex.acquire()
        routine = None
        for item in self._items:
            #print('== ', item.id, id)
            if (item.id == id):
                routine = item
                break
        if (lock):
            self._dataMutex.release()
        return routine
    
routines = RoutineModel(db, mutex, settings)

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
    sponsorblock: dict | None = None,
    playlistItemId: str = '',
    
    @staticmethod
    def createFromRow(row):
        video = Video(
            id=int(row['id'] or 0),
            order=int(row['order'] or 0),
            videoId=row['videoId'],
            source=row['source'],
            url=row['url'],
            filename=row['filename'],
            filesize=int(row['filesize'] or 0),
            title=row['title'],
            description=row['description'],
            duration=int(row['duration'] or 0),
            position=float(row['position'] or 0),
            width=int(row['width'] or 0),
            height=int(row['height'] or 0),
            tbr=int(row['tbr'] or 0),
            fps=int(row['fps'] or 0),
            vcodec=row['vcodec'],
            status=int(row['status'] or 0),
            watchedUrl=str(row['watchedUrl'] or ''),
            channelName='', # no saved in db # see namespaces/videos::getPlayerInformation
            channelImageUrl='', 
            date='', 
            likes=0, 
            views=0, 
            rating='None',
            sponsorblock=None,
            playlistItemId='',
        )
        return video

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
            'sponsorblock': self.sponsorblock,
            'playlistItemId': self.playlistItemId,
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
                logger.debug('debug=True Deleting videos.')
                cursor = self._db.cursor()
                cursor.execute('DELETE FROM videos')
                self._db.commit()

        # load videos into memory
        with self._mutex:
            cursor = self._db.cursor()
            cursor.execute('SELECT id, `order`, videoId, source, url, filename, filesize, title, description, duration, position, width, height, tbr, fps, vcodec, status, watchedUrl FROM videos ORDER BY `order`')
            rows = cursor.fetchall()
            columns = cursor.description
        with self._dataMutex:
            for row in rows:
                video = Video.createFromRow(row)                
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
    
    def insert(self, video: Video):
        with self._mutex:
            # save to DB (if not exists)
            cursor = self._db.cursor()
            cursor.execute('INSERT INTO videos (videoId) VALUES (?)', (video.videoId,))
            video.id = cursor.lastrowid
            logger.debug('Inserted video into DB id=' + str(video.id))
            self._db.commit()

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
        logger.debug('model.video().remove() removing id=' + str(video.id) + ', videoId=' + video.videoId)
        try:
            self._items.remove(video)
        except:
            pass
            
        downloader.THREAD.remove(video) # remove from download queue

        with self._mutex:
            cursor = self._db.cursor()
            # get video id so we can delete logs
            cursor.execute('SELECT id FROM videos WHERE videoId = ?', (video.videoId,))
            id = cursor.fetchone()
            if id is not None:
                # delete logs
                cursor.execute('DELETE FROM logs WHERE video_id = ?', (id['id'],))
            
            # delete video record
            cursor.execute('DELETE FROM videos WHERE videoId = ?', (video.videoId,))
            self._db.commit()

        if (lock):
            self._dataMutex.release()


    def getItems(self, lock: bool = True):
        if (lock):
            self._dataMutex.acquire()
        items = self._items.copy()
        if (lock):
            self._dataMutex.release()
        return items
    
    def setItems(self, items, lock: bool = True):
        """
        Update list of videos
        """
        if (lock):
            self._dataMutex.acquire()
        self._items = items
        if (lock):
            self._dataMutex.release()
            
    def debugItems(self):
        print('DEBUG printing all videos in memory')
        items = self.getItems(lock=False)
        for item in items:
            print('DEBUG', f'id={item.id}, url={item.url}')

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
    
    def byIndex(self, index: int, lock: bool = True):
        """
        Get video by index
        """
        if (lock):
            self._dataMutex.acquire()
        video = self._items[index]
        if (lock):
            self._dataMutex.release()
        return video
    
    def getYouTube(self, readonly: bool = True):
        """
        Get youtube API object
        """
        api_service_name = "youtube"
        api_version = "v3"
        youtube = None

        oauthToken = self._settings.get('youtubeApiToken', '')
        apiKey = self._settings.get('googleAPIKey', '')
        if (apiKey != '' and readonly):
            youtube = googleapiclient.discovery.build(
                api_service_name, api_version, developerKey=apiKey)
        elif (oauthToken != ''):
            data = json.loads(oauthToken)
            
            credentials = Credentials.from_authorized_user_info(data)
            
            # check if token needs to be refreshed
            if (credentials.expired):
                logger.debug('Refreshing google access token.')
                
                # refresh expired token
                try:
                    credentials.refresh(Request())
                    if (credentials.refresh_token == None or credentials.refresh_token == ''):
                        logger.warning('Error: No refresh token found.')
                        return
                    
                    logger.debug('Saving new token')
                    self._settings.put('youtubeApiToken', credentials.to_json())
                except:
                    logger.error('Error refreshing token.')
                
            youtube = googleapiclient.discovery.build(
                api_service_name, api_version, credentials=credentials)
        return youtube
    
    def getPlaylistId(self):
        """
        Parse playlist id from url in settings
        """
        playerlistUrl = self._settings.get('playlistUrl', '')
        if (playerlistUrl == ''):
            logger.warning('playlistUrl not set')
            return None
            
        parsed = urlparse(playerlistUrl)
        if (parsed.scheme == ''):
            # just an ID
            playlistId = parsed.path
        else:
            qs = parse_qs(parsed.query)
            playlistId = qs['list'][0]
        return playlistId
    
    def createYoutubeVideo(self, videoId:str, playlistItemId:str, sharedObject = None):
        """
        Add youtube video to memory model and DB (if it isn't already added)
        Youtube video has already been added to the playlist
        Will also download video file using yt-dlp
        """
        if (sharedObject == None):
            sharedObject = {
                'change': False,
                'ytVideos': [],
            }
        
        #logger.debug(json.dumps(item))
        url = f'https://www.youtube.com/watch?v={videoId}'
                    
        with self._mutex:
            # check if exists in DB
            cursor = self._db.cursor()
            cursor.execute('SELECT id FROM videos WHERE videoId = ?', (videoId,))
            row = cursor.fetchone()
            if (row != None):
                # found
                #logger.debug(f'  Already exists videoId={videoId}')
                aVideo = self.byVideoId(videoId=videoId, lock=False)
                if (aVideo == None):
                    # not found in memory
                    logger.error('video id=' + videoId + ' not found in memory.')
                    return
                sharedObject['ytVideos'].append(aVideo)
                
                # set playlist item id
                aVideo.playlistItemId = playlistItemId
                return aVideo

        # set video information
        with yt_dlp.YoutubeDL({}) as ydl:
            logger.debug('getting file information from youtube')
            info = ydl.extract_info(url, download = False)

            # ydl.sanitize_info makes the info json-serializable
            #logger.debug('------------------------------- dumping ydl info')
            # save info to file
            #logger.debug(json.dumps(ydl.sanitize_info(info)),  file=open('yt_dlp_video.json', 'w'))
            video = Video(
                id=0, 
                order=0, 
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
                progress=None,
                sponsorblock=None,
                playlistItemId=playlistItemId,
            )

            thumbnailUrl = info.get('thumbnail')

        # save to DB
        sharedObject['ytVideos'].append(video)
        sharedObject['change'] = True
        self.insert(video=video)
        self.save(video = video, lock = False)
        
        # log added
        log.create({
            'video_id': video.id,
            'action': 'onAdded',
            'data': url,
        })

        # save video thumbnail
        path = '/videos/' + str(video.id) + '-' + video.filename + '.jpg'
        if (not os.path.exists(path)):
            data = requests.get(thumbnailUrl).content
            f = open(path, 'wb')
            f.write(data)
            f.close()

        # add to items and add to downloader queue
        logger.info(f' Adding videoId={video.videoId}')
        with self._dataMutex:
            self._items.append(video)

        # add to downloader queue
        downloader.THREAD.append(video)
        
        return video

    def fetch(self):
        """
        Fetch list from YouTube API.
        Throws: RefreshError, ServiceUnavailable, RetryError, Exception
        """
        logger.info('model.video.fetch()')

        youtube = self.getYouTube()
            
        if (youtube == None):
            logger.warning('  no credentials created yet')
            return None

        # get playlistId
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=50,
            playlistId=self.getPlaylistId()
        )
        response = request.execute()
        
        sharedObject = {
            'change': False, # broadcast list of changed
            'ytVideos': [], # make sure youtube videos stay in order
        }

        for item in response['items']:
            self.createYoutubeVideo(videoId=item['contentDetails']['videoId'], playlistItemId=item['id'], sharedObject=sharedObject)

        # check for deleted youtube videos
        with self._dataMutex:
            for video in self._items.copy():
                if video.source != 'youtube':
                    continue
                found = False
                for cVideo in sharedObject['ytVideos']:
                    if (cVideo.videoId == video.videoId):
                        found = True
                        break
                if (not found):
                    # delete
                    #logger.info('  removing id=' + str(video.id) + ', videoId=' + video.videoId)
                    self.remove(video, False)
                    sharedObject['change'] = True
                
        # create a new array with all youtube source videos in order provided from playlist
        ytIndex = -1
        ytLength = len(sharedObject['ytVideos'])
        nItems = []

        with self._dataMutex:
            for index, video in enumerate(self._items):
                if (video.source == 'youtube' and ytIndex < ytLength - 1):
                    ytIndex += 1

                    ytVideo = sharedObject['ytVideos'][ytIndex]
                    nItems.append(ytVideo)
                    #logger.info('yt add ' + str(ytVideo.id))
                    if (ytVideo.order != ytIndex):
                        # update order in DB
                        logger.info(f'  Updating order of {ytVideo.videoId} to {ytIndex}.')
                        ytVideo.order = ytIndex
                        self.save(ytVideo, False)
                        change = True
                else:
                    nItems.append(video)
            self._items = nItems

        if (sharedObject['change']):
            logger.debug('broadcasting changed list of videos.')
            videos.broadcast()
        logger.info('done fetch')

video = VideoModel(db, mutex, settings)


class LogModel:
    def __init__(self, db, mutex, settings):
        self._db = db
        self._mutex = mutex
        self._settings = settings
        
    def create(self, obj):
        with self._mutex:
            cursor = self._db.cursor()
            cursor.execute('INSERT INTO logs (video_id, action, data, created_at) VALUES (?, ?, ?, ?)', (obj['video_id'], obj['action'], obj['data'], int(time.time()),))
            id = cursor.lastrowid
            logger.debug('Inserted log into DB id=' + str(obj['video_id']))
            self._db.commit()
            
    def getItems(self, videoId):
        items = []
        with self._mutex:
            cursor = self._db.cursor()
            cursor.execute('SELECT id, video_id, action, data, created_at FROM logs WHERE video_id = ? ORDER BY created_at DESC', (videoId,))
            rows = cursor.fetchall()
            for row in rows:
                items.append({
                    'id': int(row['id'] or 0),
                    'video_id': int(row['video_id'] or 0),
                    'action': row['action'],
                    'data': row['data'],
                    'created_at': int(row['created_at'] or 0),
                })
        return items
        
log = LogModel(db, mutex, settings)