/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
 */
/* global BigInt */

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
import { CircularProgress, Typography, Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions, Button, LinearProgress, } from '@mui/material';

import Layout from './pages/Layout';
import Main from './pages/Main';
import Settings from './pages/Settings';
import Player from './pages/Player';
import { defaultSnack, Controller } from './controllers/Controller';

const FILE_BUFFER_SIZE = (1024 * 1024) - (96 * 1024); // chunk size

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
  let sendingFile = false;

  const dragRef = useRef(0);
  const [dialog, setDialog] = useState(null);

  const onDrop = (event) => {
    if (event.dataTransfer.types.includes('text/uri-list')) {
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
    } else if (event.dataTransfer.types.includes('Files') && !sendingFile) {
      const dialogFileProgress = (file, progress) => {
        setDialog(
          <Dialog open={true}>
            <DialogTitle>Add Video</DialogTitle>
            <DialogContent>
              <DialogContentText>
                Uploading file {file.name}.
              </DialogContentText>
              <LinearProgress className="fileUploadProgress" color="primary" variant="determinate" value={progress * 100} />
            </DialogContent>
          </Dialog>
        );
      };
    
      for (const file of event.dataTransfer.files) {
        //console.log(file);

        if (!file.type.startsWith('video')) {
          setDialog(
            <Dialog open={true}>
              <DialogTitle>Error Uploading Video</DialogTitle>
              <DialogContent>
                <DialogContentText>
                  Expecting video file. Mime-type {file.type} not supported.
                </DialogContentText>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => {setDialog(null)}}>OK</Button>
              </DialogActions>
            </Dialog>
          );
          break;
        }

        dialogFileProgress(file, 0);

        // send file to websocket server
        const totalBytes = file.size;
        const uuid = controller.current.generateUuid();
        let part = 0;
        let sentBytes = 0;
        let start = -FILE_BUFFER_SIZE;
        let end = 0;
        sendingFile = true;

        const reader = new FileReader();
        const next = () => {
          // send next part to server
          start += FILE_BUFFER_SIZE;
          end += FILE_BUFFER_SIZE;
          reader.readAsArrayBuffer(file.slice(start, end));
        };

        reader.onload = (readerEvent) => {
          const fileBuffer = readerEvent.target.result;
          const length = fileBuffer.byteLength;

          console.log('Sending part ' + part, 'sentBytes=' + sentBytes, 'length=' + length);

          // send to websocket server
          // determine size of ArrayBuffer for this ws message
          //   8 bytes magic number
          //   8 bytes (string) version
          //   28 bytes (string) namespace
          //   36 bytes (string) uuid
          //   8 bytes (string) action
          //   4 bytes (uint) part 
          //   4 bytes (uint) start
          //   4 bytes (uint) length - up to buffer_size
          //   8 bytes (uint64) total file size
          //   n bytes (length) data for upload
          const magicNumber = '\x89webSOK\n';

          let buffer = new ArrayBuffer(108 + length);
          let data = new DataView(buffer);
          //let offset = 0;
          const writeString = (str, offset) => {
            let l = str.length;
            for (let i = 0; i < l; i++) {
              data.setUint8(offset++, str.charCodeAt(i));
            }
            return offset;
          };
          const writeUInt32 = (i, offset) => {
            data.setUint32(offset, i, true);
            offset += 4;
            return offset;
          };
          const writeUInt64 = (i, offset) => {
            data.setBigUint64(offset, i, true);
            offset += 8;
            return offset;
          };

          writeString(magicNumber, 0);
          writeString('1.0.0', 8);
          writeString('file-upload', 16);
          writeString(uuid, 44);
          writeString('store', 80);
          writeUInt32(part, 88);
          writeUInt32(start, 92);
          writeUInt32(length, 96); // 96
          writeUInt64(BigInt(totalBytes), 100); // 100

          // copy video binary data to array buffer
          new Uint8Array(buffer).set(new Uint8Array(fileBuffer), 108);

          // update progress
          part++;
          sentBytes += length;
          const progress = sentBytes / totalBytes;
          dialogFileProgress(file, progress);

          // send to websocket
          controller.current.send(buffer, 'arrayBuffer');

          // send next part
          if (sentBytes >= totalBytes) {
            // done
            setDialog(null);
            sendingFile = false;

            // complete message
            buffer = new ArrayBuffer(92 + file.name.length);
            data = new DataView(buffer);
            writeString(magicNumber, 0);
            writeString('1.0.0', 8);
            writeString('file-upload', 16);
            writeString(uuid, 44);
            writeString('cmpt', 80);
            writeUInt32(file.name.length, 88);
            writeString(file.name, 92);
            controller.current.send(buffer, 'arrayBuffer');
          } else {
            const waitForBuffer = () => {
              const bufferedAmount = controller.current.getClient().getBufferedAmount();
              if (bufferedAmount > 0) {
                setTimeout(() => {
                  waitForBuffer();
                }, 1);
              } else {
                next();
              }
            };
            waitForBuffer();
          }
        };
        next();
      }
    }
  };

  const onDragEnter = (event) => {
    dragRef.current++;
    if (event.dataTransfer.types.includes('text/uri-list')) {
      // show dragging dialog for url
      setDialog(
        <Dialog open={true}>
          <DialogTitle>Add Video</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Drop YouTube URL to Add Video to YouTube Playlist.
            </DialogContentText>
          </DialogContent>
        </Dialog>
      );
    } else if (event.dataTransfer.types.includes('Files') && !sendingFile) {
      // show dragging dialog for files
      setDialog(
        <Dialog open={true}>
          <DialogTitle>Add Video</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Drop Physical File to Upload Video.
            </DialogContentText>
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