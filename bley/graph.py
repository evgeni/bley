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

import datetime
import sys
import os

from optparse import OptionParser

from .bley import parse_config

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def main():
    parser = OptionParser(version='2.0.0')
    parser.add_option("-d", "--destdir", dest="destdir",
                      help="write to DESTDIR")
    parser.add_option("-c", "--config", dest="conffile",
                      help="load configuration from CONFFILE")
    parser.add_option("-q", "--quiet",
                      action="store_true", dest="quiet",
                      help="be quiet (no output)")
    (settings, args) = parser.parse_args()

    if not settings.conffile:
        if os.path.isfile('/etc/bley/bley.conf'):
            settings.conffile = '/etc/bley/bley.conf'
        elif os.path.isfile('bley.conf'):
            settings.conffile = 'bley.conf'

    config = parse_config(settings.conffile)

    settings.destdir = settings.destdir or config.get('bleygraph', 'destdir')
    if not os.path.exists(settings.destdir):
        print('creating destination dir: %s' % settings.destdir)
        os.mkdir(settings.destdir)

    dbtype = config.get('bley', 'dbtype')
    if dbtype == 'pgsql':
        import psycopg2
        database = psycopg2
        dbsettings = {'host': config.get('bley', 'dbhost'), 'database': config.get('bley', 'dbname'),
                      'user': config.get('bley', 'dbuser'), 'password': config.get('bley', 'dbpass')}
    elif dbtype == 'mysql':
        import MySQLdb
        database = MySQLdb
        dbsettings = {'host': config.get('bley', 'dbhost'), 'db': config.get('bley', 'dbname'),
                      'user': config.get('bley', 'dbuser'), 'passwd': config.get('bley', 'dbpass')}
    elif dbtype == 'sqlite3':
        import sqlite3
        database = sqlite3
        dbsettings = {'database': config.get('bley', 'dbname'), 'detect_types': 1}
    else:
        print("No supported database configured.")
        sys.exit(1)

    if config.has_option('bley', 'dbport') and config.getint('bley', 'dbport') != 0:
        dbsettings['port'] = config.getint('bley', 'dbport')

    matplotlib.use('Agg')

    dnswl_threshold = config.getint('bley', 'dnswl_threshold')
    dnsbl_threshold = config.getint('bley', 'dnsbl_threshold')
    rfc_threshold = config.getint('bley', 'rfc_threshold')

    now = datetime.datetime.now()

    db = database.connect(**dbsettings)
    dbc = db.cursor()

    years = mdates.YearLocator()   # every year
    months = mdates.MonthLocator()  # every month
    hours = mdates.HourLocator()
    twohours = mdates.HourLocator(interval=2)
    fourhours = mdates.HourLocator(interval=4)
    halfday = mdates.HourLocator(interval=12)
    oneday = mdates.DayLocator()
    twoday = mdates.DayLocator(interval=2)
    fourday = mdates.DayLocator(interval=4)
    teday = mdates.DayLocator(interval=28)
    hoursFmt = mdates.DateFormatter('%Y/%m/%d %H:%M')
    daysFmt = mdates.DateFormatter('%Y/%m/%d')

    __TIMESLOTS = [
        {'title': '12h', 'slot': 60, 'major_locator': twohours,
         'minor_locator': hours, 'formatter': hoursFmt, 'slotname': '1h'},
        {'title': '24h', 'slot': 2 * 60, 'major_locator': fourhours,
         'minor_locator': twohours, 'formatter': hoursFmt, 'slotname': '2h'},
        {'title': '7d', 'slot': 12 * 60, 'major_locator': oneday,
         'minor_locator': halfday, 'formatter': daysFmt, 'slotname': '12h'},
        {'title': '28d', 'slot': 2 * 24 * 60, 'major_locator': fourday,
         'minor_locator': twoday, 'formatter': daysFmt, 'slotname': '2d'},
        {'title': '365d', 'slot': 28 * 24 * 60, 'major_locator': teday,
         'minor_locator': teday, 'formatter': daysFmt, 'slotname': '28d'},
    ]
    __QUERY_BASE = "SELECT COUNT(action) FROM bley_log WHERE action=%s AND logtime<'%s' AND logtime>='%s'"

    __badcheck_queries = {
        'in DNSBL': {'query': 'check_db=-1 and check_cache=0 and check_dnsbl>=%i' % (dnsbl_threshold), 'color': 'black'},
        'bad HELO': {'query': 'check_db=-1 and check_cache=0 and check_helo>=%i and check_dnsbl<%i' % (rfc_threshold, dnsbl_threshold), 'color': 'red'},
        'bad grey': {'query': 'check_db=2 and check_cache=0 and check_dnsbl<%i' % (dnsbl_threshold), 'color': 'blue'},
        'from DynIP': {'query': 'check_db=-1 and check_cache=0 and (check_helo+check_dyn)>=%i and check_helo<%i and check_dnsbl<%i' % (rfc_threshold, rfc_threshold, dnsbl_threshold), 'color': 'orange'},
        'bad SPF': {'query': 'check_db=-1 and check_cache=0 and (check_helo+check_dyn+check_spf)>=%i and (check_helo+check_dyn)<%i and check_dnsbl<%i' % (rfc_threshold, rfc_threshold, dnsbl_threshold), 'color': 'yellow'},
        'sender==recipient': {'query': 'check_db=-1 and check_cache=0 and (check_helo+check_dyn+check_spf+check_s_eq_r)>=%i and (check_helo+check_dyn+check_spf)<%i and check_dnsbl<%i' % (rfc_threshold, rfc_threshold, dnsbl_threshold), 'color': 'orange'},
        'bad cache': {'query': 'check_db=-1 and check_cache=1 and check_dnsbl<%i' % (dnsbl_threshold), 'color': 'pink'},
    }
    __goodcheck_queries = {
        'known good': {'query': '(check_db=0 or check_db=1) and check_cache=0', 'color': 'green'},
        'good grey': {'query': 'check_db=2 and check_cache=0', 'color': 'lightblue'},
        'new good': {'query': 'check_db=-1 and check_cache=0 and check_dnswl<%i' % (dnswl_threshold), 'color': 'lightgreen'},
        'in DNSWL': {'query': 'check_db=-1 and check_cache=0 and check_dnswl>=%i' % (dnswl_threshold), 'color': 'lightgrey'},
        'good cache': {'query': 'check_db=-1 and check_cache=1', 'color': 'darkgreen'},
    }

    __HTML_TEMPLATE = '''<html>
    <head>
    <title>bley stats</title>
    </head>
    <body>
    <p>%(ar)s</p>
    <p>%(ch)s</p>
    </body>
    </html>'''

    __ar_files = []
    __ch_files = []

    for s in __TIMESLOTS:
        d = datetime.timedelta(0, s['slot'] * 60, 0)
        n = now - datetime.timedelta(0, 30 * 60, 0)
        i = 12
        a = {'dates': [], 'mails': []}
        r = {'dates': [], 'mails': []}
        checks = {}
        for check in __badcheck_queries:
            checks[check] = {'dates': [], 'mails': [], 'color': __badcheck_queries[check]['color']}
        for check in __goodcheck_queries:
            checks[check] = {'dates': [], 'mails': [], 'color': __goodcheck_queries[check]['color']}

        if not settings.quiet:
            print("plotting %s:" % (s['title']))
        fig = plt.figure()
        ax = fig.add_subplot(111)
        fig2 = plt.figure()
        ax2 = fig2.add_subplot(111)
        while i:
            q1 = __QUERY_BASE % ("'DUNNO'", str(n), str(n - d))
            q2 = __QUERY_BASE % ("'DEFER_IF_PERMIT'", str(n), str(n - d))
            if dbtype == 'sqlite3':
                q1 = q1.replace('%s', '?')
                q2 = q2.replace('%s', '?')

            dbc.execute(q1)
            r1 = dbc.fetchone()
            dbc.execute(q2)
            r2 = dbc.fetchone()
            numdate = mdates.date2num(n)
            a['dates'].append(numdate)
            r['dates'].append(numdate)
            a['mails'].append(r1[0])
            r['mails'].append(r2[0])
            for check in __badcheck_queries:
                q = "%s AND %s" % (q2, __badcheck_queries[check]['query'])
                if dbtype == 'sqlite3':
                    q = q.replace('%s', '?')
                dbc.execute(q)
                res = dbc.fetchone()
                checks[check]['dates'].append(numdate)
                checks[check]['mails'].append(res[0])
            for check in __goodcheck_queries:
                q = "%s AND %s" % (q1, __goodcheck_queries[check]['query'])
                if dbtype == 'sqlite3':
                    q = q.replace('%s', '?')
                dbc.execute(q)
                res = dbc.fetchone()
                checks[check]['dates'].append(numdate)
                checks[check]['mails'].append(res[0])
            n = n - d
            i -= 1

        ax.plot(a['dates'], a['mails'], label="ham", color='green')
        ax.plot(r['dates'], r['mails'], label="spam", color='red')
        for check in checks:
            ax2.plot(checks[check]['dates'], checks[check]['mails'], label=check, color=checks[check]['color'])

        ax.legend(loc=2)
        ax2.legend(loc=2)

        fig.text(0.125, 0, "ham [ max: %s, avg: %s, min: %s  ]\nspam [ max: %s, avg: %s, min: %s  ]" %
                 (max(a['mails']), round(float(sum(a['mails'])) / len(a['mails']), 2), min(a['mails']),
                  max(r['mails']), round(float(sum(r['mails'])) / len(r['mails']), 2), min(r['mails'])))

        ax.xaxis.set_major_formatter(s['formatter'])
        ax.xaxis.set_major_locator(s['major_locator'])
        ax.xaxis.set_minor_locator(s['minor_locator'])
        ax2.xaxis.set_major_formatter(s['formatter'])
        ax2.xaxis.set_major_locator(s['major_locator'])
        ax2.xaxis.set_minor_locator(s['minor_locator'])

        fig.suptitle('bley ACCEPT/REJECT stats for the last %s (slot=%s)' % (s['title'], s['slotname']))
        fig2.suptitle('bley check stats for the last %s (slot=%s)' % (s['title'], s['slotname']))

        fig.autofmt_xdate()
        fig2.autofmt_xdate()
        if not settings.quiet:
            print(" - %s" % (os.path.join(settings.destdir, 'ar-%s.png' % s['title'])))
            print(" - %s" % (os.path.join(settings.destdir, 'ch-%s.png' % s['title'])))
        fig.savefig(os.path.join(settings.destdir, 'ar-%s.png' % s['title']))
        fig2.savefig(os.path.join(settings.destdir, 'ch-%s.png' % s['title']))
        __ar_files.append('<img src="ar-%s.png" alt="bley ACCEPT/REJECT stats for the last %s" />' % (s['title'], s['title']))
        __ch_files.append('<img src="ch-%s.png" alt="bley check stats for the last %s" />' % (s['title'], s['title']))

    dbc.close()
    db.close()

    html = {
        'ar': '<br />'.join(__ar_files),
        'ch': '<br />'.join(__ch_files),
    }

    f = open(os.path.join(settings.destdir, 'index.html'), 'w')
    f.write(__HTML_TEMPLATE % html)
    f.close()


if __name__ == '__main__':
    main()
