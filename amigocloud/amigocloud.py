import hashlib
import json
import os
import urlparse

import requests
requests.packages.urllib3.disable_warnings()
from socketIO_client import SocketIO, BaseNamespace

BASE_URL = 'https://www.amigocloud.com'
CHUNK_SIZE = 100000  # 100kB
MAX_SIZE_SIMPLE_UPLOAD = 8000000  # 8MB


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

    def get(self, url, params=None, raw=False, stream=False, **request_kwargs):
        """
        GET request to AmigoCloud endpoint.
        """

        full_url = self.build_url(url)
        params = params or {}

        # Add token (if it's not already there)
        if self._token:
            params.setdefault('token', self._token)

        response = requests.get(full_url, params=params, stream=stream,
                                **request_kwargs)
        self.check_for_errors(response)  # Raise exception if something failed

        if stream:
            return response
        if raw or not response.content:
            return response.content
        return json.loads(response.text)

    def _secure_request(self, url, method, data=None, files=None, headers=None,
                        raw=False, send_as_json=True, content_type=None,
                        **request_kwargs):

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

        # If files are being sent, we cannot encode data as JSON
        if send_as_json and not files:
            headers['content-type'] = 'application/json'
            data = json.dumps(data or {})
        else:
            if content_type:
                headers['content-type'] = content_type
            data = data or ''

        method = getattr(requests, method, None)
        response = method(full_url, data=data, files=files, headers=headers,
                          **request_kwargs)
        self.check_for_errors(response)  # Raise exception if something failed

        if raw or not response.content:
            return response.content
        return json.loads(response.text)

    def post(self, url, data=None, files=None, headers=None, raw=False,
             send_as_json=True, content_type=None, **request_kwargs):
        """
        POST request to AmigoCloud endpoint.
        """

        return self._secure_request(
            url, 'post', data=data, files=files, headers=headers, raw=raw,
            send_as_json=send_as_json, content_type=content_type,
            **request_kwargs
        )

    def put(self, url, data=None, files=None, headers=None, raw=False,
            send_as_json=True, content_type=None, **request_kwargs):
        """
        PUT request to AmigoCloud endpoint.
        """

        return self._secure_request(
            url, 'put', data=data, files=files, headers=headers, raw=raw,
            send_as_json=send_as_json, content_type=content_type,
            **request_kwargs
        )

    def patch(self, url, data=None, files=None, headers=None, raw=False,
              send_as_json=True, content_type=None, **request_kwargs):
        """
        PATCH request to AmigoCloud endpoint.
        """

        return self._secure_request(
            url, 'patch', data=data, files=files, headers=headers, raw=raw,
            send_as_json=send_as_json, content_type=content_type,
            **request_kwargs
        )

    def delete(self, url, data=None, files=None, headers=None, raw=False,
               send_as_json=True, content_type=None, **request_kwargs):
        """
        DELETE request to AmigoCloud endpoint.
        """

        return self._secure_request(
            url, 'delete', data=data, files=files, headers=headers, raw=raw,
            send_as_json=send_as_json, content_type=content_type,
            **request_kwargs
        )

    def upload_datafile(self, project_owner, project_id, filepath,
                        chunk_size=CHUNK_SIZE, force_chunked=False):
        """
        Upload datafile to a project.
        """

        simple_upload_url = 'users/%s/projects/%s/datasets/upload'
        chunked_upload_url = 'users/%s/projects/%s/datasets/chunked_upload'

        filename = os.path.basename(filepath)

        with open(filepath, 'rb') as datafile:
            datafile_size = os.path.getsize(filepath)
            if not force_chunked and datafile_size < MAX_SIZE_SIMPLE_UPLOAD:
                # Simple upload
                url = simple_upload_url % (project_owner, project_id)
                return self.post(url, files={'datafile': (filename, datafile)})
            url = chunked_upload_url % (project_owner, project_id)
            data = {}
            md5_hash = hashlib.md5()
            start_byte = 0
            # Chunked upload
            while True:
                chunk = datafile.read(chunk_size)
                md5_hash.update(chunk)
                end_byte = start_byte + len(chunk) - 1
                content_range = 'bytes %d-%d/%d' % (start_byte, end_byte,
                                                    datafile_size)
                ret = self.post(url, data=data,
                                files={'datafile': (filename, chunk)},
                                headers={'Content-Range': content_range})
                data['upload_id'] = ret['upload_id']
                start_byte = end_byte + 1
                if start_byte == datafile_size:
                    break
            # Complete request
            url_complete = url + '/complete'
            return self.post(url_complete, {'upload_id': data['upload_id'],
                                            'md5': md5_hash.hexdigest()})

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
