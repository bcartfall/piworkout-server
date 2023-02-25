/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Divider, Typography, TextField, Select, Grid, MenuItem, FormControl, InputLabel, Grow } from '@mui/material';
import CloudOffIcon from '@mui/icons-material/CloudOff';
import SaveIcon from '@mui/icons-material/Save';

export default function Settings(props) {
  const navigate = useNavigate();

  const { settings, controller } = props;

  useEffect(() => {
    // update title
    controller.setTitle('Settings');
  }, []);

  const onChange = (name, value) => {
    let t = { ...settings };
    t[name] = value;
    controller.setSettings(t);
  };

  const onSubmit = () => {
    controller.snack({
      message: 'Settings updated.',
    });

    // send to server
    controller.send({
      'namespace': 'settings',
      'method': 'PUT',
      'data': { ...settings },
    });

    navigate('/');
  };

  const onDisconnect = () => {
    controller.send({
      'namespace': 'connect',
      'method': 'DELETE',
    });

    navigate('/');
  };

  return (
    <Grow in={true}>
      <div className="page">
        <form onSubmit={onSubmit}>
          <Typography variant="h4">
            Manage Server and Client Settings
          </Typography>
          <Divider sx={{ m: 2 }} />
          <Typography variant="">
            Disconnect from the YouTube API to connect with another account or refresh the access token.
            <Button variant="outlined" size="small" color="error" sx={{ ml: 2 }} onClick={onDisconnect}><CloudOffIcon sx={{ mr: 0.5 }} /> Disconnect From YouTube API</Button>
          </Typography>
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
              <a href="https://github.com/dandv/convert-chrome-cookies-to-netscape-format" target="_blank">How To Copy Cookies</a> | <a href="https://youtube.com" target="_blank">YouTube</a>
            </Grid>
          </Grid>
          <Button variant="contained" sx={{ mt: 2 }} fullWidth onClick={onSubmit}><SaveIcon sx={{ mr: 0.5 }} /> Save Settings</Button>
        </form>
      </div>
    </Grow>
  );
}
