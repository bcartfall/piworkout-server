/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-07-13
 * See README.md
 */

import { useState, useCallback, useRef, useEffect, } from 'react';
import ControllerContext from './context';
import { Controller } from '../../controllers/Controller';
import { defaultSnack } from '../../controllers/Controller';

export default function ControllerProvider({ children, isElectron, failedToConnect, setFailedToConnect, connected, setConnected, loaded, setLoaded, }) {
  const controller = useRef();

  const [layout, setLayout] = useState({
    snack: { ...defaultSnack },
    logDialog: {open: false, video: null},
    title: '',
  });

  const [settings, setSettings] = useState({
    audioDelay: '',
    networkDelay: '',
    videoQuality: '',
    playlistUrl: '',
    youtubeCookie: '',
    googleAPIKey: '',
  });
  const [videos, setVideos] = useState([]);

  const [routines, setRoutines] = useState([]);
  const [currentRoutine, setCurrentRoutine] = useState(null);
  const [currentExercise, setCurrentExercise] = useState(null);

  useEffect(() => {
    if (!controller.current) {
      // setup controller
      controller.current = new Controller({ layout, setLayout, settings, setSettings, videos, setVideos, routines, setRoutines, connected, setConnected, setLoaded, isElectron });
      controller.current.setupClient();
      controller.current.getClient().onFailedToConnect(() => {
        console.log('setting on failed to connect');
        setFailedToConnect(true);
      });
      }
}, [controller, layout, settings, videos, setFailedToConnect, isElectron, setConnected, setLoaded, routines, setRoutines, connected, ]);

  const onKeyDown = useCallback((event) => {
    return controller.current.onKeydown(event);
  }, [controller]);

  useEffect(() => {
      // listen to keyevents
      document.addEventListener('keydown', onKeyDown, true);

      return () => {
        // cleanup events
        //console.log('cleanup');
        document.removeEventListener('keydown', onKeyDown, true);
      };
  }, [onKeyDown]);

  const value = {
    state: { routines, currentRoutine, currentExercise, layout, videos, settings, connected, },
    actions: { setRoutines, setCurrentRoutine, setCurrentExercise, setLayout, setVideos, setSettings, setConnected, },
    controller: controller.current,
  };

  return (
    <ControllerContext.Provider value={value}>
      {children}
    </ControllerContext.Provider>
  )
}