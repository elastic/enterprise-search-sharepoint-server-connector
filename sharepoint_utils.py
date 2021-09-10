from tika import parser


def print_and_log(logger, level, message):
    print(message)

    if level.lower() == 'debug':
        log_debug(logger, message)
    elif level.lower() == 'info':
        log_info(logger, message)
    elif level.lower() == 'warn':
        log_warn(logger, message)
    elif level.lower() == 'error':
        log_error(logger, message)


def log_debug(logger, message):
    logger.debug(message)


def log_info(logger, message):
    logger.info(message)


def log_warn(logger, message):
    logger.warn(message)


def log_error(logger, message):
    logger.error(message)


def extract(file):
    try:
        parsed = parser.from_file(file)
        parsed_text = parsed['content']
        parsed_text = parsed_text.lower()
        return parsed_text
    except Exception:
        raise Exception
