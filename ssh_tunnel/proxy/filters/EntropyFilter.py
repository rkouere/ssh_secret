import math
import logging
from collections import Counter
from urllib.parse import urlparse
from ssh_tunnel.proxy.filters import Filter

entropy_by_host = {}
ENTROPY_THRESHOLD = 200


def entropy_of_string(s):
    p, lns = Counter(s), float(len(s))
    return -sum(count/lns * math.log(count/lns, 2) for count in p.values())


class EntropyFilter(Filter):
    """Drop requests if their entropy average is too high"""
    def drop(self, path, headers, body):
        if len(body):
            entropy = entropy_of_string(body)
            host = urlparse(path).netloc
            if host not in entropy_by_host:
                entropy_by_host[host] = {'entropy': 0.0, 'total': 0, 'count': 0, 'ratio': 0}
            entropy_by_host[host]['entropy'] += entropy
            entropy_by_host[host]['total'] += len(body)
            entropy_by_host[host]['count'] += 1
            entropy_by_host[host]['ratio'] += entropy_by_host[host]['entropy'] / entropy_by_host[host]['total']
            logging.info("Entropy : {} -- {} (host {})".format(entropy, entropy_by_host[host], host))
            dropped = entropy_by_host[host]['count'] > 2 and entropy > ENTROPY_THRESHOLD
            return (dropped, "Entropy is {} > {}".format(entropy, ENTROPY_THRESHOLD))
        return (False, None)
