/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import React, { useEffect, useRef } from 'react';
import { Alert, Button } from '@mui/material';
import PiVideo from '../components/PiVideo';
import SettingsIcon from '@mui/icons-material/Settings';
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import YouTubeIcon from '@mui/icons-material/YouTube';

export default function Main({ controller, videos, connected }) {
  const navigate = useNavigate();

  const [searchParams, ] = useSearchParams();

  let sendingApi = useRef(false);

  useEffect(() => {
    // update title
    controller.setTitle('');

    if (!sendingApi.current) {
      // connect with YouTube API
      sendingApi.current = true;
      if (searchParams.get('state')) {
        // update api with state
        const data = {
          'namespace': 'connect',
          'method': 'PUT',
          'state': searchParams.get('state'),
          'scope': searchParams.get('scope'),
          'stateUrl': window.location.href,
          'redirectUri': window.location.protocol + '//' + window.location.host + '/',
        };
        console.log('sending api state', data);
        controller.send(data);
        navigate('/');
      }
    }
  }, [controller, navigate, searchParams]);

  const onConnect = () => {
    // send request to get redirect url
    controller.send({
      'namespace': 'connect',
      'method': 'GET',
      'action': 'authorizationUrl',
      'redirectUri': window.location.protocol + '//' + window.location.host + '/',
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
  }

  let videoElement;
  if (!videos.length) {
    videoElement = (
      <Alert severity="warning" action={
        <Link to="/settings" className="link">
          <Button variant="outlined" size="small">
            <SettingsIcon fontSize="small" sx={{ mr: 0.5 }} /> Settings
          </Button>
        </Link>
      }>
        No videos found. Make sure you have set a Playlist URL in settings.
      </Alert>
    );
  } else {
    // list of videos
    videoElement = videos.map((video) => {
      if (video.title) {
        // must have a title
        return <PiVideo key={video.id} video={video} controller={controller} />;
      }
      return '';
    });
  }

  return (
    <div className="page">
      {connectElement}
      {videoElement}
    </div>
  );
}