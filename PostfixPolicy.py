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

class PostfixPolicy:
    '''Basic implementation of a Postfix policy service.'''

    __csocket = None

    def __init__ (self, csocket):
        self.__csocket = csocket

    def parse_input (self):
        '''Parse stuff from Postfix and call check_policy() afterwards.'''
        while True:
            postfix_params = {}
            buff = self.__csocket.recv(8192)
            if not buff: break
            lines = buff.splitlines()
            for line in lines:
                line = line.strip()
                if line == '':
                    break
                else:
                    try:
                        (pkey, pval) = line.split('=', 1)
                        postfix_params[pkey] = pval
                    except:
                        print 'Could not parse "%s"' % line

            self.check_policy(postfix_params)

    def check_policy (self, postfix_params):
        '''You probably want to override this one to do something useful.'''
        self.send_action('DUNNO')

    def send_action (self, action='DUNNO'):
        '''Send action back to Postfix.'''
        self.__csocket.sendall('action=%s\n\n' % action)