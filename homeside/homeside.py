#!/usr/bin/env python3
import argparse
import io
import shutil
from threading import Thread
from socketserver import StreamRequestHandler, TCPServer
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

_ssh_server = None
_queued_content = None


class SSHTunnelHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = _queued_content

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


class SSHSocketRequestHandler(StreamRequestHandler):
        def handle(self):
            print("got request : {}".format(self.request))
            global _queued_content
            _queued_content = self.request.recv(1024)


class SSHThread(Thread):
    def __init__(self, bind, port, *args, **kwargs):
        self.bind = bind
        self.port = port
        super(*args, **kwargs)
        Thread.__init__(self)

    def start(self):
        self.server = TCPServer((self.bind, self.port), SSHSocketRequestHandler)
        ssh_server_info = self.server.socket.getsockname()
        print("Socket listening on", ssh_server_info[0], "port", ssh_server_info[1], "...")

    def run(self):
        self.server.serve_forever()


class HTTPThread(Thread):
    def __init__(self, bind, port, *args, **kwargs):
        self.bind = bind
        self.port = port
        super(*args, **kwargs)
        Thread.__init__(self)

    def start(self):
        self.server = HTTPServer((self.bind, self.port), SSHTunnelHTTPRequestHandler)
        ssh_server_info = self.server.socket.getsockname()
        print("Socket listening on", ssh_server_info[0], "port", ssh_server_info[1], "...")

    def run(self):
        self.server.serve_forever()


def run(protocol="HTTP/1.0", port=8000, ssh_port=2222, bind=""):
    """Test the HTTP request handler class.

    This runs an HTTP server on port 8000 (or the first command line
    argument).

    """
    global _ssh_server

    # Instanciate ssh thread
    ssh_thread = SSHThread(bind, ssh_port)
    ssh_thread.start()

    # Instanciate http thread
    http_thread = HTTPThread(bind, port)
    http_thread.start()

    while True:
        try:
            ssh_thread.run()
            http_thread.run()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            ssh_thread.server.server_close()
            http_thread.server_close()
            sys.exit(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', '-b', default='', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
    parser.add_argument('port', action='store',
                        default=8000, type=int,
                        nargs='?',
                        help='Specify alternate port [default: 8000]')
    args = parser.parse_args()
    run(port=args.port, bind=args.bind)
