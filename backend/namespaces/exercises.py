"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-10-02
 * See README.md
"""

import struct

import logging
logger = logging.getLogger('piworkout-server')

def binaryReceive(message, queue):
    """
    Handle exercises
    """
    
    I = struct.Struct('<I') # unsigned 4 bytes integer little-endian
    
    uuid = message[44:80].decode('ascii').rstrip('\x00')
    #action = message[80:88].decode('ascii').rstrip('\x00')
    exerciseId = I.unpack(message[88:92])[0]
    length = I.unpack(message[92:96])[0]
    
    path = './images/exercises/' + str(exerciseId) + '.jpg'
    
    fp = open(path, 'wb')
    buffer = message[96:(length + 96)]
    print('Saving exercise image ' + str(len(buffer)) + ' bytes')
    fp.write(buffer)