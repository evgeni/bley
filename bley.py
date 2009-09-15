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
from BleyWorker import BleyWorker

def main():
	
	serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	serversocket.bind(('192.168.0.1', 1337))
	serversocket.listen(5)
	
	running = True
	while running:
		(clientsocket, address) = serversocket.accept()
		worker = BleyWorker(clientsocket)
		worker.start()
		#running = False
	
	return 0

if __name__ == '__main__': main()
