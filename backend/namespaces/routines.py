"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-06-26
 * See README.md
"""

import model, server

import logging
logger = logging.getLogger('piworkout-server')

def receive(event, queue):
    #print('routines', event)
    if (event['action']):
        if (event['action'] == 'exercise'):
            # Specific Exercise
            if (event['method']):
                if (event['method'] == 'DELETE'):
                    exerciseDelete(event, queue)
                elif (event['method'] == 'PUT'):
                    exercisePut(event, queue)
                elif (event['method'] == 'GET'):
                    exerciseGet(event, queue)
            pass
        else:
            # List of Routines
            if (event['method']):
                if (event['method'] == 'DELETE'):
                    routineDelete(event, queue)
                elif (event['method'] == 'PUT'):
                    routinePut(event, queue)
                elif (event['method'] == 'GET'):
                    routineGet(event, queue)

def routineDelete(event, queue):
    routine = model.routines.byId(int(event['id']))
    if (routine == None):
        logger.warning('Routine not found.')
        return
    
    if (routine.exercises == None or len(routine.exercises) == 0):
        model.routines.remove(routine=routine)
        # update all clients
        broadcast()
    else:
        logger.warning('Routine is not empty.')
        
def routinePut(event, queue):
    logger.info('Routine PUT action')
    routine = None
    if ('id' in event):
        routine = model.routines.byId(int(event['id']))
    if (routine == None):
        # create new routine
        routine = model.Routine()
        model.routines.insert(routine=routine)
        
    data = event['data']
    
    routine.order = int(data['order'] or routine.order)
    routine.name = str(data['name'] or routine.name)
    routine.description = str(data['description'] or routine.description)
    routine.exercises = []
    
    model.routines.save(routine=routine)
    
    # update all clients
    broadcast()
    
def routineGet(event, queue):
    routine = None
    if (event['id']):
        routine = model.routines.byId(int(event['id']))
        
    if (routine == None):
        # entire list
        server.send(queue=queue, obj={
            'namespace': 'routines',
            'routines': data(),
        })
    else:
        # single routine
        server.send(queue=queue, obj={
            'namespace': 'routines',
            'routine': routine.toObject(),
        })
        
        
def exerciseDelete(event, queue):
    routine = model.routines.byId(int(event['routineId']))
    if (routine == None):
        logger.warning('Routine not found.')
        return
    
    exercise = None
    for item in routine.exercises:
        if (int(item.id) == int(event['exerciseId'])):
            exercise = item
            break
            
    if (exercise == None):
        logger.warning('Exercise not found in routine.')
        return
    routine.removeExercise(routine, exercise)
        
def exercisePut(event, queue):
    routine = model.routines.byId(int(event['routineId']))
    if (routine == None):
        logger.warning('Routine not found.')
        return
    
    exercise = None
    for item in routine.exercises:
        if (int(item.id) == int(event['exerciseId'])):
            exercise = item
            break
    
    if (exercise == None):
        # create new exercise
        exercise = model.Exercise()
        model.routines.insertExercise(routine, exercise)
        return
    
    exercise.routineId = int(routine.id)
    exercise.order = int(event['order'] or exercise.order)
    exercise.name = str(event['name'] or exercise.name)
    exercise.tooltip = str(event['tooltip'] or exercise.name)
    exercise.image = str(event['image'] or exercise.name)
    exercise.description = str(event['description'] or exercise.name)
    exercise.video_url = str(event['video_url'] or exercise.name)
    model.routines.saveExercise(routine, exercise)
    
    # update all clients
    broadcast()
    
def exerciseGet(event, queue):
    routine = model.routines.byId(int(event['routineId']))
    if (routine == None):
        logger.warning('Routine not found.')
        return
    
    exercise = None
    for item in routine.exercises:
        if (int(item.id) == int(event['exerciseId'])):
            exercise = item
            break
        
    if (exercise == None):
        # entire list
        a = []
        for item in routine.exercises:
            a.append(item.toObject())
        server.send(queue=queue, obj={
            'namespace': 'routines',
            'exercises': a,
        })
    else:
        # single routine
        server.send(queue=queue, obj={
            'namespace': 'routines',
            'exercise': exercise.toObject(),
        })

def data():
    res = []
    logger.info('routines.data()')
    with model.routines.dataMutex():
        for item in model.routines.data(False, False):
            res.append(item.toObject())
    return res

def broadcast(sender = None):
    server.broadcast(obj={
        'namespace': 'routines',
        'routines': data(),
    }, sender=sender)
