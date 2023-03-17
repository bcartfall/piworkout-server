/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-03-17
 * See README.md
 */

import React, { useState, useImperativeHandle, } from 'react';
import { Chip } from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';

export default React.forwardRef(function VideoTime(_, ref) {
  const [videoTime, setVideoTime] = useState('0:00 / 0:00');

  useImperativeHandle(ref, () => {
    return {
      updateTime: (nTime) => {
        if (videoTime !== nTime) {
          setVideoTime(nTime);
        }
      },
    };
  }, [videoTime, setVideoTime,]);

  return <Chip label={videoTime} avatar={<AccessTimeIcon />} />;
});