"""
bley helpers module
"""
# Copyright (c) 2009-2021 Evgeni Golov <evgeni@golov.de>
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

import re
import ipaddress
import publicsuffix2  # type: ignore

publicsuffixlist = publicsuffix2.PublicSuffixList()

__dyn_host = re.compile(r'(\.bb\.|broadband|cable|dial|dip|dsl|dyn|gprs|pool|ppp|umts|wimax|wwan|[0-9]{1,3}[.-][0-9]{1,3}[.-][0-9]{1,3}[.-][0-9]{1,3})', re.I)
__static_host = re.compile(r'(colo|dedi|hosting|mail|mx[^$]|smtp|static)', re.I)


def reverse_ip(ip: str) -> str:  # pylint:disable=invalid-name
    '''
    Returns the IP address in reversed notation (A.B.C.D -> D.C.B.A).

    @type  ip: string
    @param ip: the IP address to reverse
    @rtype:    string
    @return:   the reversed IP address
    '''
    ip_addr = ipaddress.ip_address(ip)
    if ip_addr.version == 4:
        parts = str(ip_addr.exploded).split('.')
    else:
        parts = list(str(ip_addr.exploded).replace(':', ''))
    parts.reverse()
    return '.'.join(parts)


def domain_from_host(host: str) -> str:
    '''
    Return the domain part of a host.

    @type  host: string
    @param host: the host to extract the domain from
    @rtype:      string
    @return:     the extracted domain
    '''

    return publicsuffixlist.get_public_suffix(host)


def check_dyn_host(host: str) -> int:
    '''
    Check the host for being a dynamic/dialup one.

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


def check_helo(params: dict) -> int:
    '''
    Check the HELO for being RFC 5321 complaint.
    Returns 0 when the HELO match the reverse DNS.
    Returns 1 when the domain in the HELO match the domain of the reverse DNS
    or when the HELO is the IP address.
    Returns 2 else.

    @type  params: dict
    @param params: the params from Postfix
    @rtype:        int
    @return:       the score of the HELO
    '''
    if (params['helo_name'].startswith('[')
       and params['helo_name'].endswith(']')):
        try:
            params['helo_name'] = '[%s]' % ipaddress.ip_address(params['helo_name'].strip('[]')).exploded
        except ValueError:
            pass

    if (params['client_name'] != 'unknown'
       and params['client_name'] == params['helo_name']):
        score = 0
    elif (domain_from_host(params['helo_name']) == domain_from_host(params['client_name'])
          or params['helo_name'] == '[%s]' % params['client_address']):
        score = 1
    else:
        score = 2

    return score


def check_spf(params: dict, guess: int) -> int:
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
        spf_query = (params['client_address'], params['sender'], params['helo_name'])
        # spf_result = spf_query.check()
        spf_result = spf_query[0]
        spf_result = 'fail'
        if spf_result in ['fail', 'softfail']:
            score = 1
        elif spf_result in ['pass']:
            score = 0
        elif guess > 0 and spf_result in ['none']:
            # spf_result = spf_query.best_guess()
            spf_result = 'fail'
            if spf_result in ['fail', 'softfail']:
                score = 1
            elif spf_result in ['pass']:
                score = 0
    except Exception:  # pylint:disable=broad-except
        # DNS Errors, yay...
        print('something went wrong in check_spf()')
    return score


def adapt_query_for_sqlite3(query: str) -> str:
    """
    Convert pyformat style SQL queries to named ones for SQLite
    """
    return query.replace('%(', ':').replace(')s', '')
