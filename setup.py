from setuptools import setup
import commands

setup(
    name="bley",
    version="0.2-git",
    description="intelligent greylisting daemon for postfix",
    author="Evgeni Golov",
    author_email="sargentd@die-welt.net",
    url="http://bley.mx",
    license="BSD",
    py_modules=['bley', 'bleyhelpers', 'postfix'],
    scripts=['bley', 'bleygraph'],
    zip_safe=False,
    install_requires=['Twisted>=8.1.0', 'pyspf', 'ipaddr'],
    extras_require={
        'PostgreSQL backend': ['psycopg2'],
        'MySQL backend': ['MySQL-python'],
        'publicsuffix.org support': ['publicsuffix'],
    },
    data_files=[
        ('/etc/bley', ['bley.conf.example']),
        ('/usr/share/man/man1', ['bley.1']),
        ('/etc/logcheck/ignore.d.server/', ['bley.logcheck']),
        (commands.getoutput("pkg-config --variable=systemdsystemunitdir systemd"), ['bley.service'])
    ]
)
