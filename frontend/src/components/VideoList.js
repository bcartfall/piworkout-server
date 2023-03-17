/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-03-17
 * See README.md
 */

import React, { useState, useImperativeHandle, } from 'react';

import PiVideoPlayListItem from '../components/PiVideoPlayListItem';

export default React.forwardRef(function VideoList({ controller, playVideo, currentVideo, }, ref) {
  const [videos, setVideos] = useState(controller.getVideos());

  useImperativeHandle(ref, () => {
    return {
      updateVideos: (nVideos) => {
        setVideos([...nVideos]);
      },
    };
  }, [setVideos,]);

  return (
    <>
      {videos.map((video, index) => {
        if (video.title) {
          return <PiVideoPlayListItem key={video.id} index={index} video={video} active={currentVideo.id === video.id} controller={controller} playVideo={playVideo} />;
        }
        return '';
      })}
    </>
  );
});