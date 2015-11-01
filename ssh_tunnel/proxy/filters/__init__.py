import logging
import importlib
import time

blacklisted_uris = set()

class Filter():
    """Abstract class which defines a Filter plugin. It must implement the ``drop`` method"""
    def drop(self, path, headers, body):
        """Returns True if the request is suspitious and should be filtered"""
        raise Exception("Should be implemented")

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__str__()


def blacklist(path):
    blacklisted_uris.add(path)
    logging.info("Added {} to the blacklist".format(path))
    logging.info("Blacklist : {}".format(blacklisted_uris))


def load_filters_from_string(string):
    if string == "none":
        return []
    if string == "all":
        string = " ".join(list_filters())
    return [getattr(importlib.import_module(__name__+"."+classname), classname) for classname in string.split(' ')]


def list_filters():
    return [f.__name__ for f in Filter.__subclasses__()]

access_log = {}
def addToLog(path):
    if path in access_log:
        access_log[path].append(time.time())
    else:
        access_log[path] = [time.time()]

