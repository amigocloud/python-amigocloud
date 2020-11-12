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
-  |gevent|_: Handles the websocket connections.
-  |socketIO_client|_: Handles the AmigoCloud websocket connection.
-  |six|_: A library to assit with python2 to python3 compatibility. 

This dependencies will be automatically installed.

Usage
-----

Authentication
~~~~~~~~~~~~~~

This library uses API token to authenticate you. To generate or access your API tokens, go to `API tokens <https://www.amigocloud.com/accounts/tokens>`__.

.. code:: python

    from amigocloud import AmigoCloud
    amigocloud = AmigoCloud(token='R:dlNDEiOWciP3y26kG2cHklYpr2HIPK40HD32r1')

You could also use a project token. Remember that project tokens can only be used to query endpoints relative to the project it belongs to.
If the project URL doesn't match its project, `AmigoCloudError` will be thrown.

.. code:: python

    from amigocloud import AmigoCloud
    amigocloud = AmigoCloud(token='C:Ndl3xGWeasYt9rqyuVsByf5HPMAGyte10y1Mub',
                            project_url='users/123/projects/1234')


You can use a READ token if you only want to do requests that won't alter data. Otherwise, you'll need to use more permissive tokens.

Requests
~~~~~~~~

Once you're logged in you can start making requests to the server. You
can use full urls or relative API urls:

.. code:: python

    # All three will do the same request:
    amigocloud.get('me')
    amigocloud.get('/me')
    amigocloud.get('https://www.amigocloud.com/api/v1/me')

For convenience, when using project tokens, urls are relative to the project's url (unless it starts with `/`):

.. code:: python

    # All three will do the same request:
    amigocloud.get('datasets')
    amigocloud.get('/users/123/projects/1234/datasets')
    amigocloud.get('https://www.amigocloud.com/api/v1/users/123/projects/1234/datasets')

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


Cursor Requests
~~~~~~~~~~~~~~~

Many requests return a paginated list. For example: projects, datasets, base layers, 
and sql queries. They can be identified when the request returns a dictionary with 
four items. 

.. code:: python

    from amigocloud import AmigoCloud
    amigocloud = AmigoCloud(token='yourapitoken')

    project_list = amigocloud.get('/me/projects')
    pprint ( project_list )

will return a dictionary like this (modified for brevity):  

.. code:: javascript

    {
        u'count': 319,
        u'next': u'https://app.amigocloud.com/api/v1/me/projects?limit=20&offset=20&token=yourapitoken',
        u'previous': None,
        u'results': [] 
    } 

From the results, you can see that this endpoint can be iterated through. 
To make it easier to iterate through these lists, you can use the ``get_cursor`` 
function. The cursor iterates over the results and if it reaches the limit of 
the response it will automatically make a request to get the next values. So 
you can get all data and iterate over it, without worrying about the 
pagination.

.. code:: python

    projects = amigocloud.get_cursor('/me/projects')
    for project in projects:
        print('Project:', project['name'])

If you want to iterate one request at a time it can be requested as:

.. code:: python

    # using a project token to authenticate

    datasets = amigocloud.get_cursor('datasets')

    dataset1 = datasets.next()
    print('Dataset1:', dataset1['name'])

    # Boolean to ask if there is a next value.
    # otherwise a StopIteration exception is raised.
    if datasets.has_next:
        dataset2 = datasets.next()
        print('Dataset2:', dataset2['name'])

Also, you can request some extra values, that are included in the response.

.. code:: python

    dataset_rows = amigocloud.get_cursor(
        'https://www.amigocloud.com/api/v1/projects/1234/sql',
        {'query': 'select * from dataset_1'})

    print('Response extra values:', dataset_rows.get('columns'))

    for row in dataset_rows:
        print('Row:', row)

Cursors can be used for Projects, Datasets, BaseLayers, SQL queries, etc.
It also supports non-iterable responses. For this cases it returns only one result.

.. code:: python

    cursor = amigocloud.get_cursor('me')

    for me in cursor:
        print('Me:', me)


Websocket connection
~~~~~~~~~~~~~~~~~~~~

The websocket connection is started when the AmigoCloud object is
instantiated, and it is closed when the object is destroyed. You always
need to use a user token for websockets.

Make sure to read `our help page about our websocket events <http://help.amigocloud.com/hc/en-us/articles/204246154>`__ before continue reading.

To start listening to websocket events related to your user (multicast
events), do (you must be logged in to start listening to your events):

.. code:: python

    amigocloud.listen_user_events()

Once you're listening to your events, you can start adding callbacks to
them. A callback is a function that will be called everytime the event
is received. These functions should have only one parameter, that would be a python dict.

.. code:: python

    def project_created(data):
        print 'User id=%(user_id)s created project id=%(project_id)s' % data
    amigocloud.add_callback('project:creation_succeeded', project_created)

Realtime events are broadcast events related to realtime dataset. To start listening to them, do:

.. code:: python

    amigocloud.listen_dataset_events(owner_id, project_id, dataset_id)

Then add a callback for them:

.. code:: python

    def realtime(data):
        print 'Realtime dataset id=%(dataset_id)s' % data
        for obj in data['data']:
            print "Object '%(object_id)s' is now at (%(latitude)s, %(longitude)s)" % obj
    amigocloud.add_callback('realtime', realtime)

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
.. _requests: https://requests.readthedocs.io/en/master/
.. |gevent| replace:: ``gevent``
.. _gevent: https://github.com/gevent/gevent
.. |socketIO_client| replace:: ``socketIO_client``
.. _socketIO_client: https://github.com/invisibleroads/socketIO-client
.. |six| replace:: ``six``
.. _six: https://github.com/benjaminp/six
