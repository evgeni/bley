ABOUT
=====
`bley` is an intelligent greylisting daemon for Postfix (and Exim).

It uses various test (incl. RBL and SPF) to decide whether a sender
should be greylisted or not, thus mostly eliminating the usual
greylisting delay while still filtering most of the spam.

DEPENDENCIES
============
`bley` is written in [Python](http://python.org) using the
[Twisted](http://twistedmatrix.com/) framework. It uses
[pyspf](http://pypi.python.org/pypi/pyspf) for SPF validation and
[publicsuffix](https://pypi.python.org/pypi/publicsuffix) for checking
of domains against the [PublicSuffix.org](http://publicsuffix.org)
database. Database interaction is implemented via
[sqlite3](http://docs.python.org/2/library/sqlite3.html) for SQLite,
[psycopg2](http://initd.org/psycopg/) for PostgreSQL and
[MySQL-Python](http://mysql-python.sourceforge.net/) for MySQL.

INSTALLATION
============

Quick and dirty
---------------
Unpack the tarball (or clone the git tree), adjust `bley.conf` and run
`./bley`.

Still quick, but not dirty
--------------------------
Unpack the tarball (or clone the git tree), run `python setup.py build`
followed by `python setup.py install`, adjust `/etc/bley/bley.conf`
(see CONFIGURATION below) and run `/usr/bin/bley`.

CONFIGURATION
=============
Basically you just have to configure the database:

    dbtype = pgsql for PostgreSQL, mysql for MySQL or sqlite3 for SQLite
    dbhost = the host where the database runs on (usually localhost)
    dbport = the port where the database runs on (can be left unset for
             the default 5432 for PostgreSQL and 3306 for MySQL)
    dbuser = the name of the database user
    dbpass = the password of the database user
    dbname = the name (or path in case of SQLite) of the database

After that you can point your Postfix to `bley` as a 
[policy server](http://www.postfix.org/SMTPD_POLICY_README.html) by
adding `check_policy_service inet:127.0.0.1:1337` to your
`smtpd_recipient_restrictions` in `main.cf`.

`bley` will be working now, but you probably would like to tune it more
for your needs (esp. the used DNWLs and DNSBLs, the greylisting times
and the hit thresholds).

BUILD STATUS
============
[![Build Status](https://travis-ci.org/evgeni/bley.png?branch=master)](https://travis-ci.org/evgeni/bley)
