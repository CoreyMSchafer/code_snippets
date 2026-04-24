# SPDX-License-Identifier: Apache-2.0
r"""
================================================
B615: Test for unsafe Hugging Face Hub downloads
================================================

This plugin checks for unsafe downloads from Hugging Face Hub without proper
integrity verification. Downloading models, datasets, or files without
specifying a revision based on an immmutable revision (commit) can
lead to supply chain attacks where malicious actors could
replace model files and use an existing tag or branch name
to serve malicious content.

The secure approach is to:

1. Pin to specific revisions/commits when downloading models, files or datasets

Common unsafe patterns:
- ``AutoModel.from_pretrained("org/model-name")``
- ``AutoModel.from_pretrained("org/model-name", revision="main")``
- ``AutoModel.from_pretrained("org/model-name", revision="v1.0.0")``
- ``load_dataset("org/dataset-name")`` without revision
- ``load_dataset("org/dataset-name", revision="main")``
- ``load_dataset("org/dataset-name", revision="v1.0")``
- ``AutoTokenizer.from_pretrained("org/model-name")``
- ``AutoTokenizer.from_pretrained("org/model-name", revision="main")``
- ``AutoTokenizer.from_pretrained("org/model-name", revision="v3.3.0")``
- ``hf_hub_download(repo_id="org/model_name", filename="file_name")``
- ``hf_hub_download(repo_id="org/model_name",
        filename="file_name",
        revision="main"
        )``
- ``hf_hub_download(repo_id="org/model_name",
        filename="file_name",
        revision="v2.0.0"
    )``
- ``snapshot_download(repo_id="org/model_name")``
- ``snapshot_download(repo_id="org/model_name", revision="main")``
- ``snapshot_download(repo_id="org/model_name", revision="refs/pr/1")``


:Example:

.. code-block:: none

        >> Issue: Unsafe Hugging Face Hub download without revision pinning
        Severity: Medium   Confidence: High
        CWE: CWE-494 (https://cwe.mitre.org/data/definitions/494.html)
        Location: examples/huggingface_unsafe_download.py:8
        7    # Unsafe: no revision specified
        8    model = AutoModel.from_pretrained("org/model_name")
        9

.. seealso::

     - https://cwe.mitre.org/data/definitions/494.html
     - https://huggingface.co/docs/huggingface_hub/en/guides/download

.. versionadded:: 1.8.6

"""
import ast
import string

import bandit
from bandit.core import issue
from bandit.core import test_properties as test


@test.checks("Call")
@test.test_id("B615")
def huggingface_unsafe_download(context):
    """
    This plugin checks for unsafe artifact download from Hugging Face Hub
    without immutable/reproducible revision pinning.
    """
    # Check if any HuggingFace-related modules are imported
    hf_modules = [
        "transformers",
        "datasets",
        "huggingface_hub",
    ]

    # Check if any HF modules are imported
    hf_imported = any(
        context.is_module_imported_like(module) for module in hf_modules
    )

    if not hf_imported:
        return

    qualname = context.call_function_name_qual
    if not isinstance(qualname, str):
        return

    unsafe_patterns = {
        # transformers library patterns
        "from_pretrained": ["transformers"],
        # datasets library patterns
        "load_dataset": ["datasets"],
        # huggingface_hub patterns
        "hf_hub_download": ["huggingface_hub"],
        "snapshot_download": ["huggingface_hub"],
        "repository_id": ["huggingface_hub"],
    }

    qualname_parts = qualname.split(".")
    func_name = qualname_parts[-1]

    if func_name not in unsafe_patterns:
        return

    required_modules = unsafe_patterns[func_name]
    if not any(module in qualname_parts for module in required_modules):
        return

    # Check for revision parameter (the key security control).
    # First, check the raw AST to see if a revision/commit_id keyword was
    # passed as a non-literal expression (variable, attribute, subscript,
    # function call, etc.).  In those cases we cannot statically determine
    # the value, so we give the user the benefit of the doubt.
    call_node = context._context.get("call")
    if call_node is not None:
        for kw in getattr(call_node, "keywords", []):
            if kw.arg in ("revision", "commit_id") and not isinstance(
                kw.value, ast.Constant
            ):
                return

    revision_value = context.get_call_arg_value("revision")
    commit_id_value = context.get_call_arg_value("commit_id")

    # Check if a revision or commit_id is specified
    revision_to_check = revision_value or commit_id_value

    if revision_to_check is not None:
        # Check if it's a secure revision (looks like a commit hash)
        # Commit hashes: 40 chars (full SHA) or 7+ chars (short SHA)
        if isinstance(revision_to_check, str):
            # Remove quotes if present
            revision_str = str(revision_to_check).strip("\"'")

            # Check if it looks like a commit hash (hexadecimal string)
            # Must be at least 7 characters and all hexadecimal
            is_hex = all(c in string.hexdigits for c in revision_str)
            if len(revision_str) >= 7 and is_hex:
                # This looks like a commit hash, which is secure
                return

    # Edge case: check if this is a local path (starts with ./ or /)
    first_arg = context.get_call_arg_at_position(0)
    if first_arg and isinstance(first_arg, str):
        if first_arg.startswith(("./", "/", "../")):
            # Local paths are generally safer
            return

    return bandit.Issue(
        severity=bandit.MEDIUM,
        confidence=bandit.HIGH,
        text=(
            f"Unsafe Hugging Face Hub download without revision pinning "
            f"in {func_name}()"
        ),
        cwe=issue.Cwe.DOWNLOAD_OF_CODE_WITHOUT_INTEGRITY_CHECK,
        lineno=context.get_lineno_for_call_arg(func_name),
    )
