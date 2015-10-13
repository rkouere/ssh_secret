import argparse
import queue
import socket
import sys
import time
from threading import Thread
try:
    import requests
except ImportError:
    print("Please download requests with `pip install requests`")
    sys.exit(1)

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
    def __init__(self, socket, baseurl, interval, *args, **kwargs):
        self.socket = socket
        self.baseurl = baseurl
        self.interval = interval
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        while True:
            r = try_post(self.baseurl+"/down", self.interval)
            if len(r.content):
                print("Sending data to SSH server : "+str(r.content))
                self.socket.send(r.content)


class SSHWriteThread(Thread):
    def __init__(self, socket, baseurl, interval, *args, **kwargs):
        self.socket = socket
        self.baseurl = baseurl
        self.interval = interval
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        while True:
            rawdata = self.socket.recv(2048)
            print("Read data from SSH server :"+str(rawdata))
            try_post(self.baseurl+"/down", self.interval, data=rawdata)


def run(baseurl="http://localhost:8000", ssh_port=22, bind="", interval=1):
    try:
        ssh_socket.connect((bind, ssh_port))
    except ConnectionRefusedError:
        print("Cannot connect to local sshd on port {}".format(ssh_port))
        sys.exit(1)

    read_thread = SSHReadThread(ssh_socket, baseurl, interval)
    write_thread = SSHWriteThread(ssh_socket, baseurl, interval)

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
    args = parser.parse_args()
    run(ssh_port=args.ssh_port, baseurl=args.baseurl, bind=args.bind, interval=float(args.interval))
