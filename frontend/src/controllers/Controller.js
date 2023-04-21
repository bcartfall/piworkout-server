/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import CloseIcon from '@mui/icons-material/Close';
import { IconButton, } from '@mui/material';
import Client from '../websocket/Client';

export const defaultSnack = {
  open: false,
  message: '',
  autoHideDuration: 2500,
  onClose: () => {},
  action: null, // defined in method as close icon
};

export class Controller {
  constructor({ layout, setLayout, settings, setSettings, videos, setVideos, setConnected, setLoaded, isElectron }) {
    console.log('init controller');
    this._layout = layout;
    this._setLayout = setLayout;
    this._settings = settings;
    this._setSettings = setSettings;
    this._videos = videos;
    this._setVideos = setVideos;
    this._connected = false;
    this._setConnected = setConnected;
    this._setLoaded = setLoaded;
    this._currentVideo = null;
    this._client = null;
    this._isElectron = isElectron;

    // load localSettings
    if (isElectron) {
      this._localSettings = {
        ssl: true,
        backendHost: null,
        ...window.electron.store.get('settings'),
      };
    } else {
      this._localSettings = {
        ssl: window.location.protocol === 'https:',
        backendHost: window.location.host,
      };
    }
    // load web socket
    this._client = new Client({ controller: this });
  }

  isElectron() {
    return this._isElectron;
  }

  getLocalSettings(key = null, defaultValue = null) {
    if (key) {
      if (key in this._localSettings) {
        return this._localSettings[key];
      } else {
        return defaultValue;
      }
    }
    return this._localSettings;
  }

  setLocalSettings(key, value) {
    this._localSettings[key] = value;
    window.electron.store.set('settings', this._localSettings);
  }

  getVideoUrl(path) {
    return this.getUrl('videos/' + path.trimStart('/'));
  }

  getUrl(path) {
    if (!('backendHost' in this._localSettings)) {
      return '';
    }
    const schema = ('ssl' in this._localSettings && this._localSettings['ssl']) ? 'https://' : 'http://';
    return schema + this._localSettings['backendHost'] + '/' + path.trimStart('/');
  }

  getLayoutTitle() {
    return 'piWorkout' + (this._layout.title ? ' - ' + this._layout.title : '');
  }

  setTitle(title) {
    // update layout and page title
    let newLayout = { ...this._layout };
    newLayout.title = title;
    this.setLayout(newLayout);

    document.title = this.getLayoutTitle();
  }

  setConnected(value) {
    this._connected = value;
    this._setConnected(value);
  }

  setLayout(layout) {
    this._layout = layout;
    this._setLayout(layout);
  }

  snack(data) {
    // open a snack
    let newLayout = {...this._layout};
    newLayout.snack = {
      ...defaultSnack,
      open: true,
      ...data,
    };

    if (!newLayout.snack.action) {
      // default action
      newLayout.snack.action = (
        <IconButton
          size="small"
          aria-label="close"
          color="inherit"
          onClick={() => {this.closeSnack()}}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      );
    }

    this.setLayout(newLayout);
  }

  closeSnack() {
    // close snack
    let newLayout = {...this._layout};
    newLayout.snack.open = false;
    this._setLayout(newLayout);
  }

  logDialog(video) {
    // open log dialog
    let newLayout = {...this._layout};
    newLayout.logDialog = {...newLayout.logDialog, open: true, video,};

    this.setLayout(newLayout);
  }

  getClient() {
    return this._client;
  }

  generateUuid() {
    // non compliant uuid like random string
    return Math.random().toString(36).substring(2, 15);
  }

  setSettings(settings) {
    this._settings = settings;
    this._setSettings(settings);
  }

  getSettings() {
    return this._settings;
  }

  getVideos() {
    return this._videos;
  }

  setVideos(videos) {
    this._videos = [...videos];
    this._setVideos(this._videos);
  }

  videosUseState() {
    return [this._videos, this._setVideos];
  }

  async send(data, type = 'json') {
    return this._client.send(data, type);
  }

  setPlayer({player, video, audio, onKeyDown }) {
    this._player = player;
    this._video = video;
    this._audio = audio;
    this._onKeyDown = onKeyDown;
  }

  getVideo() {
    return this._video;
  }

  getAudio() {
    return this._audio;
  }

  onKeydown(event) {
    console.log('onKeydown', event);
    if (this._onKeyDown) {
      this._onKeyDown(event);
    }
  }

  syncAudio(action) {
    const videoTime = this._video.currentTime;
    let position = videoTime - (parseInt(this._settings.audioDelay, 10) / 1000);
    if (position > this._audio.duration) {
      position = this._audio.duration;
    }
    if (position < 0) {
      // wait for position to be >= 0
      const delay = -position * 1000;
      setTimeout(() => {

        console.log('audio needs to be delayed until video has reached delay=', delay)
        this.syncAudio(action);
      }, delay);
      return false;
    }

    this._audio.currentTime = position;
    if (action === 'play') {
      console.log('audio.play()', 'syncAudio');
      this._audio.play().catch(e => {
        console.error('Error playing audio', e);

        // try again
        setTimeout(() => {
          this.syncAudio(action);
        }, 1000);
        return false;
      });
    } else if (action === 'pause') {
      this._audio.pause();
    }
  }

  getCurrentTime() {
    if (!this._video) {
      return 0;
    } else {
      return this._video.currentTime;
    }
  }  

  setCurrentVideo(video) {
    this._currentVideo = video;
  }

  togglePlay(event) {
    if (!this._video) {
      return;
    }

    event.preventDefault();
    if (this._video.paused || this._video.ended) {
      this._video.play();
    } else {
      this._video.pause();
    }
  }
};