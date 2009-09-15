#!/usr/bin/env python
#
#       BleyWorker.py
#       
#       Copyright 2009 Evgeni Golov <evgeni@debian.org>
#       
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

from threading import Thread
import psycopg2
import adns
import datetime
from BleyHelpers import *

class BleyWorker (Thread):
	
	csocket = None
	postfix_params = {}
	db = None
	dbc = None
	adns_handle = None
	dnsbls = []
	dnswls = []
	
	def __init__ (self, csocket):
		self.csocket = csocket
		self.postfix_params = {}
		self.db = psycopg2.connect("dbname=bley")
		self.dbc = self.db.cursor()
		self.adns_handle = adns.init()
		self.dnsbls = ['ix.dnsbl.manitu.net', 'dnsbl.njabl.org', 'dnsbl.ahbl.org', 'dnsbl.sorbs.net']
		self.dnswls = ['list.dnswl.org', 'exemptions.ahbl.org']
		Thread.__init__(self)
	
	def run(self):
		while True:
			buff = self.csocket.recv(4096)
			if not buff: break
			lines = buff.splitlines()
			for line in lines:
				line = line.strip()
				if line == '':
					print 'Got final line'
					break
				else:
					try:
						(pkey, pval) = line.split('=')
						self.postfix_params[pkey] = pval
						print 'Set %s=%s' % (pkey,pval)
					except:
						print 'Could not parse "%s"' % line

			action = 'DUNNO'
			status = self.check_local_db(self.postfix_params)
			# -1 : not found
			#  0 : regular host, not in black, not in white, let it go
			#  1 : regular host, but in white, let it go, dont check EHLO
			#  2 : regular host, but in black, lets grey for now
			if self.postfix_params['recipient'].lower().startswith('postmaster'):
				action = 'DUNNO'
			elif status == -1: # not found in local db...
				in_dnswl = self.check_dnswls(self.postfix_params['client_address'])
				in_dnsbl = 0
				if in_dnswl >= 1:
					new_status = 1
				else:
					in_dnsbl = self.check_dnsbls(self.postfix_params['client_address'])
					if in_dnsbl >= 2 or check_helo(self.postfix_params) >= 2:
						new_status = 2
						action = 'DEFER_IF_PERMIT greylisted, try again later.'
					else:
						new_status = 0
	                        query = "INSERT INTO bley_status (ip, status, last_action, last_from, last_to) VALUES(%(client_address)s, %(new_status)s, 'now', %(sender)s, %(recipient)s)"
				params = self.postfix_params.copy()
				params['new_status'] = new_status
	                        self.dbc.execute(query, params)
	                        self.db.commit()

				print 'Found %s in %i DNSWLs and %i DNSBLs (saved status %i)' % (self.postfix_params['client_address'], in_dnswl, in_dnsbl, new_status)
			elif status[0] >= 2: # found to be greyed
				delta = datetime.datetime.now()-status[1]
				if delta > datetime.timedelta(0, 60*60, 0): # older than a hour
					action = 'DUNNO'
					query = "UPDATE bley_status SET status=0, last_action='now', last_from=%(sender)s, last_to=%(recipient)s WHERE ip=%(client_address)s"
					self.dbc.execute(query, self.postfix_params)
					self.db.commit()
				else:
					action = 'DEFER_IF_PERMIT greylisted, try again later.'
			else: # found to be clean
				action = 'DUNNO'
				query = "UPDATE bley_status SET last_action='now', last_from=%(sender)s, last_to=%(recipient)s WHERE ip=%(client_address)s"
				self.dbc.execute(query, self.postfix_params)
				self.db.commit()

			self.csocket.sendall('action=%s\n\n' % action)

	def check_local_db(self, postfix_params):
		query = "SELECT status,last_action FROM bley_status WHERE ip=%(client_address)s LIMIT 1"
		self.dbc.execute(query, postfix_params)
		result = self.dbc.fetchone()
		if not result:
			return -1
		else:
			return result

	def check_dnswls(self, ip):
		result = 0
		for l in self.dnswls:
			if self.check_dnsl(l, ip):
				result += 1
		return result

	def check_dnsbls(self, ip):
		result = 0
                for l in self.dnsbls:
                        if self.check_dnsl(l, ip):
                                result += 1
                return result

	def check_dnsl(self, lst, ip):
		rip = reverse_ip(ip)
		lookup = '%s.%s' % (rip, lst)
		res = self.adns_handle.synchronous(lookup, adns.rr.A)
		return res[3] != ()
