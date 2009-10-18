#!/usr/bin/env python
#
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

from threading import Thread
import psycopg2
import adns
import datetime
from bleyhelpers import *
from PostfixPolicy import PostfixPolicy

class BleyWorker (PostfixPolicy, Thread):
	
	settings = None
	db = None
	dbc = None
	adns_handle = None
	
	def __init__ (self, csocket, settings):
		self.settings = settings
		self.db = self.settings.database.connect(self.settings.dsn)
		self.dbc = self.db.cursor()
		self.adns_handle = adns.init()
		PostfixPolicy.__init__(self, csocket)
		Thread.__init__(self)
	
	def run(self):
		self.parse_input()

	def check_policy (self, postfix_params):
		check_results = {'DNSWL': 0, 'DNSBL': 0, 'HELO': 0, 'DYN': 0, 'DB': -1, 'SPF': 0, 'S_EQ_R': 0 }
		action = 'DUNNO'

		status = self.check_local_db(postfix_params)
		# -1 : not found
		#  0 : regular host, not in black, not in white, let it go
		#  1 : regular host, but in white, let it go, dont check EHLO
		#  2 : regular host, but in black, lets grey for now
		if postfix_params['recipient'].lower().startswith('postmaster'):
			action = 'DUNNO'
		elif status == -1: # not found in local db...
			check_results['DNSWL'] = self.check_dnswls(postfix_params['client_address'])
			if check_results['DNSWL'] >= self.settings.dnswl_threshold:
				new_status = 1
			else:
				check_results['DNSBL'] = self.check_dnsbls(postfix_params['client_address'])
				check_results['HELO'] = check_helo(postfix_params)
				check_results['DYN'] = is_dyn_host(postfix_params['client_name'])
				check_results['SPF'] = check_spf(postfix_params)
				if postfix_params['sender']==postfix_params['recipient']:
					check_results['S_EQ_R'] = 1
				if check_results['DNSBL'] >= self.settings.dnsbl_threshold or check_results['HELO']+int(check_results['DYN'])+check_results['SPF']+check_results['S_EQ_R'] >= self.settings.rfc_threshold:
					new_status = 2
					action = 'DEFER_IF_PERMIT %s' % self.settings.reject_msg
				else:
					new_status = 0
                        query = "INSERT INTO bley_status (ip, status, last_action, last_from, last_to) VALUES(%(client_address)s, %(new_status)s, 'now', %(sender)s, %(recipient)s)"
			params = postfix_params.copy()
			params['new_status'] = new_status
			try:
                            self.dbc.execute(query, params)
			except IntegrityError:
                            # the other thread already commited while we checked, ignore
                            pass
                        self.db.commit()

		elif status[0] >= 2: # found to be greyed
			check_results['DB'] = status[0]
			delta = datetime.datetime.now()-status[1]
			if delta > self.settings.greylist_period+status[2]*self.settings.greylist_penalty or delta > self.settings.greylist_max:
				action = 'DUNNO'
				query = "UPDATE bley_status SET status=0, last_action='now', last_from=%(sender)s, last_to=%(recipient)s WHERE ip=%(client_address)s"
				self.dbc.execute(query, postfix_params)
				self.db.commit()
			else:
				action = 'DEFER_IF_PERMIT %s' % self.settings.reject_msg
				query = "UPDATE bley_status SET fail_count=fail_count+1, last_action='now', last_from=%(sender)s, last_to=%(recipient)s WHERE ip=%(client_address)s"
				self.dbc.execute(query, postfix_params)
				self.db.commit()

		else: # found to be clean
			check_results['DB'] = status[0]
			action = 'DUNNO'
			query = "UPDATE bley_status SET last_action='now', last_from=%(sender)s, last_to=%(recipient)s WHERE ip=%(client_address)s"
			self.dbc.execute(query, postfix_params)
			self.db.commit()

		self.settings.logger('decided action=%s, checks: %s, postfix: %s\n' % (action, check_results, postfix_params))
		self.send_action(action)

	def check_local_db(self, postfix_params):
		query = "SELECT status,last_action,fail_count FROM bley_status WHERE ip=%(client_address)s LIMIT 1"
		self.dbc.execute(query, postfix_params)
		result = self.dbc.fetchone()
		if not result:
			return -1
		else:
			return result

	def check_dnswls(self, ip):
		result = 0
		for l in self.settings.dnswls:
			if self.check_dnsl(l, ip):
				result += 1
		return result

	def check_dnsbls(self, ip):
		result = 0
                for l in self.settings.dnsbls:
                        if self.check_dnsl(l, ip):
                                result += 1
                return result

	def check_dnsl(self, lst, ip):
		rip = reverse_ip(ip)
		lookup = '%s.%s' % (rip, lst)
		try:
			res = self.adns_handle.synchronous(lookup, adns.rr.A)
			return res[3] != ()
		except:
			# DNS Errors
			return False
