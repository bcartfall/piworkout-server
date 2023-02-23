/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import Client from '../websocket/Client';

export const defaultSnack = {
  open: false,
  message: '',
  autoHideDuration: 2500,
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

    // load localSettings
    if (isElectron) {
      this._localSettings = window.electron.store.get('settings');
      if (!this._localSettings) {
        this._localSettings = {};
      }
    } else {
      this._localSettings = {
        backendHost: 'localhost:5000',
      };
    }
    // load web socket
    this._client = new Client({ controller: this });
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
    if (!('backendHost' in this._localSettings)) {
      return '';
    }
    const schema = ('ssl' in this._localSettings && this._localSettings['ssl']) ? 'https://' : 'http://';
    return schema + this._localSettings['backendHost'] + '/videos/' + path;
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
    this.setLayout(newLayout);
  }

  closeSnack() {
    // close snack
    let newLayout = {...this._layout};
    newLayout.snack.open = false;
    this._setLayout(newLayout);
  }

  getClient() {
    return this._client;
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

  send(json) {
    this._client.send(json);
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

  onKeydown(event) {
    console.log('onKeydown', event);
    if (this._onKeyDown) {
      this._onKeyDown(event);
    }
  }

  syncAudio(action) {
    let position = this._video.currentTime - (parseInt(this._settings.audioDelay, 10) / 1000);
    if (position > this._audio.duration) {
      position = this._audio.duration;
    }
    if (position < 0) {
      // wait for position to be >= 0
      setTimeout(() => {
        this.syncAudio(action);
      }, -position * 1000);
      return false;
    }

    this._audio.currentTime = position;
    if (action === 'play') {
      console.log('audio.play()', 'syncAudio');
      this._audio.play().catch(e => {
        console.error('Error playing audio', e);
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