import hashlib
import json
import os
import urllib
from datetime import datetime

import gevent
import requests
from six import string_types
from six.moves.urllib.parse import urlparse, urlunparse, parse_qs
from socketIO_client import SocketIO, BaseNamespace

# Disable useless warnings
# Works with requests==2.6.0, fails with some other versions
try:
    requests.packages.urllib3.disable_warnings()
except AttributeError:
    pass

BASE_URL = 'https://app.amigocloud.com'
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

    error_msg = {
        'logged_in_websockets': ('You must be logged in with a user token '
                                 'to start receiving websocket events.')
    }

    def __init__(self, token=None, project_url=None, base_url=BASE_URL,
                 use_websockets=True, websocket_port=None):
        """
        :param str token: AmigoCloud API Token
        :param str project_url: Specify it if you are using a project token
        :param str base_url: points to https://www.amigocloud.com by default
        :param bool use_websockets: True by default. Parameter will be ignored
            when using Project Tokens
        :param int websocket_port: Standard websocket port by default
        """
        # Urls
        if base_url.endswith('/'):
            self.base_url = base_url[:-1]
        else:
            self.base_url = base_url
        self.api_url = self.base_url + '/api/v1'

        self._token = None
        self._user_id = None
        self._project_id = None
        self._project_url = None

        # Auth
        if token:
            self.authenticate(token, project_url)

        # Websockets
        if use_websockets and not project_url:
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
        return '/'.join(
            s.strip('/') for s in (self._project_url or self.api_url, url))

    def check_for_errors(self, response):
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise AmigoCloudError(str(exc), exc.response)

    def authenticate(self, token, project_url=None):
        self._token = token
        self._project_url = (self.build_url(project_url) if project_url
                             else None)
        if not self._project_url:
            response = self.get('/me')
            self._user_id = response['id']
        else:
            response = self.get('')
            self._project_id = response['id']

    def logout(self):
        self._token = None
        self._user_id = None
        self._project_id = None
        self._project_url = None

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
            parsed = list(urlparse(full_url))
            if not parsed[4]:  # query
                parsed[4] = 'token=%s' % self._token
                full_url = urlunparse(parsed)
            elif 'token' not in parse_qs(parsed[4]):
                parsed[4] += '&token=%s' % self._token
                full_url = urlunparse(parsed)
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

    def upload_file(self, simple_upload_url, chunked_upload_url, file_obj,
                    chunk_size=CHUNK_SIZE, force_chunked=False,
                    extra_data=None):
        """
        Generic method to upload files to AmigoCloud. Can be used for different
        API endpoints.
        `file_obj` could be a file-like object or a filepath.
        If the size of the file is greater than MAX_SIZE_SIMPLE_UPLOAD (8MB)
        `chunked_upload_url` will be used, otherwise `simple_upload_url` will
        be.
        If `simple_upload_url` evaluates to False, or `force_chunked` is True,
        the `chunked_upload_url` will always be used.
        """

        if isinstance(file_obj, string_types):
            # file_obj is a filepath: open file and close it at the end
            file_obj = open(file_obj, 'rb')
            close_file = True
        else:
            # assume file_obj is a file-like object
            close_file = False

        # Get file size
        file_obj.seek(0, os.SEEK_END)
        file_size = file_obj.tell()
        file_obj.seek(0)

        try:
            # Simple upload?
            if (simple_upload_url and not force_chunked
                    and file_size < MAX_SIZE_SIMPLE_UPLOAD):
                return self.post(simple_upload_url, data=extra_data,
                                 files={'datafile': file_obj})
            # Chunked upload
            data = {}
            md5_hash = hashlib.md5()
            start_byte = 0
            while True:
                chunk = file_obj.read(chunk_size)
                md5_hash.update(chunk)
                end_byte = start_byte + len(chunk) - 1
                content_range = 'bytes %d-%d/%d' % (start_byte, end_byte,
                                                    file_size)
                ret = self.post(chunked_upload_url, data=data,
                                files={'datafile': chunk},
                                headers={'Content-Range': content_range})
                data.setdefault('upload_id', ret['upload_id'])
                start_byte = end_byte + 1
                if start_byte == file_size:
                    break
            # Complete request
            if chunked_upload_url.endswith('/'):
                chunked_upload_complete_url = chunked_upload_url + 'complete'
            else:
                chunked_upload_complete_url = chunked_upload_url + '/complete'
            data['md5'] = md5_hash.hexdigest()
            if extra_data:
                data.update(extra_data)
            return self.post(chunked_upload_complete_url, data=data)
        finally:
            if close_file:
                file_obj.close()

    def upload_datafile(self, project_owner, project_id, file_obj,
                        chunk_size=CHUNK_SIZE, force_chunked=False):
        """
        Upload datafile to a project. The file must be a supported format or a
        zip file containing supported formats.
        To see the formats we support, go to this URL:
        http://help.amigocloud.com/hc/en-us/articles/202413410-Supported-Format
        """

        simple_upload_url = 'users/%s/projects/%s/datasets/upload' % (
            project_owner, project_id
        )
        chunked_upload_url = 'users/%s/projects/%s/datasets/chunked_upload' % (
            project_owner, project_id
        )

        return self.upload_file(simple_upload_url, chunked_upload_url,
                                file_obj, chunk_size=chunk_size,
                                force_chunked=force_chunked)

    def upload_gallery_photo(self, gallery_id, source_amigo_id, file_obj,
                             chunk_size=CHUNK_SIZE, force_chunked=False,
                             metadata=None):
        """
        Upload a photo to a dataset's gallery.
        """

        simple_upload_url = 'related_tables/%s/upload' % gallery_id
        chunked_upload_url = 'related_tables/%s/chunked_upload' % gallery_id

        data = {'source_amigo_id': source_amigo_id}
        if isinstance(file_obj, basestring):
            data['filename'] = os.path.basename(file_obj)
        else:
            data['filename'] = os.path.basename(file_obj.name)
        if metadata:
            data.update(metadata)

        return self.upload_file(simple_upload_url, chunked_upload_url,
                                file_obj, chunk_size=chunk_size,
                                force_chunked=force_chunked, extra_data=data)

    def listen_user_events(self):
        """
        Authenticate to start listening to user events.
        """

        if not self._user_id:
            raise AmigoCloudError(self.error_msg['logged_in_websockets'])

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
            raise AmigoCloudError(self.error_msg['logged_in_websockets'])

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

    def geocode_addresses(self, project_id, dataset_id, address_field,
                          geometry_field, **extra_params):
        """
        Geocode addresses in a dataset. The dataset must have a string field
        with the addresses to geocode and a geometry field (points) for the
        geocoding results.
        :param project_id: Must be a string.
        :param dataset_id: Must be a string.
        :param address_field: Name of the address field in the dataset.
        :param geometry_field: Name of the geometry field in the dataset.
        :param extra_params: Dictionary to filter the Geocoding response.
                       For example: {'country':'PE'}
                       More information:
                       https://developers.google.com/maps/documentation/geocoding/intro#ComponentFiltering
        """

        project_url = ('/projects/{project_id}'
                       ).format(project_id=project_id)

        dataset_url = ('{project_url}/datasets/{dataset_id}'
                       ).format(project_url=project_url,
                                dataset_id=dataset_id)

        project_query_url = ('{project_url}/sql'
                             ).format(project_url=project_url)

        dataset_data = self.get(dataset_url)
        dataset_count = dataset_data['feature_count']

        print('%d rows to process' % dataset_count)
        print('Estimated time: %d minutes' % (dataset_count * 2 / 60))
        start = datetime.now()
        print('Started at %s hrs' % start.strftime('%H:%M'))

        get_query = ('SELECT {address_column}, amigo_id '
                     'FROM dataset_{dataset_id}'
                     ).format(address_column=address_field,
                              dataset_id=dataset_id)
        rows = []

        print('Exporting addresses...')

        for i in range(0, dataset_count, 1000):
            response = self.get(
                project_query_url,
                params={
                    'query': get_query,
                    'offset': i,
                    'limit': 1000
                }
            )
            dataset_rows = response['data']
            rows.extend(dataset_rows)

        print('Done!')
        print('Geocoding addresses...')

        geocoder_url = '/me/geocoder/search'
        geocoder_params = {'focus.point.lat': 0, 'focus.point.lon': 0}

        components = ''

        for key, value in extra_params.items():
            components += '{key}:{value}|'.format(key=key, value=value)

        geocoder_params['components'] = components[:-1]

        def geocode_address(row_data):
            address = row_data[address_field]
            amigo_id = row_data['amigo_id']

            geocoder_params['text'] = address
            geocoder_result = self.get(geocoder_url,
                                       params=geocoder_params,
                                       stream=True)

            if geocoder_result.status_code == 200:
                coordinates = json.loads(geocoder_result.text)[
                    'features'][0]['geometry']['coordinates']
                lng = str(coordinates[0])
                lat = str(coordinates[1])

                return ("('{amigo_id}', "
                        "ST_SetSRID(ST_MakePoint({lng}, {lat}), 4326)),"
                        ).format(amigo_id=amigo_id,
                                 lng=lng,
                                 lat=lat)

            return ''

        processed = 0
        steps = 30
        for i in range(0, len(rows), steps):
            rows_to_geocode = rows[i: i + steps]
            threads = []

            for row in rows_to_geocode:
                threads.append(gevent.spawn(geocode_address,
                                            row))
            gevent.joinall(threads)
            values = ''.join([thread.value for thread in threads])

            if values != '':
                data = {
                    'query': ('UPDATE dataset_{dataset_id} as d '
                              'SET {geo_column} = c.{geo_column} '
                              'FROM (values {values}) '
                              'as c(amigo_id, {geo_column}) '
                              'WHERE c.amigo_id = d.amigo_id'
                              ).format(dataset_id=dataset_id,
                                       geo_column=geometry_field,
                                       values=values[:-1])
                }

                self.post(project_query_url, data=data)

            processed += len(rows_to_geocode)
            print('%d%%' % (float(processed) / dataset_count * 100))

        count_query = ('SELECT count(*) '
                       'FROM dataset_{dataset_id} '
                       'WHERE {geo_column} IS NOT NULL'
                       ).format(dataset_id=dataset_id,
                                geo_column=geometry_field)
        points_count = self.get(
            project_query_url,
            params={'query': count_query})['data'][0]['count']

        print('Done!')
        print('Finished at %s hrs' % datetime.now().strftime('%H:%M'))
        print('Success rate: %d of %d points created' %
              (points_count, dataset_count))
        total_time = datetime.now() - start
        print('Total time: %s' % total_time)
        average_time = total_time.total_seconds() / dataset_count
        print('Average time per request: %.3f seconds' % average_time)
