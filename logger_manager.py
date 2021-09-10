# Standard library imports
import logging
import logging.handlers
import os


def setup_logging(log_name, log_level=logging.INFO):
    """ Setup logger.

    :param log_name: name for logger
    :param log_level: log level, a string
    :return: a logger object
    """

    # Make path till log file
    log_name += ".log"
    log_file = os.path.join(os.getcwd(), log_name)
    # Get directory in which log file is present
    log_dir = os.path.dirname(log_file)
    # Create directory at the required path to store log file, if not found
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(log_name)
    logger.propagate = False

    # Set log level
    logger.setLevel(log_level)

    handler_exists = any(
        [True for h in logger.handlers if h.baseFilename == log_file])

    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, mode="a", maxBytes=10485760, backupCount=10)
        # Format logs
        fmt_str = "%(asctime)s %(levelname)s p%(process)s %(thread)d [%(filename)s] [%(funcName)s] - %(message)s"
        formatter = logging.Formatter(fmt_str)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        if log_level is not None:
            file_handler.setLevel(log_level)

    return logger
