import argparse
import queue
import socket
import sys
import time
try:
    import requests
except ImportError:
    print("Please download requests with `pip install requests`")
    sys.exit(1)

ssh_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def run(baseurl="http://localhost:8000", ssh_port=22, bind=""):
    try:
        ssh_socket.connect((bind, ssh_port))
    except ConnectionRefusedError:
        print("Cannot connect to local sshd on port {}".format(ssh_port))
        sys.exit(1)
    while True:
        while True:
            try:
                r = requests.post(baseurl+"/down")
                break
            except requests.exceptions.ConnectionError:
                print("Connection failed, retry in 1 sec")
                time.sleep(1)
        print("Connection reetablished")
        print(r.content)
        ssh_socket.send(r.content)
        rawdata = ssh_socket.recv(1024)
        print(rawdata)
        requests.post(baseurl+"/up", data=rawdata)


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
