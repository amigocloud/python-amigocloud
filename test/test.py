import os 
from pprint import pprint
from amigocloud import AmigoCloud

amigocloudtoken = os.getenv("AMIGOCLOUDTOKEN")

amigocloud = AmigoCloud(token=amigocloudtoken)

class TestIterator: 

    def test_check_cursor_endpoint(self):

        project_list = amigocloud.get('/me/projects')

        pprint( project_list )


    def chec_test_projects(self):

        projects_list = amigocloud.get_cursor('/me/projects')

        for  project in projects_list: 
            print(u'project name : {name}'.format(name=project['name']))

