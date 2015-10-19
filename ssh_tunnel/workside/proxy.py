import requests
import argparse
import shutil
import io
import binascii
from http.server import HTTPServer, BaseHTTPRequestHandler

blacklisted = set()


class BlacklistedException(Exception):
    pass


class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            request = requests.get(self.path)
        except ConnectionRefusedError:
            self.log_message("{} not reachable".format(self.path))
        f = io.BytesIO()
        f.write(request.content)
        f.seek(0)
        self.send_response(request.status_code)
        self.end_headers()
        shutil.copyfileobj(f, self.wfile)

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        try:
            self.filter_request(body)
        except BlacklistedException:
            self.send_response(400)
            self.end_headers()
            self.log_message("Suspicious behaviour detected at {}".format(self.path))
        try:
            request = requests.post(self.path, data=body)
            self.filter_request(request.content)
            f = io.BytesIO()
            f.write(request.content)
            f.seek(0)
            self.send_response(request.status_code)
            self.end_headers()
            shutil.copyfileobj(f, self.wfile)
        except (ConnectionRefusedError, requests.exceptions.ConnectTimeout):
            self.log_message("{} not reachable".format(self.path))
        except BlacklistedException:
            self.send_response(400)
            self.end_headers()
            self.log_message("Suspicious behaviour detected at {}".format(self.path))

    def filter_request(self, body):
        """
        Return True if the request should be filtered
        """
        bodies = []
        if self.path in blacklisted:
            self.log_message("{} is blacklisted".format(self.path))
            raise BlacklistedException()
        # Construct a list of decoded bodies
        bodies.append(body)
        try:
            bodies.append(binascii.a2b_base64(body))
        except binascii.Error:
            self.log_message("Not a base64")

        for target in bodies:
            if len(target) < 32 and b"OpenSSH" in target:
                self.log_message("Openssh detected")
                self.blacklist(self.path)
                raise BlacklistedException()

    def blacklist(self, host):
        blacklisted.add(host)
        self.log_message("Added {} to the blacklist".format(self.path))
        self.log_message("Blacklist : {}".format(blacklisted))


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
