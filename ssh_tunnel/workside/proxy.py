import requests
import argparse
import shutil
import io
import binascii
import logging
import random
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn


blacklisted_uris = set()


def blacklist(path):
    blacklisted_uris.add(path)
    logging.info("Added {} to the blacklist".format(path))
    logging.info("Blacklist : {}".format(blacklisted_uris))


def load_filters_from_string(string):
    if string == "none":
        return []
    if string == "all":
        string = " ".join(list_filters())
    thismodule = sys.modules[__name__]
    return [getattr(thismodule, classname) for classname in string.split(' ')]


def list_filters():
    return [f.__name__ for f in Filter.__subclasses__()]


class Filter():
    """Abstract class which defines a Filter plugin. It must implement the ``drop`` method"""
    def drop(self, path, headers, body):
        """Returns True if the request is suspitious and should be filtered"""
        raise Exception("Should be implemented")

    def __str__(self):
        return "Filter"


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

    def __str__(self):
        return "OpenSSHString"


class BlacklistFilter(Filter):
    """Drops a request if the uri is in a global blacklist"""
    def drop(self, path, headers, body):
        return path in blacklisted_uris

    def __str__(self):
        return "Blacklist"


class UserAgentFilter(Filter):
    """Filter illegitimate User Agent"""
    def drop(self, path, headers, body):
        return "mozilla" not in headers.get('User-Agent', '').lower()

    def __str__(self):
        return "Useragent"


class ReplayerFilter(Filter):
    """Technically not a filter ; randomly replay requests to mess with the servers"""
    def drop(self, path, headers, body):
        if random.getrandbits(1) > 0:
            print("replaying request for the lulz")
            try:
                requests.post(path)
            except requests.exceptions.ConnectionError:
                pass
        # Always return False as the request should not been dropped
        return False

    def __str__(self):
        return "Replayer"


class ProxyHandler(BaseHTTPRequestHandler):

    filters = []
    verbose = False

    @property
    def https(self):
        return self.path.endswith(":443")

    @property
    def url(self):
        if self.https:
            return "https://"+self.path
        else:
            return self.path

    def do_CONNECT(self):
        try:
            request = requests.request("connect", self.url)
        except ConnectionRefusedError:
            logging.info("{} not reachable".format(self.url))
            self.err400()
        f = io.BytesIO()
        f.write(request.content)
        f.seek(0)
        self.send_response(request.status_code)
        self.end_headers()
        shutil.copyfileobj(f, self.wfile)

    def do_GET(self):
        if self.verbose:
            print(self.headers)
        try:
            request = requests.get(self.url)
            f = io.BytesIO()
            f.write(request.content)
            f.seek(0)
            self.send_response(request.status_code)
            self.end_headers()
            shutil.copyfileobj(f, self.wfile)
        except (ConnectionRefusedError, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            logging.info("{} not reachable".format(self.url))
            self.err400()

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        if self.verbose:
            print(self.headers)
            print(body)
        if self.filter_request(body):
            return
        try:
            request = requests.post(self.url, data=body)
            if self.filter_request(request.content, path=self.url, headers=request.headers):
                return
            f = io.BytesIO()
            f.write(request.content)
            f.seek(0)
            self.send_response(request.status_code)
            self.end_headers()
            shutil.copyfileobj(f, self.wfile)
        except (ConnectionRefusedError, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            self.log_message("{} not reachable".format(self.url))
            self.err400()

    def filter_request(self, body, path=None, headers=None):
        """
        Respond with 400 if a request is suspicious
        """
        if not headers:
            headers = self.headers
        if not path:
            path = self.path
        for f in self.filters:
            if f.drop(self.path, self.headers, body):
                self.err400()
                self.log_message("Suspicious behaviour detected at {} by filter {}".format(self.path, f))

    def err400(self):
        """Ends the current request with a 400 error code"""
        f = io.BytesIO()
        f.write(b"You wrong I'm a teapot LOL1")
        f.seek(0)
        self.send_response(418)
        self.end_headers()
        shutil.copyfileobj(f, self.wfile)


class ThreadedProxyServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', '-b', default='', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
    parser.add_argument('--port', '-p', default=8008, type=int,
                        help='Specify alternate port [default: 8008]')
    parser.add_argument('--verbose', '-v', action="store_true",
                        help='Toogle verbose mode')
    parser.add_argument('filters', default="all", type=str,
                        help='A list of filters. Available are {}. [default: all]'.format(list_filters() + ['all', 'none']))
    args = parser.parse_args()
    print("Server starting")
    if args.verbose:
        print("Verbose on")
    filters = load_filters_from_string(args.filters)
    for f in filters:
        print("Installing filter {}".format(f.__name__))
        ProxyHandler.filters.append(f())
    ProxyHandler.verbose = args.verbose
    proxy = ThreadedProxyServer(("", args.port), ProxyHandler)
    print("Proxy listening on port {}".format(args.port))
    proxy.serve_forever()
