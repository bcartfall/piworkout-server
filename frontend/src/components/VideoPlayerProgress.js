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
  const sbb = useRef(null);
  const storyBoardSpriteMap = useRef(null);
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

    if (storyBoardSpriteMap.current) {
      // set storyboard sprite map
      updateStoryBoard(time, storyBoardSpriteMap.current)

      let sbW = storyBoardSpriteMap.current.offsetWidth, sbH = storyBoardSpriteMap.current.offsetHeight;

      let sbX = Math.max(x - (sbW / 2), 0);
      if (sbX + sbW > rect.width) {
        sbX = rect.width - sbW;
      }
      storyBoardSpriteMap.current.style.left = sbX + 'px';
      storyBoardSpriteMap.current.style.top = (-sbH - 46) + 'px';
    }

    if (mouseState.current === 'down') {
      seekFromMouse(event);
    }
  };

  const onMouseEnter = useCallback(() => {
    if (tooltip.current) {
      tooltip.current.style.display = 'block';
    }
    if (storyBoardSpriteMap.current && sbb.current && sbb.current[currentVideo.id]) {
      storyBoardSpriteMap.current.style.display = 'block';
    }
  }, [storyBoardSpriteMap, sbb, currentVideo,]);

  const onMouseLeave = (event) => {
    if (tooltip.current) {
      tooltip.current.style.display = 'none';
    }
    if (storyBoardSpriteMap.current) {
      storyBoardSpriteMap.current.style.display = 'none';
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

  const updateStoryBoard = useCallback((position, spriteMap) => {
    let buffer = '';
    if (!sbb.current) {
      spriteMap.style.backgroundImage = `url('data:image/jpeg;base64,${buffer}')`;
      spriteMap.style.backgroundPosition = '0px 0px';
    }

    if (!sbb.current[currentVideo.id]) {
      spriteMap.style.backgroundImage = `url('data:image/jpeg;base64,${buffer}')`;
      spriteMap.style.backgroundPosition = '0px 0px';
    }
    const obj = sbb.current[currentVideo.id];

    // get frame
    let iTime = 0, frameIndex = -1, frame = null, elapsed = -1;
    //console.log(obj.sbbIndex);
    for (let i in obj.sbbIndex) {
      const tFrame = obj.sbbIndex[i];
      iTime += tFrame.duration;

      if (position <= iTime) {
        // found frame
        frameIndex = i;
        frame = tFrame;
        elapsed = position - (iTime - tFrame.duration); // time elapsed in this frame
        break;
      }
    }

    // todo determine the x, y of the spriteMap

    const frameKey = `${frameIndex}`;
    //console.log('found frame', frameKey, obj.lastFrameKey)
    if (!frame) {
      return;
    }
    if (obj.lastFrameKey !== frameKey) {
      obj.lastFrameKey = frameKey;
      buffer = Buffer.from(new Uint8Array(obj.arrayBuffer.slice(frame.offset, frame.offset + frame.size))).toString('base64');
      spriteMap.style.backgroundImage = `url('data:image/jpeg;base64,${buffer}')`;
    }

    // set storyboard image width and height
    spriteMap.style.width = obj.width + 'px';
    spriteMap.style.height = obj.height + 'px';

    // dermine position in spritemap based on fps and frame.duration
    const p = Math.floor(elapsed * obj.fps);
    console.log(p, obj.columns);
    const y = Math.floor(p / obj.columns),
      x = p % obj.columns;

    // set position of sprite map
    spriteMap.style.backgroundPosition = (-(x * obj.width)) + 'px ' + (-(y * obj.height)) + 'px';

  }, [sbb, currentVideo,]);

  useEffect(() => {
    if (!sbb.current) {
      sbb.current = {};
    }
    if (!sbb.current || !sbb.current[currentVideo.id]) {
      const url = controller.getVideoUrl(currentVideo.id + '-' + currentVideo.filename + '.sbb')
      console.log('Loading sbb file.', url);

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

        // frame width and height
        const width = data.getUint32(16, true);
        const height = data.getUint32(20, true);

        // story board frames
        const fps = data.getFloat64(24, true);

        // number of cols and rows in each image
        const rows = data.getUint32(32, true);
        const columns = data.getUint32(36, true);

        // index
        let sbbIndex = [];
        let indexOffset = 64;
        for (let i = 0; i < imagesCount; i++) {
          const a = {
            index: data.getUint32(indexOffset, true),
            offset: data.getUint32(indexOffset + 4, true),
            size: data.getUint32(indexOffset + 8, true),
            duration: data.getFloat64(indexOffset + 12, true),
          };
          indexOffset += 20;
          sbbIndex.push(a);
        }

        const obj = {
          arrayBuffer,
          lastFrameKey: '',
          imagesCount,
          width,
          height,
          fps,
          rows,
          columns,
          sbbIndex,
        };
        //console.log('sbb', obj);
        sbb.current[currentVideo.id] = obj;
      };

      request.send(null);
    }
  }, [sbb, currentVideo, controller, updateStoryBoard,]);

  return (
    <>
      <LinearProgress ref={progressRef} variant="determinate" className="videoPlayerProgress" value={progress} sx={{ height: '15px', cursor: 'pointer' }} onMouseDown={onMouseDown} onMouseUp={onMouseUp} onMouseMove={onMouseMove} onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave} />
      <span ref={tooltip} style={{ position: 'absolute', width: 'auto', padding: '4px 8px', textAlign: 'center', fontSize: '0.8rem', zIndex: '1', top: '-35px', borderRadius: '4px', backgroundColor: '#444', color: '#fff', display: 'none' }}>0:00</span>
      <div ref={storyBoardSpriteMap} style={{ position: 'absolute', width: '320px', height: '180px', zIndex: '1', top: '-226px', borderRadius: '4px', border: '2px solid white', display: 'none', backgroundPositionX: 0, backgroundPositionY: 0 }} />
    </>
  );
}