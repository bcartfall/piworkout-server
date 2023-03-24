/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import React, { useState, } from 'react';

import { Card, Box, CardContent, CardMedia, Typography, LinearProgress, Grow } from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import VideoContextMenu from './VideoContextMenu';

export default function PiVideoPlayListItem({ video, controller, index, active, playVideo, updateVideos, }) {
  const [contextMenu, setContextMenu] = useState(null);

  const handleContextMenu = (event) => {
    event.preventDefault();
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

  let progress = 100, color;
  if (video.progress && video.progress.totalBytes) {
    // determine progress from how much has donwloaded
    progress = video.progress.progress * 100; // 0 to 100
    //console.log("downloading progress: " + progress, video.id, video.progress.downloadedBytes, video.progress.totalBytes)
    color = 'secondary';
  } else {
    // determine progress from how much we have watched
    progress = Math.round(video.position / video.duration * 10000) * 0.01;
    color = 'error';
  }
  progress = Math.min(100, Math.max(0, progress));

  let duration = '';
  let i = video.duration;
  const hours = Math.floor(i / 3600).toString(),
    minutes = Math.floor((i / 60) % 60).toString(),
    seconds = (i % 60).toString();
  if (hours > 0) {
    duration = hours.padStart(2, '0') + ':';
  }
  duration += minutes.padStart(2, '0') + ':' + seconds.padStart(2, '0');

  let numberElement;
  if (active) {
    numberElement = <PlayArrowIcon />;
  } else {
    numberElement = <Typography>{index + 1}.</Typography>;
  }

  return (
    <div onContextMenu={handleContextMenu}>
      <div key={video.id} onClick={() => {playVideo(video)}}>
        <Grow key={video.id} in={true}>
          <Card sx={{ display: 'flex', mb: 2 }} className={'piVideo piVideo-item' + (active ? ' active' : '')}>
            <Box sx={{ width: '24px', position: 'relative' }} className="number">
              {numberElement}
            </Box>
            <Box sx={{ position: 'relative', width: '30%', display: 'inherited', flexDirection: 'column' }}>
              {!active &&
                <Box className="cover">
                  <Box className="center">
                    <PlayArrowIcon fontSize="large" />
                  </Box>
                </Box>
              }
              <CardMedia
                component="img"
                image={controller.getVideoUrl(video.id + '-' + video.filename + ".jpg")}
                alt={video.title}
              />
              <Box sx={{ position: 'absolute', right: 8, bottom: 8, fontSize: '0.8rem', borderRadius: 2, backgroundColor: 'black', p: 0.25, pl: 0.75, pr: 0.75 }}>{duration}</Box>
            </Box>
            <Box sx={{ width: '65%', display: 'flex', flexDirection: 'column' }} className="content">
              <CardContent sx={{ flex: '1 0 auto' }} className="cardContent">
                <Typography component="div" className="title" variant="h6">
                  {video.title}
                </Typography>
              </CardContent>
              {progress > 0 &&
                <LinearProgress className="videoPlayerProgress" color={color} variant="determinate" value={progress} />}
            </Box>
          </Card>
        </Grow>
      </div>
      <VideoContextMenu video={video} controller={controller} updateVideos={updateVideos} contextMenu={contextMenu} onClose={handleContextClose} />
    </div>
  );
}