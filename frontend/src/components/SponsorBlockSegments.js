/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import React from 'react';

import { SPONSORBLOCK_SKIP_CATEGORIES, SPONSORBLOCK_SKIP_COLORS } from '../enums/SponsorBlock'

export default React.memo(function SponsorBlockSegments({ currentVideo, height, }) {
  // display sponsorblock segments
  let progressSegments = [];
  if (currentVideo.sponsorblock) {
    console.log('setup sponsorblock segments', currentVideo.sponsorblock);
    for (const i in currentVideo.sponsorblock.segments) {
      const segment = currentVideo.sponsorblock.segments[i];
      const categoryIndex = SPONSORBLOCK_SKIP_CATEGORIES.indexOf(segment.category);
      if (categoryIndex < 0) {
        continue;
      }

      const width = (segment.segment[1] - segment.segment[0]) / segment.videoDuration,
        left = segment.segment[0] / segment.videoDuration;

      progressSegments.push(<div key={'segment-' + i} style={{ position: 'absolute', width: (width * 100) + '%', 'height': height, left: (left * 100) + '%', top: 0, backgroundColor: SPONSORBLOCK_SKIP_COLORS[categoryIndex], pointerEvents: 'none', }} />);
    }
  }

  return progressSegments;
});