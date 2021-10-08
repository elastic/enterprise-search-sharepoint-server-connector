from tika import parser

def print_and_log(logger, level, message):
    print(message)
    getattr(logger, level.lower())(message)

def extract(content):
    
    parsed = parser.from_buffer(content)
    parsed_text = parsed['content']
    if parsed_text:
        return parsed_text
    else:
        return {}