import requests
import argparse
import shutil
import io
import logging
import socket
from time import clock

from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from ssh_tunnel.proxy.filters import list_filters, load_filters_from_string
from ssh_tunnel.proxy.filters.ReplayerFilter import ReplayerFilter
from ssh_tunnel.proxy.filters.OpenSSHStringFilter import OpenSSHStringFilter  # nopep8
from ssh_tunnel.proxy.filters.BlacklistFilter import BlacklistFilter  # nopep8
from ssh_tunnel.proxy.filters.RandomDetectorFilter import RandomDetectorFilter  # nopep8
from ssh_tunnel.proxy.filters.UserAgentFilter import UserAgentFilter  # nopep8
from ssh_tunnel.proxy.ssl_thread import SSLThread


class ProxyHandler(BaseHTTPRequestHandler):

    filters = []

    def __init__(self, *args, **kwargs):
        self.start = clock()
        BaseHTTPRequestHandler.__init__(self, *args, *kwargs)

    @property
    def https(self):
        return self.path.endswith(":443")

    @property
    def url(self):
        return self.path

    def handle_one_request(self):
        """Handle a single HTTP request.
        Override the standard request handler to print debug if needed
        """
        try:
            try:
                self.raw_requestline = self.rfile.readline(65537)
            except ConnectionError:
                logging.error("Failed to read request line : {}".format(self.request))
                self.close_connection = True
                return
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
        except ConnectionError:
            logging.error("Connection reset by peer : {}".format(self))

    def do_CONNECT(self):
        # Client ask for an end-to-end tcp connection. Handle it in a new thread
        host, port = self.path[:self.path.find(":")], self.path[self.path.find(":")+1:]
        ssl_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_socket.connect((host, int(port)))
        ssl_in_thread = SSLThread(ssl_socket, self.request)
        ssl_out_thread = SSLThread(self.request, ssl_socket)
        ssl_in_thread.start()
        ssl_out_thread.start()

        self.send_response(200)
        self.end_headers()

        ssl_in_thread.run()
        ssl_out_thread.run()
        return

    def do_GET(self):
        try:
            request = requests.get(self.url, headers=self.headers, allow_redirects=False)
            logging.debug("< {}".format(request.headers))
            logging.debug("< {}".format(request.content))
            if self.filter_request(request.content):
                return
            self.proxy_request(request)
        except (ConnectionRefusedError, requests.exceptions.ConnectionError, requests.exceptions.Timeout):
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
            request = requests.post(self.url, data=body, headers=self.headers, allow_redirects=False)
            logging.debug("< {}".format(request.headers))
            logging.debug("< {}".format(request.content))
            if self.filter_request(request.content, path=self.url, headers=request.headers):
                return
            self.proxy_request(request)
        except (ConnectionRefusedError, requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            self.log_message("{} not reachable".format(self.url))
            self.err400()

    def filter_request(self, body, path=None, headers=None, excludes=[]):
        """
        Respond with 400 if a request is suspicious
        """
        if not headers:
            headers = self.headers
        if not path:
            path = self.url
        for f in self.filters:
            if f.__class__ not in excludes and f.drop(self.url, self.headers, body):
                self.err400()
                logging.info("\033[1;31mSuspicious behaviour detected at {} by filter {}\033[1;0m".format(self.url, f))

    def err400(self):
        """Ends the current request with a 400 error code"""
        f = io.BytesIO()
        f.write(b"")
        f.seek(0)
        self.send_response(418)
        self.end_headers()

    def proxy_request(self, request):
        """
        Actually send the asked request to the client
        """
        if request.content:
            f = io.BytesIO()
            f.write(request.content)
            f.seek(0)
        self.send_response(request.status_code)
        for h in request.headers:
            if h == "Content-Length":
                # Rewrite Content-Length header in case requests alreay unzipped the body
                self.send_header(h, len(request.content))
            elif h in ["Content-Encoding", "Server", "Date"]:
                # Override Content-Encoding if gzipped
                # Others because the proxy set it's own instead
                pass
            else:
                self.send_header(h, request.headers[h])
        self.end_headers()
        if request.content:
            shutil.copyfileobj(f, self.wfile)

    def log_request(self, code='-', size='-'):
        """Log an accepted request.

        This is called by send_response().

        """

        self.log_message('"%s" %s %s %s',
                         self.requestline, str(code), str(size), str(clock()-self.start))


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
    parser.add_argument('filters', nargs="?", default="all", type=str,
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
    for _filter in filters:
        f = _filter()
        logging.info("Installing filter {}".format(str(f)))
        ProxyHandler.filters.append(f)
    ProxyHandler.verbose = args.verbose
    proxy = ThreadedProxyServer(("", args.port), ProxyHandler)
    logging.info("Proxy listening on port {}".format(args.port))
    proxy.serve_forever()
