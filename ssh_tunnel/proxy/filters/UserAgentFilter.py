from ssh_tunnel.proxy.filters import Filter


class UserAgentFilter(Filter):
    """Filter illegitimate User Agent"""
    def drop(self, path, headers, body):
        return "mozilla" not in headers.get('User-Agent', '').lower()
