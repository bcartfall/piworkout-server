/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

export default class Client {
  constructor({ controller }) {
    this._controller = controller;
    this._ws = null;
    this._hasBackendFailure = false;
    this._initResolve = null;
    this._connected = false;
    this._retryCount = 0;
    this._onFailedToConnect = null;

    this.setup().then(() => {}).catch(() => {});
  }

  /**
   * Connect to Websocket
   * @param {string} backendHost If specified client will attempt to connect to host, else will load from settings
   * @returns 
   */
  setup(backendHost = null) {
    return new Promise((resolve, reject) => {
      this._initResolve = resolve;

      if (!backendHost) {
        const localSettings = this._controller.getLocalSettings();
        backendHost = localSettings.backendHost;
      }
      if (!backendHost) {
        this._hasBackendFailure = true;
        this._controller._setLoaded(true);
        return;
      }
      try {
        this._ws = new WebSocket('ws://' + backendHost + '/backend'); // ws://localhost:5000/backend
      } catch (e) {
        this._initResolve = null;
        reject(e);
      }
      this._ws.onopen = (event) => { this.onOpen(event) };
      this._ws.onmessage = (event) => { this.onMessage(event); };
      this._ws.onclose = (event) => { 
        this.onClose(event); 
      };
      this._ws.onerror = (event) => { 
        this._initResolve = null;
        reject(event);
        this.onError(event); 
      };
    });
  }

  send(json) {
    return this._ws.send(JSON.stringify(json));
  }

  onOpen(event) {
    this._hasBackendFailure = false;
    this._connected = true;
    this._retryCount = 0;
  }

  onMessage(event) {
    const json = JSON.parse(event.data);
    console.log('onmessage', json);
    switch (json.namespace) {
      case 'init': this.onInit(event, json); break
      case 'settings': this.onSettings(event, json); break;
      case 'connect': this.onConnect(event, json); break;
      case 'videos': this.onVideos(event, json); break;
      default:
    }
  }

  onClose(event) {
    console.log('WebSocket is closed. Reconnect will be attempted in 1 second.', event.reason);
    this._hasBackendFailure = true;
    this._retryCount++;

    if (!this._connected && this._retryCount >= 1) {
      if (this._onFailedToConnect) {
        this._onFailedToConnect();
      }
    } else {
      setTimeout(() => {
        // reconnect
        this.setup();
      }, 1000);
    }
  }

  onError(err) {
    console.error('Socket encountered error: ', err.message, 'Closing socket');
    this._ws.close();
  }

  onInit(event, json) {
    if (this._initResolve) {
      this._initResolve(json);
      this._initResolve = null;
    }
    this._controller.setConnected(json.data.connected);
    this._controller.setSettings({ ...json.data.settings });
    this._controller.setVideos([...json.data.videos]);
    this._controller._setLoaded(true);

    // send 'up' to server to get back any queued messages
    if (this._pingInterval) {
      clearInterval(this._pingInterval);
    }
    setInterval(() => {
      this.send({
        'namespace': 'up',
      });
    }, 1000 / 10);
  }

  onSettings(event, json) {
    this._controller.setSettings({...json.settings});
  }

  onConnect(event, json) {
    if (json.authorizationUrl) {
      // redirect
      if (window.electron) {
        window.electron.shell.openExternal(json.authorizationUrl);
      } else {
        window.open(json.authorizationUrl, '_self');
      }
    } else {
      this._controller._setConnected(json.connected);
    }
  }

  onVideos(event, json) {
    //console.log('onVideos()', json);

    if (json.video) {
      // update single video
      let found = false,
        videos = this._controller.getVideos();
      for (let id in videos) {
        if (videos[id].id === json.video.id) {
          videos[id] = json.video;
          found = true;
          break;
        }
      }
      if (!found) {
        videos.append(json.video);
      }

      this._controller.setVideos(videos);
    } else {
      // update all videos
      this._controller.setVideos(json.videos);
    }
  }

  getHasBackendFailure() {
    return this._hasBackendFailure;
  }

  onFailedToConnect(callback) {
    this._onFailedToConnect = callback;
  }
}