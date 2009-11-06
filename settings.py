import psycopg2
import datetime

# On which IP and port should the daemon listen?
listen_addr = '192.168.0.1'
listen_port = 1337

# Which DNSBLs and DNSWLs to use?
dnsbls = ['ix.dnsbl.manitu.net', 'dnsbl.njabl.org', 'dnsbl.ahbl.org', 'dnsbl.sorbs.net']
dnswls = ['list.dnswl.org', 'exemptions.ahbl.org']

# Whitelist after dnswl_threshold hits.
dnswl_threshold = 1
# Greylist after dnsbl_threshold hits.
dnsbl_threshold = 1
# Greylist after rfc_threshold hits in the RFC checks.
rfc_threshold = 2

reject_msg = 'greylisted, try again later'

# Which database to use?
database = psycopg2
dsn = "dbname=bley"

# Where to save the PID file?
pid_file = '/home/bley/bley/bley.pid'
# Where to save the log file?
log_file = '/home/bley/bley/bley.log'

# Wait greylist_period before accepting greyed sender.
greylist_period = datetime.timedelta(0, 30*60, 0)
# Max wait greylist_max before accepting greyed sender.
# (Accept all senders after 24h.)
greylist_max    = datetime.timedelta(0, 24*60*60, 0)
# Add greylist_penalty for every connection before greylist_period.
greylist_penalty= datetime.timedelta(0, 10*60, 0)

# Purge good entries from the database after purge_days inactivities.
purge_days = 40
# Purge bad entries from the database after purge_bad_days inactivities.
purge_bad_days = 10

# Start maximum max_procs BleyWorker threads.
max_procs = 20
