#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
import pytest
import unittest
import unittest.mock

from ees_sharepoint import utils

class TestUtils(unittest.TestCase):
    def test_encode(self):
      encoded_string = utils.encode("some nice object'")
      assert encoded_string == "some%20nice%20object''"
