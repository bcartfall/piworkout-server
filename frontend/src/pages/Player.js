/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import React, { useEffect, useCallback, useRef, useState } from 'react';
import { useParams, useNavigate } from "react-router-dom";
import { Grid, Box, Typography, Card, Divider, Fade, IconButton, Tooltip, Chip, Snackbar, Alert } from '@mui/material';
import VideoPlayerProgress from '../components/VideoPlayerProgress';
import VideoTime from '../components/VideoTime';
import VideoList from '../components/VideoList';
import ThumbUpOffAltIcon from '@mui/icons-material/ThumbUpOffAlt';
import ThumbUpAltIcon from '@mui/icons-material/ThumbUpAlt';
import ThumbDownOffAltIcon from '@mui/icons-material/ThumbDownOffAlt';
import ThumbDownAltIcon from '@mui/icons-material/ThumbDownAlt';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import SkipPreviousIcon from '@mui/icons-material/SkipPrevious';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import FullscreenExitIcon from '@mui/icons-material/FullscreenExit';
import defaultChannelImage from '../assets/images/youtube.svg';
import eStatus from '../enums/VideoStatus';
import { SPONSORBLOCK_SKIP_CATEGORIES } from '../enums/SponsorBlock'
import VideoContextMenu from '../components/VideoContextMenu';
import useController from '../contexts/controller/use';

export default React.memo(function Player({ }) {
  const { state: { settings, }, controller } = useController();
  const navigate = useNavigate();
  const [currentVideo, setCurrentVideo] = useState(null);
  const [rating, setRating] = useState('');
  const shouldRequestInformation = useRef(true);
  const videoRef = useRef(null);
  const audioRef = useRef(null);
  const videoMounted = useRef(false);
  const audioMounted = useRef(false);
  const playerRef = useRef(null);
  const playerMounted = useRef(false);
  const videoChanging = useRef(false);
  const videoTimeRef = useRef(null);
  const videoListRef = useRef(null);
  const playTimeRef = useRef(0);
  const lastAction = useRef(new Date().getTime());
  const lastMouseAction = useRef(new Date().getTime());
  const videoClick = useRef({
    count: 0, singleTimeout: 0, doubleTimeout: 0,
  });
  const nextSkip = useRef(null);
  const progressRef = useRef(null);

  const [playing, setPlaying] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  const isFullScreen = useRef(false);
  const [showPlaying, setShowPlaying] = useState(false);
  const [showPaused, setShowPaused] = useState(false);
  const [showStatus, setShowStatus] = useState(true);
  const [showCursor, setShowCursor] = useState(true);
  const [videoInfo, setVideoInfo] = useState('');
  const [showSponsorSkipped, setShowSponsorSkipped] = useState(false);
  const [contextMenu, setContextMenu] = useState(null);

  let { id } = useParams(); // get id from url (e.g. /player/:id)
  id = Math.trunc(id);

  console.log('rendering Player', id);

  const updateNextSkip = useCallback((source, currentTime, video = null) => {
    let skipSegment = null;
    if (!video) {
      video = currentVideo;
    }
    if (video.sponsorblock) {
      for (const segment of video.sponsorblock.segments) {
        const categoryIndex = SPONSORBLOCK_SKIP_CATEGORIES.indexOf(segment.category);
        if (categoryIndex < 0) {
          continue;
        }
        if (currentTime < segment.segment[0]) {
          skipSegment = segment;
          break;
        }
      }
    }
    if (skipSegment) {
      console.log('Setting next skip segment', skipSegment);
      nextSkip.current = [skipSegment.segment[0], skipSegment];
    }
  }, [nextSkip, currentVideo,]);

  const updateVideoPosition = useCallback((video) => {
    const currentTime = controller.getCurrentTime();
    if (video.duration > 0) {
      // set progress
      const duration = video.duration;
      if (progressRef.current) {
        progressRef.current.updateProgress(currentTime / duration * 100);
      }

      // update video time
      if (videoTimeRef.current) {
        let a = '';
        const aH = Math.floor(currentTime / 3600).toString(),
          aM = Math.floor((currentTime / 60) % 60).toString(),
          aS = Math.floor(currentTime % 60).toString();
        if (aH > 0) {
          a += aH.padStart(2, '0') + ':';
        }
        a += aM.padStart(2, '0') + ':' + aS.padStart(2, '0');

        let b = '';
        const bH = Math.floor(duration / 3600).toString(),
          bM = Math.floor((duration / 60) % 60).toString(),
          bS = Math.floor(duration % 60).toString();
        if (bH > 0) {
          b += bH.padStart(2, '0') + ':';
        }
        b += bM.padStart(2, '0') + ':' + bS.padStart(2, '0');

        const newTime = a + ' / ' + b;
        videoTimeRef.current.updateTime(newTime);
      }
    }

    // update videos to have correct position for this video
    let videos = controller.getVideos();
    for (let i in videos) {
      const t = videos[i];
      if (t.id === video.id) {
        // we don't want this component to render so we don't use controller.setVideos(videos)
        videos[i].position = currentTime;
        //console.log('setting position of video ' + t.id + ' to ' + t.position);

        // update position in videolist
        if (videoListRef.current) {
          videoListRef.current.updateVideos(videos);
        }
        break;
      }
    }
  }, [controller, videoTimeRef, progressRef, ]);

  const handleStatus = useCallback((action) => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    if (action !== 'progress') {
      lastAction.current = new Date().getTime();
    }
    if (action === 'mousemove' || action === 'mouseclick') {
      lastMouseAction.current = new Date().getTime();
    }

    let showStatus = true;
    const now = new Date().getTime();

    if (!video.paused && isFullScreen.current) {
      // determine if status bar should not shown based on time since last action (e.g. seek)
      if (now - lastAction.current >= 3000) {
        showStatus = false;
      }
    }

    let showCursor = false;
    if (!isFullScreen.current || showPaused) {
      // always show when not fullscreen or when paused
      showCursor = true;
    } else if (showStatus && now - lastMouseAction.current < 3000) {
      // show if mouse action within 3s
      showCursor = true;
    }

    setShowStatus(showStatus);
    setShowCursor(showCursor);
  }, [videoRef, lastAction, isFullScreen, setShowStatus, setShowCursor, showPaused,]);

  const onPlay = useCallback((e) => {
    controller.syncAudio('play');
    playTimeRef.current = Date.now();

    const currentTime = controller.getCurrentTime();
    const obj = {
      'namespace': 'player',
      'action': 'play',
      'source': 'web',
      'videoId': currentVideo.id,
      'time': currentTime,
    };
    console.log(obj);
    controller.send(obj);

    handleStatus('play');

    // send log
    controller.send({
      namespace: 'logs',
      action: 'onPlay',
      videoId: currentVideo ? currentVideo.id : 0,
      data: controller.getCurrentTime(),
    });
    console.log('-------------------------- PLAY ----------------', currentVideo);
    
    // determine next segement to skip
    updateNextSkip('play', currentTime);
  }, [currentVideo, controller, handleStatus, updateNextSkip,]);

  const onChangeProgress = useCallback((time) => {
    //console.log('onChangeProgress', time, videoRef);
    if (!videoRef.current) {
      return;
    }
    videoRef.current.currentTime = time;
    updateVideoPosition(currentVideo);
    controller.syncAudio('seek');

    const obj = {
      'namespace': 'player',
      'action': 'seek',
      'source': 'web',
      'videoId': currentVideo.id,
      'time': time,
    };
    console.log(obj);
    controller.send(obj);
    updateNextSkip('seek', time);
  }, [videoRef, controller, updateVideoPosition, currentVideo, updateNextSkip,]);

  const onProgress = useCallback((e) => {
    const videoEl = controller.getVideo();
    const audioEl = controller.getAudio();

    if (controller.getCurrentTime() <= 0 || videoEl.paused || videoEl.ended) {
      return;
    }

    const currentTime = controller.getCurrentTime();
    const diff = (currentTime - audioEl.currentTime);
    //console.log('video position=', currentTime, 'audio position=', audioEl.currentTime, ', diff=', diff);
    
    // for the first n seconds of playback try to match audio delay to the setting by adjusting video playback speed
    if (playTimeRef.current !== -1 && Date.now() - playTimeRef.current < 5000) {
      const target = parseInt(controller.getSettings().audioDelay, 10);
      const normal = (diff * 1000) - target;

      // exponentially adjust video rate between 25% and 400% depending on deviance from 1000ms
      const playbackRate = Math.pow(Math.min(Math.max(1 - (normal / 1000), 0.5), 2), 2);
      console.log('audio delay=' + Math.round(diff * 1000), ', target=' + target, ', adjusting playbackRate=' + playbackRate);
      videoEl.playbackRate = playbackRate;
    } else {
      playTimeRef.current = -1;
      videoEl.playbackRate = 1.0;
    }

    const obj = {
      'namespace': 'player',
      'action': 'progress',
      'source': 'web',
      'videoId': currentVideo.id,
      'time': currentTime,
    };
    
    //console.log(obj);
    controller.send(obj);
    updateVideoPosition(currentVideo);
    handleStatus('progress');

    if (nextSkip.current) {
      // check if we need to seek ahead of sponsor
      if (currentTime >= nextSkip.current[0]) {
        // skip segment
        const skipTo = nextSkip.current[1].segment[1];
        nextSkip.current = null;
        onChangeProgress(skipTo);

        setShowSponsorSkipped(true);
        setTimeout(() => {
          setShowSponsorSkipped(false);
        }, 3000);
      }
    }
  }, [updateVideoPosition, currentVideo, controller, handleStatus, nextSkip, onChangeProgress, ]);

  const onPause = useCallback(async (e) => {
    controller.syncAudio('pause');
    const obj = {
      'namespace': 'player',
      'action': 'pause',
      'source': 'web',
      'videoId': currentVideo ? currentVideo.id : 0,
      'time': controller.getCurrentTime(),
    };
    console.log(obj);
    const promise = controller.send(obj);
    if (currentVideo) {
      updateVideoPosition(currentVideo);
    }
    
    // send log
    controller.send({
      namespace: 'logs',
      action: 'onPause',
      videoId: currentVideo ? currentVideo.id : 0,
      data: controller.getCurrentTime(),
    });

    handleStatus('pause');
    return promise;
  }, [updateVideoPosition, currentVideo, controller, handleStatus]);

  const skip = useCallback((direction) => {
    const videos = controller.getVideos();
    let index = -1, l = videos.length;
    for (let i = 0; i < l; i++) {
      if (currentVideo.id === videos[i].id) {
        index = i;
        break;
      }
    }
    if (index < 0) {
      return null;
    }

    videoRef.current.pause();

    if (direction === 'next') {
      if (index < l - 1) {
        // play next video
        console.log('play next video');
        const nVideo = videos[index + 1];

        playerMounted.current = false;
        videoRef.current = null;
        videoMounted.current = false;
        audioRef.current = null;
        audioMounted.current = false;
        videoChanging.current = true;
        nextSkip.current = null;
        shouldRequestInformation.current = true;
        navigate('/player/' + nVideo.id);
      }
    } else if (direction === 'previous') {
      if (index > 0) {
        // play previous video
        console.log('play previous video');
        const pVideo = videos[index - 1];

        playerMounted.current = false;
        videoRef.current = null;
        videoMounted.current = false;
        audioRef.current = null;
        audioMounted.current = false;
        videoChanging.current = true;
        nextSkip.current = null;
        shouldRequestInformation.current = true;
        navigate('/player/' + pVideo.id);
      }
    }
  }, [currentVideo, navigate, controller, ]);

  const onEnded = useCallback((e) => {
    const obj = {
      'namespace': 'player',
      'action': 'ended',
      'source': 'web',
      'videoId': currentVideo.id,
      'time': controller.getCurrentTime(),
    };
    console.log(obj);
    controller.send(obj);
    updateVideoPosition(currentVideo);

    // play the next video
    skip('next');
  }, [updateVideoPosition, currentVideo, controller, skip]);

  const playVideo = useCallback((video) => {
    console.log('playVideo', video);

    // check if same video
    if (currentVideo.id === video.id) {
      return;
    }

    updateVideoPosition(currentVideo);

    if (video.status === eStatus.COMPLETE) {
      shouldRequestInformation.current = true;

      // let server know we're about to play another video
      const v = controller.getVideo();
      if (v) {
        v.pause();
        setPlaying(false);
      }

      // play clicked on
      playerMounted.current = false;
      videoRef.current = null;
      videoMounted.current = false;
      audioRef.current = null;
      audioMounted.current = false;
      videoChanging.current = true;
      nextSkip.current = null;
      navigate('/player/' + video.id);
    }
  }, [updateVideoPosition, currentVideo, controller, navigate,]);

  const getResolution = (video, source) => {
    // determine resolution (browser based player will use best video possible)
    let resolution = '';
    if (video.height >= 2160) {
      resolution = '4K';
    } else if (video.height >= 1440) {
      resolution = '1440p';
    } else if (video.height >= 1080) {
      resolution = '1080p';
    } else if (video.height >= 720 && source === 'info') {
      resolution = '720p';
    } else if (video.height >= 480 && source === 'info') {
      resolution = '480p';
    } else if (source === 'info') {
      resolution = 'SD';
    } else {
      resolution = '720p';
    }

    //console.log(video.height, source);

    if (video.source === 'file-upload' && source === 'file') {
      // doesn't support different resolutions
      resolution = 'upload';
    }
    return resolution;
  };

  useEffect(() => {
    if (id) {
      const videos = controller.getVideos();
      for (let video of videos) {
        if (video.id === id) {
          setCurrentVideo(video);
          controller.setCurrentVideo(video);
          console.log('------------------------ 5553', shouldRequestInformation.current)

          // get more information about video and channel when video id changes
          if (shouldRequestInformation.current) {
            shouldRequestInformation.current = false;
            console.log('requesting more information.', video.id);
            const uuid = controller.generateUuid();
            controller.send({
              'namespace': 'videos',
              'action': 'playerInformation',
              'id': video.id,
              'uuid': uuid,
            });

            // wait for response
            controller.getClient().onMessageCall((event, json) => {
              if (json.uuid === uuid) {
                // set current video will rerender and show updated information
                setCurrentVideo(json.video);
                updateNextSkip('playerInformation', json.video.position, json.video);

                // clear callback
                controller.getClient().onMessageCall(null);
              }
            });
          }
          break;
        }
      }
    }
    if (currentVideo) {
      controller.setTitle(currentVideo.title);
    }
    
    // catch window closing
    if (controller.isElectron()) {
      window.electron.app.onBeforeClose(async (e) => {
        console.log('Closing window. Pause video.');
        if (playing && videoRef.current) {
          videoRef.current.pause();
        }
      });
    }
  }, [currentVideo, shouldRequestInformation, controller, id, playing, onPause, updateNextSkip, ]);

  const toggleFullscreen = useCallback((event) => {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    if (!isFullScreen.current) {
      isFullScreen.current = true;
      setFullscreen(true);
      playerRef.current.requestFullscreen().catch((err) => {
        isFullScreen.current = false;
        setFullscreen(false);
      });
    } else {
      isFullScreen.current = false;
      setFullscreen(false);
      document.exitFullscreen();
    }

    handleStatus('fullscreen');
  }, [setFullscreen, handleStatus,]);

  const togglePlay = useCallback((event) => {
    event.preventDefault();
    const video = controller.getVideo();
    if (video.paused) {
      // resume
      if (!showPlaying) {
        setShowPlaying(true);
        setTimeout(() => {
          setShowPlaying(false);
        }, 250);
      }
      console.log('video.play()', 'togglePlay');
      video.play();
      setPlaying(true);
      handleStatus('play');
    } else {
      // pause
      if (!showPaused) {
        setShowPaused(true);
        setTimeout(() => {
          setShowPaused(false);
        }, 250);
      }
      video.pause();
      setPlaying(false);
      handleStatus('pause');
    }

  }, [setShowPaused, setShowPlaying, controller, showPaused, showPlaying, handleStatus,]);

  const onClickPlayer = useCallback((e) => {
    e.preventDefault();
    videoClick.current.count += 1;

    if (!videoClick.current.singleTimeout) {
      videoClick.current.singleTimeout = setTimeout(() => {
        if (videoClick.current.count === 1) {
          togglePlay(e);
        }
        videoClick.current.singleTimeout = 0;
      }, 250);
    }
    if (!videoClick.current.doubleTimeout) {
      videoClick.current.doubleTimeout = setTimeout(() => {
        if (videoClick.current.count > 1) {
          // toggle fullscreen
          toggleFullscreen();
        }
        videoClick.current.count = 0;
        videoClick.current.doubleTimeout = 0;
      }, 500);
    } else {
      if (videoClick.current.count > 1) {
        videoClick.current.count = 0;
        clearTimeout(videoClick.current.doubleTimeout);
        videoClick.current.doubleTimeout = 0;
        // toggle fullscreen
        toggleFullscreen();
      }
    }

    handleStatus('mouseclick');
  }, [togglePlay, videoClick, toggleFullscreen, handleStatus,]);

  const onMount = useCallback(() => {
    const video = videoRef.current;
    video.current = true;
    video.dataset.mounted = true;

    const audio = audioRef.current;
    audioMounted.current = true;

    const player = playerRef.current;
    playerMounted.current = true;

    videoChanging.current = false;

    const seek = (event, seconds) => {
      event.preventDefault();
      console.log('seek()', seconds);

      const currentTime = video.currentTime + seconds;
      video.currentTime = currentTime;
      updateVideoPosition(currentVideo);
      controller.syncAudio('seek');

      const obj = {
        'namespace': 'player',
        'action': 'seek',
        'source': 'web',
        'videoId': currentVideo.id,
        'time': currentTime,
      };
      console.log(obj);
      controller.send(obj);

      handleStatus('seek');
      updateNextSkip('seek', currentTime);
    };

    const onKeyDown = (event) => {
      console.log(event);
      const key = event.key.toUpperCase();
      switch (key) {
        case 'ARROWLEFT': return seek(event, -5);
        case 'ARROWRIGHT': return seek(event, 5);
        case 'F': return toggleFullscreen(event);
        case ' ': 
        case 'K':
          return togglePlay(event);
        default:
      }

      if (event.shiftKey) {
        switch (key) {
          case 'P': return skip('previous');
          case 'N': return skip('next');
          default:
        }
      }
    };

    controller.setPlayer({ player, video, audio, onKeyDown });

    video.addEventListener('play', onPlay);
    video.addEventListener('pause', onPause);
    video.addEventListener('ended', onEnded);
    video.addEventListener('timeupdate', onProgress);

    if (currentVideo) {
      // set current time to video model's position
      const playing = !!(video.currentTime > 0 && !video.paused && !video.ended && video.readyState > 2);
      if (!playing) {
        if (currentVideo.position >= currentVideo.duration - 5) {
          currentVideo.position = 0; // restart if was at end
        }
        video.currentTime = currentVideo.position;
        controller.syncAudio('init');

        video.play().catch(e => { });
      }
      setPlaying(true);

      // 
      let bitrate;
      if (currentVideo.tbr >= 1000) {
        bitrate = Math.round(currentVideo.tbr * 0.001) + 'M';
      } else {
        bitrate = (Math.round(currentVideo.tbr * 0.1) * 10) + 'K';
      }

      setVideoInfo(getResolution(currentVideo, 'info') + '/' + currentVideo.fps + '/' + currentVideo.vcodec.toUpperCase() + '/' + bitrate);

      // setup windows mediasession
      if ('mediaSession' in navigator) {
        navigator.mediaSession.metadata = new MediaMetadata({
          title: currentVideo.title,
          artist: currentVideo.channelName,
          artwork: [
            { src: controller.getVideoUrl(currentVideo.id + '-' + currentVideo.filename + '.jpg'), sizes: '96x96', type: 'image/jpeg' },
            { src: controller.getVideoUrl(currentVideo.id + '-' + currentVideo.filename + '.jpg'), sizes: '128x128', type: 'image/jpeg' },
            { src: controller.getVideoUrl(currentVideo.id + '-' + currentVideo.filename + '.jpg'), sizes: '192x192', type: 'image/jpeg' },
            { src: controller.getVideoUrl(currentVideo.id + '-' + currentVideo.filename + '.jpg'), sizes: '256x256', type: 'image/jpeg' },
            { src: controller.getVideoUrl(currentVideo.id + '-' + currentVideo.filename + '.jpg'), sizes: '384x384', type: 'image/jpeg' },
            { src: controller.getVideoUrl(currentVideo.id + '-' + currentVideo.filename + '.jpg'), sizes: '512x512', type: 'image/jpeg' },
          ]
        });

        navigator.mediaSession.setActionHandler('play', () => {
          console.log('video.play()', 'mediaSession');
          video.play().catch(e => { });
          setPlaying(true);
        });
        navigator.mediaSession.setActionHandler('pause', () => {
          video.pause().catch(e => { });
          setPlaying(false);
        });
        navigator.mediaSession.setActionHandler('previoustrack', () => {
          skip('previous');
        });
        navigator.mediaSession.setActionHandler('nexttrack', () => {
          skip('next');
        });

        handleStatus('mount');
      }
    }
  }, [playerRef, videoRef, audioRef, controller, skip, onPlay, onEnded, onProgress, onPause, currentVideo, toggleFullscreen, updateVideoPosition, togglePlay, handleStatus, setPlaying, updateNextSkip,]);

  useEffect(() => {
    // videoRef and audioRef has been loaded
    //console.log(videoRef.current);
    //console.log(videoRef.current ? 1 : 0, !videoMounted.current ? 1 : 0, audioRef.current ? 1 : 0, !audioMounted.current ? 1 : 0, (playerRef.current || videoChanging.current) ? 1 : 0, !playerMounted.current ? 1 : 0);
    if (videoRef.current && !videoMounted.current && audioRef.current && !audioMounted.current && (playerRef.current || videoChanging.current) && !playerMounted.current) {
      console.log('mount', currentVideo);
      onMount();
    }
  }, [id, playerRef, videoRef, audioRef, currentVideo, videoChanging, onMount,]);

  useEffect(() => {
    return () => {
      console.log('unmount');
    }
  }, [controller,]);

  const getViews = () => {
    if (!currentVideo || !currentVideo.views) {
      return '-';
    }
    return humanReadable(currentVideo.views) + ' views';
  };

  const getLikes = () => {
    if (!currentVideo || !currentVideo.likes) {
      return '-';
    }
    return humanReadable(currentVideo.likes);
  };

  const humanReadable = (number) => {
    if (number > 1000000) {
      return (Math.round(number / 100000) / 10) + 'M';
    } else if (number > 1000) {
      return (Math.round(number / 100) / 10) + 'K';
    } else {
      return number;
    }
  };

  const onRating = (rating) => {
    if (settings.googleAPIKey !== '') {
      // google API Key can't submit rating
      return;
    }
    if (currentVideo.rating === rating) {
      currentVideo.rating = 'none';
    } else {
      currentVideo.rating = rating;
    }
    setRating(currentVideo.rating);

    // send to API
    const obj = {
      'namespace': 'videos',
      'action': 'rate',
      'source': 'web',
      'id': currentVideo.id,
      'rating': currentVideo.rating,
    };
    controller.send(obj);
  };

  const handleContextMenu = (event) => {
    event.preventDefault();
    event.stopPropagation();
    
    setContextMenu(
      contextMenu === null
        ? {
            mouseX: event.clientX + 2,
            mouseY: event.clientY - 6,
          }
        : // repeated contextmenu when it is already open closes it with Chrome 84 on Ubuntu
          // Other native context menus might behave different.
          // With this behavior we prevent contextmenu from the backdrop to re-locale existing context menus.
          null,
    );
  };

  const handleContextClose = () => {
    setContextMenu(null);
  };

  if (!currentVideo) {
    return <div>Loading...</div>;
  }

  return (
    <div key={'player-page'} className="page page-video" onContextMenu={handleContextMenu}>
      <Grid container spacing={2}>
        <Grid item sm={8}>
          <Box ref={playerRef} key="player" sx={{ width: '100%', aspectRatio: '16 / 9', objectFit: 'scale-down', overflow: 'hidden', cursor: (showCursor ? 'default' : 'none') }} onClick={onClickPlayer} onMouseMove={() => { handleStatus('mousemove'); }}>
            <Box sx={{ position: 'relative', width: '100%', 'height': '100%', backgroundColor: 'black' }}>
              <Fade in={showPlaying} timeout={250}>
                <div>
                  <Box sx={{ position: 'absolute', left: '50%', top: '50%', marginLeft: '-2.5rem', marginTop: '-2.5rem', width: '5rem', height: '5rem', backgroundColor: '#aaa', borderRadius: '1rem' }}>
                    <PlayArrowIcon fontSize="large" sx={{ fontSize: '5rem' }} />
                  </Box>
                </div>
              </Fade>
              <Fade in={showPaused} timeout={250}>
                <div>
                  <Box sx={{ position: 'absolute', left: '50%', top: '50%', marginLeft: '-2.5rem', marginTop: '-2.5rem', width: '5rem', height: '5rem', backgroundColor: '#aaa', borderRadius: '1rem' }}>
                    <PauseIcon fontSize="large" sx={{ fontSize: '5rem' }} />
                  </Box>
                </div>
              </Fade>
              <video key={'video-' + currentVideo.id} ref={videoRef} style={{ width: '100%', height: '100%' }} autoPlay={false} muted={true} poster={controller.getVideoUrl(currentVideo.id + '-' + currentVideo.filename + '.jpg')}>
                <source src={controller.getVideoUrl(currentVideo.id + '-' + getResolution(currentVideo, 'file') + '-' + currentVideo.filename)}></source>
              </video>
              <audio key={'audio-' + currentVideo.id} ref={audioRef} autoPlay={false}>
                <source src={controller.getVideoUrl(currentVideo.id + '-' + getResolution(currentVideo, 'file') + '-' + currentVideo.filename)} />
              </audio>
              <Box onClick={(e) => { e.stopPropagation(); }} sx={{ position: 'absolute', display: 'flex', flexDirection: 'row', alignItems: 'center', width: '100%', pl: 0, pt: 0.5, pb: 0.5, height: '50px', bottom: (showStatus ? 0 : '-65px'), opacity: (showStatus ? 1 : 0), left: 0, textAlign: 'left', backgroundColor: 'rgba(0, 0, 0, 0.6)', transition: 'all 200ms ease-in-out' }}>
                <Tooltip title="Previous (shift + p)" placement="top" disableInteractive>
                  <IconButton onClick={() => { skip('previous') }} sx={{ ml: 2 }}>
                    <SkipPreviousIcon fontSize="large" />
                  </IconButton>
                </Tooltip>
                {!playing &&
                  <Tooltip title="Play (k)" placement="top" disableInteractive>
                    <IconButton onClick={togglePlay} sx={{ ml: 2 }}>
                      <PlayArrowIcon fontSize="large" />
                    </IconButton>
                  </Tooltip>
                }
                {playing &&
                  <Tooltip title="Pause (k)" placement="top" disableInteractive>
                    <IconButton onClick={togglePlay} sx={{ ml: 2 }}>
                      <PauseIcon fontSize="large" />
                    </IconButton>
                  </Tooltip>
                }
                <Tooltip title="Next (shift + n)" placement="top" disableInteractive>
                  <IconButton onClick={() => { skip('next') }} sx={{ ml: 2 }}>
                    <SkipNextIcon fontSize="large" />
                  </IconButton>
                </Tooltip>
                <VideoTime ref={videoTimeRef} />
                <Box sx={{ flex: 1 }} />
                <Chip label={videoInfo} />
                <Box>
                  <Tooltip title="Toggle Fullscreen (f)" placement="top" disableInteractive>
                    <IconButton onClick={toggleFullscreen} sx={{ mr: 2 }}>
                      {fullscreen && <FullscreenExitIcon fontSize="large" />}
                      {!fullscreen && <FullscreenIcon fontSize="large" />}
                    </IconButton>
                  </Tooltip>
                </Box>
                <Box sx={{ position: 'absolute', left: 0, top: '-15px', width: '100%' }}>
                  <VideoPlayerProgress ref={progressRef} key={'progress-' + currentVideo.id} controller={controller} currentVideo={currentVideo} onChangeProgress={onChangeProgress} />
                </Box>
              </Box>
              <Snackbar open={showSponsorSkipped} anchorOrigin={{ vertical: "bottom", horizontal: "right" }}>
                <Alert severity="warning" sx={{ width: '100%' }}>
                  Sponsor has been skipped.
                </Alert>
              </Snackbar>
            </Box>
          </Box>
          <Box>
            <Typography sx={{ mt: 1, mb: 1, fontWeight: 'bold', textAlign: 'left', fontSize: '1.2rem' }}>
              {currentVideo.title}
            </Typography>
          </Box>
          <Box sx={{ mb: 2, display: 'flex', flexDirection: 'row', alignItems: 'center', width: 'fit-content' }}>
            <img src={currentVideo.channelImageUrl ? currentVideo.channelImageUrl : defaultChannelImage} alt="Channel" style={{ width: '40px', overflow: 'hidden', float: 'left' }} />
            <Box sx={{ display: 'inline-block', flex: 1, ml: 2, flexWrap: 'no-wrap', textAlign: 'left' }}>
              <Typography sx={{ fontWeight: '500', fontSize: '1.0rem' }}>{currentVideo.channelName ? currentVideo.channelName : '-'}</Typography>
              <Typography nowrap="true" sx={{ fontWeight: '300', fontSize: '0.8rem', color: '#ddd', whiteSpace: 'nowrap' }}>{getViews()} | {currentVideo.date ? currentVideo.date : '-'}</Typography>
            </Box>
            <Box sx={{ display: 'flex', flex: 1, alignItems: 'center', width: 'fit-content', ml: 2, mt: 0.5, backgroundColor: '#444', borderRadius: '0.5rem', pt: 1, pr: 1.5, pb: 1, pl: 1.5 }} changerating={rating}>
              <Box sx={{ display: 'flex', flex: 1, cursor: 'pointer' }} onClick={() => onRating('like')}>
                {currentVideo.rating !== 'like' && <ThumbUpOffAltIcon fontSize="medium" />}
                {currentVideo.rating === 'like' && <ThumbUpAltIcon fontSize="medium" />}
                <Typography sx={{ flex: 1, ml: 1 }} component="span">{getLikes()}</Typography>
              </Box>
              <Divider orientation="vertical" variant="middle" sx={{ ml: 1, mr: 1, mt: 0, mb: 0, 'height': '28px' }} />
              <Box sx={{ display: 'flex', cursor: 'pointer' }} onClick={() => onRating('dislike')}>
                {currentVideo.rating !== 'dislike' && <ThumbDownOffAltIcon fontSize="medium" />}
                {currentVideo.rating === 'dislike' && <ThumbDownAltIcon fontSize="medium" />}
              </Box>
            </Box>
          </Box>
          <Card variant="outlined" sx={{ textAlign: 'left', color: '#ccc', whiteSpace: 'pre-line', p: 2 }}>
            <Typography sx={{}}>
              {currentVideo.description}
            </Typography>
          </Card>
        </Grid>
        <Grid item sm={4}>
          <VideoList key="videolist" ref={videoListRef} controller={controller} currentVideo={currentVideo} playVideo={playVideo} />
        </Grid>
      </Grid>
      <VideoContextMenu source="player" video={currentVideo} controller={controller} contextMenu={contextMenu} onClose={handleContextClose} />
    </div>
  );
});