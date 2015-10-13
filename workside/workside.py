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


class SSHReadThread(Thread):
    def __init__(self, socket, baseurl, *args, **kwargs):
        self.socket = socket
        self.baseurl = baseurl
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        while True:
            while True:
                try:
                    r = requests.post(self.baseurl+"/down")
                    print("Connection etablished")
                    break
                except requests.exceptions.ConnectionError:
                    print("Connection failed, retry in 1 sec")
                    time.sleep(1)
            if len(r.content):
                print("Sending data to SSH server : "+str(r.content))
                self.socket.send(r.content)


class SSHWriteThread(Thread):
    def __init__(self, socket, baseurl, *args, **kwargs):
        self.socket = socket
        self.baseurl = baseurl
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        while True:
            rawdata = self.socket.recv(2048)
            print("Read data from SSH server :"+str(rawdata))
            while True:
                try:
                    r = requests.post(self.baseurl+"/up", data=rawdata)
                    print("Connection etablished")
                    break
                except requests.exceptions.ConnectionError:
                    print("Connection failed, retry in 1 sec")
                    time.sleep(1)




def run(baseurl="http://localhost:8000", ssh_port=22, bind=""):
    try:
        ssh_socket.connect((bind, ssh_port))
    except ConnectionRefusedError:
        print("Cannot connect to local sshd on port {}".format(ssh_port))
        sys.exit(1)

    read_thread = SSHReadThread(ssh_socket, baseurl)
    write_thread = SSHWriteThread(ssh_socket, baseurl)

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
    args = parser.parse_args()
    run(ssh_port=args.ssh_port, baseurl=args.baseurl, bind=args.bind)
