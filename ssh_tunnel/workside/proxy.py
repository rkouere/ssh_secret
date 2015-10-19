import requests
import argparse
import shutil
import io
import binascii
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler


blacklisted_uris = set()


def blacklist(path):
    blacklisted_uris.add(path)
    logging.info("Added {} to the blacklist".format(path))
    logging.info("Blacklist : {}".format(blacklisted_uris))


class Filter():
    """Abstract class which defines a Filter plugin. It must implement the ``drop`` method"""
    def drop(self, path, headers, body):
        """Returns True if the request is suspitious and should be filtered"""
        raise Exception("Should be implemented")


class OpenSSHStringFilter(Filter):
    """Finds the OpenSSH version exchange at the beginnig of the protocol"""
    def drop(self, path, headers, body):
        bodies = []
        # Construct a list of decoded bodies
        bodies.append(body)
        try:
            bodies.append(binascii.a2b_base64(body))
        except binascii.Error:
            print("not a base64")

        for target in bodies:
            if len(target) < 32 and b"OpenSSH" in target:
                print("Openssh detected")
                blacklist(path)
                return True
        return False


class BlacklistFilter(Filter):
    def drop(self, path, headers, body):
        """Drops a request if the uri is in a global blacklist"""
        return path in blacklisted_uris


class UserAgentFilter(Filter):
    """Filter illegitimate User Agent"""
    def drop(self, path, headers, body):
        return "mozilla" not in headers.get('User-Agent', '').lower()


class ProxyHandler(BaseHTTPRequestHandler):

    filters = [
        BlacklistFilter(),
        OpenSSHStringFilter(),
#        UserAgentFilter()
    ]

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
        if self.filter_request(body):
            return
        try:
            request = requests.post(self.path, data=body)
            if self.filter_request(request.content, path=self.path, headers=request.headers):
                return
            f = io.BytesIO()
            f.write(request.content)
            f.seek(0)
            self.send_response(request.status_code)
            self.end_headers()
            shutil.copyfileobj(f, self.wfile)
        except (ConnectionRefusedError, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            self.log_message("{} not reachable".format(self.path))

    def filter_request(self, body, path=None, headers=None):
        """
        Respond with 400 if a request is suspicious
        """
        if not headers:
            headers = self.headers
        if not path:
            path = self.path
        for f in self.filters:
            if f.drop(self.path, self.headers, body):
                self.send_response(400)
                self.end_headers()
                self.log_message("Suspicious behaviour detected at {} by {}".format(self.path, f))


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
