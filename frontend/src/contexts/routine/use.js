/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-07-13
 * See README.md
 */

import { useContext } from 'react';
import RoutineContext from './context';

export default function useRoutine() {
  return useContext(RoutineContext);
}