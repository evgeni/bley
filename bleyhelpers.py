# Copyright (c) 2009 Evgeni Golov <evgeni.golov@uni-duesseldorf.de>
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

import spf
import re

__dyn_host = re.compile('(cable|dial|dip|dsl|dyn|gprs|umts|[0-9]{1,3}[.-][0-9]{1,3}[.-][0-9]{1,3}[.-][0-9]{1,3})', re.I)
__static_host = re.compile('(colo|dedi|hosting|mail|mx|smtp|static)', re.I)

def reverse_ip(ip):
    return spf.reverse_dots(ip)

def domain_from_host(host):
    d = host.split('.')
    if len(d) > 1:
       domain = '%s.%s' % (d[-2], d[-1])
    else:
       domain = host
    return domain

def is_dyn_host(host):
    if __static_host.search(host):
        return 0
    if __dyn_host.search(host):
        return 1
    return 0

def check_helo(params):
    if params['client_name'] != 'unknown' and params['client_name'] == params['helo_name']:
        score = 0
    elif domain_from_host(params['helo_name']) == domain_from_host(params['client_name']) or params['helo_name'] == '[%s]' % params['client_address']:
        score = 1
    else:
        score = 2
        
    return score

def check_spf(params):
    score = 0
    try:
        s = spf.query(params['client_address'], params['sender'], params['helo_name'])
        r = s.check()
        if r[0] in ['fail', 'softfail']:
            score = 1
        elif r[0] in ['pass']:
            score = -2
        else:
            r = s.best_guess()
            if r[0] in ['fail', 'softfail']:
                score = 1
            elif r[0] in ['pass']:
                score = -1
    except:
        # DNS Errors, yay...
        print 'something went wrong in check_spf()'
    return score

