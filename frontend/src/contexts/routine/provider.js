/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-07-13
 * See README.md
 */

import { useEffect, useState } from 'react';
import RoutineContext from './context';
import useController from '../controller/use';

export default function RoutineProvider({ children }) {
  const { state: { currentRoutine, routines, }, actions: { setCurrentRoutine, }, controller } = useController();

  const setRoutineById = (id) => {
    let routine = null;
    for (let i of routines) {
      if (i.id === id) {
        routine = i;
        break;
      }
    }
    setCurrentRoutine(routine);
  };

  const value = {
    state: { routines, currentRoutine, },
    actions: { setRoutineById, setCurrentRoutine, },
  };
  return (
    <RoutineContext.Provider value={value}>
      {children}
    </RoutineContext.Provider>
  )
}