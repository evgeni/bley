"""
setup.py for bley
"""
from setuptools import setup, find_packages


setup(
    name="bley",
    version="3.0",
    description="intelligent greylisting daemon for postfix",
    author="Evgeni Golov",
    author_email="evgeni@golov.de",
    url="http://bley.mx",
    license="BSD",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    zip_safe=False,
)
