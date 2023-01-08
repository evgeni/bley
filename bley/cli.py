#!/usr/bin/env python
#
# Copyright (c) 2009-2014 Evgeni Golov <evgeni@golov.de>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the University nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

from __future__ import print_function

import os
import sys
import datetime
import logging
import socket

from optparse import OptionParser

import ipaddress
import re

from twisted.internet import reactor

try:
    from twisted.scripts._twistd_unix import UnixApplicationRunner
except:
    print("Could not import _twistd_unix. Exiting...")
    sys.exit(1)

from twisted.application import internet, service
from .bley import BleyPolicyFactory, parse_config

logger = logging.getLogger('bley')

__CREATE_DB_QUERY = '''
  CREATE TABLE IF NOT EXISTS bley_status
  (
    ip VARCHAR(39) NOT NULL,
    status SMALLINT NOT NULL DEFAULT 1,
    last_action TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
    sender VARCHAR(254),
    recipient VARCHAR(254),
    fail_count INT DEFAULT 0,
    INDEX bley_status_index USING btree (ip, sender, recipient),
    INDEX bley_status_action_index USING btree (last_action)
  ) CHARACTER SET 'ascii'
'''
__UPDATE_DB_QUERY = '''
  ALTER TABLE bley_status CHANGE last_action
  last_action TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
'''
__CREATE_DB_QUERY_PG = '''
  CREATE TABLE bley_status
  (
    ip VARCHAR(39) NOT NULL,
    status SMALLINT NOT NULL DEFAULT 1,
    last_action TIMESTAMP NOT NULL,
    sender VARCHAR(254),
    recipient VARCHAR(254),
    fail_count INT DEFAULT 0
  );
  CREATE INDEX bley_status_index
   ON bley_status USING btree (ip ASC NULLS LAST, sender ASC NULLS LAST,
   recipient ASC NULLS LAST);
  CREATE INDEX bley_status_action_index
   ON bley_status USING btree (last_action ASC NULLS LAST);
'''
__CHECK_DB_QUERY_PG = '''
  SELECT tablename FROM pg_catalog.pg_tables WHERE tablename = 'bley_status'
'''

__CREATE_DB_QUERY_SL = '''
  CREATE TABLE IF NOT EXISTS bley_status
  (
    ip VARCHAR(39) NOT NULL,
    status SMALLINT NOT NULL DEFAULT 1,
    last_action TIMESTAMP NOT NULL,
    sender VARCHAR(254),
    recipient VARCHAR(254),
    fail_count INT DEFAULT 0
  );
  CREATE INDEX IF NOT EXISTS bley_status_index
   ON bley_status (ip ASC, sender ASC, recipient ASC);
  CREATE INDEX IF NOT EXISTS bley_status_action_index
   ON bley_status (last_action);
'''

__CLEAN_DB_QUERY = '''
   DELETE FROM bley_status WHERE last_action<%(old)s OR
   (last_action<%(old_bad)s AND status>=2)
'''
__CLEAN_DB_QUERY_SL = '''
   DELETE FROM bley_status WHERE last_action<:old OR
   (last_action<:old_bad AND status>=2)
'''

__CREATE_LOGDB_QUERY = '''
  CREATE TABLE IF NOT EXISTS bley_log
  (
    logtime TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
    ip VARCHAR(39) NOT NULL,
    sender VARCHAR(254),
    recipient VARCHAR(254),
    action VARCHAR(254),
    check_dnswl INT DEFAULT 0,
    check_dnsbl INT DEFAULT 0,
    check_helo INT DEFAULT 0,
    check_dyn INT DEFAULT 0,
    check_db INT DEFAULT 0,
    check_spf INT DEFAULT 0,
    check_s_eq_r INT DEFAULT 0,
    check_postmaster INT DEFAULT 0,
    check_cache INT DEFAULT 0,
    INDEX bley_log_index USING btree (logtime, action)
  )  CHARACTER SET 'ascii';
'''
__CREATE_LOGDB_QUERY_PG = '''
  CREATE TABLE bley_log
  (
    logtime TIMESTAMP NOT NULL,
    ip VARCHAR(39) NOT NULL,
    sender VARCHAR(254),
    recipient VARCHAR(254),
    action VARCHAR(254),
    check_dnswl INT DEFAULT 0,
    check_dnsbl INT DEFAULT 0,
    check_helo INT DEFAULT 0,
    check_dyn INT DEFAULT 0,
    check_db INT DEFAULT 0,
    check_spf INT DEFAULT 0,
    check_s_eq_r INT DEFAULT 0,
    check_postmaster INT DEFAULT 0,
    check_cache INT DEFAULT 0
  );
  CREATE INDEX bley_log_index
   ON bley_log USING btree (logtime DESC NULLS FIRST, action ASC NULLS LAST);
'''
__CHECK_LOGDB_QUERY_PG = '''
  SELECT tablename FROM pg_catalog.pg_tables WHERE tablename = 'bley_log'
'''

__CREATE_LOGDB_QUERY_SL = '''
  CREATE TABLE IF NOT EXISTS bley_log
  (
    logtime TIMESTAMP NOT NULL,
    ip VARCHAR(39) NOT NULL,
    sender VARCHAR(254),
    recipient VARCHAR(254),
    action VARCHAR(254),
    check_dnswl INT DEFAULT 0,
    check_dnsbl INT DEFAULT 0,
    check_helo INT DEFAULT 0,
    check_dyn INT DEFAULT 0,
    check_db INT DEFAULT 0,
    check_spf INT DEFAULT 0,
    check_s_eq_r INT DEFAULT 0,
    check_postmaster INT DEFAULT 0,
    check_cache INT DEFAULT 0
  );
  CREATE INDEX IF NOT EXISTS bley_log_index
   ON bley_log (logtime DESC, action ASC);
'''


def bley_start():

    version = '2.0.0'
    parser = OptionParser(version=version)
    parser.add_option("-p", "--pidfile", dest="pid_file",
                      help="use PID_FILE for storing the PID")
    parser.add_option("-c", "--config", dest="conffile", action="append",
                      help="load configuration from CONFFILE")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose",
                      help="use verbose output")
    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug",
                      help="don't daemonize the process and log to stdout")
    parser.add_option("-f", "--foreground",
                      action="store_true", dest="foreground",
                      help="don't daemonize the process")
    (settings, args) = parser.parse_args()
    settings.version = version
    settings.hostname = socket.getfqdn()

    if not settings.conffile:
        if os.path.isfile('/etc/bley/bley.conf'):
            settings.conffile = ['/etc/bley/bley.conf']
        elif os.path.isfile('bley.conf'):
            settings.conffile = ['bley.conf']

    if settings.conffile:
        settings.confdir = os.path.dirname(settings.conffile[0])
    else:
        settings.confdir = './'

    config = parse_config(settings.conffile)

    settings.listen_addr = config.get('bley', 'listen_addr')
    settings.listen_port = config.getint('bley', 'listen_port')
    settings.pid_file = settings.pid_file or config.get('bley', 'pid_file')
    settings.log_file = config.get('bley', 'log_file')
    settings.cache_valid = config.getint('bley', 'cache_valid')
    settings.dbtype = config.get('bley', 'dbtype')
    if settings.dbtype == 'pgsql':
        database = 'psycopg2'
        import psycopg2
        settings.database = psycopg2
        settings.dbsettings = {'host': config.get('bley', 'dbhost'),
                               'database': config.get('bley', 'dbname'),
                               'user': config.get('bley', 'dbuser'),
                               'password': config.get('bley', 'dbpass')}
    elif settings.dbtype == 'mysql':
        database = 'MySQLdb'
        import MySQLdb
        settings.database = MySQLdb
        settings.dbsettings = {'host': config.get('bley', 'dbhost'),
                               'db': config.get('bley', 'dbname'),
                               'user': config.get('bley', 'dbuser'),
                               'passwd': config.get('bley', 'dbpass')}
    elif settings.dbtype == 'sqlite3':
        global __CLEAN_DB_QUERY
        database = 'sqlite3'
        import sqlite3
        settings.database = sqlite3
        settings.dbsettings = {'database': os.path.join(config.get('bley', 'dbpath'), config.get('bley', 'dbname')), 'detect_types': 1}
        __CLEAN_DB_QUERY = __CLEAN_DB_QUERY_SL
    else:
        print("No supported database configured.")
        sys.exit(1)
    if (config.has_option('bley', 'dbport') and
       config.getint('bley', 'dbport') != 0):
        settings.dbsettings['port'] = config.getint('bley', 'dbport')

    settings.reject_msg = config.get('bley', 'reject_msg')
    settings.greylist_header = config.get('bley', 'greylist_header', raw=True)

    settings.dnswls = [d.strip() for d in config.get('bley', 'dnswls').split(',') if d.strip() != ""]
    settings.dnsbls = [d.strip() for d in config.get('bley', 'dnsbls').split(',') if d.strip() != ""]

    settings.dnswl_threshold = config.getint('bley', 'dnswl_threshold')
    settings.dnsbl_threshold = config.getint('bley', 'dnsbl_threshold')
    settings.rfc_threshold = config.getint('bley', 'rfc_threshold')
    settings.greylist_period = datetime.timedelta(0, config.getint('bley', 'greylist_period') * 60, 0)
    settings.greylist_max = datetime.timedelta(0, config.getint('bley', 'greylist_max') * 60, 0)
    settings.greylist_penalty = datetime.timedelta(0, config.getint('bley', 'greylist_penalty') * 60, 0)
    settings.purge_days = config.getint('bley', 'purge_days')
    settings.purge_bad_days = config.getint('bley', 'purge_bad_days')
    settings.use_spf = config.getint('bley', 'use_spf')
    settings.use_spf_guess = config.getint('bley', 'use_spf_guess')

    settings.exim_workaround = config.getboolean('bley', 'exim_workaround')

    if settings.debug:
        settings.foreground = True
        settings.log_file = None

    logger.setLevel(logging.INFO)
    if settings.log_file == 'syslog':
        from logging.handlers import SysLogHandler
        import platform
        system = platform.system()
        addr = None
        if system == 'Linux':
            addr = '/dev/log'
        elif system == 'Darwin':
            addr = '/var/run/syslog'
        elif 'BSD' in system:
            addr = '/var/run/log'
        lh = SysLogHandler(address=addr, facility=SysLogHandler.LOG_MAIL)
        formatter = logging.Formatter('%(name)s: %(message)s')
        lh.setFormatter(formatter)
        logger.addHandler(lh)
    elif settings.log_file in ['-', '', None]:
        from logging import StreamHandler
        lh = StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s %(name)s: %(message)s')
        lh.setFormatter(formatter)
        logger.addHandler(lh)
    else:
        from logging.handlers import WatchedFileHandler
        lh = WatchedFileHandler(settings.log_file)
        formatter = logging.Formatter('%(asctime)s %(name)s: %(message)s')
        lh.setFormatter(formatter)
        logger.addHandler(lh)

    if config.has_option('bley', 'whitelist_recipients_file'):
        settings.whitelist_recipients_file = config.get('bley', 'whitelist_recipients_file')
        if not os.path.isabs(settings.whitelist_recipients_file):
            settings.whitelist_recipients_file = os.path.join(settings.confdir, settings.whitelist_recipients_file)
        settings.whitelist_recipients = read_whitelist(settings.whitelist_recipients_file)[0]
    else:
        settings.whitelist_recipients = []
    if config.has_option('bley', 'whitelist_clients_file'):
        settings.whitelist_clients_file = config.get('bley', 'whitelist_clients_file')
        if not os.path.isabs(settings.whitelist_clients_file):
            settings.whitelist_clients_file = os.path.join(settings.confdir, settings.whitelist_clients_file)
        (settings.whitelist_clients, settings.whitelist_clients_ip) = read_whitelist(settings.whitelist_clients_file)
    else:
        settings.whitelist_clients = []
        settings.whitelist_clients_ip = []

    logger.info("Starting up")

    db = settings.database.connect(**settings.dbsettings)
    dbc = db.cursor()
    if settings.dbtype == 'pgsql':
        dbc.execute(__CHECK_DB_QUERY_PG)
        if not dbc.fetchall():
            dbc.execute(__CREATE_DB_QUERY_PG)
        dbc.execute(__CHECK_LOGDB_QUERY_PG)
        if not dbc.fetchall():
            dbc.execute(__CREATE_LOGDB_QUERY_PG)
    elif settings.dbtype == 'sqlite3':
        dbc.executescript(__CREATE_DB_QUERY_SL)
        dbc.executescript(__CREATE_LOGDB_QUERY_SL)
    else:
        dbc.execute("set sql_notes = 0")
        dbc.execute(__CREATE_DB_QUERY)
        dbc.execute(__CREATE_LOGDB_QUERY)
        dbc.execute("set sql_notes = 1")
        dbc.execute(__UPDATE_DB_QUERY)
    db.commit()
    dbc.close()
    db.close()

    settings.db = settings.database.connect(**settings.dbsettings)

    class NoLogObserver(object):
        def emit(self, eventDict):
            return

    class NoAppLogger(object):

        def __init__(self, options):
            return

        def start(self, application):
            return

        def _getLogObserver(self):
            return NoLogObserver().emit

        def stop(self):
            return

    class BleyRunner(UnixApplicationRunner):
        loggerFactory = NoAppLogger

        def createOrGetApplication(self):
            bley_app = service.Application("bley")
            bley_service = internet.TCPServer(settings.listen_port,
                                              BleyPolicyFactory(settings),
                                              interface=settings.listen_addr)
            bley_service.setServiceParent(bley_app)
            return bley_app
    bley_config = {'originalname': None, 'euid': None, 'profile': None,
                   'no_save': True, 'debug': False, 'uid': None, 'gid': None,
                   'chroot': None, 'rundir': '.',
                   'nodaemon': settings.foreground, 'umask': None,
                   'pidfile': settings.pid_file,
                   'syslog': settings.log_file == 'syslog', 'prefix': 'bley',
                   'logfile': settings.log_file}
    runner = BleyRunner(bley_config)
    reactor.addSystemEventTrigger('before', 'shutdown', bley_stop, settings)
    reactor.callWhenRunning(clean_db, settings)
    runner.run()


def bley_stop(settings):
    logger.info("Shutting down")


def clean_db(settings):
    if settings.verbose:
        logger.info("cleaning database")
    db = settings.database.connect(**settings.dbsettings)
    dbc = db.cursor()
    now = datetime.datetime.now()
    old = now - datetime.timedelta(settings.purge_days, 0, 0)
    old_bad = now - datetime.timedelta(settings.purge_bad_days, 0, 0)
    p = {'old': str(old), 'old_bad': str(old_bad)}
    dbc.execute(__CLEAN_DB_QUERY, p)
    db.commit()
    dbc.close()
    db.close()
    reactor.callLater(30 * 60, clean_db, settings)


def read_whitelist(whitelist_filename):
    global logger
    try:
        whitelist_fh = open(whitelist_filename, 'r')
    except:
        logger.warning('Could not open file: %s' % (whitelist_filename))
        return (['postmaster@'], ())
    whitelist = list()
    whitelist_ip = list()
    for line in whitelist_fh:
        line = line.split('#', 1)[0]
        line = line.split(';', 1)[0]
        line = line.strip()
        if line == "":
            continue
        if line.startswith('/') and line.endswith('/'):
            # line is regex
            whitelist.append(re.compile(line[1:-1]))
            continue
        try:
            line_ipaddr = ipaddress.ip_network(line)
            # line is IP address
            whitelist_ip.append(line_ipaddr)
        except (ValueError):
            # Ordinary string (domain name or username)
            whitelist.append(line)
    return (whitelist, whitelist_ip)

if __name__ == '__main__':
    bley_start()
