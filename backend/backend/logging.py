# Standard Library
import logging

logging.basicConfig()
logging.root.setLevel(logging.DEBUG)
global_logger = logging.getLogger("root")
global_logger.setLevel(logging.DEBUG)


def getLogger(name):
    child = global_logger.getChild(name)
    child.setLevel(logging.DEBUG)
    return child
