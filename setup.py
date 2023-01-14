from setuptools import setup, find_packages
import subprocess


def systemd_unit_path():
    try:
        command = ["pkg-config", "--variable=systemdsystemunitdir", "systemd"]
        path = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        return path.strip()
    except (subprocess.CalledProcessError, OSError):
        return "/lib/systemd/system"


setup(
    name="bley",
    version="2.0.0",
    description="intelligent greylisting daemon for postfix",
    author="Evgeni Golov",
    author_email="evgeni@golov.de",
    url="http://bley.mx",
    license="BSD",
    packages=find_packages(exclude=['contrib', 'docs', 'test']),
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'bley = bley.cli:bley_start',
            'bleygraph = bley.graph:main'
        ]
    },
    install_requires=['Twisted>=8.1.0', 'pyspf'],
    extras_require={
        'PostgreSQL backend': ['psycopg2'],
        'MySQL backend': ['mysqlclient'],
        'publicsuffix.org support': ['publicsuffix2'],
    },
    data_files=[
        ('/etc/bley', ['bley.conf.example',
                       'whitelist_recipients.example',
                       'whitelist_clients.example']),
        ('/usr/share/man/man1', ['bley.1', 'bleygraph.1']),
        ('/etc/logcheck/ignore.d.server/', ['bley.logcheck']),
        (systemd_unit_path(), ['bley.service'])
    ]
)
