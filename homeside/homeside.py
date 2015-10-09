#!/usr/bin/env python3
import argparse
import io
import shutil
import socket
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

_ssh_socket = None


class SSHTunnelHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global _ssh_socket
        _ssh_socket.listen(0)
        body = _ssh_socket.recv(1024)
        f = io.BytesIO()
        f.write(body)
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "raw")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        # This should be done after sending the headers
        shutil.copyfileobj(f, self.wfile)
        f.close()


def run(protocol="HTTP/1.0", port=8000, ssh_port=2222, bind=""):
    """Test the HTTP request handler class.

    This runs an HTTP server on port 8000 (or the first command line
    argument).

    """
    global _ssh_socket
    server_address = (bind, port)
    httpd = HTTPServer(server_address, SSHTunnelHTTPRequestHandler)

    # Instanciate ssh socket
    _ssh_socket = socket.socket()
    _ssh_socket.bind((bind, ssh_port))

    sa = httpd.socket.getsockname()
    print("Serving HTTP on", sa[0], "port", sa[1], "...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        httpd.server_close()
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
