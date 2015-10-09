#!/usr/bin/env python3
import argparse
import sys
import io
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler


class SSHTunnelHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = "you are at {}".format(self.path).encode()
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


def run(protocol="HTTP/1.0", port=8000, bind=""):
    """Test the HTTP request handler class.

    This runs an HTTP server on port 8000 (or the first command line
    argument).

    """
    server_address = (bind, port)
    httpd = HTTPServer(server_address, SSHTunnelHTTPRequestHandler)

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
                        default=2222, type=int,
                        nargs='?',
                        help='Specify alternate port [default: 2222]')
    args = parser.parse_args()
    run(port=args.port, bind=args.bind)
