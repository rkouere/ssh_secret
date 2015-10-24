from ssh_tunnel.proxy.filters import Filter, blacklisted_uris


class BlacklistFilter(Filter):
    """Drops a request if the uri is in a global blacklist"""
    def drop(self, path, headers, body):
        return path in blacklisted_uris
