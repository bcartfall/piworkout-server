"""
 * Developed by Hutz Media Ltd. <info@hutzmedia.com>
 * Copyright 2023-01-12
 * See README.md
"""

from flask import jsonify, request, redirect
import os
import json
import google.oauth2.credentials
import google_auth_oauthlib.flow

import model


# get:/api/connect
def get(action: str = ''):
    if (action == 'disconnect'):
        # disconnect from api
        model.settings.delete('YOUTUBE_API_TOKEN')
        return redirect('http://' + os.getenv('APP_HOST') + ':' + os.getenv('APP_PORT'))
    elif (request.args.get('state')):
        state = request.args.get('state')
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            '/app/auth/client_secret.json',
            scopes=[request.args.get('scope')],
            state=state)
        flow.redirect_uri = 'http://' + os.getenv('APP_HOST') + ':' + os.getenv('APP_PORT') + '/api/connect'

        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)

        # store the credentials
        credentials = flow.credentials

        data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        model.settings.put('YOUTUBE_API_TOKEN', json.dumps(data))

        return redirect('http://' + os.getenv('APP_HOST') + ':' + os.getenv('APP_PORT'))
    else:
        authorization_url = None
        token = model.settings.get('YOUTUBE_API_TOKEN', '')
        if (token == ''):
            connected = False
            # Use the client_secret.json file to identify the application requesting
            # authorization. The client ID (from that file) and access scopes are required.
            flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                '/app/auth/client_secret.json',
                scopes=['https://www.googleapis.com/auth/youtube.force-ssl'])

            # Indicate where the API server will redirect the user after the user completes
            # the authorization flow. The redirect URI is required. The value must exactly
            # match one of the authorized redirect URIs for the OAuth 2.0 client, which you
            # configured in the API Console. If this value doesn't match an authorized URI,
            # you will get a 'redirect_uri_mismatch' error.
            flow.redirect_uri = 'http://' + os.getenv('APP_HOST') + ':' + os.getenv('APP_PORT') + '/api/connect'

            # Generate URL for request to Google's OAuth 2.0 server.
            # Use kwargs to set optional request parameters.
            authorization_url, state = flow.authorization_url(
                # Enable offline access so that you can refresh an access token without
                # re-prompting the user for permission. Recommended for web server apps.
                access_type='offline',
                # Enable incremental authorization. Recommended as a best practice.
                include_granted_scopes='true')
        else:
            connected = True

        obj = {
            'connected': connected,
            'authorizationUrl': authorization_url,
        }
        return jsonify(obj)