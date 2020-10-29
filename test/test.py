import os
import pytest
from pprint import pprint
from amigocloud import AmigoCloud

amigocloudtoken = os.getenv("AMIGOCLOUDTOKEN")

amigocloud = AmigoCloud(token=amigocloudtoken)

class TestIterator:

    def test_check_cursor_endpoint(self):

        project_list = amigocloud.get('/me/projects')

        pprint( project_list )


    def test_check_projects(self):

        projects_list = amigocloud.get_cursor('/me/projects')

        for project in projects_list: 
            print(u'project name : {name}'.format(name=project['name']))

        assert projects_list.has_next == False

        # Exception raised when trying to get nonexistent next value.
        with pytest.raises(StopIteration):
            projects_list.next()

    def test_next_project(self):
        """Test request one project and check the attributes"""

        projects_list = amigocloud.get_cursor('/me/projects')

        project = projects_list.next()
        assert type(project) == dict
        assert 'name' in project
        assert type(project['name']) == str

        while projects_list.has_next:
            projects_list.next()

        assert projects_list.has_next == False
        
        # Exception raised when trying to get nonexistent next value.
        with pytest.raises(StopIteration):
            projects_list.next()

    def test_check_datasets(self):
        """Test datasets inside test project"""

        projects_list = amigocloud.get_cursor('/me/projects', {
            'search': 'PythonAmigotest'})
        project = projects_list.next()
        dataset_list = amigocloud.get_cursor(project['datasets'])

        assert sum(1 for d in dataset_list) == dataset_list.get('count')

    def test_sql_query_with_many_rows(self):
        """Test returning more than 1000 rows from sql query"""

        projects_list = amigocloud.get_cursor('/me/projects', {
            'search': 'PythonAmigotest'})
        project = projects_list.next()
        dataset_list = amigocloud.get_cursor(project['datasets'], {
            'search': 'sql-dataset'})
        dataset = dataset_list.next()
        
        dataset_rows = amigocloud.get_cursor(project['sql'], {
            'query': 'select * from dataset_{d_id}'.format(d_id=dataset['id'])})
        assert sum(1 for d in dataset_rows) == dataset_rows.get('count')

    def test_non_iterable_response(self):
        """Test returning response with simple object"""

        simple_json_object = amigocloud.get_cursor('/me')
        data = simple_json_object.next()

        assert type(data) == dict
        assert ('first_name' in data) == True
        assert simple_json_object.has_next == False

