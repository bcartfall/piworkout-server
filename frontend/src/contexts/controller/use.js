/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-07-13
 * See README.md
 */

import { useContext } from 'react';
import ControllerContext from './context';

export default function useController() {
  return useContext(ControllerContext);
}