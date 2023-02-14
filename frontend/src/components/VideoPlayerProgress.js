/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import React, { useState, useRef } from 'react';

import { LinearProgress, Tooltip } from '@mui/material';

export default function VideoPlayerProgress({ currentVideo, progress, onChangeProgress }) {
  const [seekTooltip, setSeekTooltip] = useState('0:00');
  const positionRef = useRef({
    x: 0,
    y: 0,
  });
  const popperRef = useRef(null);
  const progressRef = useRef(null);

  const onMouseMove = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;

    const mousePos = x / rect.width;
    const time = currentVideo.duration * mousePos;

    let duration = '';
    const hours = Math.floor(time / 3600).toString(),
      minutes = Math.floor((time / 60) % 60).toString(),
      seconds = Math.floor(time % 60).toString();
    if (hours > 0) {
      duration = hours.padStart(2, '0') + ':';
    }
    duration += minutes.padStart(2, '0') + ':' + seconds.padStart(2, '0');

    setSeekTooltip(duration);

    // tooltip follows mouse on x only
    positionRef.current = { x: event.clientX, y: event.clientY };

    if (popperRef.current != null) {
      popperRef.current.update();
    }
  };

  const onClick = (event) => {
    event.preventDefault();
    event.stopPropagation();
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;

    const mousePos = x / rect.width;
    const time = currentVideo.duration * mousePos;
    onChangeProgress(time);
  };

  return (
    <Tooltip 
      title={seekTooltip} 
      placement="top" 
      arrow 
      enterDelay={0} 
      leaveDelay={0}
      PopperProps={{
        popperRef,
        anchorEl: {
          getBoundingClientRect: () => {
            return new DOMRect(
              positionRef.current.x,
              progressRef.current.getBoundingClientRect().y,
              0,
              0,
            );
          },
        },
      }}
    >
      <LinearProgress ref={progressRef} variant="determinate" className="videoPlayerProgress" value={progress} sx={{ height: '15px', cursor: 'pointer' }} onClick={onClick} onMouseMove={onMouseMove} />
    </Tooltip>
  );
}