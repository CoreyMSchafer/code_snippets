#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Bandit is a tool designed to find common security issues in Python code.

Bandit is a tool designed to find common security issues in Python code.
To do this Bandit processes each file, builds an AST from it, and runs
appropriate plugins against the AST nodes. Once Bandit has finished
scanning all the files it generates a report.

Bandit was originally developed within the OpenStack Security Project and
later rehomed to PyCQA.

https://bandit.readthedocs.io/
"""
from bandit.cli import main

main.main()
