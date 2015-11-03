from ssh_tunnel.proxy.filters import Filter


class UserAgentFilter(Filter):
    """Filter illegitimate User Agent"""
    def drop(self, path, headers, body):
        agent = headers.get('User-Agent', '').lower()
        return ("mozilla" not in agent, "User-Agent was {}".format(agent))
