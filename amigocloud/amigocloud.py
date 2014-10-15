from datetime import datetime, timedelta
import json

import requests
from socketIO_client import SocketIO, BaseNamespace

BASE_URL = 'https://www.amigocloud.com'
WEBSOCKET_PORT = 5005

CLIENT_ID = '82e597d526db4fd027a7'
CLIENT_SECRET = '07b03a991c84901ac7341ff967563f1c2e4d6cd3'


class AmigoCloudError(Exception):

    def __init__(self, message, response=None):
        self.message = message
        self.response = response
        self.text = getattr(self.response, 'text', None)

    def __str__(self):
        if self.text:
            return self.message + '\n' + self.text
        return self.message


class AmigoCloud(object):

    def __init__(self, email=None, password=None, client_id=CLIENT_ID,
                 client_secret=CLIENT_SECRET, base_url=BASE_URL,
                 websocket_port=WEBSOCKET_PORT):

        # Urls
        if base_url.endswith('/'):
            self.base_url = base_url[:-1]
        else:
            self.base_url = base_url
        self.api_url = self.base_url + '/api/v1'

        # OAuth2
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = None
        self._expires_on = None

        # Websockets
        self.socketio = SocketIO(self.base_url.replace('https:', 'http:'),
                                 websocket_port)
        self.amigosocket = self.socketio.define(BaseNamespace, '/amigosocket')

        # Login
        if email and password:
            self.login(email, password)

    def build_url(self, url):

        if url.startswith('http'):
            # User already specified the full url
            return url
        # User wants to use the api_url
        if url.startswith('/'):
            return self.api_url + url
        return self.api_url + '/' + url

    def check_for_errors(self, response):
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise AmigoCloudError(exc.message, exc.response)

    def login(self, email, password):
        """
        Logs in the user and keeps the session ID.
        """

        post_data = {'client_id': self._client_id,
                     'client_secret': self._client_secret,
                     'grant_type': 'password',
                     'username': email,
                     'password': password}
        response = self.post('/oauth2/access_token', send_as_json=False,
                             data=post_data)

        self._access_token = response['access_token']
        delta = timedelta(seconds=response['expires_in'])
        self._expires_on = datetime.now() + delta

    def logout(self):
        self._access_token = None

    def _authorization_header(self):
        if not self._access_token:
            return {}
        if datetime.now() < self._expires_on:
            return {'Authorization': 'Bearer %s' % self._access_token}
        msg = 'Your access_token has expired. Please login again.'
        raise AmigoCloudError(msg)

    def get(self, url, params=None, raw=False):
        """
        GET request to AmigoCloud endpoint.
        """

        full_url = self.build_url(url)
        params = params or {}

        response = requests.get(full_url, params=params,
                                headers=self._authorization_header())
        self.check_for_errors(response)  # Raise exception if something failed

        if raw or not response.content:
            return response.content
        return json.loads(response.text)

    def _secure_request(self, url, method, data=None, raw=False,
                        send_as_json=True):

        full_url = self.build_url(url)
        headers = self._authorization_header()

        if send_as_json:
            headers.update({'content-type': 'application/json'})
            data = json.dumps(data or {})
        else:
            data = data or ''

        method = getattr(requests, method, None)
        response = method(full_url, data=data, headers=headers)
        self.check_for_errors(response)  # Raise exception if something failed

        if raw or not response.content:
            return response.content
        return json.loads(response.text)

    def post(self, url, data=None, raw=False, send_as_json=True):
        """
        POST request to AmigoCloud endpoint.
        """

        return self._secure_request(url, 'post', data=data, raw=raw,
                                    send_as_json=send_as_json)

    def put(self, url, data=None, raw=False, send_as_json=True):
        """
        PUT request to AmigoCloud endpoint.
        """

        return self._secure_request(url, 'put', data=data, raw=raw,
                                    send_as_json=send_as_json)

    def patch(self, url, data=None, raw=False, send_as_json=True):
        """
        PATCH request to AmigoCloud endpoint.
        """

        return self._secure_request(url, 'patch', data=data, raw=raw,
                                    send_as_json=send_as_json)

    def delete(self, url, data=None, raw=False, send_as_json=True):
        """
        DELETE request to AmigoCloud endpoint.
        """

        return self._secure_request(url, 'delete', data=data, raw=raw,
                                    send_as_json=send_as_json)

    def listen_user_events(self):
        """
        Authenticate to start listening to user events.
        """

        if not self._access_token:
            msg = 'You must be logged in to start receiving websocket events.'
            raise AmigoCloudError(msg)

        response = self.get('/me')
        user_id = response['id']
        response = self.get(response['start_websocket_session'])
        websocket_session = response['websocket_session']
        auth_data = {'userid': user_id, 'websocket_session': websocket_session}
        self.amigosocket.emit('authenticate', auth_data)

    def listen_dataset_events(self, user_id, project_id, dataset_id):
        """
        Authenticate to start using dataset events.
        """

        if not self._access_token:
            msg = 'You must be logged in to start receiving websocket events.'
            raise AmigoCloudError(msg)

        url = '/users/%s/projects/%s/datasets/%s/start_websocket_session'
        response = self.get(url % (user_id, project_id, dataset_id))
        websocket_session = response['websocket_session']
        auth_data = {'userid': user_id, 'datasetid': dataset_id,
                     'websocket_session': websocket_session}
        self.amigosocket.emit('authenticate', auth_data)

    def add_callback(self, event_name, callback):
        """
        Add callback to websocket connection.
        """

        self.amigosocket.on(event_name, callback)

    def start_listening(self, seconds=None):
        """
        Start listening events.
        If seconds=None it means it will listen forever.
        """

        self.socketio.wait(seconds=seconds)
