from tika import parser


def print_and_log(logger, level, message):
    """ Prints the log messages
        :param logger: logger name
        :param level: log level
        :param message: log message
    """
    print(message)
    getattr(logger, level.lower())(message)


def extract(content):
    """ Extracts the contents
        :param content: content to be extracted
        Returns:
            parsed_test: parsed text
    """
    parsed = parser.from_buffer(content)
    parsed_text = parsed['content']
    return parsed_text
