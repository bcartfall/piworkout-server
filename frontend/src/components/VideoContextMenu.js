/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-03-21
 * See README.md
 */

import React, { useCallback, } from 'react';

import { Menu, MenuItem, ListItemIcon, ListItemText, Button, Divider, } from '@mui/material';
import PlaylistRemoveIcon from '@mui/icons-material/PlaylistRemove';
import RestoreIcon from '@mui/icons-material/Restore';
import LinkIcon from '@mui/icons-material/Link';
import AccessTimeIcon from '@mui/icons-material/AccessTime';

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

  const actionCopyUrl = useCallback(() => {
    navigator.clipboard.writeText(video.url);

    controller.snack({
      message: 'Video URL copied to clipboard.',
    });

    return onClose();
  }, [video, onClose, controller, ]);

  const actionCopyUrlAtTime = useCallback(() => {
    navigator.clipboard.writeText(video.url + (video.url.includes('?') ? '&' : '?') + 't=' + Math.round(video.position));

    controller.snack({
      message: 'Video URL copied to clipboard.',
    });

    return onClose();
  }, [video, onClose, controller, ]);

  const actionShowLog = useCallback(() => {
    controller.logDialog(video);

    return onClose();
  }, [video, onClose, controller, ]);

  return (
    <Menu open={contextMenu !== null} onClose={onClose} anchorReference="anchorPosition" anchorPosition={contextMenu !== null ? {top: contextMenu.mouseY, left: contextMenu.mouseX} : undefined}>
      <MenuItem onClick={actionRemove}>
        <ListItemIcon>
          <PlaylistRemoveIcon fontSize="small" />
        </ListItemIcon>
        <ListItemText>Remove Video from Playlist</ListItemText>
      </MenuItem>
      <Divider />
      <MenuItem onClick={actionCopyUrlAtTime}>
          <ListItemIcon>
            <LinkIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Copy Video URL at Current Time</ListItemText>
        </MenuItem>
        <MenuItem onClick={actionCopyUrl}>
          <ListItemIcon>
            <LinkIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Copy Video URL</ListItemText>
        </MenuItem>
        <Divider />
        <MenuItem onClick={actionShowLog}>
          <ListItemIcon>
            <AccessTimeIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Show Log</ListItemText>
        </MenuItem>
    </Menu>
  )
};