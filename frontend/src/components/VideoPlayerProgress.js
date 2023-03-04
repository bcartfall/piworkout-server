/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import jDataView from 'jdataview';
import { Buffer } from 'buffer';

import React, { useRef, useEffect, useCallback } from 'react';
import { LinearProgress } from '@mui/material';

export default function VideoPlayerProgress({ currentVideo, progress, onChangeProgress, controller }) {
  const progressRef = useRef(null);
  const bif = useRef(null);
  const storyBoardImage = useRef(null);
  const mouseState = useRef('up');
  const tooltip = useRef(null);

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

    if (tooltip.current) {
      // set tooltip position and text
      tooltip.current.innerHTML = duration; 
      let ttWidth = tooltip.current.offsetWidth;

      let ttX = Math.max(x - (ttWidth / 2), 0);
      if (ttX + ttWidth > rect.width) {
        ttX = rect.width - ttWidth;
      }
      tooltip.current.style.left = ttX + 'px';
    }

    if (storyBoardImage.current) {
      // set storyboard image
      storyBoardImage.current.src = getStoryboard(time);

      let sbX = Math.max(x - 160, 0);
      if (sbX + 320 > rect.width) {
        sbX = rect.width - 320;
      }
      storyBoardImage.current.style.left = sbX + 'px';
    }

    if (mouseState.current === 'down') {
      seekFromMouse(event);
    }
  };

  const onMouseEnter = useCallback(() => {
    if (tooltip.current) {
      tooltip.current.style.display = 'block';
    }
    if (storyBoardImage.current && bif.current && bif.current[currentVideo.id]) {
      storyBoardImage.current.style.display = 'block';
    }
  }, [storyBoardImage, bif, currentVideo,]);

  const onMouseLeave = (event) => {
    if (tooltip.current) {
      tooltip.current.style.display = 'none';
    }
    if (storyBoardImage.current) {
      storyBoardImage.current.style.display = 'none';
    }

    if (mouseState.current === 'down') {
      seekFromMouse(event);
    }
    mouseState.current = 'up';
  };

  const seekFromMouse = (event) => {
    event.preventDefault();
    event.stopPropagation();
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;

    const mousePos = x / rect.width;
    const time = currentVideo.duration * mousePos;
    onChangeProgress(time);
  };

  const onMouseDown = (event) => {
    mouseState.current = 'down';
    seekFromMouse(event);
  };

  const onMouseUp = (event) => {
    mouseState.current = 'up';
  };

  const getStoryboard = useCallback((position) => {
    let buffer = 'data:image/jpeg;base64,';
    if (!bif.current) {
      return buffer;
    }

    if (!bif.current[currentVideo.id]) {
      return buffer;
    }
    const obj = bif.current[currentVideo.id];

    const index = Math.floor(position / (obj.interval / 1000));
    const frame = obj.bifIndex[index];
    if (!frame) {
      return buffer;
    }

    // buf.toString('base64')
    buffer += Buffer.from(new Uint8Array(obj.arrayBuffer.slice(frame.offset, frame.offset + frame.length))).toString('base64');

    //buffer += btoa(String.fromCharCode.apply(null, new Uint8Array(obj.arrayBuffer.slice(frame.offset, frame.offset + frame.length))));
    return buffer;
  }, [bif, currentVideo,]);

  useEffect(() => {
    if (!bif.current) {
      bif.current = {};
    }
    if (!bif.current || !bif.current[currentVideo.id]) {
      const url = controller.getVideoUrl(currentVideo.id + '-' + currentVideo.filename + '.bif')
      console.log('Loading bif file.', url);

      const request = new XMLHttpRequest();

      request.open('GET', url, true);
      request.responseType = 'arraybuffer';

      request.onload = (event) => {
        if (event.target.status !== 200) {
          return;
        }

        // parse data
        const arrayBuffer = event.target.response;
        const data = new jDataView(arrayBuffer);

        // version
        //const version = data.getUint32(8, true);

        // number of images
        const imagesCount = data.getUint32(12, true);

        // framewise seperation
        const interval = data.getUint32(16, true);

        // index
        let bifIndex = [];
        let indexOffset = 64;
        for (let i = 0; i < imagesCount; i++) {
          const index = data.getUint32(indexOffset, true);
          const offset = data.getUint32(indexOffset + 4, true); // image offset
          const nextOffset = data.getUint32(indexOffset + 12, true); // next image offset

          const a = {
            index,
            offset,
            length: nextOffset - offset,
          };
          bifIndex.push(a);
          //console.log(a);
          indexOffset += 8;
        }

        bif.current[currentVideo.id] = {
          arrayBuffer,
          imagesCount,
          interval,
          bifIndex,
        };

        // test
      };

      request.send(null);
    }
  }, [bif, currentVideo, controller, getStoryboard,]);

  return (
    <>
      <LinearProgress ref={progressRef} variant="determinate" className="videoPlayerProgress" value={progress} sx={{ height: '15px', cursor: 'pointer' }} onMousfDown={onMouseDown} onMouseUp={onMouseUp} onMouseMove={onMouseMove} onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave} />
      <span ref={tooltip} style={{ position: 'absolute', width: 'auto', padding: '4px 8px', textAlign: 'center', fontSize: '0.8rem', zIndex: '1', top: '-35px', borderRadius: '4px', backgroundColor: '#444', color: '#fff', display: 'none' }}>0:00</span>
      <img ref={storyBoardImage} src="" alt="Story Board" style={{ position: 'absolute', width: '320px', height: '180px', zIndex: '1', top: '-226px', borderRadius: '8px', border: '2px solid white', display: 'none' }} />
    </>
  );
}