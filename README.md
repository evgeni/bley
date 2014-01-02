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
Unpack the tarball (or clone the git tree), adjust `bley.conf.example`,
rename it to `bley.conf` and run `./bley`.

Still quick, but not dirty
--------------------------
Unpack the tarball (or clone the git tree), run `python setup.py build`
followed by `python setup.py install`, copy `/etc/bley/bley.conf.example`
to `/etc/bley/bley.conf`, adjust it to your needs (see CONFIGURATION below)
and run `/usr/bin/bley`.

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

Additional Configuration
------------------------

Sometimes, you want to bind `bley` to something else than `127.0.0.1:1337`,
this can be achieved with the following two parameters.

    listen_addr = 127.0.0.1
    listen_port = 1337

As `bley` is designed to be a deamon, it will write a pid file and a log file.
The locations of the two can be configured with the following parameters.

    pid_file = bley.pid
    log_file = bley.log

Setting `log_file` to the special word `syslog` will make `bley` log to
`syslog` instead of a file, using the `mail` facility.

If you want to inform the sender about the greylisting, you can adjust
the message sent via

    reject_msg = greylisted, try again later

The DNSWLs and DNSBLs `bley` uses for its tests can be set via

    dnsbls = ix.dnsbl.manitu.net, dnsbl.ahbl.org, dnsbl.sorbs.net
    dnswls = list.dnswl.org

Thresholds define how many sub-checks have to hit, to trigger a feature
(whitelisting in case of dnswl, greylisting in case of dnsbl and rfc).

    dnswl_threshold = 1
    dnsbl_threshold = 1
    rfc_threshold = 2

How long should a sender be greylisted, when should we allow him in at
the very last and how long should he have to wait more, if he retries to
early (all in minutes)?

    greylist_period = 29
    greylist_max    = 720
    greylist_penalty= 10

After how many days should old entries be deleted from the database?
Entries of senders who have not verified to be "good" should be purged
earlier.

    purge_days = 40
    purge_bad_days = 10

SPF ([Sender Policy Framework](http://www.openspf.org)) checks can be turned
off. [SPF Best Guess](http://www.openspf.net/Best_Practices/No_Best_Guess)
should always be turned off.

    use_spf = 1
    use_spf_guess = 0

If you use Exim instead of Postfix, set this to 1. It will automatically
close connections after the decision is sent. While Postfix supports
checking multiple senders over the same connections, Exim does not. In fact
it even closes the sending part of the socket as soon all details have been
transmitted.

    exim_workaround = 0

BUILD STATUS
============
[![Build Status](https://travis-ci.org/evgeni/bley.png?branch=master)](https://travis-ci.org/evgeni/bley)
