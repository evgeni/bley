def reverse_ip(ip):
    ip = ip.split('.')
    ip.reverse()
    rev = '.'.join(ip)
    return rev

def domain_from_host(host):
    d = host.split('.')
    if len(d) > 1:
       domain = '%s.%s' % (d[-2], d[-1])
    else:
       domain = host
    return domain

def is_dyn_host(host):
	host = host.lower()
	return host.find('dyn') != -1 or host.find('dial') != -1

def check_helo(params):
	if params['client_name'] != 'unknown' and params['client_name'] == params['helo_name']:
		score = 0
	elif domain_from_host(params['helo_name']) == domain_from_host(params['client_name']) or params['helo_name'] == '[%s]' % params['client_address']:
		score = 1
	else:
		score = 2
		
	if is_dyn_host(params['client_name']):
		score += 1
	print "Checked EHLO to score=%s" % score
	return score
