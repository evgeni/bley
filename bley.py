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

import socket
import daemon
import os
import signal

from BleyWorker import BleyWorker
import settings

def bley_start():
    if settings.pid_file:
        f = open(settings.pid_file, 'w')
        f.write(str(os.getpid()))
        f.close()

    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind((settings.listen_addr, settings.listen_port))
    serversocket.listen(5)
	
    while running:
        (clientsocket, address) = serversocket.accept()
        worker = BleyWorker(clientsocket, settings)
        worker.start()

def bley_stop(signum, frame):
    running = False
    if settings.pid_file:
        os.unlink(settings.pid_file)

context = daemon.DaemonContext(
    stderr=open(settings.log_file, 'a')
    )

context.signal_map = {
    signal.SIGTERM: bley_stop,
    signal.SIGHUP: 'terminate',
    }


running = True

context.open()
bley_start()
