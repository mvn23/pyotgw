import os

from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="pyotgw",
    version="1.0b1",
    author="Milan van Nugteren",
    author_email="milan@network23.nl",
    description=(
        "A library to interface with the opentherm gateway through "
        "serial or network connection."
    ),
    license="GPLv3+",
    keywords="opentherm gateway otgw",
    url="https://github.com/mvn23/pyotgw",
    packages=["pyotgw"],
    python_requires=">=3.7",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    install_requires=["pyserial-asyncio"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ],
)
