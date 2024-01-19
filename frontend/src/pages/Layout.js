/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import React, { useCallback, useState } from 'react';
import { Outlet, Link } from "react-router-dom";

import { AppBar, Toolbar, Typography, useScrollTrigger, Box, Fab, Fade, IconButton, Snackbar, Button, Dialog, DialogTitle, DialogContent, DialogContentText, TextField, DialogActions, } from '@mui/material';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import LiveTvIcon from '@mui/icons-material/LiveTv';
import SettingsIcon from '@mui/icons-material/Settings';
import ReplayIcon from '@mui/icons-material/Replay';
import AddLinkIcon from '@mui/icons-material/AddLink';

import LogDialog from '../components/LogDialog';
import ExerciseToolbar from '../components/ExerciseToolbar';
import useController from '../contexts/controller/use';

const exerciseToolbarEnabled = false; // todo enable when working on toolbar

function ScrollTop(props) {
  const { children, window } = props;
  // Note that you normally won't need to set the window ref as useScrollTrigger
  // will default to window.
  // This is only being set here because the demo is in an iframe.
  const trigger = useScrollTrigger({
    target: window ? window() : undefined,
    disableHysteresis: true,
    threshold: 100,
  });

  const handleClick = (event) => {
    const anchor = (event.target.ownerDocument || document).querySelector(
      '#back-to-top-anchor',
    );

    if (anchor) {
      anchor.scrollIntoView({
        block: 'center',
      });
    }
  };

  return (
    <Fade in={trigger}>
      <Box
        onClick={handleClick}
        role="presentation"
        sx={{ position: 'fixed', bottom: 16, right: 16 }}
      >
        {children}
      </Box>
    </Fade>
  );
}

export default function Layout(props) {
  const { state: { layout }, controller } = useController();
  const { snack } = layout;

  const closeLog = useCallback(() => {
    let nLayout = {...layout};
    nLayout.logDialog.open = false;
    controller.setLayout(nLayout);
  }, [controller, layout,]);

  const closeSnack = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }

    controller.closeSnack();
  };

  const refresh = () => {
    console.log('refresh()');
    controller.send({
      'namespace': 'videos',
      'action': 'refresh',
    });
  };

  ///////////////
  // add url link
  const [addUrlDialog, setAddUrlDialog] = useState(null);

  const onAddUrl = () => {
    // show add url dialog
    let url = '';
    const handleClose = () => {
      setAddUrlDialog(null);
    };
    const handleSubmit = (event) => {
      setAddUrlDialog(null);

      // send
      controller.send({
        'namespace': 'videos',
        'action': 'add',
        'url': url,
        'order': 0, // top
        'source': '', // determine on server
      });
    };
    const handleOnChange = (event) => {
      url = event.target.value;
    };

    setAddUrlDialog(
      <Dialog open={true} onClose={handleClose}>
        <DialogTitle>Add Video</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Enter in YouTube URL to add video to playlist.
          </DialogContentText>
          <TextField
            autoFocus
            margin="dense"
            id="url"
            label="YouTube URL"
            type="url"
            fullWidth
            variant="standard"
            onChange={handleOnChange}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button onClick={handleSubmit}>Add Video</Button>
        </DialogActions>
      </Dialog>
    );
  };
  ///////////////

  return (
    <>
      <AppBar color="primary">
        <Toolbar>
          <Typography
            variant="h6"
            noWrap
            sx={{
              mr: 2,
              display: { xs: 'none', md: 'flex' },
              fontWeight: 700,
              letterSpacing: '0rem',
              color: 'inherit',
              textDecoration: 'none',
              flexGrow: 1,
            }}
          >
            <Link to="/" className="link">
              <LiveTvIcon sx={{ mr: 1 }} /> {controller.getLayoutTitle()}
            </Link>
          </Typography>
          <Box sx={{ flexGrow: 0 }}>
            {addUrlDialog !== null && addUrlDialog}
            <IconButton sx={{ mr: 1 }} onClick={onAddUrl}>
              <AddLinkIcon />
            </IconButton>
            <IconButton sx={{ mr: 1 }} onClick={refresh}>
              <ReplayIcon />
            </IconButton>
            <Link to="/settings" className="link">
              <IconButton sx={{ p: 0, color: 'inherit' }}>
                <SettingsIcon />
              </IconButton>
            </Link>
          </Box>
        </Toolbar>
        { exerciseToolbarEnabled && (<ExerciseToolbar />)}
      </AppBar>
      <Toolbar id="back-to-top-anchor" />
      <Outlet />
      <ScrollTop {...props}>
        <Fab size="small" aria-label="scroll back to top">
          <KeyboardArrowUpIcon />
        </Fab>
      </ScrollTop>
      <Snackbar
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
        open={snack.open}
        message={snack.message}
        autoHideDuration={snack.autoHideDuration}
        onClose={closeSnack}
        action={snack.action}
        key="snackbar-top-right"
      />
      <LogDialog open={layout.logDialog.open} video={layout.logDialog.video} onClose={closeLog} />
    </>
  );
};
