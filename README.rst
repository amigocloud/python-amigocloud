python-amigocloud
=================

Python client for the `AmigoCloud <https://www.amigocloud.com>`__ REST
API.

Installation
------------

Install via pip:

::

    pip install amigocloud

Dependencies
------------

-  |requests|_: Handles the HTTP requests to the AmigoCloud REST API.
-  |socketIO_client|_: Handles the AmigoCloud websocket connection.

This dependencies will be automatically installed.

Usage
-----

Authentication
~~~~~~~~~~~~~~

To start using this library, first login with your AmigoCloud
credentials:

.. code:: python

    from amigocloud import AmigoCloud
    amigocloud = AmigoCloud(email='user@example.com', password='********')

Requests
~~~~~~~~

Once you're logged in you can start making requests to the server. You
can use full urls or relative API urls:

.. code:: python

    # All three will do the same request:
    amigocloud.get('me')
    amigocloud.get('/me')
    amigocloud.get('https://www.amigocloud.com/api/v1/me')

Creating a new AmigoCloud project from Python is as simple as:

.. code:: python

    data = {'name': 'New Project', 'description': 'Created from Python'}
    amigocloud.post('me/projects', data)

All responses are parsed as JSON and return a Python object (usually a
``dict``). This data can be later used in another request:

.. code:: python

    me = amigocloud.get('me')
    visible_projects = amigocloud.get(me['visible_projects'])

    print 'My projects:'
    for project in visible_projects['results']:
        print '*', project['name']

You can get the raw response if you want by using the ``raw`` parameter:

.. code:: python

    me = amigocloud.get('me')
    images = amigocloud.get(me['images'])

    with open('thumbnail.png', 'wb') as thumbnail:
        image_data = amigocloud.get(images['thumbnail'], raw=True)
        thumbnail.write(image_data)

Websocket connection
~~~~~~~~~~~~~~~~~~~~

The websocket connection is started when the AmigoCloud object is
instantiated, and it is closed when the object is destroyed.

To start listening to websocket events related to your user do (you must
be logged in to start listening to your events):

.. code:: python

    amigocloud.listen_user_events()

Once you're listening to your events, you can start adding callbacks to
them. A callback is a function that will be called everytime the event
is received.

.. code:: python

    def project_created(data):
        print 'Data received:', data
    amigocloud.add_callback('project:creation_succeeded', project_created)

Finally, start running the websocket client:

.. code:: python

    ac.start_listening()

This method receives an optional parameter ``seconds``. If ``seconds``
is ``None`` (default value), the client will listen forever. You might
want to run this method in a new thread.

Exceptions
~~~~~~~~~~

An ``AmigoCloudError`` exception will be raised if anything fails during
the request:

.. code:: python

    try:
        amigocloud.post('me/projects')
    except AmigoCloudError as err:
        print 'Something failed!'
        print 'Status code was', err.response.status_code
        print 'Message from server was', err.text

.. |requests| replace:: ``requests``
.. _requests: http://docs.python-requests.org/en/latest
.. |socketIO_client| replace:: ``socketIO_client``
.. _socketIO_client: https://github.com/invisibleroads/socketIO-client