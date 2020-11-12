#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('VERSION.txt', 'r') as v:
    version = v.read().strip()

with open('requirements.txt', 'r') as r:
    requires = r.read().split()

with open('README.rst', 'r') as r:
    readme = r.read()

download_url = 'https://github.com/amigocloud/python-amigocloud/tarball/%s'


setup(
    name='amigocloud',
    packages=['amigocloud'],
    version=version,
    description='Python client for the AmigoCloud REST API',
    long_description=readme,
    long_description_content_type='text/x-rst',
    author='AmigoCloud',
    author_email='support@amigocloud.com',
    url='https://github.com/amigocloud/python-amigocloud',
    download_url=download_url % version,
    install_requires=requires,
    license='MIT',
    keywords=(
        'gis geo geographic spatial spatial-data spatial-data-analysis '
        'spatial-analysis data-science maps mapping web-mapping python '
        'native-development geodata'),
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP :: Site Management',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Manufacturing',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Telecommunications Industry',
        'Operating System :: OS Independent'
    ]
)
