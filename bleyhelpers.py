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

import spf
import re
import ipaddress
import six
try:
    import publicsuffix2
except ImportError:
    publicsuffix2 = None

publicsuffixlist = None

__dyn_host = re.compile('(\.bb\.|broadband|cable|dial|dip|dsl|dyn|gprs|pool|ppp|umts|wimax|wwan|[0-9]{1,3}[.-][0-9]{1,3}[.-][0-9]{1,3}[.-][0-9]{1,3})', re.I)
__static_host = re.compile('(colo|dedi|hosting|mail|mx[^$]|smtp|static)', re.I)


def reverse_ip(ip):
    '''Returns the IP address in reversed notation (A.B.C.D -> D.C.B.A).

    @type  ip: string
    @param ip: the IP address to reverse
    @rtype:    string
    @return:   the reversed IP address
    '''
    ip = ipaddress.ip_address(six.u(ip))
    if ip.version == 4:
        a = str(ip.exploded).split('.')
        a.reverse()
        return '.'.join(a)
    else:
        a = list(str(ip.exploded).replace(':', ''))
        a.reverse()
        return '.'.join(a)


def domain_from_host(host):
    '''Return the domain part of a host.

    @type  host: string
    @param host: the host to extract the domain from
    @rtype:      string
    @return:     the extracted domain
    '''

    if publicsuffix2:
        global publicsuffixlist
        if publicsuffixlist is None:
            publicsuffixlist = publicsuffix2.PublicSuffixList()
        domain = publicsuffixlist.get_public_suffix(host)
    else:
        d = host.split('.')
        if len(d) > 1:
            domain = '%s.%s' % (d[-2], d[-1])
        else:
            domain = host
    return domain


def check_dyn_host(host):
    '''Check the host for being a dynamic/dialup one.

    @type  host: string
    @param host: the host to check
    @rtype:      int
    @return:     0 if host is not dynamic, 1 if it is
    '''
    if __static_host.search(host):
        return 0
    if __dyn_host.search(host):
        return 1
    return 0


def check_helo(params):
    '''Check the HELO for being RFC 5321 complaint.
    Returns 0 when the HELO match the reverse DNS.
    Returns 1 when the domain in the HELO match the domain of the reverse DNS
    or when the HELO is the IP address.
    Returns 2 else.

    @type  params: dict
    @param params: the params from Postfix
    @rtype:        int
    @return:       the score of the HELO
    '''
    if (params['helo_name'].startswith('[') and
       params['helo_name'].endswith(']')):
        try:
            params['helo_name'] = '[%s]' % ipaddress.ip_address(six.u(params['helo_name']).strip('[]')).exploded
        except:
            pass

    if (params['client_name'] != 'unknown' and
       params['client_name'] == params['helo_name']):
        score = 0
    elif (domain_from_host(params['helo_name']) == domain_from_host(params['client_name']) or
          params['helo_name'] == '[%s]' % params['client_address']):
        score = 1
    else:
        score = 2

    return score


def check_spf(params, guess):
    '''Check the SPF record of the sending address.
    Try Best Guess when the domain has no SPF record.
    Returns 1 when the SPF result is in ['fail', 'softfail'],
    returns 0 else.

    @type  params: dict
    @param params: the params from Postfix
    @type  guess:  int
    @param guess:  1 if use 'best guess', 0 if not
    @rtype:        int
    @return:       1 if bad SPF, 0 else
    '''
    score = 0
    try:
        s = spf.query(params['client_address'], params['sender'], params['helo_name'])
        r = s.check()
        if r[0] in ['fail', 'softfail']:
            score = 1
        elif r[0] in ['pass']:
            score = 0
        elif guess > 0 and r[0] in ['none']:
            r = s.best_guess()
            if r[0] in ['fail', 'softfail']:
                score = 1
            elif r[0] in ['pass']:
                score = 0
    except:
        # DNS Errors, yay...
        print('something went wrong in check_spf()')
    return score


def adapt_query_for_sqlite3(query):
    # WARNING: This is a hack to convert the usual pyformat strings
    # to named ones used by sqlite3
    return query.replace('%(', ':').replace(')s', '')
