from setuptools import setup, find_packages

# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='alsdac',
    version='0.1.0',

    # Author details
    author='Ronald J Pandolfi',
    author_email='ronpandolfi@lbl.gov',

    packages=find_packages(),
    description='Python API over the ALS LabView Data Acquisition and Controls System TCP/IP commands',
    long_description=long_description,
    # The project's main homepage.
    url='https://github.com/ronpandolfi/alsdac',
    license='BSD (3-clause)',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Physics',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: BSD License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.6'
    ],

    # What does your project relate to?
    keywords='synchrotron controls beamline hardware data',

    install_requires=['trio'],
)
