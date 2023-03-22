/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-03-21
 * See README.md
 */

import React, { useCallback, } from 'react';

import { Menu, MenuItem, ListItemIcon, ListItemText, Button, } from '@mui/material';
import PlaylistRemoveIcon from '@mui/icons-material/PlaylistRemove';
import RestoreIcon from '@mui/icons-material/Restore';

export default function VideoContextMenu({ video, controller, contextMenu, onClose, updateVideos, }) {
  const [videos, setVideos] = controller.videosUseState();

  const actionRemove = useCallback(() => {
    console.log('removing video', video);
    let nVideos = [...videos];
    // remove video.id
    for (let i in videos) {
      if (videos[i].id === video.id) {
        nVideos.splice(i, 1);
        break;
      }
    }
    setVideos(nVideos);

    if (updateVideos) {
      updateVideos(nVideos);
    }

    const undoRemove = () => {
      console.log('undo delete video');

      controller.snack({
        open: false,
      });

      controller.send({
        'namespace': 'videos',
        'action': 'add',
        'url': video.url,
        'order': video.order,
        'source': video.source,
      });
    };

    // set snack and set undelete
    controller.snack({
      message: 'Video has been removed from playlist.',
      action: (
        <Button variant="outlined" color="warning" size="small" onClick={undoRemove}>
          <RestoreIcon fontSize="small" sx={{ mr: 0.5 }} /> Undo
        </Button>
      ),
    });

    controller.send({
      'namespace': 'videos',
      'action': 'remove',
      'id': video.id,
    });

    return onClose();
  }, [video, onClose, videos, setVideos, controller, updateVideos, ]);

  return (
    <Menu open={contextMenu !== null} onClose={onClose} anchorReference="anchorPosition" anchorPosition={contextMenu !== null ? {top: contextMenu.mouseY, left: contextMenu.mouseX} : undefined}>
      <MenuItem onClick={actionRemove}>
        <ListItemIcon>
          <PlaylistRemoveIcon fontSize="small" />
        </ListItemIcon>
        <ListItemText>Remove Video from Playlist</ListItemText>
      </MenuItem>
    </Menu>
  )
};