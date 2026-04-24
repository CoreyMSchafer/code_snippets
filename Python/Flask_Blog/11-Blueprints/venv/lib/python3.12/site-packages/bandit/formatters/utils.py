# Copyright (c) 2016 Rackspace, Inc.
#
# SPDX-License-Identifier: Apache-2.0
"""Utility functions for formatting plugins for Bandit."""
import io


def wrap_file_object(fileobj):
    """If the fileobj passed in cannot handle text, use TextIOWrapper
    to handle the conversion.
    """
    if isinstance(fileobj, io.TextIOBase):
        return fileobj
    return io.TextIOWrapper(fileobj)
