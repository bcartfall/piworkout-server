/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-07-13
 * See README.md
 */
/* global BigInt */

import React, { useRef, useState, } from 'react';
import useController from '../contexts/controller/use';

import { Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions, Button, LinearProgress, } from '@mui/material';

const FILE_BUFFER_SIZE = (1024 * 1024) - (96 * 1024); // chunk size

export default function Drag({ children }) {
  const controller = useController().controller;

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
        controller.send({
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
        const uuid = controller.generateUuid();
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
          controller.send(buffer, 'arrayBuffer');
  
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
            controller.send(buffer, 'arrayBuffer');
          } else {
            const waitForBuffer = () => {
              const bufferedAmount = controller.getClient().getBufferedAmount();
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

  return (
    <div className="app" onDrop={onDrop} onDragEnter={onDragEnter} onDragLeave={onDragLeave}>
      {children}
      {dialog !== null && dialog}
    </div>
  );
}