#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
import ast
import re

import bandit
from bandit.core import issue
from bandit.core import test_properties as test

# yuck, regex: starts with a windows drive letter (eg C:)
# or one of our path delimiter characters (/, \, .)
full_path_match = re.compile(r"^(?:[A-Za-z](?=\:)|[\\\/\.])")


def _evaluate_shell_call(context):
    no_formatting = isinstance(
        context.node.args[0], ast.Constant
    ) and isinstance(context.node.args[0].value, str)

    if no_formatting:
        return bandit.LOW
    else:
        return bandit.HIGH


def gen_config(name):
    if name == "shell_injection":
        return {
            # Start a process using the subprocess module, or one of its
            # wrappers.
            "subprocess": [
                "subprocess.Popen",
                "subprocess.call",
                "subprocess.check_call",
                "subprocess.check_output",
                "subprocess.run",
            ],
            # Start a process with a function vulnerable to shell injection.
            "shell": [
                "os.system",
                "os.popen",
                "os.popen2",
                "os.popen3",
                "os.popen4",
                "popen2.popen2",
                "popen2.popen3",
                "popen2.popen4",
                "popen2.Popen3",
                "popen2.Popen4",
                "commands.getoutput",
                "commands.getstatusoutput",
                "subprocess.getoutput",
                "subprocess.getstatusoutput",
            ],
            # Start a process with a function that is not vulnerable to shell
            # injection.
            "no_shell": [
                "os.execl",
                "os.execle",
                "os.execlp",
                "os.execlpe",
                "os.execv",
                "os.execve",
                "os.execvp",
                "os.execvpe",
                "os.spawnl",
                "os.spawnle",
                "os.spawnlp",
                "os.spawnlpe",
                "os.spawnv",
                "os.spawnve",
                "os.spawnvp",
                "os.spawnvpe",
                "os.startfile",
            ],
        }


def has_shell(context):
    keywords = context.node.keywords
    result = False
    if "shell" in context.call_keywords:
        for key in keywords:
            if key.arg == "shell":
                val = key.value
                if isinstance(val, ast.Constant) and (
                    isinstance(val.value, int)
                    or isinstance(val.value, float)
                    or isinstance(val.value, complex)
                ):
                    result = bool(val.value)
                elif isinstance(val, ast.List):
                    result = bool(val.elts)
                elif isinstance(val, ast.Dict):
                    result = bool(val.keys)
                elif isinstance(val, ast.Name) and val.id in ["False", "None"]:
                    result = False
                elif isinstance(val, ast.Constant):
                    result = val.value
                else:
                    result = True
    return result


@test.takes_config("shell_injection")
@test.checks("Call")
@test.test_id("B602")
def subprocess_popen_with_shell_equals_true(context, config):
    """**B602: Test for use of popen with shell equals true**

    Python possesses many mechanisms to invoke an external executable. However,
    doing so may present a security issue if appropriate care is not taken to
    sanitize any user provided or variable input.

    This plugin test is part of a family of tests built to check for process
    spawning and warn appropriately. Specifically, this test looks for the
    spawning of a subprocess using a command shell. This type of subprocess
    invocation is dangerous as it is vulnerable to various shell injection
    attacks. Great care should be taken to sanitize all input in order to
    mitigate this risk. Calls of this type are identified by a parameter of
    'shell=True' being given.

    Additionally, this plugin scans the command string given and adjusts its
    reported severity based on how it is presented. If the command string is a
    simple static string containing no special shell characters, then the
    resulting issue has low severity. If the string is static, but contains
    shell formatting characters or wildcards, then the reported issue is
    medium. Finally, if the string is computed using Python's string
    manipulation or formatting operations, then the reported issue has high
    severity. These severity levels reflect the likelihood that the code is
    vulnerable to injection.

    See also:

    - :doc:`../plugins/linux_commands_wildcard_injection`
    - :doc:`../plugins/subprocess_without_shell_equals_true`
    - :doc:`../plugins/start_process_with_no_shell`
    - :doc:`../plugins/start_process_with_a_shell`
    - :doc:`../plugins/start_process_with_partial_path`

    **Config Options:**

    This plugin test shares a configuration with others in the same family,
    namely `shell_injection`. This configuration is divided up into three
    sections, `subprocess`, `shell` and `no_shell`. They each list Python calls
    that spawn subprocesses, invoke commands within a shell, or invoke commands
    without a shell (by replacing the calling process) respectively.

    This plugin specifically scans for methods listed in `subprocess` section
    that have shell=True specified.

    .. code-block:: yaml

        shell_injection:

            # Start a process using the subprocess module, or one of its
            wrappers.
            subprocess:
                - subprocess.Popen
                - subprocess.call


    :Example:

    .. code-block:: none

        >> Issue: subprocess call with shell=True seems safe, but may be
        changed in the future, consider rewriting without shell
           Severity: Low   Confidence: High
           CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
           Location: ./examples/subprocess_shell.py:21
        20  subprocess.check_call(['/bin/ls', '-l'], shell=False)
        21  subprocess.check_call('/bin/ls -l', shell=True)
        22

        >> Issue: call with shell=True contains special shell characters,
        consider moving extra logic into Python code
           Severity: Medium   Confidence: High
           CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
           Location: ./examples/subprocess_shell.py:26
        25
        26  subprocess.Popen('/bin/ls *', shell=True)
        27  subprocess.Popen('/bin/ls %s' % ('something',), shell=True)

        >> Issue: subprocess call with shell=True identified, security issue.
           Severity: High   Confidence: High
           CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
           Location: ./examples/subprocess_shell.py:27
        26  subprocess.Popen('/bin/ls *', shell=True)
        27  subprocess.Popen('/bin/ls %s' % ('something',), shell=True)
        28  subprocess.Popen('/bin/ls {}'.format('something'), shell=True)

    .. seealso::

     - https://security.openstack.org
     - https://docs.python.org/3/library/subprocess.html#frequently-used-arguments
     - https://security.openstack.org/guidelines/dg_use-subprocess-securely.html
     - https://security.openstack.org/guidelines/dg_avoid-shell-true.html
     - https://cwe.mitre.org/data/definitions/78.html

    .. versionadded:: 0.9.0

    .. versionchanged:: 1.7.3
        CWE information added

    """  # noqa: E501
    if config and context.call_function_name_qual in config["subprocess"]:
        if has_shell(context):
            if len(context.call_args) > 0:
                sev = _evaluate_shell_call(context)
                if sev == bandit.LOW:
                    return bandit.Issue(
                        severity=bandit.LOW,
                        confidence=bandit.HIGH,
                        cwe=issue.Cwe.OS_COMMAND_INJECTION,
                        text="subprocess call with shell=True seems safe, but "
                        "may be changed in the future, consider "
                        "rewriting without shell",
                        lineno=context.get_lineno_for_call_arg("shell"),
                    )
                else:
                    return bandit.Issue(
                        severity=bandit.HIGH,
                        confidence=bandit.HIGH,
                        cwe=issue.Cwe.OS_COMMAND_INJECTION,
                        text="subprocess call with shell=True identified, "
                        "security issue.",
                        lineno=context.get_lineno_for_call_arg("shell"),
                    )


@test.takes_config("shell_injection")
@test.checks("Call")
@test.test_id("B603")
def subprocess_without_shell_equals_true(context, config):
    """**B603: Test for use of subprocess without shell equals true**

    Python possesses many mechanisms to invoke an external executable. However,
    doing so may present a security issue if appropriate care is not taken to
    sanitize any user provided or variable input.

    This plugin test is part of a family of tests built to check for process
    spawning and warn appropriately. Specifically, this test looks for the
    spawning of a subprocess without the use of a command shell. This type of
    subprocess invocation is not vulnerable to shell injection attacks, but
    care should still be taken to ensure validity of input.

    Because this is a lesser issue than that described in
    `subprocess_popen_with_shell_equals_true` a LOW severity warning is
    reported.

    See also:

    - :doc:`../plugins/linux_commands_wildcard_injection`
    - :doc:`../plugins/subprocess_popen_with_shell_equals_true`
    - :doc:`../plugins/start_process_with_no_shell`
    - :doc:`../plugins/start_process_with_a_shell`
    - :doc:`../plugins/start_process_with_partial_path`

    **Config Options:**

    This plugin test shares a configuration with others in the same family,
    namely `shell_injection`. This configuration is divided up into three
    sections, `subprocess`, `shell` and `no_shell`. They each list Python calls
    that spawn subprocesses, invoke commands within a shell, or invoke commands
    without a shell (by replacing the calling process) respectively.

    This plugin specifically scans for methods listed in `subprocess` section
    that have shell=False specified.

    .. code-block:: yaml

        shell_injection:
            # Start a process using the subprocess module, or one of its
            wrappers.
            subprocess:
                - subprocess.Popen
                - subprocess.call

    :Example:

    .. code-block:: none

        >> Issue: subprocess call - check for execution of untrusted input.
           Severity: Low   Confidence: High
           CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
           Location: ./examples/subprocess_shell.py:23
        22
        23    subprocess.check_output(['/bin/ls', '-l'])
        24

    .. seealso::

     - https://security.openstack.org
     - https://docs.python.org/3/library/subprocess.html#frequently-used-arguments
     - https://security.openstack.org/guidelines/dg_avoid-shell-true.html
     - https://security.openstack.org/guidelines/dg_use-subprocess-securely.html
     - https://cwe.mitre.org/data/definitions/78.html

    .. versionadded:: 0.9.0

    .. versionchanged:: 1.7.3
        CWE information added

    """  # noqa: E501
    if config and context.call_function_name_qual in config["subprocess"]:
        if not has_shell(context):
            return bandit.Issue(
                severity=bandit.LOW,
                confidence=bandit.HIGH,
                cwe=issue.Cwe.OS_COMMAND_INJECTION,
                text="subprocess call - check for execution of untrusted "
                "input.",
                lineno=context.get_lineno_for_call_arg("shell"),
            )


@test.takes_config("shell_injection")
@test.checks("Call")
@test.test_id("B604")
def any_other_function_with_shell_equals_true(context, config):
    """**B604: Test for any function with shell equals true**

    Python possesses many mechanisms to invoke an external executable. However,
    doing so may present a security issue if appropriate care is not taken to
    sanitize any user provided or variable input.

    This plugin test is part of a family of tests built to check for process
    spawning and warn appropriately. Specifically, this plugin test
    interrogates method calls for the presence of a keyword parameter `shell`
    equalling true. It is related to detection of shell injection issues and is
    intended to catch custom wrappers to vulnerable methods that may have been
    created.

    See also:

    - :doc:`../plugins/linux_commands_wildcard_injection`
    - :doc:`../plugins/subprocess_popen_with_shell_equals_true`
    - :doc:`../plugins/subprocess_without_shell_equals_true`
    - :doc:`../plugins/start_process_with_no_shell`
    - :doc:`../plugins/start_process_with_a_shell`
    - :doc:`../plugins/start_process_with_partial_path`

    **Config Options:**

    This plugin test shares a configuration with others in the same family,
    namely `shell_injection`. This configuration is divided up into three
    sections, `subprocess`, `shell` and `no_shell`. They each list Python calls
    that spawn subprocesses, invoke commands within a shell, or invoke commands
    without a shell (by replacing the calling process) respectively.

    Specifically, this plugin excludes those functions listed under the
    subprocess section, these methods are tested in a separate specific test
    plugin and this exclusion prevents duplicate issue reporting.

    .. code-block:: yaml

        shell_injection:
            # Start a process using the subprocess module, or one of its
            wrappers.
            subprocess: [subprocess.Popen, subprocess.call,
                         subprocess.check_call, subprocess.check_output
                         execute_with_timeout]


    :Example:

    .. code-block:: none

        >> Issue: Function call with shell=True parameter identified, possible
        security issue.
           Severity: Medium   Confidence: High
           CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
           Location: ./examples/subprocess_shell.py:9
        8 pop('/bin/gcc --version', shell=True)
        9 Popen('/bin/gcc --version', shell=True)
        10

    .. seealso::

     - https://security.openstack.org/guidelines/dg_avoid-shell-true.html
     - https://security.openstack.org/guidelines/dg_use-subprocess-securely.html
     - https://cwe.mitre.org/data/definitions/78.html

    .. versionadded:: 0.9.0

    .. versionchanged:: 1.7.3
        CWE information added

    """  # noqa: E501
    if config and context.call_function_name_qual not in config["subprocess"]:
        if has_shell(context):
            return bandit.Issue(
                severity=bandit.MEDIUM,
                confidence=bandit.LOW,
                cwe=issue.Cwe.OS_COMMAND_INJECTION,
                text="Function call with shell=True parameter identified, "
                "possible security issue.",
                lineno=context.get_lineno_for_call_arg("shell"),
            )


@test.takes_config("shell_injection")
@test.checks("Call")
@test.test_id("B605")
def start_process_with_a_shell(context, config):
    """**B605: Test for starting a process with a shell**

    Python possesses many mechanisms to invoke an external executable. However,
    doing so may present a security issue if appropriate care is not taken to
    sanitize any user provided or variable input.

    This plugin test is part of a family of tests built to check for process
    spawning and warn appropriately. Specifically, this test looks for the
    spawning of a subprocess using a command shell. This type of subprocess
    invocation is dangerous as it is vulnerable to various shell injection
    attacks. Great care should be taken to sanitize all input in order to
    mitigate this risk. Calls of this type are identified by the use of certain
    commands which are known to use shells. Bandit will report a LOW
    severity warning.

    See also:

    - :doc:`../plugins/linux_commands_wildcard_injection`
    - :doc:`../plugins/subprocess_without_shell_equals_true`
    - :doc:`../plugins/start_process_with_no_shell`
    - :doc:`../plugins/start_process_with_partial_path`
    - :doc:`../plugins/subprocess_popen_with_shell_equals_true`

    **Config Options:**

    This plugin test shares a configuration with others in the same family,
    namely `shell_injection`. This configuration is divided up into three
    sections, `subprocess`, `shell` and `no_shell`. They each list Python calls
    that spawn subprocesses, invoke commands within a shell, or invoke commands
    without a shell (by replacing the calling process) respectively.

    This plugin specifically scans for methods listed in `shell` section.

    .. code-block:: yaml

        shell_injection:
            shell:
                - os.system
                - os.popen
                - os.popen2
                - os.popen3
                - os.popen4
                - popen2.popen2
                - popen2.popen3
                - popen2.popen4
                - popen2.Popen3
                - popen2.Popen4
                - commands.getoutput
                - commands.getstatusoutput
                - subprocess.getoutput
                - subprocess.getstatusoutput

    :Example:

    .. code-block:: none

        >> Issue: Starting a process with a shell: check for injection.
           Severity: Low   Confidence: Medium
           CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
           Location: examples/os_system.py:3
        2
        3   os.system('/bin/echo hi')

    .. seealso::

     - https://security.openstack.org
     - https://docs.python.org/3/library/os.html#os.system
     - https://docs.python.org/3/library/subprocess.html#frequently-used-arguments
     - https://security.openstack.org/guidelines/dg_use-subprocess-securely.html
     - https://cwe.mitre.org/data/definitions/78.html

    .. versionadded:: 0.10.0

    .. versionchanged:: 1.7.3
        CWE information added

    """  # noqa: E501
    if config and context.call_function_name_qual in config["shell"]:
        if len(context.call_args) > 0:
            sev = _evaluate_shell_call(context)
            if sev == bandit.LOW:
                return bandit.Issue(
                    severity=bandit.LOW,
                    confidence=bandit.HIGH,
                    cwe=issue.Cwe.OS_COMMAND_INJECTION,
                    text="Starting a process with a shell: "
                    "Seems safe, but may be changed in the future, "
                    "consider rewriting without shell",
                )
            else:
                return bandit.Issue(
                    severity=bandit.HIGH,
                    confidence=bandit.HIGH,
                    cwe=issue.Cwe.OS_COMMAND_INJECTION,
                    text="Starting a process with a shell, possible injection"
                    " detected, security issue.",
                )


@test.takes_config("shell_injection")
@test.checks("Call")
@test.test_id("B606")
def start_process_with_no_shell(context, config):
    """**B606: Test for starting a process with no shell**

    Python possesses many mechanisms to invoke an external executable. However,
    doing so may present a security issue if appropriate care is not taken to
    sanitize any user provided or variable input.

    This plugin test is part of a family of tests built to check for process
    spawning and warn appropriately. Specifically, this test looks for the
    spawning of a subprocess in a way that doesn't use a shell. Although this
    is generally safe, it maybe useful for penetration testing workflows to
    track where external system calls are used.  As such a LOW severity message
    is generated.

    See also:

    - :doc:`../plugins/linux_commands_wildcard_injection`
    - :doc:`../plugins/subprocess_without_shell_equals_true`
    - :doc:`../plugins/start_process_with_a_shell`
    - :doc:`../plugins/start_process_with_partial_path`
    - :doc:`../plugins/subprocess_popen_with_shell_equals_true`

    **Config Options:**

    This plugin test shares a configuration with others in the same family,
    namely `shell_injection`. This configuration is divided up into three
    sections, `subprocess`, `shell` and `no_shell`. They each list Python calls
    that spawn subprocesses, invoke commands within a shell, or invoke commands
    without a shell (by replacing the calling process) respectively.

    This plugin specifically scans for methods listed in `no_shell` section.

    .. code-block:: yaml

        shell_injection:
            no_shell:
                - os.execl
                - os.execle
                - os.execlp
                - os.execlpe
                - os.execv
                - os.execve
                - os.execvp
                - os.execvpe
                - os.spawnl
                - os.spawnle
                - os.spawnlp
                - os.spawnlpe
                - os.spawnv
                - os.spawnve
                - os.spawnvp
                - os.spawnvpe
                - os.startfile

    :Example:

    .. code-block:: none

        >> Issue: [start_process_with_no_shell] Starting a process without a
           shell.
           Severity: Low   Confidence: Medium
           CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
           Location: examples/os-spawn.py:8
        7   os.spawnv(mode, path, args)
        8   os.spawnve(mode, path, args, env)
        9   os.spawnvp(mode, file, args)

    .. seealso::

     - https://security.openstack.org
     - https://docs.python.org/3/library/os.html#os.system
     - https://docs.python.org/3/library/subprocess.html#frequently-used-arguments
     - https://security.openstack.org/guidelines/dg_use-subprocess-securely.html
     - https://cwe.mitre.org/data/definitions/78.html

    .. versionadded:: 0.10.0

    .. versionchanged:: 1.7.3
        CWE information added

    """  # noqa: E501

    if config and context.call_function_name_qual in config["no_shell"]:
        return bandit.Issue(
            severity=bandit.LOW,
            confidence=bandit.MEDIUM,
            cwe=issue.Cwe.OS_COMMAND_INJECTION,
            text="Starting a process without a shell.",
        )


@test.takes_config("shell_injection")
@test.checks("Call")
@test.test_id("B607")
def start_process_with_partial_path(context, config):
    """**B607: Test for starting a process with a partial path**

    Python possesses many mechanisms to invoke an external executable. If the
    desired executable path is not fully qualified relative to the filesystem
    root then this may present a potential security risk.

    In POSIX environments, the `PATH` environment variable is used to specify a
    set of standard locations that will be searched for the first matching
    named executable. While convenient, this behavior may allow a malicious
    actor to exert control over a system. If they are able to adjust the
    contents of the `PATH` variable, or manipulate the file system, then a
    bogus executable may be discovered in place of the desired one. This
    executable will be invoked with the user privileges of the Python process
    that spawned it, potentially a highly privileged user.

    This test will scan the parameters of all configured Python methods,
    looking for paths that do not start at the filesystem root, that is, do not
    have a leading '/' character.

    **Config Options:**

    This plugin test shares a configuration with others in the same family,
    namely `shell_injection`. This configuration is divided up into three
    sections, `subprocess`, `shell` and `no_shell`. They each list Python calls
    that spawn subprocesses, invoke commands within a shell, or invoke commands
    without a shell (by replacing the calling process) respectively.

    This test will scan parameters of all methods in all sections. Note that
    methods are fully qualified and de-aliased prior to checking.

    .. code-block:: yaml

        shell_injection:
            # Start a process using the subprocess module, or one of its
            wrappers.
            subprocess:
                - subprocess.Popen
                - subprocess.call

            # Start a process with a function vulnerable to shell injection.
            shell:
                - os.system
                - os.popen
                - popen2.Popen3
                - popen2.Popen4
                - commands.getoutput
                - commands.getstatusoutput
            # Start a process with a function that is not vulnerable to shell
            injection.
            no_shell:
                - os.execl
                - os.execle


    :Example:

    .. code-block:: none

        >> Issue: Starting a process with a partial executable path
        Severity: Low   Confidence: High
        CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
        Location: ./examples/partial_path_process.py:3
        2    from subprocess import Popen as pop
        3    pop('gcc --version', shell=False)

    .. seealso::

     - https://security.openstack.org
     - https://docs.python.org/3/library/os.html#process-management
     - https://cwe.mitre.org/data/definitions/78.html

    .. versionadded:: 0.13.0

    .. versionchanged:: 1.7.3
        CWE information added

    """

    if config and len(context.call_args):
        if (
            context.call_function_name_qual in config["subprocess"]
            or context.call_function_name_qual in config["shell"]
            or context.call_function_name_qual in config["no_shell"]
        ):
            node = context.node.args[0]
            # some calls take an arg list, check the first part
            if isinstance(node, ast.List) and node.elts:
                node = node.elts[0]

            # make sure the param is a string literal and not a var name
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and not full_path_match.match(node.value)
            ):
                return bandit.Issue(
                    severity=bandit.LOW,
                    confidence=bandit.HIGH,
                    cwe=issue.Cwe.OS_COMMAND_INJECTION,
                    text="Starting a process with a partial executable path",
                )
