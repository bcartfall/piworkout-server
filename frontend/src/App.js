/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */

import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { DndProvider } from 'react-dnd';

import './App.css';

import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';

import React, { useState, } from 'react';
import { HashRouter, Routes, Route } from "react-router-dom";
import { CircularProgress, Typography } from '@mui/material';

import Layout from './pages/Layout';
import Main from './pages/Main';
import Settings from './pages/Settings';
import Player from './pages/Player';
import Drag from './components/Drag';
import RoutineProvider from './contexts/routine/provider';
import ControllerProvider from './contexts/controller/provider';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
  },
});

export default function App(props) {
  let routes = '';
  const [loaded, setLoaded] = useState(false);
  const [connected, setConnected] = useState(false);
  const [failedToConnect, setFailedToConnect] = useState(false);

  if (loaded || failedToConnect) {
    routes = (
      <HashRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Main />} />
            <Route path="settings" element={<Settings />} />
            <Route path="player/:id" element={<Player />} />
            <Route path="*" element={<Main />} />
          </Route>
        </Routes>
      </HashRouter>
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
        <ControllerProvider isElectron={false} loaded={loaded} setLoaded={setLoaded} connected={connected} setConnected={setConnected} failedToConnect={failedToConnect} setFailedToConnect={setFailedToConnect}>
          <RoutineProvider>
            <CssBaseline />
            <Drag>
              {routes}
            </Drag>
          </RoutineProvider>
        </ControllerProvider>
      </ThemeProvider>
    </DndProvider>
  );
}