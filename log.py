import logging
from prompt_toolkit import print_formatted_text, ANSI

logger = None

class PrintHandler(logging.Handler):
    def emit(self, record):
        print_formatted_text(ANSI(self.format(record)))

def setup(name: str, debug: bool = False):
    """
    Setup a logger with the given name.
    """
    global logger
    wzlogger = logging.getLogger('werkzeug')
    logger = logging.getLogger(name)
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)