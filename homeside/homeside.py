#!/usr/bin/env python3
import argparse
import io
import queue
import shutil
import socket
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

_ssh_server = None
incoming_content = queue.Queue()
outgoing_content = queue.Queue()
ssh_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


class SSHTunnelHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/down":
            self.handle_down()
        elif self.path == "/up":
            self.handle_up()
        else:
            self.send_response(400)
            self.end_headers()

    def handle_down(self):
        print(incoming_content)
        body = incoming_content.get()

        f = io.BytesIO()
        f.write(body)
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "raw")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        # This needs to be done after sending the headers
        shutil.copyfileobj(f, self.wfile)
        incoming_content.task_done()
        f.close()

    def handle_up(self):
        """
        Read the content of the request, and inject it in ssh socket
        """
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        outgoing_content.put(body)
        self.send_response(201)
        self.send_header("Content-type", "raw")
        self.end_headers()
        # This needs to be done after sending the headers


class SSHRequestThread(Thread):

    def __init__(self, socket, *args, **kwargs):
        self.socket = socket
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        while True:
            rawdata = self.socket.recv(1024)
            incoming_content.put(rawdata)
            #if not outgoing_content.empty():

            rawdata = outgoing_content.get()
            print(rawdata)
            len = self.socket.send(rawdata)
            print("{} bytes sent".format(len))


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
            client_thread = SSHRequestThread(incomming)
            client_thread.start()
            client_thread.run()


class HTTPThread(Thread):
    def __init__(self, bind, port, *args, **kwargs):
        self.bind = bind
        self.port = port
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        self.server = HTTPServer((self.bind, self.port), SSHTunnelHTTPRequestHandler)
        ssh_server_info = self.server.socket.getsockname()
        print("HTTP Socket listening on", ssh_server_info[0], "port", ssh_server_info[1], "...")
        print("Now serving http")
        self.server.serve_forever()


def run(protocol="HTTP/1.0", http_port=8000, ssh_port=2222, bind=""):
    """
    This run a listening ssh thread, and a listening http thread.
    """
    # Instanciate the needed threads
    ssh_thread = SSHThread(bind, ssh_port, ssh_socket)
    http_thread = HTTPThread(bind, http_port)

    try:
        ssh_thread.start()
        http_thread.start()

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
    args = parser.parse_args()
    run(ssh_port=args.ssh_port, http_port=args.http_port, bind=args.bind)
