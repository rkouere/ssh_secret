from urllib.parse import urlparse
import logging
from ssh_tunnel.proxy.filters import Filter

RANDOM_THRESHOLD = 0.87
rate_by_host = {}


def random_for_host(host):
    return (rate_by_host[host]['rate'] / rate_by_host[host]['total'])


def random_factor(body):
    count = 0
    for b in bytearray(body):
        if 0x20 <= b <= 0xfe:
            count += 1
    return count


class RandomDetectorFilter(Filter):
    """Drop requests if they contain too much random data"""
    def drop(self, path, headers, body):
        if len(body):
            rate = random_factor(body)
            host = urlparse(path).netloc
            if host not in rate_by_host:
                rate_by_host[host] = {'rate': 0, 'total': 0, 'count': 0}
            rate_by_host[host]['rate'] += rate
            rate_by_host[host]['total'] += len(body)
            rate_by_host[host]['count'] += 1
            logging.info("Random rate : {} (host {})".format(random_for_host(host), host))
            return rate_by_host[host]['count'] > 2 and random_for_host(host) < RANDOM_THRESHOLD
