import requests
import urllib
import argparse
import logging
import shutil
import io
from http.server import HTTPServer, BaseHTTPRequestHandler


class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(self)
        request = requests.get(self.path)
        f = io.BytesIO()
        f.write(request.content)
        f.seek(0)
        self.send_response(request.status_code)
        self.end_headers()
        shutil.copyfileobj(f, self.wfile)

    def do_POST(self):
        print(self)
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        print("Read body of size {}".format(len(body)))
        request = requests.post(self.path, data=body)
        f = io.BytesIO()
        f.write(request.content)
        f.seek(0)
        self.send_response(request.status_code)
        self.end_headers()
        shutil.copyfileobj(f, self.wfile)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', '-b', default='', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
    parser.add_argument('--port', '-p', default=8008, type=int,
                        help='Specify alternate port [default: 8008]')
    args = parser.parse_args()
    print("Server starting")
    proxy = HTTPServer(("", args.port), ProxyHandler)
    print("Proxy listening on port {}".format(args.port))
    proxy.serve_forever()
