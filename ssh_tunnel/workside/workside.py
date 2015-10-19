import argparse
import queue
import socket
import sys
import time
import hashlib, binascii

from threading import Thread
try:
    import requests
except ImportError:
    print("Please download requests with `pip3 install requests`")
    sys.exit(1)

from ssh_tunnel.commons import Cipherer

ssh_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def try_post(url, interval, *args, **kwargs):
    while True:
        try:
            r = requests.post(url, *args, **kwargs)
            print("Connection etablished with {}".format(url))
            return r
        except requests.exceptions.ConnectionError:
            print("Connection to {} failed, retry in {} sec".format(url, interval))
            time.sleep(interval)

class SSHReadThread(Thread):
    def __init__(self, socket, baseurl, interval, cipherer, *args, **kwargs):
        self.socket = socket
        self.baseurl = baseurl
        self.interval = interval
        self.cipherer = cipherer
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        while True:
            r = try_post(self.baseurl+"/down", self.interval)
            if len(r.content):
                print("Sending data to SSH server : "+str(r.content))
                content = self.cipherer.decrypt(r.content)
                self.socket.send(content)


class SSHWriteThread(Thread):
    def __init__(self, socket, baseurl, interval, cipherer, *args, **kwargs):
        self.socket = socket
        self.baseurl = baseurl
        self.interval = interval
        self.cipherer = cipherer
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        while True:
            rawdata = self.socket.recv(2048)
            print("Read data from SSH server :"+str(rawdata))
            encrypted_rawdata = self.cipherer.encrypt(rawdata)
            try_post(self.baseurl+"/up", self.interval, data=encrypted_rawdata)


def run(passphrase, baseurl="http://localhost:8000", ssh_port=22, bind="", interval=1):
    try:
        ssh_socket.connect((bind, ssh_port))
    except ConnectionRefusedError:
        print("Cannot connect to local sshd on port {}".format(ssh_port))
        sys.exit(1)

    cipherer = Cipherer(passphrase)
    read_thread = SSHReadThread(ssh_socket, baseurl, interval, cipherer)
    write_thread = SSHWriteThread(ssh_socket, baseurl, interval, cipherer)

    read_thread.start()
    write_thread.start()

    read_thread.run()
    write_thread.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', '-b', default='', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
    parser.add_argument('baseurl', action='store',
                        default="http://localhost:8000", type=str,
                        nargs='?',
                        help='Specify alternate url for http interface [default: http://localhost:8000]')
    parser.add_argument('ssh_port', action='store',
                        default=22, type=int,
                        nargs='?',
                        help='Specify alternate port for ssh interface [default: 22]')
    parser.add_argument('--interval', action='store',
                        default=1,
                        nargs='?',
                        help='Specify alternate interval between http requests [default: 1 s]')
    parser.add_argument('passphrase', action='store',
                        help='Specify the passphrase to use')
    args = parser.parse_args()
    run(args.passphrase, ssh_port=args.ssh_port, baseurl=args.baseurl, bind=args.bind, interval=float(args.interval))
