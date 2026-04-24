#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
import collections
import logging

LOG = logging.getLogger(__name__)


class BanditMetaAst:
    nodes = collections.OrderedDict()

    def __init__(self):
        pass

    def add_node(self, node, parent_id, depth):
        """Add a node to the AST node collection

        :param node: The AST node to add
        :param parent_id: The ID of the node's parent
        :param depth: The depth of the node
        :return: -
        """
        node_id = hex(id(node))
        LOG.debug("adding node : %s [%s]", node_id, depth)
        self.nodes[node_id] = {
            "raw": node,
            "parent_id": parent_id,
            "depth": depth,
        }

    def __str__(self):
        """Dumps a listing of all of the nodes

        Dumps a listing of all of the nodes for debugging purposes
        :return: -
        """
        tmpstr = ""
        for k, v in self.nodes.items():
            tmpstr += f"Node: {k}\n"
            tmpstr += f"\t{str(v)}\n"
        tmpstr += f"Length: {len(self.nodes)}\n"
        return tmpstr
