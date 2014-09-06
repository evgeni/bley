from setuptools import setup
import subprocess

try:
    from subprocess import check_output
except:
    from subprocess import Popen, PIPE

    def check_output(*popenargs, **kwargs):
        return Popen(*popenargs, stdout=PIPE).communicate()[0]
    subprocess.check_output = check_output


def systemd_unit_path():
    try:
        command = ["pkg-config", "--variable=systemdsystemunitdir", "systemd"]
        path = subprocess.check_output(command, stderr=subprocess.STDOUT)
        return path.replace('\n', '')
    except (subprocess.CalledProcessError, OSError):
        return "/lib/systemd/system"

setup(
    name="bley",
    version="2.0.0-beta.1",
    description="intelligent greylisting daemon for postfix",
    author="Evgeni Golov",
    author_email="evgeni@golov.de",
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
        ('/etc/bley', ['bley.conf.example',
                       'whitelist_recipients.example',
                       'whitelist_clients.example']),
        ('/usr/share/man/man1', ['bley.1', 'bleygraph.1']),
        ('/etc/logcheck/ignore.d.server/', ['bley.logcheck']),
        (systemd_unit_path(), ['bley.service'])
    ]
)
