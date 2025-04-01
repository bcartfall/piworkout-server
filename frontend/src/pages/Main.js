/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import React, { useEffect, useRef, useCallback, } from 'react';
import { Alert, Button } from '@mui/material';
import PiVideo from '../components/PiVideo';
import SettingsIcon from '@mui/icons-material/Settings';
import { Link, useNavigate } from "react-router-dom";
import useController from '../contexts/controller/use';

export default function Main({ }) {
  const { state: { videos, failedToConnect, }, actions: { setVideos, }, controller } = useController();

  const navigate = useNavigate();
  const sendingApi = useRef(false); // only send connect request once

  const searchParams = new URLSearchParams(window.location.search);
  //console.log('rendering', videos);

  const moveVideo = useCallback((dragVideo, toIndex, commit = false) => {
    console.log('moving ', dragVideo.id, toIndex);

    let fromIndex = -1;
    for (let i in videos) {
      const video = videos[i];
      if (video.id === dragVideo.id) {
        fromIndex = i;
        break;
      }
    }
    if (fromIndex < 0) {
      return;
    }

    videos[fromIndex] = videos[toIndex];
    videos[toIndex] = dragVideo;
    setVideos([...videos]);

    if (commit) {
      controller.send({
        'namespace': 'videos',
        'action': 'order',
        'id': dragVideo.id,
        'index': toIndex,
      });
    }
  }, [videos, setVideos, controller, ]);

  useEffect(() => {
    // check if we need to redirect to settings page
    const localSettings = controller.getLocalSettings();
    if (!localSettings.backendHost) {
      navigate('/settings');
    }

    // update title
    controller.setTitle('');

    if (!sendingApi.current) {
      // connect with YouTube API
      sendingApi.current = true;
      console.log(searchParams);
      console.log('looking for api state', searchParams.get('state'))
      if (searchParams.get('state')) {
        // update api with state
        const data = {
          'namespace': 'connect',
          'method': 'PUT',
          'state': searchParams.get('state'),
          'scope': searchParams.get('scope'),
          'stateUrl': window.location.href,
          //'redirectUri': window.location.protocol + '//' + window.location.host + '/',
        };
        console.log('sending api state', data);
        controller.send(data);
        navigate('/');
      }
    }
  }, [controller, navigate, searchParams]);

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
    videoElement = videos.map((video, index) => {
      if (video.title) {
        // must have a title
        return <PiVideo key={video.id} index={index} video={video} controller={controller} moveVideo={moveVideo} />;
      }
      return '';
    });
  }

  return (
    <div className="page">
      {failedToConnect && 
        <Alert severity="error" action={
          <Link to="/settings" className="link">
            <Button variant="outlined" size="small">
              <SettingsIcon fontSize="small" sx={{ mr: 0.5 }} /> Settings
            </Button>
          </Link>
        }>
          Failed to connect to server.
        </Alert>
      }
      {!failedToConnect &&
        <>
          {videoElement}
        </>
      }
    </div>
  );
}