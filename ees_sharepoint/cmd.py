#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#

from . import create_content_source, fetch_index, deindex

def bootstrap():
  create_content_source.start()

def test_connectivity():
  #TODO: implement
  print("Not yet implemented")

def full_sync():
  fetch_index.start("full_sync")

def incremental_sync():
  fetch_index.start("incremental_sync")

def deletion_sync():
  deindex.start()
