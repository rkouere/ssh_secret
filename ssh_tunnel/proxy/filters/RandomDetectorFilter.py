from urllib.parse import urlparse
import logging
from ssh_tunnel.proxy.filters import Filter


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
