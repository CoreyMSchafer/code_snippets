#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
r"""
========================================
B609: Test for use of wildcard injection
========================================

Python provides a number of methods that emulate the behavior of standard Linux
command line utilities. Like their Linux counterparts, these commands may take
a wildcard "\*" character in place of a file system path. This is interpreted
to mean "any and all files or folders" and can be used to build partially
qualified paths, such as "/home/user/\*".

The use of partially qualified paths may result in unintended consequences if
an unexpected file or symlink is placed into the path location given. This
becomes particularly dangerous when combined with commands used to manipulate
file permissions or copy data off of a system.

This test plugin looks for usage of the following commands in conjunction with
wild card parameters:

- 'chown'
- 'chmod'
- 'tar'
- 'rsync'

As well as any method configured in the shell or subprocess injection test
configurations.


**Config Options:**

This plugin test shares a configuration with others in the same family, namely
`shell_injection`. This configuration is divided up into three sections,
`subprocess`, `shell` and `no_shell`. They each list Python calls that spawn
subprocesses, invoke commands within a shell, or invoke commands without a
shell (by replacing the calling process) respectively.

This test will scan parameters of all methods in all sections. Note that
methods are fully qualified and de-aliased prior to checking.


.. code-block:: yaml

    shell_injection:
        # Start a process using the subprocess module, or one of its wrappers.
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

    >> Issue: Possible wildcard injection in call: subprocess.Popen
       Severity: High   Confidence: Medium
       CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
       Location: ./examples/wildcard-injection.py:8
    7    o.popen2('/bin/chmod *')
    8    subp.Popen('/bin/chown *', shell=True)
    9

    >> Issue: subprocess call - check for execution of untrusted input.
       Severity: Low   Confidence: High
       CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
       Location: ./examples/wildcard-injection.py:11
    10   # Not vulnerable to wildcard injection
    11   subp.Popen('/bin/rsync *')
    12   subp.Popen("/bin/chmod *")


.. seealso::

 - https://security.openstack.org
 - https://en.wikipedia.org/wiki/Wildcard_character
 - https://www.defensecode.com/public/DefenseCode_Unix_WildCards_Gone_Wild.txt
 - https://cwe.mitre.org/data/definitions/78.html

.. versionadded:: 0.9.0

.. versionchanged:: 1.7.3
    CWE information added

"""
import bandit
from bandit.core import issue
from bandit.core import test_properties as test
from bandit.plugins import injection_shell  # NOTE(tkelsey): shared config

gen_config = injection_shell.gen_config


@test.takes_config("shell_injection")
@test.checks("Call")
@test.test_id("B609")
def linux_commands_wildcard_injection(context, config):
    if not ("shell" in config and "subprocess" in config):
        return

    vulnerable_funcs = ["chown", "chmod", "tar", "rsync"]
    if context.call_function_name_qual in config["shell"] or (
        context.call_function_name_qual in config["subprocess"]
        and context.check_call_arg_value("shell", "True")
    ):
        if context.call_args_count >= 1:
            call_argument = context.get_call_arg_at_position(0)
            argument_string = ""
            if isinstance(call_argument, list):
                for li in call_argument:
                    argument_string += f" {li}"
            elif isinstance(call_argument, str):
                argument_string = call_argument

            if argument_string != "":
                for vulnerable_func in vulnerable_funcs:
                    if (
                        vulnerable_func in argument_string
                        and "*" in argument_string
                    ):
                        return bandit.Issue(
                            severity=bandit.HIGH,
                            confidence=bandit.MEDIUM,
                            cwe=issue.Cwe.IMPROPER_WILDCARD_NEUTRALIZATION,
                            text="Possible wildcard injection in call: %s"
                            % context.call_function_name_qual,
                            lineno=context.get_lineno_for_call_arg("shell"),
                        )
