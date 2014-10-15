#!/usr/bin/env python

from distutils.core import setup


with open('VERSION.txt', 'r') as v:
    version = v.read().strip()

with open('REQUIREMENTS.txt', 'r') as r:
    requires = r.read().split()


setup(
    name='amigocloud',
    packages = ['amigocloud'],
    version=version,
    description='Python client for the AmigoCloud REST API',
    author='Julio M Alegria',
    author_email='julio@amigocloud.com',
    url='https://github.com/amigocloud/python-amigocloud',
    install_requires=requires,
    license='MIT'
)
