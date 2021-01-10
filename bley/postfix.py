'''
Basic implementation of a Postfix policy service.
'''
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
from typing import Dict


class PostfixPolicy:
    '''
    Basic implementation of a Postfix policy service.
    '''

    async def check_policy(self, params: Dict[str, str]) -> str:  # pylint:disable=unused-argument
        '''
        Check the incoming mail based on our policy and tell Postfix
        about our decision.

        You probably want to override this one with a function that does
        something useful.
        '''

        return 'DUNNO'

    async def handle_postfix_policy(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        '''
        Parse stuff from Postfix and call check_policy() afterwards.
        '''

        params: Dict[str, str] = {}

        while (line := await reader.readline()):
            decoded_line = line.decode().strip().lower()
            if decoded_line == '':
                break
            (pkey, pval) = decoded_line.split('=', 1)
            if pkey == 'client_address':
                pval = ipaddress.ip_address(pval).exploded
            params[pkey] = pval

        result = await self.check_policy(params)
        writer.write(f'action={result}\n\n'.encode('ascii'))
        await writer.drain()
        writer.close()

    async def run(self, host: str = '127.0.0.1', port: int = 8888) -> None:
        '''
        Basic implementation of a Postfix policy service.
        '''

        policy = PostfixPolicy()
        server = await asyncio.start_server(policy.handle_postfix_policy, host, port)

        async with server:
            await server.serve_forever()
