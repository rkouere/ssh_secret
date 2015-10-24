import requests
import argparse
import shutil
import io
import logging
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from ssh_tunnel.proxy.filters import list_filters, load_filters_from_string
from ssh_tunnel.proxy.filters.ReplayerFilter import ReplayerFilter
from ssh_tunnel.proxy.filters.OpenSSHStringFilter import OpenSSHStringFilter  # nopep8
from ssh_tunnel.proxy.filters.BlacklistFilter import BlacklistFilter  # nopep8
from ssh_tunnel.proxy.filters.RandomDetectorFilter import RandomDetectorFilter  # nopep8
from ssh_tunnel.proxy.filters.UserAgentFilter import UserAgentFilter  # nopep8


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
                self.send_error(414)
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
                    405,
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
        if self.filter_request(body, excludes=[ReplayerFilter]):
            # Do not use the ReplayerFilter on this round as it mess too much
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

    def filter_request(self, body, path=None, headers=None, excludes=[]):
        """
        Respond with 400 if a request is suspicious
        """
        if not headers:
            headers = self.headers
        if not path:
            path = self.path
        for f in self.filters:
            if f.__class__ not in excludes and f.drop(self.path, self.headers, body):
                self.err400()
                self.log_message("Suspicious behaviour detected at {} by filter {}".format(self.path, f))

    def err400(self):
        """Ends the current request with a 400 error code"""
        f = io.BytesIO()
        f.write(b"")
        f.seek(0)
        self.send_response(418)
        self.end_headers()


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
        logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.DEBUG)
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
