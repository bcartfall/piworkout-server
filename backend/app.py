"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

import requests
import os

import model, server
from threads import downloader, listfetch, bifgenerator

def main():
    # allow localhost
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # threads
    downloader.run()
    listfetch.run()
    bifgenerator.run()

    # socket server
    host = os.environ['BACKEND_HOST']
    port = os.environ['BACKEND_PORT']
    print('Starting websocket on ' + host + ':' + port)
    server.start()



if __name__ == "__main__":
    try:
        # allow localhost
        main()
    finally:
        # exit downloader thread gracefully
        downloader.close()
        listfetch.close()
        bifgenerator.close()

        # close db
        model.close()
        print('closing app')