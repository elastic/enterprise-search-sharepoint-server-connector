#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module contains uncategorisied utility methods."""

import urllib.parse

from tika import parser


def extract(content):
    """ Extracts the contents
        :param content: content to be extracted
        Returns:
            parsed_test: parsed text"""
    parsed = parser.from_buffer(content)
    parsed_text = parsed['content']
    return parsed_text


def encode(object_name):
    """Performs encoding on the name of objects
        containing special characters in their url, and
        replaces single quote with two single quote since quote
        is treated as an escape character in odata
        :param object_name: name that contains special characters"""
    name = urllib.parse.quote(object_name, safe="'")
    return name.replace("'", "''")


def split_in_chunks(input_list, chunk_size):
    """This method splits a list into separate chunks with maximum size
        as chunk_size
        :param input_list: list to be partitioned into chunks
        :param chunk_size: maximum size of a chunk
        Returns:
            :list_of_chunks: list containing the chunks
    """
    list_of_chunks = []
    for i in range(0, len(input_list), chunk_size):
        list_of_chunks.append(input_list[i:i + chunk_size])
    return list_of_chunks
