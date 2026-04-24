# Copyright (c) 2024 Stacklok, Inc.
#
# SPDX-License-Identifier: Apache-2.0
r"""
==================================
B614: Test for unsafe PyTorch load
==================================

This plugin checks for unsafe use of `torch.load` and
`torch.serialization.load`. Using `torch.load` or
`torch.serialization.load` with untrusted data can lead to arbitrary
code execution. There are two safe alternatives:

1. Use `torch.load` with `weights_only=True` where only tensor data is
   extracted, and no arbitrary Python objects are deserialized
2. Use the `safetensors` library from huggingface, which provides a safe
   deserialization mechanism

With `weights_only=True`, PyTorch enforces a strict type check, ensuring
that only torch.Tensor objects are loaded.

:Example:

.. code-block:: none

        >> Issue: Use of unsafe PyTorch load
        Severity: Medium   Confidence: High
        CWE: CWE-502 (https://cwe.mitre.org/data/definitions/502.html)
        Location: examples/pytorch_load_save.py:8
        7    loaded_model.load_state_dict(torch.load('model_weights.pth'))
        8    another_model.load_state_dict(torch.load('model_weights.pth',
                map_location='cpu'))
        9
        10   print("Model loaded successfully!")

.. seealso::

     - https://cwe.mitre.org/data/definitions/502.html
     - https://pytorch.org/docs/stable/generated/torch.load.html#torch.load
     - https://github.com/huggingface/safetensors

.. versionadded:: 1.7.10

"""
import bandit
from bandit.core import issue
from bandit.core import test_properties as test


@test.checks("Call")
@test.test_id("B614")
def pytorch_load(context):
    """
    This plugin checks for unsafe use of `torch.load` and
    `torch.serialization.load`. Using `torch.load` or
    `torch.serialization.load` with untrusted data can lead to
    arbitrary code execution. The safe alternative is to use
    `weights_only=True` or the safetensors library.
    """
    imported = context.is_module_imported_exact("torch")
    qualname = context.call_function_name_qual
    if not imported and isinstance(qualname, str):
        return

    if qualname in {"torch.load", "torch.serialization.load"}:
        # For torch.load, check if weights_only=True is specified
        weights_only = context.get_call_arg_value("weights_only")
        if weights_only == "True" or weights_only is True:
            return

        return bandit.Issue(
            severity=bandit.MEDIUM,
            confidence=bandit.HIGH,
            text="Use of unsafe PyTorch load",
            cwe=issue.Cwe.DESERIALIZATION_OF_UNTRUSTED_DATA,
            lineno=context.get_lineno_for_call_arg("load"),
        )
