/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import React from 'react';
import { Outlet, Link } from "react-router-dom";

import { AppBar, Toolbar, Typography, useScrollTrigger, Box, Container, Fab, Fade, IconButton, Snackbar } from '@mui/material';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import LiveTvIcon from '@mui/icons-material/LiveTv';
import SettingsIcon from '@mui/icons-material/Settings';
import CloseIcon from '@mui/icons-material/Close';
import ReplayIcon from '@mui/icons-material/Replay';

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
  const { layout, controller } = props;
  const { snack, title } = layout;

  const closeSnack = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }

    props.controller.closeSnack();
  };

  const refresh = () => {
    console.log('refresh()');
    controller.send({
      'namespace': 'videos',
      'action': 'refresh',
    });
  };

  return (
    <>
      <AppBar>
        <Toolbar>
          <Typography
            variant="h6"
            noWrap
            sx={{
              mr: 2,
              display: { xs: 'none', md: 'flex' },
              fontFamily: 'monospace',
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
            <IconButton sx={{ mr: 2 }} onClick={refresh}>
              <ReplayIcon />
            </IconButton>
            <Link to="/settings" className="link">
              <IconButton sx={{ p: 0, color: 'inherit' }}>
                <SettingsIcon />
              </IconButton>
            </Link>
          </Box>
        </Toolbar>
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
        action={<IconButton
          size="small"
          aria-label="close"
          color="inherit"
          onClick={closeSnack}
        >
          <CloseIcon fontSize="small" />
        </IconButton>}
        key="snackbar-top-right"
      />
    </>
  );
};
