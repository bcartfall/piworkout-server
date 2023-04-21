/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Divider, Typography, TextField, Select, Grid, MenuItem, FormControl, InputLabel, Grow, CircularProgress, Alert, FormControlLabel, Checkbox } from '@mui/material';
import CloudOffIcon from '@mui/icons-material/CloudOff';
import SaveIcon from '@mui/icons-material/Save';
import YouTubeIcon from '@mui/icons-material/YouTube';

export default function Settings(props) {
  const navigate = useNavigate();

  const { settings, controller } = props;

  const [hasBackendFailure, setHasBackendFailure] = useState(controller.getClient().getHasBackendFailure());
  const [connecting, setConnecting] = useState(false);
  const [backendHost, setBackendHost] = useState(controller.getLocalSettings('backendHost', 'localhost:5000'));
  const [ssl, setSsl] = useState(controller.getLocalSettings('ssl', true));
  const [error, setError] = useState(null);

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
          props.setFailedToConnect(false);

          // save
          controller.setLocalSettings('backendHost', backendHost);
          controller.setLocalSettings('ssl', ssl);
        }).catch((response) => {
          // failed to connect
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
                <TextField fullWidth required label="Backend Host" value={backendHost} onChange={(e) => setBackendHost(e.target.value)} />
              </Grid>
              <Grid item xs={2}>
                <FormControlLabel control={<Checkbox checked={ssl} onChange={(event) => {setSsl(event.target.checked);}} />} label="SSL" />
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
  if (!props.connected) {
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
                <FormControlLabel control={<Checkbox checked={ssl} onChange={(event) => {setSsl(event.target.checked);}} />} label="SSL" />
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
              <TextField fullWidth required label="Play List URL" value={settings.playlistUrl} onChange={(e) => onChange('playlistUrl', e.target.value)} />
            </Grid>
            <Grid item xs={12}>
              <TextField label="YouTube Cookie" multiline rows={4} fullWidth value={settings.youtubeCookie} onChange={(e) => onChange('youtubeCookie', e.target.value)} />
              <a href="https://github.com/dandv/convert-chrome-cookies-to-netscape-format" target="_blank" rel="noreferrer">How To Copy Cookies</a> | <a href="https://youtube.com" target="_blank" rel="noreferrer">YouTube</a>
            </Grid>
          </Grid>
          <Button type="submit" variant="contained" sx={{ mt: 2 }} fullWidth onClick={onSubmit}><SaveIcon sx={{ mr: 0.5 }} /> Save Settings</Button>
        </form>
      </div>
    </Grow>
  );
}
