from tika import parser

def print_and_log(logger, level, message):
    print(message)
    getattr(logger, level.lower())(message)
