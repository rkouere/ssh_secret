#!/usr/bin/env python3
import argparse
import io
import queue
import shutil
import socket
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from ssh_tunnel.commons import Cipherer

_ssh_server = None
incoming_content = queue.Queue()
outgoing_content = queue.Queue()
ssh_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
cipherer = None

class SSHTunnelHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/":
            self.handle_root()
        elif self.path == "/down":
            self.handle_down()
        elif self.path == "/up":
            self.handle_up()
        else:
            self.send_response(400)
            self.end_headers()

    def handle_root(self):
        body = b"SSH to HTTP tunnel is up and running"
        print(body)
        f = io.BytesIO()
        f.write(body)
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "raw")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        # This needs to be done after sending the headers
        shutil.copyfileobj(f, self.wfile)
        f.close()

    def handle_down(self):
        try:
            body = incoming_content.get(timeout=1)
            body = cipherer.encrypt(body)
        except queue.Empty:
            body = b""

        f = io.BytesIO()
        f.write(body)
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "raw")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        # This needs to be done after sending the headers
        shutil.copyfileobj(f, self.wfile)
        f.close()

    def handle_up(self):
        """
        Read the content of the request, and inject it in ssh socket
        """
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        body = cipherer.decrypt(body)
        outgoing_content.put(body)
        self.send_response(201)
        self.send_header("Content-type", "raw")
        self.end_headers()

    def log_message(self, format, *args):
        # Mute the default message logger
        return


class SSHReadThread(Thread):
    def __init__(self, socket, *args, **kwargs):
        self.socket = socket
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        while True:
            rawdata = self.socket.recv(2048)
            incoming_content.put(rawdata)


class SSHWriteThread(Thread):
    def __init__(self, socket, *args, **kwargs):
        self.socket = socket
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        while True:
            rawdata = outgoing_content.get()
            len = self.socket.send(rawdata)


class SSHThread(Thread):
    def __init__(self, bind, port, ssh_socket, *args, **kwargs):
        self.socket = ssh_socket
        self.bind = bind
        self.port = port
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        self.socket.bind((self.bind, self.port))
        self.socket.listen(0)
        ssh_server_info = self.socket.getsockname()
        print("SSH Socket listening on", ssh_server_info[0], "port", ssh_server_info[1], "...")
        print("Now serving ssh")
        while True:
            incomming, _ = self.socket.accept()
            print("Got a client ! Handle it in a new thread")
            client_reading_thread = SSHReadThread(incomming)
            client_writing_thread = SSHWriteThread(incomming)
            client_reading_thread.start()
            client_writing_thread.start()
            client_reading_thread.run()
            client_writing_thread.run()

class HTTPThread(Thread):
    def __init__(self, bind, port, cipherer, *args, **kwargs):
        self.bind = bind
        self.port = port
        self.cipherer = cipherer
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        self.server = HTTPServer((self.bind, self.port), SSHTunnelHTTPRequestHandler)
        ssh_server_info = self.server.socket.getsockname()
        print("HTTP Socket listening on", ssh_server_info[0], "port", ssh_server_info[1], "...")
        print("Now serving http")
        self.server.serve_forever()


def run(passphrase, protocol="HTTP/1.0", http_port=8000, ssh_port=2222, bind=""):
    """This run a listening ssh thread, a listening http thread, then
    starts an external ssh client connecting to the listining ssh port
    """
    # Instanciate the needed threads
    global cipherer
    cipherer = Cipherer(passphrase)
    ssh_thread = SSHThread(bind, ssh_port, ssh_socket)
    http_thread = HTTPThread(bind, http_port, cipherer)

    try:
        ssh_thread.start()
        http_thread.start()
        print("Starting external ssh client")
        os.system('ssh -v localhost -p {}'.format(ssh_port))

    except Exception as e:
        print(e)
        ssh_thread.socket.close()
        http_thread.server.server_close()
        sys.exit(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', '-b', default='', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
    parser.add_argument('http_port', action='store',
                        default=8000, type=int,
                        nargs='?',
                        help='Specify alternate port for http interface [default: 8000]')
    parser.add_argument('ssh_port', action='store',
                        default=2222, type=int,
                        nargs='?',
                        help='Specify alternate port for ssh interface [default: 2222]')
    parser.add_argument('passphrase', action='store',
                        help='Specify the passphrase to use. Must be the same that the one specified on workside')
    args = parser.parse_args()
    run(args.passphrase, ssh_port=args.ssh_port, http_port=args.http_port, bind=args.bind)
