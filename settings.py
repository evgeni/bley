import ConfigParser
from datetime import timedelta

defaults = {
    'listen_addr': '127.0.0.1',
    'log_file': None,
    'pid_file': None,
}
config = ConfigParser.SafeConfigParser(defaults)
config.read('bley.conf')

# [bley]
listen_addr = config.get('bley', 'listen_addr')
listen_port = config.getint('bley', 'listen_port')
pid_file    = config.get('bley', 'pid_file')
log_file    = config.get('bley', 'log_file')
exec("import %s as database" % config.get('bley', 'database'))
dsn         = config.get('bley', 'dsn')
reject_msg  = config.get('bley', 'reject_msg')

# [lists]
dnswls      = [d.strip() for d in config.get('bley', 'dnswls').split(',')]
dnsbls      = [d.strip() for d in config.get('bley', 'dnsbls').split(',')]

# [thresholds]
dnswl_threshold  = config.getint('bley', 'dnswl_threshold')
dnsbl_threshold  = config.getint('bley', 'dnsbl_threshold')
rfc_threshold    = config.getint('bley', 'rfc_threshold')
greylist_period  = timedelta(0, config.getint('bley', 'greylist_period')*60, 0)
greylist_max     = timedelta(0, config.getint('bley', 'greylist_max')*60, 0)
greylist_penalty = timedelta(0, config.getint('bley', 'greylist_penalty')*60, 0)
purge_days       = config.getint('bley', 'purge_days')
purge_bad_days   = config.getint('bley', 'purge_bad_days')
