"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import sys
import os
import logging
from logging.handlers import RotatingFileHandler

import model, server
from threads import downloader, listfetch, sbgenerator

# setup logger
logger = logging.getLogger('piworkout-server')
handler = RotatingFileHandler('./log/piworkout-server.log', maxBytes=10 * 1024 * 1024, backupCount=8)
formatter = logging.Formatter('%(asctime)s,%(msecs)03d %(levelname)-8s %(message)s [%(filename)s:%(lineno)d]')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

stdout_handler = logging.StreamHandler(stream=sys.stdout)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

def main():   
    # allow localhost
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # threads
    downloader.run()
    listfetch.run()
    sbgenerator.run()

    # websocket server
    host = os.environ['BACKEND_HOST']
    port = os.environ['BACKEND_PORT']
    logger.info('Starting websocket on ' + host + ':' + port)
    server.start()

if __name__ == "__main__":
    try:
        # allow localhost
        main()
    finally:
        # exit downloader thread gracefully
        downloader.close()
        listfetch.close()
        sbgenerator.close()

        # close db
        model.close()
        logger.info('closing app')