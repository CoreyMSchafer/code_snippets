# Copyright (c) 2015 VMware, Inc.
#
# SPDX-License-Identifier: Apache-2.0
r"""
=========================================
B505: Test for weak cryptographic key use
=========================================

As computational power increases, so does the ability to break ciphers with
smaller key lengths. The recommended key length size for RSA and DSA algorithms
is 2048 and higher. 1024 bits and below are now considered breakable. EC key
length sizes are recommended to be 224 and higher with 160 and below considered
breakable. This plugin test checks for use of any key less than those limits
and returns a high severity error if lower than the lower threshold and a
medium severity error for those lower than the higher threshold.

:Example:

.. code-block:: none

    >> Issue: DSA key sizes below 1024 bits are considered breakable.
       Severity: High   Confidence: High
       CWE: CWE-326 (https://cwe.mitre.org/data/definitions/326.html)
       Location: examples/weak_cryptographic_key_sizes.py:36
    35  # Also incorrect: without keyword args
    36  dsa.generate_private_key(512,
    37                           backends.default_backend())
    38  rsa.generate_private_key(3,

.. seealso::

 - https://csrc.nist.gov/publications/detail/sp/800-131a/rev-2/final
 - https://security.openstack.org/guidelines/dg_strong-crypto.html
 - https://cwe.mitre.org/data/definitions/326.html

.. versionadded:: 0.14.0

.. versionchanged:: 1.7.3
    CWE information added

"""
import bandit
from bandit.core import issue
from bandit.core import test_properties as test


def gen_config(name):
    if name == "weak_cryptographic_key":
        return {
            "weak_key_size_dsa_high": 1024,
            "weak_key_size_dsa_medium": 2048,
            "weak_key_size_rsa_high": 1024,
            "weak_key_size_rsa_medium": 2048,
            "weak_key_size_ec_high": 160,
            "weak_key_size_ec_medium": 224,
        }


def _classify_key_size(config, key_type, key_size):
    if isinstance(key_size, str):
        # size provided via a variable - can't process it at the moment
        return

    key_sizes = {
        "DSA": [
            (config["weak_key_size_dsa_high"], bandit.HIGH),
            (config["weak_key_size_dsa_medium"], bandit.MEDIUM),
        ],
        "RSA": [
            (config["weak_key_size_rsa_high"], bandit.HIGH),
            (config["weak_key_size_rsa_medium"], bandit.MEDIUM),
        ],
        "EC": [
            (config["weak_key_size_ec_high"], bandit.HIGH),
            (config["weak_key_size_ec_medium"], bandit.MEDIUM),
        ],
    }

    for size, level in key_sizes[key_type]:
        if key_size < size:
            return bandit.Issue(
                severity=level,
                confidence=bandit.HIGH,
                cwe=issue.Cwe.INADEQUATE_ENCRYPTION_STRENGTH,
                text="%s key sizes below %d bits are considered breakable. "
                % (key_type, size),
            )


def _weak_crypto_key_size_cryptography_io(context, config):
    func_key_type = {
        "cryptography.hazmat.primitives.asymmetric.dsa."
        "generate_private_key": "DSA",
        "cryptography.hazmat.primitives.asymmetric.rsa."
        "generate_private_key": "RSA",
        "cryptography.hazmat.primitives.asymmetric.ec."
        "generate_private_key": "EC",
    }
    arg_position = {
        "DSA": 0,
        "RSA": 1,
        "EC": 0,
    }
    key_type = func_key_type.get(context.call_function_name_qual)
    if key_type in ["DSA", "RSA"]:
        key_size = (
            context.get_call_arg_value("key_size")
            or context.get_call_arg_at_position(arg_position[key_type])
            or 2048
        )
        return _classify_key_size(config, key_type, key_size)
    elif key_type == "EC":
        curve_key_sizes = {
            "SECT571K1": 571,
            "SECT571R1": 570,
            "SECP521R1": 521,
            "BrainpoolP512R1": 512,
            "SECT409K1": 409,
            "SECT409R1": 409,
            "BrainpoolP384R1": 384,
            "SECP384R1": 384,
            "SECT283K1": 283,
            "SECT283R1": 283,
            "BrainpoolP256R1": 256,
            "SECP256K1": 256,
            "SECP256R1": 256,
            "SECT233K1": 233,
            "SECT233R1": 233,
            "SECP224R1": 224,
            "SECP192R1": 192,
            "SECT163K1": 163,
            "SECT163R2": 163,
        }
        curve = context.get_call_arg_value("curve") or (
            len(context.call_args) > arg_position[key_type]
            and context.call_args[arg_position[key_type]]
        )
        key_size = curve_key_sizes[curve] if curve in curve_key_sizes else 224
        return _classify_key_size(config, key_type, key_size)


def _weak_crypto_key_size_pycrypto(context, config):
    func_key_type = {
        "Crypto.PublicKey.DSA.generate": "DSA",
        "Crypto.PublicKey.RSA.generate": "RSA",
        "Cryptodome.PublicKey.DSA.generate": "DSA",
        "Cryptodome.PublicKey.RSA.generate": "RSA",
    }
    key_type = func_key_type.get(context.call_function_name_qual)
    if key_type:
        key_size = (
            context.get_call_arg_value("bits")
            or context.get_call_arg_at_position(0)
            or 2048
        )
        return _classify_key_size(config, key_type, key_size)


@test.takes_config
@test.checks("Call")
@test.test_id("B505")
def weak_cryptographic_key(context, config):
    return _weak_crypto_key_size_cryptography_io(
        context, config
    ) or _weak_crypto_key_size_pycrypto(context, config)
