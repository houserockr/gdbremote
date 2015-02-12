 #!/usr/bin/env python

import socket
from subprocess import *
import subprocess
import select
from os import read
import signal
import sys
import errno

TCPBUFSIZ = 1024
TCPADDR = '127.0.0.1'
TCPPORT = 4711
SUBPBUFSIZ = 1024
BIN = '/usr/local/bin/gdb'

print "Starting process %s..." % BIN
process = Popen([BIN], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print process

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.setblocking(0)
server.bind((TCPADDR, TCPPORT))
server.listen(1)

clients = []
rlist = [server, process.stdout, process.stderr]
wlist = []
xlist = []

def appendClient(client):
    rlist.append(client)
    clients.append(client)

def broadcastData(data):
    for sock in clients:
        sock.send(data)

def signalHandler(sig, frame):
    if sig == signal.SIGINT:
        process.kill()
        for sock in clients:
            sock.close()
        server.close()
    sys.exit(0)

def exitProc(code):
    for sock in clients:
        sock.close()
    server.close()
    sys.exit(code)

# set up a signal handler
signal.signal(signal.SIGINT, signalHandler)

while True:
    try: r,w,e = select.select(rlist, wlist, xlist)
    except select.error, v:
        if v[0] != errno.EINTR: raise
        else: signalHandler(signal.SIGINT, 0)
    for fd in r:
        if fd == server:
            # new client connected, add to readList
            conn, addr = server.accept()
            appendClient(conn)
            print "Client (%s, %s) connected" % addr
        elif fd == process.stdout or fd == process.stderr:
            # Got data from running process, redirect
            if process.poll() is not None:
                exitProc(0)
            data = read(fd.fileno(), SUBPBUFSIZ)
            broadcastData(data)
        else:
            # Got data from one of the connected clients
            data = fd.recv(TCPBUFSIZ)
            process.stdin.write(data)
            process.stdin.flush()
