/**
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-06-22
 * See README.md
 */

import React, { useCallback, useState, } from 'react';
import useRoutine from '../contexts/routine/use';

import { FormControl, Tooltip, Select, MenuItem, Typography, Box, IconButton, Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions, Button, TextField, List, ListItem, ListItemText, ListItemIcon, Divider, } from '@mui/material';

import ArrowLeftIcon from '@mui/icons-material/ArrowLeft';
import ArrowRightIcon from '@mui/icons-material/ArrowRight';
import SportsGymnasticsIcon from '@mui/icons-material/SportsGymnastics';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import defaultImage from '../assets/images/exercise.jpg';
import useController from '../contexts/controller/use';

export default function ExerciseToolbar() {
  const { state: { currentRoutine, routines, }, actions: { setRoutineById, setCurrentRoutine, } } = useRoutine();
  const { controller } = useController();

  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editRoutineForm, setEditRoutineForm] = useState({});
  const [showConfirmDeleteDialog, setShowConfirmDeleteDialog] = useState(false);
  const [showExerciseDialog, setShowExerciseDialog] = useState(false);
  const [exerciseForm, setExerciseForm] = useState({});
  const [currentExercise, setCurrentExercise] = useState(null);

  const handleCloseEdit = () => {
    setShowEditDialog(false);
  };

  const exerciseAction = useCallback((action) => {
    if (action === 'add') {
      setCurrentExercise(null);
      setExerciseForm({});
      setShowExerciseDialog(true);
    }
  }, []);

  const handleSubmitExercise = useCallback(() => {
    setCurrentExercise(null);
    setShowExerciseDialog(false);
  }, [setCurrentExercise, setShowExerciseDialog]);

  const handleSubmitEdit = useCallback(() => {
    if (currentRoutine) {
      // update
      controller.send({
        'namespace': 'routines',
        'action': 'routine',
        'method': 'PUT',
        'id': currentRoutine.id,
        'data': {
          'order': editRoutineForm.order,
          'name': editRoutineForm.name,
          'description': editRoutineForm.description,
          'exercises': currentRoutine.exercises,
        },
      });

      setCurrentRoutine({
        ...currentRoutine,
        order: editRoutineForm.order,
        name: editRoutineForm.name,
        description: editRoutineForm.description,
        exercises: currentRoutine.exercises,
      });
    } else {
      // add
      controller.send({
        'namespace': 'routines',
        'action': 'routine',
        'method': 'PUT',
        'data': {
          'order': routines.length,
          'name': editRoutineForm.name,
          'description': '',
        },
      });
    }

    setShowEditDialog(false);
  }, [controller, currentRoutine, setCurrentRoutine, editRoutineForm]);

  const openEdit = () => {
    setShowEditDialog(true);
    setEditRoutineForm({
      ...editRoutineForm,
      name: currentRoutine?.name,
      order: currentRoutine?.order,
      description: currentRoutine?.description,
    });
  };

  const handleDeleteEdit = useCallback(() => {
    setShowConfirmDeleteDialog(true);
  }, [setShowConfirmDeleteDialog]);

  const handleConfirmDelete = useCallback(() => {
    setShowConfirmDeleteDialog(false);
    setShowEditDialog(false);

    // send delete
    controller.send({
      'namespace': 'routines',
      'action': 'routine',
      'method': 'DELETE',
      'id': currentRoutine.id,
    });

    // select empty routine
    setCurrentRoutine(null);
  }, [setShowConfirmDeleteDialog, setShowEditDialog, currentRoutine,]);

  const changeEditForm = useCallback((attribute, e) => {
    // change form
    const nForm = {...editRoutineForm};
    nForm[attribute] = e.target.value;
    setEditRoutineForm(nForm);
  }, [editRoutineForm, setEditRoutineForm]);

  const changeExerciseForm = useCallback((attribute, e) => {
    if (attribute === 'image') {
      const file = e.target.files[0];
      const reader = new FileReader();

      reader.onloadend = () => {
        // send to websocket server
        // determine size of ArrayBuffer for this ws message
        //   8 bytes magic number
        //   8 bytes (string) version
        //   28 bytes (string) namespace
        //   36 bytes (string) uuid
        //   8 bytes (string) action
        //   4 bytes (uint) exercise_id
        //   4 bytes (uint) total file size
        //   n bytes (length) data for image
        const magicNumber = '\x89webSOK\n';
        const uuid = controller.generateUuid();
        const fileBuffer = reader.result;

        let buffer = new ArrayBuffer(96 + fileBuffer.byteLength);
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

        writeString(magicNumber, 0);
        writeString('1.0.0', 8);
        writeString('exercises', 16);
        writeString(uuid, 44);
        writeString('image', 80);
        writeUInt32(currentExercise ? currentExercise.id : 0, 88);
        writeUInt32(fileBuffer.byteLength, 92);
        new Uint8Array(buffer).set(new Uint8Array(fileBuffer), 96);
        
        controller.send(buffer, 'arrayBuffer');
        console.log('sending image', buffer);

        const readerDataUrl = new FileReader();
        readerDataUrl.onload = (e) => {
          const nForm = {...exerciseForm};
          nForm.image = e.target.result;
          setExerciseForm(nForm);
        }
        readerDataUrl.readAsDataURL(file);
      };

      reader.readAsArrayBuffer(file);
    } else {
      const nForm = {...exerciseForm};
      nForm[attribute] = e.target.value;
      setExerciseForm(nForm);
    }
  }, [exerciseForm, setExerciseForm, controller]);

  return (
    <>
      <Box backgroundColor="#434343" sx={{ height: '50px', display: 'flex', flexDirection: 'row', alignItems: 'center' }}>
        {/* This is a sample design */}
        <Typography sx={{ ml: 3.5 }}>Workout Routine:</Typography>
        <FormControl sx={{ ml: 2, minWidth: 120 }} size="small">
          <Select
            labelId="workout-routine"
            id="workout-routine"
            value={currentRoutine ? currentRoutine.id : 0}
            onChange={(e) => { setRoutineById(e.target.value) }}
          >
            <MenuItem value={0}>-</MenuItem>
            {routines.map((routine) => <MenuItem key={routine.id} value={routine.id}>{routine.name}</MenuItem>)}
          </Select>
        </FormControl>
        <Box sx={{ mr: 2, marginLeft: 'auto' }}>
          <Tooltip title="Edit Workout Routine" placement="top" disableInteractive>
            <IconButton onClick={openEdit} sx={{ }}>
              <EditIcon />
            </IconButton>
          </Tooltip>
        </Box>
        {/*
        {currentRoutine !== null && (
          <>
            <Typography sx={{ ml: 4 }}>Current Exercise:</Typography>
            <Tooltip title="Previous (Z)" placement="top" disableInteractive>
              <IconButton onClick={() => { }} sx={{ ml: 2 }}>
                <ArrowLeftIcon />
              </IconButton>
            </Tooltip>
            <Chip sx={{ }} avatar={<Avatar alt="" src={defaultImage} />} label="The 100 (Pilates)" />
            <Chip sx={{ ml: 0.5 }} label="11/22" variant="outlined" />
            <Tooltip title="Next (X)" placement="top" disableInteractive>
              <IconButton onClick={() => { }} sx={{ }}>
                <ArrowRightIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Play Exercise Video (V)" placement="top" disableInteractive>
              <IconButton onClick={() => { }} sx={{ }}>
                <SportsGymnasticsIcon />
              </IconButton>
            </Tooltip>
          </>
        )}
        <Box sx={{ mr: 2, marginLeft: 'auto' }}>
          <Tooltip title="Edit Workout Routine" placement="top" disableInteractive>
            <IconButton onClick={() => { setShowEditDialog(true) }} sx={{ }}>
              <EditIcon />
            </IconButton>
          </Tooltip>
        </Box>*/}
      </Box>
      {showEditDialog && (
        <Dialog open={true} onClose={handleCloseEdit} fullWidth={true} maxWidth="md">
          <DialogTitle>{currentRoutine ? 'Edit' : 'Add'} Routine</DialogTitle>
          <DialogContent>
            <DialogContentText>
              {currentRoutine ? 'Modify routine exercises.' : 'Add routine.'}
            </DialogContentText>
            <TextField
              autoFocus
              margin="dense"
              id="name"
              label="Routine Name"
              type="name"
              value={editRoutineForm?.name}
              fullWidth
              variant="standard"
              onChange={(e) => {changeEditForm("name", e)}}
            />
            <Box sx={{mt: 5}}>
              <Typography variant="h6">
                Exercises
              </Typography>
              <List>
                <ListItem>
                  <ListItemText
                    primary="Single Leg Stretch (Pilates)"
                    secondary="Lorem ipsum... Todo replace this with actual list..."
                  />
                  <ListItemIcon>
                    <KeyboardArrowUpIcon fontSize="small" sx={{ml: 2, cursor: 'pointer'}} onClick={() => {exerciseAction('up')}} />
                    <KeyboardArrowDownIcon fontSize="small" sx={{ml: 2, cursor: 'pointer'}} onClick={() => {exerciseAction('down')}} />
                    <DeleteIcon fontSize="small" sx={{ml: 4, cursor: 'pointer'}} onClick={() => {exerciseAction('delete')}} />
                    <EditIcon fontSize="small" sx={{ml: 2, cursor: 'pointer'}} onClick={() => {exerciseAction('edit')}} />
                  </ListItemIcon>
                </ListItem>
              </List>
              <Button variant="outlined" onClick={() => {exerciseAction('add')}}>Add Exercise</Button>
            </Box>
          </DialogContent>
          <DialogActions>
            {currentRoutine?.exercises.length === 0 && (
              <Button style={{mr: 5}} onClick={handleDeleteEdit}>Delete</Button>
            )}
            <Button onClick={handleCloseEdit}>Cancel</Button>
            <Button onClick={handleSubmitEdit}>{currentRoutine ? 'Update' : 'Add'} Routine</Button>
          </DialogActions>
        </Dialog>
      )}
      {showConfirmDeleteDialog && (
      <Dialog open={true} onClose={() => {setShowConfirmDeleteDialog(false)}}>
        <DialogTitle>Delete Routine</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Delete routine?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {setShowConfirmDeleteDialog(false)}} autoFocus>
            Cancel
          </Button>
          <Button onClick={handleConfirmDelete}>Confirm</Button>
        </DialogActions>
      </Dialog>
      )}
      {showExerciseDialog && (
      <Dialog open={true} onClose={() => {setShowConfirmDeleteDialog(false)}}>
        <DialogTitle>{currentExercise ? 'Edit': 'Add'} Exercise</DialogTitle>
        <DialogContent>
          <TextField autoFocus margin="dense" id="name" label="Name" type="text" value={exerciseForm?.name} fullWidth variant="standard" onChange={(e) => {changeExerciseForm('name', e)}} />
          <TextField margin="dense" id="tooltip" label="Tooltip" type="text" value={exerciseForm?.tooltip} fullWidth variant="standard" onChange={(e) => {changeExerciseForm('tooltip', e)}} />
          <TextField margin="dense" id="description" label="Description" type="text" value={exerciseForm?.description} fullWidth variant="standard" onChange={(e) => {changeExerciseForm('description', e)}} />
          <TextField margin="dense" id="video_url" label="Video URL" type="text" value={exerciseForm?.video_url} fullWidth variant="standard" onChange={(e) => {changeExerciseForm('video_url', e)}} />
          <Box sx={{mt: 4, mb: 4}} />
          <label htmlFor="upload-image">
            <Typography>Exercise Image</Typography>
            <Button variant="contained" component="span">
              Upload
            </Button>
            <input
              id="upload-image"
              hidden
              accept="image/*"
              type="file"
              onChange={(e) => {changeExerciseForm('image', e)}}
            />
            {exerciseForm?.image && (
              <img src={exerciseForm.image} alt="Preview" style={{maxWidth: '50px', display: 'block', marginTop: '15px'}} />
            )}
          </label>
          {currentExercise?.image && <img src={currentExercise.image} alt="Uploaded Image" width="50" />}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {setShowExerciseDialog(false)}}>
            Cancel
          </Button>
          <Button autoFocus onClick={handleSubmitExercise}>{currentExercise ? 'Add': 'Update'}</Button>
        </DialogActions>
      </Dialog>
      )}
    </>
  );
};