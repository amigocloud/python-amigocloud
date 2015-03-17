import json
import urlparse

import requests
from socketIO_client import SocketIO, BaseNamespace

BASE_URL = 'https://www.amigocloud.com'


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
    """
    Client for the AmigoCloud REST API.
    Uses API tokens for authentication. To generate yours, go to:
        https://www.amigocloud.com/accounts/tokens
    """

    def __init__(self, token=None, base_url=BASE_URL, use_websockets=True,
                 websocket_port=None):

        # Urls
        if base_url.endswith('/'):
            self.base_url = base_url[:-1]
        else:
            self.base_url = base_url
        self.api_url = self.base_url + '/api/v1'

        # Auth
        self.logout()
        if token:
            self.authenticate(token)

        # Websockets
        if use_websockets:
            self.socketio = SocketIO(self.base_url, websocket_port)
            self.amigosocket = self.socketio.define(BaseNamespace,
                                                    '/amigosocket')
        else:
            self.socketio = None
            self.amigosocket = None

    def build_url(self, url):

        if url.startswith('http'):
            # User already specified the full url
            return url
        # User wants to use the api_url
        if url.startswith('/'):
            return self.api_url + url
        return '%s/%s' % (self.api_url, url)

    def check_for_errors(self, response):
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise AmigoCloudError(exc.message, exc.response)

    def authenticate(self, token):
        self._token = token
        response = self.get('/me')
        self._user_id = response['id']

    def logout(self):
        self._token = None
        self._user_id = None

    def get(self, url, params=None, raw=False):
        """
        GET request to AmigoCloud endpoint.
        """

        full_url = self.build_url(url)
        params = params or {}

        # Add token (if it's not already there)
        if self._token:
            params.setdefault('token', self._token)

        response = requests.get(full_url, params=params)
        self.check_for_errors(response)  # Raise exception if something failed

        if raw or not response.content:
            return response.content
        return json.loads(response.text)

    def _secure_request(self, url, method, data=None, headers=None, raw=False,
                        send_as_json=True, content_type=None):

        full_url = self.build_url(url)

        # Add token (if it's not already there)
        if self._token:
            parsed = list(urlparse.urlparse(full_url))
            if not parsed[4]:  # query
                parsed[4] = 'token=%s' % self._token
                full_url = urlparse.urlunparse(parsed)
            elif 'token' not in urlparse.parse_qs(parsed[4]):
                parsed[4] += '&token=%s' % self._token
                full_url = urlparse.urlunparse(parsed)
        headers = headers or {}

        if send_as_json:
            headers['content-type'] = 'application/json'
            data = json.dumps(data or {})
        else:
            if content_type:
                headers['content-type'] = content_type
            data = data or ''

        method = getattr(requests, method, None)
        response = method(full_url, data=data, headers=headers)
        self.check_for_errors(response)  # Raise exception if something failed

        if raw or not response.content:
            return response.content
        return json.loads(response.text)

    def post(self, url, data=None, headers=None, raw=False, send_as_json=True,
             content_type=None):
        """
        POST request to AmigoCloud endpoint.
        """

        return self._secure_request(url, 'post', data=data, raw=raw,
                                    send_as_json=send_as_json,
                                    content_type=content_type)

    def put(self, url, data=None, raw=False, send_as_json=True,
            content_type=None):
        """
        PUT request to AmigoCloud endpoint.
        """

        return self._secure_request(url, 'put', data=data, raw=raw,
                                    send_as_json=send_as_json,
                                    content_type=content_type)

    def patch(self, url, data=None, raw=False, send_as_json=True,
              content_type=None):
        """
        PATCH request to AmigoCloud endpoint.
        """

        return self._secure_request(url, 'patch', data=data, raw=raw,
                                    send_as_json=send_as_json,
                                    content_type=content_type)

    def delete(self, url, data=None, raw=False, send_as_json=True,
               content_type=None):
        """
        DELETE request to AmigoCloud endpoint.
        """

        return self._secure_request(url, 'delete', data=data, raw=raw,
                                    send_as_json=send_as_json,
                                    content_type=content_type)

    def listen_user_events(self):
        """
        Authenticate to start listening to user events.
        """

        if not self._user_id:
            msg = 'You must be logged in to start receiving websocket events.'
            raise AmigoCloudError(msg)

        response = self.get('/me/start_websocket_session')
        websocket_session = response['websocket_session']
        auth_data = {'userid': self._user_id,
                     'websocket_session': websocket_session}
        self.amigosocket.emit('authenticate', auth_data)

    def listen_dataset_events(self, owner_id, project_id, dataset_id):
        """
        Authenticate to start using dataset events.
        """

        if not self._user_id:
            msg = 'You must be logged in to start receiving websocket events.'
            raise AmigoCloudError(msg)

        url = '/users/%s/projects/%s/datasets/%s/start_websocket_session'
        response = self.get(url % (owner_id, project_id, dataset_id))
        websocket_session = response['websocket_session']
        auth_data = {'userid': self._user_id,
                     'datasetid': dataset_id,
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
