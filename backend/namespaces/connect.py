"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

# namespace: connect
# method: GET, PUT, or DELETE
# action (optional): authorizationUrl
# state (optional)

import model, server
from threads import listfetch

import json
import os
#import google.oauth2.credentials
import google_auth_oauthlib.flow

import logging
logger = logging.getLogger('piworkout-server')

def receive(event, queue):
    logger.info('connect.receive()', event)
    if (event['method'] == 'GET' and event['action'] == 'authorizationUrl'):
        authorization_url = None
        # Use the client_secret.json file to identify the application requesting
        # authorization. The client ID (from that file) and access scopes are required.
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            '/app/backend/client_secret.json',
            scopes=['https://www.googleapis.com/auth/youtube.force-ssl'])

        # Indicate where the API server will redirect the user after the user completes
        # the authorization flow. The redirect URI is required. The value must exactly
        # match one of the authorized redirect URIs for the OAuth 2.0 client, which you
        # configured in the API Console. If this value doesn't match an authorized URI,
        # you will get a 'redirect_uri_mismatch' error.
        #flow.redirect_uri = event['redirectUri']
        flow.redirect_uri = os.getenv('GOOGLE_OAUTH_REDIRECT_URI')
        if (flow.redirect_uri == None):
            logger.error('GOOGLE_OAUTH_REDIRECT_URI Redirect URI is not set in .env')
            return None
        logger.info('Creating ouath request for ' + flow.redirect_uri)

        # Generate URL for request to Google's OAuth 2.0 server.
        # Use kwargs to set optional request parameters.
        authorization_url, state = flow.authorization_url(
            # Enable offline access so that you can refresh an access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type='offline',
            prompt='consent',
            # Enable incremental authorization. Recommended as a best practice.
            include_granted_scopes='true')

        server.send(queue, {
            'namespace': 'connect',
            'authorizationUrl': authorization_url
        })
    elif (event['method'] == 'PUT' and 'state' in event):
        logger.info('generating token', event)
        logger.debug('scopes=' + event['scope'])
        logger.debug('state=' + event['state'])
        
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            '/app/backend/client_secret.json',
            scopes=[event['scope']],
            state=event['state'])
        #flow.redirect_uri = event['redirectUri']
        flow.redirect_uri = os.getenv('GOOGLE_OAUTH_REDIRECT_URI')

        authorization_response = event['stateUrl']
        flow.fetch_token(authorization_response=authorization_response)

        # store the credentials
        credentials = flow.credentials
        
        if (credentials.refresh_token == None or credentials.refresh_token == ''):
            logger.warning('Error: No refresh token received')
            return
        
        model.settings.put('youtubeApiToken', credentials.to_json())
        server.broadcast({
            'namespace': 'connect',
            'connected': True,
        })

        # should fetch
        listfetch.fetchOnNextCycle()
        
    elif (event['method'] == 'DELETE'):
        model.settings.put('youtubeApiToken', '')
        server.broadcast({
            'namespace': 'connect',
            'connected': False,
        })