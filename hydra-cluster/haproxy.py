__author__ = 'ragnar'

"""
Helper script to write to and read from HAProxy UNIX socket.
"""

import sys
import socket

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect('/var/run/haproxy/admin.sock')

cmd = bytes('{}\n'.format(' '.join(sys.argv[1:])), 'ascii')

s.send(cmd)

data = s.recv(1024)
res = ''
while True:
    res += data.decode('ascii')
    data = s.recv(1024)
    if not data:
        break

s.close()
print(res)
