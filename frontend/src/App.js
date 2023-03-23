/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { HTML5Backend } from 'react-dnd-html5-backend'
import { DndProvider } from 'react-dnd'

import './App.css';

import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { CircularProgress, Typography, Dialog, DialogTitle, DialogContent, } from '@mui/material';

import Layout from './pages/Layout';
import Main from './pages/Main';
import Settings from './pages/Settings';
import Player from './pages/Player';
import { defaultSnack, Controller } from './controllers/Controller';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
  },
});

export default function App(props) {
  const [layout, setLayout] = useState({
    snack: { ...defaultSnack },
    title: '',
  });

  const [connected, setConnected] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [settings, setSettings] = useState({
    audioDelay: '',
    networkDelay: '',
    videoQuality: '',
    playlistUrl: '',
    youtubeCookie: '',
    googleAPIKey: '',
  });
  const [videos, setVideos] = useState([]);

  // control layout and provide access to websocket server
  const controller = useRef();

  const onKeyDown = useCallback((event) => {
    return controller.current.onKeydown(event);
  }, [controller]);

  useEffect(() => {
    if (!controller.current) {
      // setup controller
      const isElectron = false;
      controller.current = new Controller({ layout, setLayout, settings, setSettings, videos, setVideos, setConnected, setLoaded, isElectron });
    }
  }, [controller, layout, settings, videos]);

  useEffect(() => {
      // listen to keyevents
      document.addEventListener('keydown', onKeyDown, true);

      return () => {
        // cleanup events
        //console.log('cleanup');
        document.removeEventListener('keydown', onKeyDown, true);
      };
  }, [onKeyDown]);

  /////////////////////////////////////////////////////////////
  // drag and drop files/urls
  const dragRef = useRef(0);
  const [dialog, setDialog] = useState(null);

  const onDrop = (event) => {
    const url = event.dataTransfer.getData("Url").trim();
    if (url !== "") {
      // add youtube url to playlist
      controller.current.send({
        'namespace': 'videos',
        'action': 'add',
        'url': url,
        'order': 0, // top
        'source': '', // determine on server
      });
    }
    setDialog(null);
  };

  const onDragEnter = (event) => {
    dragRef.current++;
    if (event.dataTransfer.types.includes("text/uri-list")) {
      // show dragging dialog
      //setOpacity(0.5);
      setDialog(
        <Dialog open={true}>
          <DialogTitle>Add Video</DialogTitle>
          <DialogContent>
            <Typography>
              Drop YouTube URL to Add Video to Playlist
            </Typography>
          </DialogContent>
        </Dialog>
      );
    } else {
      // clear dialog
      setDialog(null);
    }
  };

  const onDragLeave = (event) => {
    dragRef.current--;

    if (dragRef.current === 0) {
      setDialog(null);
    }
  };
  /////////////////////////////////////////////////////////////

  let routes = '';

  if (loaded) {
    routes = (
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout layout={layout} controller={controller.current} />}>
            <Route index element={<Main controller={controller.current} connected={connected} videos={videos} setVideos={setVideos} />} />
            <Route path="settings" element={<Settings controller={controller.current} connected={connected} settings={settings} />} />
            <Route path="player/:id" element={<Player controller={controller.current} settings={settings} />} />
            <Route path="*" element={<Main controller={controller.current} connected={connected} videos={videos} setVideos={setVideos} />} />
          </Route>
        </Routes>
      </BrowserRouter>
    );
  } else {
    routes = (
      <>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>
          Loading...
        </Typography>
      </>
    );
  }

  return (
    <DndProvider backend={HTML5Backend}>
      <ThemeProvider theme={darkTheme}>
        <CssBaseline />
        <div className="app" onDrop={onDrop} onDragEnter={onDragEnter} onDragLeave={onDragLeave}>
          {routes}
          {dialog !== null && dialog}
        </div>
      </ThemeProvider>
    </DndProvider>
  );
}