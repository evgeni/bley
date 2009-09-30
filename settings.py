import psycopg2
import datetime

listen_addr = '192.168.0.1'
listen_port = 1337

dnsbls = ['ix.dnsbl.manitu.net', 'dnsbl.njabl.org', 'dnsbl.ahbl.org', 'dnsbl.sorbs.net']
dnswls = ['list.dnswl.org', 'exemptions.ahbl.org']

dnswl_threshold = 1
dnsbl_threshold = 1
rfc_thredhold = 2

reject_msg = 'greylisted, try again later'

database = psycopg2
dsn = "dbname=bley"

pid_file = '/home/bley/bley/bley.pid'
log_file = '/home/bley/bley/bley.log'

greylist_period = datetime.timedelta(0, 30*60, 0)
greylist_max    = datetime.timedelta(0, 24*60*60, 0)
