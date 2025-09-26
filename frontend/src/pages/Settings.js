/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Box, Chip, Button, Divider, Typography, TextField, Select, Grid, MenuItem, FormControl, InputLabel, Grow, CircularProgress, Alert, FormControlLabel, Checkbox } from '@mui/material';
import CloudOffIcon from '@mui/icons-material/CloudOff';
import SaveIcon from '@mui/icons-material/Save';
import YouTubeIcon from '@mui/icons-material/YouTube';
import useController from '../contexts/controller/use';

const delay = ms => new Promise(res => setTimeout(res, ms));

export default function Settings({ }) {
  const navigate = useNavigate();
  const { state: { settings, versions, connected, }, actions: { setFailedToConnect, }, controller } = useController();

  const [hasBackendFailure, setHasBackendFailure] = useState(controller.getClient().getHasBackendFailure());
  const [connecting, setConnecting] = useState(false);
  const [backendHost, setBackendHost] = useState(controller.getLocalSettings('backendHost', 'localhost:5000'));
  const [ssl, setSsl] = useState(controller.getLocalSettings('ssl', true));
  const [error, setError] = useState(null);
  const [hasYoutubeCookies, setHasYoutubeCookies] = useState(null);

  useEffect(() => {
    // update title
    controller.setTitle('Settings');
  }, [controller]);

  const onChange = (name, value) => {
    let t = { ...settings };
    t[name] = value;
    controller.setSettings(t);
  };

  const onSubmit = () => {
    console.log('onSubmit');
    if (!hasBackendFailure) {
      // send to server
      console.log('sending settings to server', settings);
      controller.send({
        'namespace': 'settings',
        'method': 'PUT',
        'data': { ...settings },
      });
    }

    // save local settings
    if (controller.isElectron()) {
      if (backendHost !== controller.getLocalSettings('backendHost') || ssl !== controller.getLocalSettings('ssl')) {
        // attempt to connect to websocket and wait for init message
        setConnecting(true);

        controller.getClient().setup(backendHost, ssl).then(() => {
          // success
          setError(null);
          setConnecting(false);
          setHasBackendFailure(false);
          setFailedToConnect(false);

          // save
          controller.setLocalSettings('backendHost', backendHost);
          controller.setLocalSettings('ssl', ssl);
        }).catch((response) => {
          // failed to connect
          console.log(response);
          setConnecting(false);
          setHasBackendFailure(true);
          setError('Error connecting to web socket at ' + backendHost + '.');
        });
        return;
      }
    }

    controller.snack({
      message: 'Settings updated.',
    });
    navigate(-1);
  };

  const onDisconnect = () => {
    controller.send({
      'namespace': 'connect',
      'method': 'DELETE',
    });

    navigate('/');
  };

  const checkForYoutubeCookies = async () => {
    // check if user has created youtube cookies for mark-position yet
    const c = await window.electron.store.getCookies('https://www.youtube.com');
    if (c && c.length > 0) {
      let found = false;
      for (let cookie of c) {
        if (cookie.name === 'LOGIN_INFO') {
          found = true;
          break;
        }
      }
      if (found) {
        return true;
      }
    }
    return false;
  };

  useEffect(() => {
    const check = async () => {
      setHasYoutubeCookies(await checkForYoutubeCookies());
    };
    check();
  }, [setHasYoutubeCookies]);

  const onOpenYoutube = useCallback(async () => {
    // open youtube and wait for browser close. user is expected to login.
    window.electron.youtube.login();

    // wait for window to close
    while (await window.electron.youtube.isOpen()) {
      await new Promise(r => setTimeout(r, 100));
    }

    setHasYoutubeCookies(await checkForYoutubeCookies());

    // send cookies
    await updateCookies();
  }, [setHasYoutubeCookies]);

  const updateCookies = async () => {
    const host = settings.ytMarkWatchedHost;
    if (!host) {
      console.error('No mark-watched host set in settings.');
      return;
    }

    const cookies = {
      'https://www.youtube.com': await window.electron.store.getCookies('https://www.youtube.com'),
      'https://accounts.youtube.com': await window.electron.store.getCookies('https://accounts.youtube.com'),
    };
    if (!cookies['https://www.youtube.com'] || cookies['https://www.youtube.com'].length === 0) {
      return;
    }
    const response = await fetch(`http://${host}/api/cookies/update`, {
      method: 'POST',
      body: JSON.stringify(cookies),
    });
    console.log('updateCookies() response=', await response.json());
  };

  const onUpdateCookies = useCallback(async () => {
    await updateCookies();
  });

  const onUpdateYtDlp = useCallback(async () => {
    controller.snack({
      message: 'Updating yt-dlp.',
    });

    controller.send({
      'namespace': 'settings',
      'method': 'GET',
      'action': 'update-yt-dlp',
    });
  });

  if (connecting) {
    return (
      <>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>
          Attempting to connect to backend...
        </Typography>
      </>
    );
  }

  if (hasBackendFailure) {
    return (
      <Grow in={true}>
        <div className="page">
          <form onSubmit={onSubmit}>
            {error && <Alert severity="info" sx={{ mb: 2 }}>
              {error}
            </Alert>}
            <Typography variant="h4">
              Configure Backend
            </Typography>
            <Divider sx={{ m: 2 }} />
            <Grid container spacing={2}>
              <Grid item xs={10}>
                <TextField fullWidth required label="Backend Host" value={backendHost ? backendHost : ''} onChange={(e) => setBackendHost(e.target.value)} />
              </Grid>
              <Grid item xs={2}>
                <FormControlLabel control={<Checkbox checked={ssl} onChange={(event) => { setSsl(event.target.checked); }} />} label="SSL" />
              </Grid>
            </Grid>
            <Button type="submit" variant="contained" sx={{ mt: 2 }} fullWidth onClick={onSubmit}><SaveIcon sx={{ mr: 0.5 }} /> Save Settings</Button>
          </form>
        </div>
      </Grow>
    );
  }

  const onConnect = () => {
    // send request to get redirect url
    controller.send({
      'namespace': 'connect',
      'method': 'GET',
      'action': 'authorizationUrl',
    });
  };

  let connectElement = '';
  if (!connected) {
    connectElement = (
      <Alert severity="info" sx={{ mb: 2 }} action={
        <Button variant="contained" size="small" onClick={onConnect}>
          <YouTubeIcon fontSize="small" sx={{ mr: 0.5 }} />
          Connect Now
        </Button>
      }>
        You are not connected with the YouTube API.
      </Alert>
    );
  } else {
    connectElement = (
      <Typography variant="">
        Disconnect from the YouTube API to connect with another account or refresh the access token.
        <Button variant="outlined" size="small" color="error" sx={{ ml: 2 }} onClick={onDisconnect}><CloudOffIcon sx={{ mr: 0.5 }} /> Disconnect From YouTube API</Button>
      </Typography>
    );
  }

  return (
    <Grow in={true}>
      <div className="page">
        <form onSubmit={onSubmit}>
          <Typography variant="h4">
            Manage Server and Client Settings
          </Typography>
          {controller.isElectron() && <>
            <Divider sx={{ m: 2 }} />
            <Grid container spacing={2}>
              <Grid item xs={10}>
                <TextField fullWidth required label="Backend Host" value={backendHost} onChange={(e) => setBackendHost(e.target.value)} />
              </Grid>
              <Grid item xs={2}>
                <FormControlLabel control={<Checkbox checked={ssl} onChange={(event) => { setSsl(event.target.checked); }} />} label="SSL" />
              </Grid>
            </Grid>
          </>}
          <Divider sx={{ m: 2 }} />
          <Typography>
            Provide a Google API Key or leave the API Key field blank and press the "Connect" button to use OAuth Authentication (recommended).
          </Typography>
          <br />
          <TextField fullWidth label="Google API Key" value={settings.googleAPIKey} onChange={(e) => onChange('googleAPIKey', e.target.value)} />
          <br /><br />
          {connectElement}
          <Divider sx={{ m: 2 }} />
          <FormControl fullWidth sx={{ mb: 2 }}>
            <TextField fullWidth required label="yt-marked-watched Host" value={settings.ytMarkWatchedHost} onChange={(e) => onChange('ytMarkWatchedHost', e.target.value)} />
          </FormControl>
          {!hasYoutubeCookies && (
            <Typography sx={{ mb: 2 }}>
              You do not currently have a youtube session.<br />Log in to Youtube so that the automatic mark-position feature will work.
            </Typography>
          )}
          <Button variant="outlined" size="small" color="secondary" sx={{ ml: 2 }} onClick={onOpenYoutube}>Open Youtube</Button>
          <Button variant="outlined" size="small" color="secondary" sx={{ ml: 2 }} onClick={onUpdateCookies}>Update yt-mark-watched Cookies</Button>
          <Divider sx={{ m: 2 }} />
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <TextField fullWidth required label="Audio Delay (ms)" value={settings.audioDelay} onChange={(e) => onChange('audioDelay', e.target.value)} />
            </Grid>
            <Grid item xs={6}>
              <FormControl fullWidth>
                <InputLabel>Select Video Quality *</InputLabel>
                <Select fullWidth required label="Select Video Quality *" value={settings.videoQuality} onChange={(e) => onChange('videoQuality', e.target.value)}>
                  <MenuItem value="720p">720p</MenuItem>
                  <MenuItem value="1080p">1080p</MenuItem>
                  <MenuItem value="1440p">1440p</MenuItem>
                  <MenuItem value="4K">4K</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField fullWidth required label="Playlist URL" value={settings.playlistUrl} onChange={(e) => onChange('playlistUrl', e.target.value)} />
            </Grid>
            <Grid item xs={12}>
              <TextField fullWidth required label="yt-dlp Additional Arguments" value={settings.ytDlpArgv} onChange={(e) => onChange('ytDlpArgv', e.target.value)} />
            </Grid>
            {true == false && (
              <Grid item xs={12}>
                <TextField label="YouTube Cookie" multiline rows={4} fullWidth value={settings.youtubeCookie} onChange={(e) => onChange('youtubeCookie', e.target.value)} />
                <a href="https://github.com/dandv/convert-chrome-cookies-to-netscape-format" target="_blank" rel="noreferrer">How To Copy Cookies</a> | <a href="https://youtube.com" target="_blank" rel="noreferrer">YouTube</a>
              </Grid>
            )}
          </Grid>
          <Button type="submit" variant="contained" sx={{ mt: 2 }} fullWidth onClick={onSubmit}><SaveIcon sx={{ mr: 0.5 }} /> Save Settings</Button>
        </form>
        <div className="versions">
          <Divider sx={{ mt: 4, mb: 4 }} />

          <Box>
            <Chip label={'piWorkout Server ' + versions.piworkoutServer} variant="outlined" />
            <Chip sx={{ ml: 1 }} label={'yt-dlp ' + versions.ytDlp} variant="outlined" />
          </Box>
          <Box sx={{ mt: 2 }}>
            <Button variant="outlined" size="small" color="secondary" onClick={onUpdateYtDlp}>Update yt-dlp</Button>
          </Box>
        </div>
      </div>
    </Grow>
  );
}
