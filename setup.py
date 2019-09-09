#!/bin/env python

"""

setuptools setup script for nport

"""

from setuptools import setup
from subprocess import Popen, PIPE


version = '0.2'

version_file = open('nport/version.py', 'w')
version_file.write("__version__ = '%s'\n" % version)
version_file.close()


setup(
    name='nport',
    version=version,
    packages=['nport', 'smith'],
    scripts=['nporttool'],
    requires=['numpy', 'scipy'],
    provides=['nport', 'smith'],
    test_suite='nose.collector',
    
    author="Brecht Machiels",
    author_email="brecht.machiels@esat.kuleuven.be",
    description="Python package for handling n-port data",
    url="https://github.com/bmachiel/python-nport",
    license="GPL",
    keywords="two-port 2n-port s-parameters touchstone citi deembedding smith",
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
