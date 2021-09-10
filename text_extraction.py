import io
import os
from tika import parser

class text_fetch(file):

    def extract(self, file):
        parsed = parser.from_file(file)
        parsed_text = parsed['content']
        parsed_text = parsed_text.lower()
        
        return parsed_text
    