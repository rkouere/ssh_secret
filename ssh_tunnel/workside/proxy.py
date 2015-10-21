import requests
import argparse
import shutil
import io
import binascii
import logging
import random
import sys
import socket
from urllib.parse import urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from http import HTTPStatus
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
        return self.__name__


class OpenSSHStringFilter(Filter):
    """Finds the OpenSSH version exchange at the beginnig of the protocol"""
    def drop(self, path, headers, body):
        bodies = []
        # Construct a list of decoded bodies
        bodies.append(body)
        try:
            bodies.append(binascii.a2b_base64(body))
        except binascii.Error:
            logging.debug("not a base64")

        for target in bodies:
            if len(target) < 32 and b"OpenSSH" in target:
                logging.info("Openssh detected")
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
            logging.info("replaying request for the lulz")
            try:
                requests.post(path)
            except requests.exceptions.ConnectionError:
                pass
        # Always return False as the request should not been dropped
        return False

    def __str__(self):
        return "Replayer"


class RandomDetectorFilter(Filter):
    """Drop requests if they contain too much random data"""
    total_random = 0
    total_body = 0
    rate_by_host = {}
    RANDOM_THRESHOLD = 0.80
    # Install a custom error handler for decode()

    def random_factor(self, body):
        count = 0
        for b in bytearray(body):
            if 0x20 <= b <= 0xfe:
                count += 1
        return count

    def random_for_host(self, host):
        return (self.rate_by_host[host]['rate'] / self.rate_by_host[host]['total'])

    def drop(self, path, headers, body):
        if len(body):
            rate = self.random_factor(body)
            host = urlparse(path).netloc
            if host not in self.rate_by_host:
                self.rate_by_host[host] = {'rate': 0, 'total': 0, 'count': 0}
            self.rate_by_host[host]['rate'] += rate
            self.rate_by_host[host]['total'] += len(body)
            self.rate_by_host[host]['count'] += 1
            logging.info("Random rate : {} (at {})".format(self.random_for_host(host), path))
            return self.rate_by_host[host]['count'] > 2 and self.random_for_host(host) < self.RANDOM_THRESHOLD

    def __str__(self):
        return "RandomDetector"


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
        elif self.path.startswith("http://"):
            return self.path
        else:
            return "http://"+self.path

    def handle_one_request(self):
        """Handle a single HTTP request.
        Override the standard request handler to print debug if needed
        """
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(HTTPStatus.REQUEST_URI_TOO_LONG)
                return
            if not self.raw_requestline:
                self.close_connection = True
                return
            if not self.parse_request():
                # An error code has been sent, just exit
                return
            mname = 'do_' + self.command
            if not hasattr(self, mname):
                self.send_error(
                    HTTPStatus.NOT_IMPLEMENTED,
                    "Unsupported method (%r)" % self.command)
                return
            method = getattr(self, mname)
            logging.debug("> {} (from {})".format(self.requestline, self.address_string()))
            for h in self.headers:
                logging.debug("> {}: {}".format(h, self.headers[h]))
            method()
            self.wfile.flush()  # actually send the response if not already done.
        except socket.timeout as e:
            # a read or a write timed out.  Discard this connection
            self.log_error("Request timed out: %r", e)
            self.close_connection = True
            return

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
        try:
            request = requests.get(self.url)
            logging.debug("< {}".format(request.headers))
            logging.debug("< {}".format(request.content))
            if self.filter_request(request.content):
                return
            f = io.BytesIO()
            f.write(request.content)
            f.seek(0)
            self.send_response(request.status_code)
            for h in request.headers:
                self.send_header(h, request.headers[h])
            self.end_headers()
            shutil.copyfileobj(f, self.wfile)
        except (ConnectionRefusedError, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            logging.info("{} not reachable".format(self.url))
            self.err400()

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        logging.debug(">")
        logging.debug("> {}".format(body))
        if self.filter_request(body):
            return
        try:
            request = requests.post(self.url, data=body)
            logging.debug("< {}".format(request.headers))
            logging.debug("< {}".format(request.content))
            if self.filter_request(request.content, path=self.url, headers=request.headers):
                return
            f = io.BytesIO()
            f.write(request.content)
            f.seek(0)
            self.send_response(request.status_code)
            for h in request.headers:
                self.send_header(h, request.headers[h])
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
        f.write(b"")
        f.seek(0)
        self.send_response(418)
        self.end_headers()
#        shutil.copyfileobj(f, self.wfile)


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
                        help='A list of filters. Available are {}. [default: all]'.format(list_filters() +
                                                                                          ['all',
                                                                                           'none']))
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)
    logging.info("Server starting")
    logging.debug("Verbose on")
    filters = load_filters_from_string(args.filters)
    for f in filters:
        logging.info("Installing filter {}".format(f.__name__))
        ProxyHandler.filters.append(f())
    ProxyHandler.verbose = args.verbose
    proxy = ThreadedProxyServer(("", args.port), ProxyHandler)
    logging.info("Proxy listening on port {}".format(args.port))
    proxy.serve_forever()
