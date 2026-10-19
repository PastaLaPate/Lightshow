import traceback

from lightshow.core.logger import Logger

logger = Logger("DEBUGGER")


def who_called_me():
    """Call to see who called the function, useful in uis where you dont know why something was called"""
    for line in traceback.format_stack():
        logger.debug(line.strip())
