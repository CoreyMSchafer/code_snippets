#
# Copyright 2016 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
r"""
======================================================
Blacklist various Python imports known to be dangerous
======================================================

This blacklist data checks for a number of Python modules known to have
possible security implications. The following blacklist tests are run against
any import statements or calls encountered in the scanned code base.

Note that the XML rules listed here are mostly based off of Christian Heimes'
work on defusedxml: https://pypi.org/project/defusedxml/

B401: import_telnetlib
----------------------

A telnet-related module is being imported. Telnet is considered insecure. Use
SSH or some other encrypted protocol.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B401 | import_telnetlib    | - telnetlib                        | high      |
+------+---------------------+------------------------------------+-----------+

B402: import_ftplib
-------------------
A FTP-related module is being imported.  FTP is considered insecure. Use
SSH/SFTP/SCP or some other encrypted protocol.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B402 | import_ftplib       | - ftplib                           | high      |
+------+---------------------+------------------------------------+-----------+

B403: import_pickle
-------------------

Consider possible security implications associated with these modules.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B403 | import_pickle       | - pickle                           | low       |
|      |                     | - cPickle                          |           |
|      |                     | - dill                             |           |
|      |                     | - shelve                           |           |
+------+---------------------+------------------------------------+-----------+

B404: import_subprocess
-----------------------

Consider possible security implications associated with these modules.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B404 | import_subprocess   | - subprocess                       | low       |
+------+---------------------+------------------------------------+-----------+


B405: import_xml_etree
----------------------

Using various methods to parse untrusted XML data is known to be vulnerable to
XML attacks. Replace vulnerable imports with the equivalent defusedxml package,
or make sure defusedxml.defuse_stdlib() is called.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B405 | import_xml_etree    | - xml.etree.cElementTree           | low       |
|      |                     | - xml.etree.ElementTree            |           |
+------+---------------------+------------------------------------+-----------+

B406: import_xml_sax
--------------------

Using various methods to parse untrusted XML data is known to be vulnerable to
XML attacks. Replace vulnerable imports with the equivalent defusedxml package,
or make sure defusedxml.defuse_stdlib() is called.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B406 | import_xml_sax      | - xml.sax                          | low       |
+------+---------------------+------------------------------------+-----------+

B407: import_xml_expat
----------------------

Using various methods to parse untrusted XML data is known to be vulnerable to
XML attacks. Replace vulnerable imports with the equivalent defusedxml package,
or make sure defusedxml.defuse_stdlib() is called.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B407 | import_xml_expat    | - xml.dom.expatbuilder             | low       |
+------+---------------------+------------------------------------+-----------+

B408: import_xml_minidom
------------------------

Using various methods to parse untrusted XML data is known to be vulnerable to
XML attacks. Replace vulnerable imports with the equivalent defusedxml package,
or make sure defusedxml.defuse_stdlib() is called.


+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B408 | import_xml_minidom  | - xml.dom.minidom                  | low       |
+------+---------------------+------------------------------------+-----------+

B409: import_xml_pulldom
------------------------

Using various methods to parse untrusted XML data is known to be vulnerable to
XML attacks. Replace vulnerable imports with the equivalent defusedxml package,
or make sure defusedxml.defuse_stdlib() is called.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B409 | import_xml_pulldom  | - xml.dom.pulldom                  | low       |
+------+---------------------+------------------------------------+-----------+

B410: import_lxml
-----------------

This import blacklist has been removed. The information here has been
left for historical purposes.

Using various methods to parse untrusted XML data is known to be vulnerable to
XML attacks. Replace vulnerable imports with the equivalent defusedxml package.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B410 | import_lxml         | - lxml                             | low       |
+------+---------------------+------------------------------------+-----------+

B411: import_xmlrpclib
----------------------

XMLRPC is particularly dangerous as it is also concerned with communicating
data over a network. Use defusedxml.xmlrpc.monkey_patch() function to
monkey-patch xmlrpclib and mitigate remote XML attacks.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B411 | import_xmlrpclib    | - xmlrpc                           | high      |
+------+---------------------+------------------------------------+-----------+

B412: import_httpoxy
--------------------
httpoxy is a set of vulnerabilities that affect application code running in
CGI, or CGI-like environments. The use of CGI for web applications should be
avoided to prevent this class of attack. More details are available
at https://httpoxy.org/.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B412 | import_httpoxy      | - wsgiref.handlers.CGIHandler      | high      |
|      |                     | - twisted.web.twcgi.CGIScript      |           |
+------+---------------------+------------------------------------+-----------+

B413: import_pycrypto
---------------------
pycrypto library is known to have publicly disclosed buffer overflow
vulnerability https://github.com/dlitz/pycrypto/issues/176. It is no longer
actively maintained and has been deprecated in favor of pyca/cryptography
library.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B413 | import_pycrypto     | - Crypto.Cipher                    | high      |
|      |                     | - Crypto.Hash                      |           |
|      |                     | - Crypto.IO                        |           |
|      |                     | - Crypto.Protocol                  |           |
|      |                     | - Crypto.PublicKey                 |           |
|      |                     | - Crypto.Random                    |           |
|      |                     | - Crypto.Signature                 |           |
|      |                     | - Crypto.Util                      |           |
+------+---------------------+------------------------------------+-----------+

B414: import_pycryptodome
-------------------------
This import blacklist has been removed. The information here has been
left for historical purposes.

pycryptodome is a direct fork of pycrypto that has not fully addressed
the issues inherent in PyCrypto.  It seems to exist, mainly, as an API
compatible continuation of pycrypto and should be deprecated in favor
of pyca/cryptography which has more support among the Python community.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B414 | import_pycryptodome | - Cryptodome.Cipher                | high      |
|      |                     | - Cryptodome.Hash                  |           |
|      |                     | - Cryptodome.IO                    |           |
|      |                     | - Cryptodome.Protocol              |           |
|      |                     | - Cryptodome.PublicKey             |           |
|      |                     | - Cryptodome.Random                |           |
|      |                     | - Cryptodome.Signature             |           |
|      |                     | - Cryptodome.Util                  |           |
+------+---------------------+------------------------------------+-----------+

B415: import_pyghmi
-------------------
An IPMI-related module is being imported. IPMI is considered insecure. Use
an encrypted protocol.

+------+---------------------+------------------------------------+-----------+
| ID   |  Name               |  Imports                           |  Severity |
+======+=====================+====================================+===========+
| B415 | import_pyghmi       | - pyghmi                           | high      |
+------+---------------------+------------------------------------+-----------+

"""
from bandit.blacklists import utils
from bandit.core import issue


def gen_blacklist():
    """Generate a list of items to blacklist.

    Methods of this type, "bandit.blacklist" plugins, are used to build a list
    of items that bandit's built in blacklisting tests will use to trigger
    issues. They replace the older blacklist* test plugins and allow
    blacklisted items to have a unique bandit ID for filtering and profile
    usage.

    :return: a dictionary mapping node types to a list of blacklist data
    """
    sets = []
    sets.append(
        utils.build_conf_dict(
            "import_telnetlib",
            "B401",
            issue.Cwe.CLEARTEXT_TRANSMISSION,
            ["telnetlib"],
            "A telnet-related module is being imported.  Telnet is "
            "considered insecure. Use SSH or some other encrypted protocol.",
            "HIGH",
        )
    )

    sets.append(
        utils.build_conf_dict(
            "import_ftplib",
            "B402",
            issue.Cwe.CLEARTEXT_TRANSMISSION,
            ["ftplib"],
            "A FTP-related module is being imported.  FTP is considered "
            "insecure. Use SSH/SFTP/SCP or some other encrypted protocol.",
            "HIGH",
        )
    )

    sets.append(
        utils.build_conf_dict(
            "import_pickle",
            "B403",
            issue.Cwe.DESERIALIZATION_OF_UNTRUSTED_DATA,
            ["pickle", "cPickle", "dill", "shelve"],
            "Consider possible security implications associated with "
            "{name} module.",
            "LOW",
        )
    )

    sets.append(
        utils.build_conf_dict(
            "import_subprocess",
            "B404",
            issue.Cwe.OS_COMMAND_INJECTION,
            ["subprocess"],
            "Consider possible security implications associated with the "
            "subprocess module.",
            "LOW",
        )
    )

    # Most of this is based off of Christian Heimes' work on defusedxml:
    #   https://pypi.org/project/defusedxml/#defusedxml-sax

    xml_msg = (
        "Using {name} to parse untrusted XML data is known to be "
        "vulnerable to XML attacks. Replace {name} with the equivalent "
        "defusedxml package, or make sure defusedxml.defuse_stdlib() "
        "is called."
    )

    sets.append(
        utils.build_conf_dict(
            "import_xml_etree",
            "B405",
            issue.Cwe.IMPROPER_INPUT_VALIDATION,
            ["xml.etree.cElementTree", "xml.etree.ElementTree"],
            xml_msg,
            "LOW",
        )
    )

    sets.append(
        utils.build_conf_dict(
            "import_xml_sax",
            "B406",
            issue.Cwe.IMPROPER_INPUT_VALIDATION,
            ["xml.sax"],
            xml_msg,
            "LOW",
        )
    )

    sets.append(
        utils.build_conf_dict(
            "import_xml_expat",
            "B407",
            issue.Cwe.IMPROPER_INPUT_VALIDATION,
            ["xml.dom.expatbuilder"],
            xml_msg,
            "LOW",
        )
    )

    sets.append(
        utils.build_conf_dict(
            "import_xml_minidom",
            "B408",
            issue.Cwe.IMPROPER_INPUT_VALIDATION,
            ["xml.dom.minidom"],
            xml_msg,
            "LOW",
        )
    )

    sets.append(
        utils.build_conf_dict(
            "import_xml_pulldom",
            "B409",
            issue.Cwe.IMPROPER_INPUT_VALIDATION,
            ["xml.dom.pulldom"],
            xml_msg,
            "LOW",
        )
    )

    # skipped B410 as the check for import_lxml has been removed

    sets.append(
        utils.build_conf_dict(
            "import_xmlrpclib",
            "B411",
            issue.Cwe.IMPROPER_INPUT_VALIDATION,
            ["xmlrpc"],
            "Using {name} to parse untrusted XML data is known to be "
            "vulnerable to XML attacks. Use defusedxml.xmlrpc.monkey_patch() "
            "function to monkey-patch xmlrpclib and mitigate XML "
            "vulnerabilities.",
            "HIGH",
        )
    )

    sets.append(
        utils.build_conf_dict(
            "import_httpoxy",
            "B412",
            issue.Cwe.IMPROPER_ACCESS_CONTROL,
            [
                "wsgiref.handlers.CGIHandler",
                "twisted.web.twcgi.CGIScript",
                "twisted.web.twcgi.CGIDirectory",
            ],
            "Consider possible security implications associated with "
            "{name} module.",
            "HIGH",
        )
    )

    sets.append(
        utils.build_conf_dict(
            "import_pycrypto",
            "B413",
            issue.Cwe.BROKEN_CRYPTO,
            [
                "Crypto.Cipher",
                "Crypto.Hash",
                "Crypto.IO",
                "Crypto.Protocol",
                "Crypto.PublicKey",
                "Crypto.Random",
                "Crypto.Signature",
                "Crypto.Util",
            ],
            "The pyCrypto library and its module {name} are no longer actively"
            " maintained and have been deprecated. "
            "Consider using pyca/cryptography library.",
            "HIGH",
        )
    )

    sets.append(
        utils.build_conf_dict(
            "import_pyghmi",
            "B415",
            issue.Cwe.CLEARTEXT_TRANSMISSION,
            ["pyghmi"],
            "An IPMI-related module is being imported. IPMI is considered "
            "insecure. Use an encrypted protocol.",
            "HIGH",
        )
    )

    return {"Import": sets, "ImportFrom": sets, "Call": sets}
