#!/usr/bin/env python3

# Copyright (c) 2000-2025, Board of Trustees of Leland Stanford Jr. University
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Library and command line tool to interact with the LOCKSS 1.x DebugPanel servlet.
"""

__version__ = '0.8.1'

__copyright__ = '''
Copyright (c) 2000-2025, Board of Trustees of Leland Stanford Jr. University
'''.strip()

__license__ = __copyright__ + '\n\n' + '''
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
may be used to endorse or promote products derived from this software without
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
'''.strip()


from base64 import b64encode
from urllib.request import Request, urlopen
from typing import Any, Dict


type RequestUrlOpenT = Any


DEFAULT_DEPTH = 123


class Node(object):
    """
    Connector to a LOCKSS 1.x node.
    """

    DEFAULT_PROTOCOL = 'http'

    def __init__(self, node_reference: str, u: str, p: str) -> None:
        """
        Constructs a new ``Node`` instance.

        :param node_reference: A LOCKSS 1.x node reference, typically of the
                               form ``http://lockss.university.edu:8081``. If
                               no protocol is specified,
                               ``Node.DEFAULT_PROTOCOL`` is assumed. If a final
                               slash is included, it is ignored.
        :type node_reference: str
        :param u: The username for the given node's Web user interface.
        :type u: str
        :param p: The password for the given node's Web user interface.
        :type p: str
        """
        super().__init__()
        if '://' not in node_reference:
            node_reference = f'{Node.DEFAULT_PROTOCOL}://{node_reference}'
        if node_reference.endswith('/'):
            node_reference = node_reference[:-1]
        self._url: str = node_reference
        self._basic: str = b64encode(f'{u}:{p}'.encode('utf-8')).decode('utf-8')

    def authenticate(self, req: Request) -> None:
        """
        Does what is necessary to authenticate with the given ``Request``
        object.

        :param req: A ``Request`` instance.
        :type req: Request
        """
        req.add_header('Authorization', f'Basic {self._basic}')

    def get_url(self) -> str:
        """
        Returns the full URL corresponding to this node (with protocol but no
        final slash).

        :return: The full URL corresponding to this node.
        :rtype: str
        """
        return self._url


def check_substance(node: Node, auid: str) -> RequestUrlOpenT:
    """
    Performs the DebugPanel servlet "Check Substance" operation on the given
    node for the given AUID.

    :param node: A ``Node`` instance.
    :type node: Node
    :param auid: An AUID.
    :type auid: str
    :return: The result of ``urllib.request.urlopen``.
    :rtype: RequestUrlOpenT
    :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
    """
    return _auid_action(node, auid, 'Check Substance')


def crawl(node: Node, auid: str) -> RequestUrlOpenT:
    """
    Performs the DebugPanel servlet "Force Start Crawl" operation on the given
    node for the given AUID.

    :param node: A ``Node`` instance.
    :type node: Node
    :param auid: An AUID.
    :type auid: str
    :return: The result of ``urllib.request.urlopen``.
    :rtype: RequestUrlOpenT
    :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
    """
    return _auid_action(node, auid, 'Force Start Crawl')


def crawl_plugins(node: Node) -> RequestUrlOpenT:
    """
    Performs the DebugPanel servlet "Crawl Plugins" operation on the given
    node.

    :param node: A ``Node`` instance.
    :type node: Node
    :return: The result of ``urllib.request.urlopen``.
    :rtype: RequestUrlOpenT
    :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
    """
    return _node_action(node, 'Crawl Plugins')


def deep_crawl(node: Node, auid: str, depth: int=DEFAULT_DEPTH) -> RequestUrlOpenT:
    """
    Performs the DebugPanel servlet "Force Deep Crawl" operation on the given
    node for the given AUID, with the given depth (default ``DEFAULT_DEPTH``).

    :param node: A ``Node`` instance.
    :type node: Node
    :param auid: An AUID.
    :type auid: str
    :param depth: A strictly positive refetch depth.
    :type auid: int
    :return: The result of ``urllib.request.urlopen``.
    :rtype: RequestUrlOpenT
    :raises ValueError: If depth is negative or zero.
    :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
    """
    if depth < 1:
        raise ValueError(f'depth must be a strictly positive integer, got {depth}')
    return _auid_action(node, auid, 'Force Deep Crawl', depth=depth)


def disable_indexing(node: Node, auid: str) -> RequestUrlOpenT:
    """
    Performs the DebugPanel servlet "Disable Indexing" operation on the given
    node for the given AUID.

    :param node: A ``Node`` instance.
    :type node: Node
    :param auid: An AUID.
    :type auid: str
    :return: The result of ``urllib.request.urlopen``.
    :rtype: RequestUrlOpenT
    :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
    """
    return _auid_action(node, auid, 'Disable Indexing')


def node(node_reference: str, u: str, p: str) -> Node:
    """
    DEPRECATED: Constructs a new ``Node`` instance (see the ``Node``
    constructor); THIS FUNCTION WILL BE REMOVED IN VERSION 0.9.0.

    :param node_reference: See the ``Node`` constructor.
    :type node_reference: str
    :param u: See the ``Node`` constructor.
    :type node_reference: str
    :param p: See the ``Node`` constructor.
    :type node_reference: str
    :return: See the ``Node`` constructor.
    :rtype: Node
    """
    return Node(node_reference, u, p)


def poll(node: Node, auid: str) -> RequestUrlOpenT:
    """
    Performs the DebugPanel servlet "Start V3 Poll" operation on the given
    node for the given AUID.

    :param node: A ``Node`` instance.
    :type node: Node
    :param auid: An AUID.
    :type auid: str
    :return: The result of ``urllib.request.urlopen``.
    :rtype: RequestUrlOpenT
    :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
    """
    return _auid_action(node, auid, 'Start V3 Poll')


def reindex_metadata(node: Node, auid: str) -> RequestUrlOpenT:
    """
    Performs the DebugPanel servlet "Force Reindex Metadata" operation on the
    given node for the given AUID.

    :param node: A ``Node`` instance.
    :type node: Node
    :param auid: An AUID.
    :type auid: str
    :return: The result of ``urllib.request.urlopen``.
    :rtype: RequestUrlOpenT
    :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
    """
    return _auid_action(node, auid, 'Force Reindex Metadata')


def reload_config(node: Node) -> RequestUrlOpenT:
    """
    Performs the DebugPanel servlet "Reload Config" operation on the given
    node.

    :param node: A ``Node`` instance.
    :type node: Node
    :return: The result of ``urllib.request.urlopen``.
    :rtype: RequestUrlOpenT
    :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
    """
    return _node_action(node, 'Reload Config')


def validate_files(node: Node, auid: str) -> RequestUrlOpenT:
    """
    Performs the DebugPanel servlet "Validate Files" operation on the given
    node for the given AUID.

    :param node: A ``Node`` instance.
    :type node: Node
    :param auid: An AUID.
    :type auid: str
    :return: The result of ``urllib.request.urlopen``.
    :rtype: RequestUrlOpenT
    :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
    """
    return _auid_action(node, auid, 'Validate Files')


def _auid_action(node: Node, auid: str, action: str, **kwargs) -> RequestUrlOpenT:
    """
    Performs one AUID-centric action.

    :param node: A ``Node`` instance.
    :type node: Node
    :param auid: An AUID.
    :type auid: str
    :param action: An AUID-oriented DebugPanel servlet action string, e.g.
                   ``Force Deep Crawl``.
    :type action: str
    :param kwargs: Key-value pairs of additional query string arguments.
    :type kwargs: Dict[str, Any]
    :return: The result of calling `urllib.request.urlopen`` on an appropriate
             URL.
    :rtype: RequestUrlOpenT
    :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
    """
    action_encoded = action.replace(" ", "%20")
    auid_encoded = auid.replace('%', '%25').replace('|', '%7C').replace('&', '%26').replace('~', '%7E')
    req = _make_request(node, f'action={action_encoded}&auid={auid_encoded}', **kwargs)
    return urlopen(req)


def _make_request(node: Node, query: str, **kwargs) -> Request:
    """
    Constructs and authenticates an HTTP request.

    :param node: A ``Node`` instance.
    :type node: Node
    :param query: A primary ampersand-separated query string, e.g.
                  ``"action=MyAction&auid=MyAuid"``.
    :type query: str
    :param kwargs: Key-value pairs of additional query string arguments, e.g.
                   ``(..., depth=99)`` to add ``"&depth=99"``.
    :type kwargs: Dict[str, Any]
    :return: An authenticated ``Request`` instance (before
             ``urllib.request.urlopen`` is called).
    :rtype: Request
    """
    for key, val in kwargs.items():
        query = f'{query}&{key}={val}'
    url = f'{node.get_url()}/DebugPanel?{query}'
    req: Request = Request(url)
    node.authenticate(req)
    return req


def _node_action(node: Node, action: str, **kwargs) -> RequestUrlOpenT:
    """
    Performs one node-centric action.

    :param node: A ``Node`` instance.
    :type node: Node
    :param action: A node-oriented DebugPanel servlet action string, e.g.
                   ``Reload Config``.
    :type action: str
    :param kwargs: Key-value pairs of additional query string arguments, e.g.
                   ``(..., depth=99)`` to add ``"&depth=99"``.
    :type kwargs: Dict[str, Any]
    :return: The result of calling `urllib.request.urlopen`` on an appropriate
             URL.
    :rtype: RequestUrlOpenT
    :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
    """
    action_encoded = action.replace(" ", "%20")
    req = _make_request(node, f'action={action_encoded}', **kwargs)
    return urlopen(req)
