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

from twisted.internet.protocol import Factory
from twisted.names import client
from twisted.internet import defer
from twisted.internet import reactor

import datetime
import logging
import re

import bleyhelpers
from postfix import PostfixPolicy

from time import sleep

import ipaddress

logger = logging.getLogger('bley')
regexp_type = type(re.compile(''))


class BleyPolicy(PostfixPolicy):
    '''Implementation of intelligent greylisting based on `PostfixPolicy`'''

    db = None
    dbc = None
    required_params = ['sender', 'recipient', 'client_address',
                       'client_name', 'helo_name']

    @defer.inlineCallbacks
    def check_policy(self):
        '''Check the incoming mail based on our policy and tell Postfix
        about our decision.

        The policy works as follows:
          1. Accept if recipient=(postmaster|abuse)
          2. Check local DB for an existing entry
          3. When not found, check
             1. DNSWLs (accept if found)
             2. DNSBLs (reject if found)
             3. HELO/dyn_host/sender_eq_recipient (reject if over threshold)
             4. SPF (reject if over threshold)
             5. Accept if not yet rejected
          4. When found
             1. Whitelisted: accept
             2. Greylisted and waited: accept
             3. Greylisted and not waited: reject

        @type  postfix_params: dict
        @param postfix_params: parameters we got from Postfix
        '''

        if not self.db:
            self.db = self.factory.settings.db
            try:
                self.dbc = self.db.cursor()
            except:
                self.safe_reconnect()

        check_results = {'DNSWL': 0, 'DNSBL': 0, 'HELO': 0, 'DYN': 0, 'DB': -1,
                         'SPF': 0, 'S_EQ_R': 0, 'WHITELISTED': 0, 'CACHE': 0}
        action = 'DUNNO'
        self.params['now'] = datetime.datetime.now()
        postfix_params = self.params

        # Strip everything after a + in the localpart,
        # usefull for mailinglists etc
        if postfix_params['sender'].find('+') != -1:
            postfix_params['sender'] = postfix_params['sender'][:postfix_params['sender'].find('+')] + postfix_params['sender'][postfix_params['sender'].find('@'):]
        if postfix_params['recipient'].find('+') != -1:
            postfix_params['recipient'] = postfix_params['recipient'][:postfix_params['recipient'].find('+')] + postfix_params['recipient'][postfix_params['recipient'].find('@'):]

        if postfix_params['client_address'] in self.factory.bad_cache.keys():
            delta = datetime.datetime.now() - self.factory.bad_cache[postfix_params['client_address']]
            if delta < datetime.timedelta(0, self.factory.settings.cache_valid, 0):
                action = 'DEFER_IF_PERMIT %s (cached result)' % self.factory.settings.reject_msg
                check_results['CACHE'] = 1
                if self.factory.settings.verbose:
                    logger.info('decided CACHED action=%s, checks: %s, postfix: %s' %
                                (action, check_results, postfix_params))
                else:
                    logger.info('decided CACHED action=%s, from=%s, to=%s' %
                                (action, postfix_params['sender'],
                                 postfix_params['recipient']))
                self.send_action(action)
                self.factory.log_action(postfix_params, action, check_results)
                return
            else:
                del self.factory.bad_cache[postfix_params['client_address']]

        if postfix_params['client_address'] in self.factory.good_cache.keys():
            delta = datetime.datetime.now() - self.factory.good_cache[postfix_params['client_address']]
            if delta < datetime.timedelta(0, self.factory.settings.cache_valid, 0):
                action = 'DUNNO'
                check_results['CACHE'] = 1
                if self.factory.settings.verbose:
                    logger.info('decided CACHED action=%s, checks: %s, postfix: %s' %
                                (action, check_results, postfix_params))
                else:
                    logger.info('decided CACHED action=%s, from=%s, to=%s' %
                                (action, postfix_params['sender'],
                                 postfix_params['recipient']))
                self.send_action(action)
                self.factory.log_action(postfix_params, action, check_results)
                return
            else:
                del self.factory.good_cache[postfix_params['client_address']]

        status = self.check_local_db(postfix_params)
        # -1 : not found
        #  0 : regular host, not in black, not in white, let it go
        #  1 : regular host, but in white, let it go, dont check EHLO
        #  2 : regular host, but in black, lets grey for now
        if self.check_whitelist(postfix_params['recipient'].lower(),
                                self.factory.settings.whitelist_recipients):
            action = 'DUNNO'
            check_results['WHITELISTED'] = 1
        elif self.check_whitelist(postfix_params['client_name'].lower(),
                                  self.factory.settings.whitelist_clients):
            action = 'DUNNO'
            check_results['WHITELISTED'] = 1
        elif self.check_whitelist_ip(postfix_params['client_address'].lower(),
                                     self.factory.settings.whitelist_clients_ip):
            action = 'DUNNO'
            check_results['WHITELISTED'] = 1
        elif status == -1:  # not found in local db...
            check_results['DNSWL'] = yield self.check_dnswls(postfix_params['client_address'], self.factory.settings.dnswl_threshold)
            if check_results['DNSWL'] >= self.factory.settings.dnswl_threshold:
                new_status = 1
            else:
                check_results['DNSBL'] = yield self.check_dnsbls(postfix_params['client_address'], self.factory.settings.dnsbl_threshold)
                check_results['HELO'] = bleyhelpers.check_helo(postfix_params)
                check_results['DYN'] = bleyhelpers.check_dyn_host(postfix_params['client_name'])
                # check_sender_eq_recipient:
                if postfix_params['sender'] == postfix_params['recipient']:
                    check_results['S_EQ_R'] = 1
                if self.factory.settings.use_spf and check_results['DNSBL'] < self.factory.settings.dnsbl_threshold and check_results['HELO'] + check_results['DYN'] + check_results['S_EQ_R'] < self.factory.settings.rfc_threshold:
                    check_results['SPF'] = bleyhelpers.check_spf(postfix_params, self.factory.settings.use_spf_guess)
                else:
                    check_results['SPF'] = 0
                if check_results['DNSBL'] >= self.factory.settings.dnsbl_threshold or check_results['HELO'] + check_results['DYN'] + check_results['SPF'] + check_results['S_EQ_R'] >= self.factory.settings.rfc_threshold:
                    new_status = 2
                    action = 'DEFER_IF_PERMIT %s' % self.factory.settings.reject_msg
                    self.factory.bad_cache[postfix_params['client_address']] = datetime.datetime.now()
                else:
                    new_status = 0
                    self.factory.good_cache[postfix_params['client_address']] = datetime.datetime.now()
            query = "INSERT INTO bley_status (ip, status, last_action, sender, recipient) VALUES(%(client_address)s, %(new_status)s, %(now)s, %(sender)s, %(recipient)s)"
            postfix_params['new_status'] = new_status
            try:
                self.safe_execute(query, postfix_params)
            except:
                # the other thread already commited while we checked, ignore
                pass

        elif status[0] >= 2:  # found to be greyed
            check_results['DB'] = status[0]
            delta = datetime.datetime.now() - status[1]
            if delta > self.factory.settings.greylist_period + status[2] * self.factory.settings.greylist_penalty or delta > self.factory.settings.greylist_max:
                action = 'DUNNO'
                query = "UPDATE bley_status SET status=0, last_action=%(now)s WHERE ip=%(client_address)s AND sender=%(sender)s AND recipient=%(recipient)s"
                self.factory.good_cache[postfix_params['client_address']] = datetime.datetime.now()
            else:
                action = 'DEFER_IF_PERMIT %s' % self.factory.settings.reject_msg
                query = "UPDATE bley_status SET fail_count=fail_count+1 WHERE ip=%(client_address)s AND sender=%(sender)s AND recipient=%(recipient)s"
                self.factory.bad_cache[postfix_params['client_address']] = datetime.datetime.now()
            self.safe_execute(query, postfix_params)

        else:  # found to be clean
            check_results['DB'] = status[0]
            action = 'DUNNO'
            query = "UPDATE bley_status SET last_action=%(now)s WHERE ip=%(client_address)s AND sender=%(sender)s AND recipient=%(recipient)s"
            self.safe_execute(query, postfix_params)
            self.factory.good_cache[postfix_params['client_address']] = datetime.datetime.now()

        if self.factory.settings.verbose:
            logger.info('decided action=%s, checks: %s, postfix: %s' %
                        (action, check_results, postfix_params))
        else:
            logger.info('decided action=%s, from=%s, to=%s' %
                        (action, postfix_params['sender'],
                         postfix_params['recipient']))
        self.factory.log_action(postfix_params, action, check_results)
        self.send_action(action)

    def check_whitelist(self, email, whitelist):
        '''Check the arg email against a whitelist
        The whitelist consists of strings or compiled regular expressions
        from the whitelist file
        Return 1 if any of
            email matches the entire entry
            email matches the regular expression
            email domain (or subdomain) matches the entry (which is a domain
            name)
            email user@ part matches an entry of the form user@
        '''
        for entry_wl in whitelist:
            if isinstance(entry_wl, regexp_type):
                if entry_wl.search(email) is not None:
                    logger.info('whitelisted %s due to rule %s' %
                                (email, entry_wl.pattern))
                    return 1
                else:
                    # It's a regex, but it doesn't match
                    # next whitelist item please
                    continue
            # whitelist item is a string
            if entry_wl.endswith('@'):
                # user@ (any domain) match
                if email.startswith(entry_wl):
                    logger.info('whitelisted %s due to rule %s' %
                                (email, entry_wl))
                    return 1
                else:
                    continue
            if len(email) > len(entry_wl):
                entry_wl_length = len(entry_wl) + 1
                if ('.' + entry_wl) == email[-entry_wl_length:]:
                    # subdomain match
                    logger.info('whitelisted %s due to rule %s' %
                                (email, entry_wl))
                    return 1
                elif ('@' + entry_wl) == email[-entry_wl_length:]:
                    # @domain match
                    logger.info('whitelisted %s due to rule %s' %
                                (email, entry_wl))
                    return 1
            if entry_wl == email:
                # Whole email match (for whitelist_recipients)
                # Or domain match (for whitelist_clients)
                logger.info('whitelisted %s due to rule %s' %
                            (email, entry_wl))
                return 1
        return 0

    def check_whitelist_ip(self, ipstr, whitelist_ip):
        '''Check the arg ipstr against a whitelist
        The whitelist consists of ip objects generated from the whitelist file
        Return 1 if
            ipstr is a valie ip address
            -- AND --
            ipstr matches one of the entries in the whitelist_ip list
        '''
        try:
            ip = ipaddress.ip_address(ipstr)
        except (ValueError):
            return 0
        for net in whitelist_ip:
            if ip in net:
                logger.info('whitelisted %s because it is in subnet %s' %
                            (str(ip), str(net)))
                return 1
        return 0

    def check_local_db(self, postfix_params):
        '''Check the sender for being in the local database.

        Queries the local SQL database for the (ip,sender,recipient) tuple.

        @type  postfix_params: dict
        @param postfix_params: parameters we got from Postfix
        @rtype: list
        @return: the result from SQL if any
        '''

        query = """SELECT status,last_action,fail_count,sender,recipient
                    FROM bley_status
                    WHERE ip=%(client_address)s
                    AND sender=%(sender)s AND recipient=%(recipient)s
                    ORDER BY status ASC
                    LIMIT 1"""
        try:
            self.safe_execute(query, postfix_params)
            result = self.dbc.fetchone()
        except:
            result = None
            logger.info('check_local_db failed. sending unknown.')
        if not result:
            return -1
        else:
            return result

    @defer.inlineCallbacks
    def check_dnswls(self, ip, max_listed):
        '''Check the IP address in DNSWLs.

        @type ip: string
        @param ip: the IP to check
        @type max: int
        @param max: stop after max hits
        @rtype: int
        @return: in how many DNSWLs did we find ip?
        '''
        result = 0
        for l in self.factory.settings.dnswls:
            try:
                d = yield self.check_dnsl(l, ip)
                result += 1
            except Exception:
                pass
            if result >= max_listed:
                break
        defer.returnValue(result)

    @defer.inlineCallbacks
    def check_dnsbls(self, ip, max_listed):
        '''Check the IP address in DNSBLs.

        @type ip: string
        @param ip: the IP to check
        @type max: int
        @param max: stop after max hits
        @rtype: int
        @return: in how many DNSBLs did we find ip?
        '''
        result = 0
        for l in self.factory.settings.dnsbls:
            try:
                d = yield self.check_dnsl(l, ip)
                result += 1
            except Exception:
                pass
            if result >= max_listed:
                break
        defer.returnValue(result)

    def check_dnsl(self, lst, ip):
        '''Check the IP address in a DNS list.

        @type ip: string
        @param ip: the IP to check
        @type lst: sting
        @param lst: the DNS list to check in
        @rtype: C{Deferred}
        @return: twisted.names.client resolver
        '''

        rip = bleyhelpers.reverse_ip(ip)
        lookup = '%s.%s' % (rip, lst)
        d = client.lookupAddress(lookup)
        return d

    def safe_execute(self, query, params=None):
        if self.factory.settings.dbtype == 'sqlite3':
            query = bleyhelpers.adapt_query_for_sqlite3(query)
        try:
            self.dbc.execute(query, params)
            self.db.commit()
        except self.factory.settings.database.OperationalError:
            self.safe_reconnect()
            if self.db:
                self.dbc.execute(query, params)
                self.db.commit()
            else:
                logger.info('Could not reconnect to the database, exiting.')
                reactor.stop()

    def safe_reconnect(self):
        logger.info('Reconnecting to the database after an error.')
        try:
            self.db.close()
        except:
            pass
        self.db = None
        retries = 0
        while not self.db and retries < 30:
            try:
                self.factory.settings.db = self.db = self.factory.settings.database.connect(**self.factory.settings.dbsettings)
                self.dbc = self.db.cursor()
            except self.factory.settings.database.OperationalError:
                self.db = None
                retries += 1
                sleep(1)


class BleyPolicyFactory(Factory):
    protocol = BleyPolicy

    def __init__(self, settings):
        self.settings = settings
        self.good_cache = {}
        self.bad_cache = {}
        self.actionlog = []
        self.exim_workaround = settings.exim_workaround
        reactor.callLater(30 * 60, self.dump_log)
        reactor.addSystemEventTrigger('before', 'shutdown', self.dump_log)

    def log_action(self, postfix_params, action, check_results):
        now = datetime.datetime.now()
        action = action.split(' ')[0]
        logline = {'time': str(now), 'ip': postfix_params['client_address'],
                   'from': postfix_params['sender'],
                   'to': postfix_params['recipient'],
                   'action': action}
        logline.update(check_results)
        self.actionlog.append(logline)

    def dump_log(self):
        query = '''INSERT INTO bley_log (logtime, ip, sender, recipient,
                action, check_dnswl, check_dnsbl, check_helo, check_dyn,
                check_db, check_spf, check_s_eq_r, check_postmaster,
                check_cache)
                VALUES(%(time)s, %(ip)s, %(from)s, %(to)s, %(action)s,
                %(DNSWL)s, %(DNSBL)s, %(HELO)s, %(DYN)s, %(DB)s,
                %(SPF)s, %(S_EQ_R)s, %(WHITELISTED)s, %(CACHE)s)'''

        if self.settings.dbtype == 'sqlite3':
            query = bleyhelpers.adapt_query_for_sqlite3(query)

        try:
            db = self.settings.database.connect(**self.settings.dbsettings)
            dbc = db.cursor()
            i = len(self.actionlog)
            while i:
                logline = self.actionlog.pop(0)
                dbc.execute(query, logline)
                i -= 1
            db.commit()
            dbc.close()
            db.close()
        except self.settings.database.DatabaseError as e:
            logger.warn('SQL error: %s' % e)
        reactor.callLater(30 * 60, self.dump_log)
