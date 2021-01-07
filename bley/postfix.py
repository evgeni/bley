# Copyright (c) 2009-2014 Evgeni Golov <evgeni@golov.de>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# 3. Neither the name of the University nor the names of its contributors
# may be used to endorse or promote products derived from this software
# without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

import asyncio
import ipaddress
from typing import Dict, List


async def handle_echo(reader, writer):
    data = await reader.read(100)
    writer.write(data)
    await writer.drain()
    writer.close()


async def main(host: str = '127.0.0.1', port: int = 8888):
    server = await asyncio.start_server(handle_echo, host, port)

    async with server:
        await server.serve_forever()


class PostfixPolicy():
    '''Basic implementation of a Postfix policy service.'''

    required_params: List[str] = []

    def __init__(self) -> None:
        self.params: Dict[str, str] = {}
        self.delimiter = b'\n'

    def lineReceived(self, line: str) -> None:
        '''Parse stuff from Postfix and call check_policy() afterwards.'''
        line = line.strip().lower()
        if line == '' or line == b'':
            if len(self.params) > 0:
                valid_request = True
                for p in self.required_params:
                    if p not in self.params:
                        valid_request = False
                        break
                if valid_request:
                    self.check_policy()
                else:
                    self.send_action('DUNNO')
            self.params = {}
        else:
            try:
                (pkey, pval) = line.split('=', 1)
                if pkey == 'client_address':
                    pval = ipaddress.ip_address(pval).exploded
                self.params[pkey] = pval
            except Exception:
                print('Could not parse "%s"' % line)

    def check_policy(self) -> None:
        '''Check the incoming mail based on our policy and tell Postfix
        about our decision.

        You probably want to override this one with a function that does
        something useful.
        '''
        self.send_action('DUNNO')

    def send_action(self, action: str = 'DUNNO') -> None:
        '''Send action back to Postfix.

        @type action: string
        @param action: the action to be sent to Postfix (default: 'DUNNO')
        '''
        line = b'action=%s' % action.encode('ascii')
        self.sendLine(line)
        self.sendLine(b'')
        if self.factory.exim_workaround:
            self.transport.loseConnection()

    def readConnectionLost(self) -> None:
        pass

    def writeConnectionLost(self) -> None:
        self.transport.loseConnection()


class PostfixPolicyFactory():
    protocol = PostfixPolicy
    exim_workaround = False
