import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "pyotgw",
    version = "0.1",
    author = "Milan van Nugteren",
    author_email = "milan at network23 dot nl",
    description = ("A library to interface with the opentherm gateway through serial"
                    "or network connection."),
    license = "GPLv3+",
    keywords = "opentherm gateway otgw",
    url = "https://network23.nl/pyotgw",
    packages=['pyotgw'],
    long_description=read('README'),
    install_requires=[
        'pyserial-asyncio',
        'logging',
    ],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ],
)
