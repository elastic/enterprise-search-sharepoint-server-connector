#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""This module contains uncategorized utility methods."""

import urllib.parse

from tika import parser
from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


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


def partition_equal_share(object_list, total_groups):
    """ Divides the list in groups of approximately equal sizes
        :param object_list: list to be partitioned
        :param total_groups: number of groups to be formed
    """
    if object_list:
        groups = min(total_groups, len(object_list))
        group_list = []
        for i in range(groups):
            group_list.append(object_list[i::groups])
        return group_list
    else:
        return []


def split_list_in_chunks(input_list, chunk_size):
    """ This method splits a list into separate chunks with maximum size
        as chunk_size
        :param input_list: List to be partitioned into chunks
        :param chunk_size: Maximum size of a chunk
        Returns:
            list_of_chunks: List containing the chunks
    """
    list_of_chunks = []
    for i in range(0, len(input_list), chunk_size):
        list_of_chunks.append(input_list[i:i + chunk_size])
    return list_of_chunks


def split_dict_in_chunks(input_dict, chunk_size):
    """ This method splits a dictionary into separate chunks with maximum size
        as chunk_size
        :param input_dict: Dictionary to be partitioned into chunks
        :param chunk_size: Maximum size of a chunk
        Returns:
            list_of_chunks: List containing the chunks
    """
    list_of_chunks = []
    for i in range(0, len(input_dict), chunk_size):
        partitioned_chunk = list(input_dict.items())[i:i + chunk_size]
        list_of_chunks.append(dict(partitioned_chunk))
    return list_of_chunks


def datetime_partitioning(start_time, end_time, processes):
    """ Divides the timerange in equal partitions by number of processors
        :param start_time: start time of the interval
        :param end_time: end time of the interval
        :param processes: number of processors the device have
    """
    start_time = datetime.strptime(start_time, DATETIME_FORMAT)
    end_time = datetime.strptime(end_time, DATETIME_FORMAT)

    diff = (end_time - start_time) / processes
    for idx in range(processes):
        yield start_time + diff * idx
    yield end_time


def get_partition_time(max_threads, start_time, end_time):
    """ Divides the time range of indexing into partitions based on number of processes.
        :param max_threads: Number of threads in multithreading
        :param start_time: Start time of a time range
        :param end_time: End time of a time range
    """
    partitions = list(datetime_partitioning(start_time, end_time, max_threads))
    datelist = []
    for sub in partitions:
        datelist.append(sub.strftime(DATETIME_FORMAT))
    return end_time, datelist
