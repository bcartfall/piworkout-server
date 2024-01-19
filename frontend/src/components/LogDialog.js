/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-03-21
 * See README.md
 */

import React, { useEffect, useState, } from 'react';
import { Dialog, Paper, TableContainer, Table, TableHead, TableRow, TableCell, TableBody, CircularProgress, Grid, AppBar, Toolbar, Typography, Slide, } from '@mui/material';

import CloseIcon from '@mui/icons-material/Close';
import IconButton from '@mui/material/IconButton';
import useController from '../contexts/controller/use';

const Transition = React.forwardRef(function Transition(props, ref) {
  return <Slide direction="up" ref={ref} {...props} />;
});

export default function LogDialog({open, video, onClose}) {
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState([]);
  const controller = useController().controller;

  useEffect(() => {
    setLoading(true);
    if (!video) {
      return;
    }

    const load = async() => {
      // load logs
      controller.getClient().onMessageCall((event, json) => {
        // wait for response
        if (json.namespace === 'logs') {
          const items = json.items;

          let nRows = [];
          for (let i in items) {
            const item = items[i];
            const { id, action } = item;

            const dt = new Date(item.created_at * 1000);
            const created_at = dt.toString();

            let data = '';
            if (action === 'onAdded') {
              data = (<a href={item.data} target="_blank" rel="noreferrer">{item.data}</a>);
            } else if (action === 'onDownloaded') {
              data = item.data;
            } else {
              // parse time
              const p = item.data;
              const hours = Math.floor(p / 3600).toString(),
                minutes = Math.floor((p / 60) % 60).toString(),
                seconds = Math.round(p % 60).toString();
              if (hours > 0) {
                data = hours.padStart(2, '0') + ':';
              }
              data += minutes.padStart(2, '0') + ':' + seconds.padStart(2, '0');  
            }

            nRows.push({
              id,
              action,
              data,
              created_at,
            });
          }
          setLoading(false);
          setRows(nRows);
        }
      });

      // request logs
      controller.send({
        namespace: 'logs',
        method: 'GET',
        videoId: video.id,
      });
    };
    load();
  }, [setLoading, video, controller,]);

  return (
    <Dialog open={open} onClose={onClose} fullScreen TransitionComponent={Transition}>
      <AppBar sx={{ position: 'relative' }}>
        <Toolbar>
          <IconButton
            edge="start"
            color="inherit"
            onClick={onClose}
            aria-label="close"
          >
            <CloseIcon />
          </IconButton>
          <Typography sx={{ ml: 2, flex: 1 }} variant="h6" component="div">
            Video Log - {video?.title}
          </Typography>
        </Toolbar>
      </AppBar>
      {loading && (
        <Grid container justify="center" sx={{mt: 5}}>
          <CircularProgress sx={{ margin: '0 auto' }} />
        </Grid>
      )}
      {!loading && (
        <TableContainer component={Paper}>
          <Table sx={{ minWidth: 650 }} aria-label="simple table">
            <TableHead>
              <TableRow>
                <TableCell>Date Time</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Position</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow
                  key={row.id}
                  sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                >
                  <TableCell>{row.created_at}</TableCell>
                  <TableCell>{row.action}</TableCell>
                  <TableCell>{row.data}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Dialog>
  );
};