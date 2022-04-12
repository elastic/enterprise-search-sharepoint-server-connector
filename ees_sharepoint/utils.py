#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module contains uncategorized utility methods."""

import urllib.parse
from datetime import datetime

from tika import parser

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def extract(content):
    """Extracts the contents
    :param content: content to be extracted
    Returns:
        parsed_test: parsed text"""
    parsed = parser.from_buffer(content)
    parsed_text = parsed["content"]
    return parsed_text


def encode(object_name):
    """Performs encoding on the name of objects
    containing special characters in their url, and
    replaces single quote with two single quote since quote
    is treated as an escape character in odata
    :param object_name: name that contains special characters"""
    name = urllib.parse.quote(object_name, safe="'")
    return name.replace("'", "''")


def split_list_into_buckets(documents, total_buckets):
    """Divide large number of documents amongst the total buckets
    :param documents: list to be partitioned
    :param total_buckets: number of groups to be formed
    """
    if documents:
        groups = min(total_buckets, len(documents))
        group_list = []
        for i in range(groups):
            group_list.append(documents[i::groups])
        return group_list
    else:
        return []


def split_documents_into_equal_chunks(documents, chunk_size):
    """This method splits a list or dictionary into equal chunks size
    :param documents: List or Dictionary to be partitioned into chunks
    :param chunk_size: Maximum size of a chunk
    Returns:
        list_of_chunks: List containing the chunks
    """
    list_of_chunks = []
    for i in range(0, len(documents), chunk_size):
        if type(documents) is dict:
            partitioned_chunk = list(documents.items())[i: i + chunk_size]
            list_of_chunks.append(dict(partitioned_chunk))
        else:
            list_of_chunks.append(documents[i: i + chunk_size])
    return list_of_chunks


def split_date_range_into_chunks(start_time, end_time, number_of_threads):
    """Divides the timerange in equal partitions by number of threads
    :param start_time: start time of the interval
    :param end_time: end time of the interval
    :param number_of_threads: number of threads defined by user in config file
    """
    start_time = datetime.strptime(start_time, DATETIME_FORMAT)
    end_time = datetime.strptime(end_time, DATETIME_FORMAT)

    diff = (end_time - start_time) / number_of_threads
    datelist = []
    for idx in range(number_of_threads):
        date_time = start_time + diff * idx
        datelist.append(date_time.strftime(DATETIME_FORMAT))
    formatted_end_time = end_time.strftime(DATETIME_FORMAT)
    datelist.append(formatted_end_time)
    return datelist
