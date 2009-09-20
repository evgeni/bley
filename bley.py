#!/usr/bin/env python
#
#       bley.py
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
