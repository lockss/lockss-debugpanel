#!/usr/bin/env python3

# Copyright (c) 2000-2026, Board of Trustees of Leland Stanford Jr. University
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

from abc import ABC, abstractmethod
from base64 import b64encode
from typing import Any, Optional, TypeAlias
from urllib.request import Request, urlopen

from lockss.pybasic.errorutil import InternalError
from lockss.pybasic.nodeutil import NodeIdentifier, NodeSpec, NodeTypeEnum


#: A type alias for what ``urllib.request.urlopen`` returns.
UrlOpenT: TypeAlias = Any


#: A default depth for the deep crawl operation.
DEFAULT_DEPTH: int = 123


class _DebugPanelClientInterface(ABC):
    """
    Abstract base class for DebugPanel servlet clients.
    """

    @abstractmethod
    def authenticate(self, u: str, p: str) -> _DebugPanelClientInterface:
        """
        Stores authentication information for this node.

        :param u: The UI username.
        :type u: str
        :param p: The UI password.
        :type p: str
        :return: This instance, for chaining.
        :rtype: _DebugPanelClientInterface
        """
        raise NotImplementedError

    @abstractmethod
    def check_substance(self, auid: str) -> UrlOpenT:
        """
        Performs the DebugPanel servlet "Check Substance" operation on this node
        for the given AUID.

        :param auid: An AUID.
        :type auid: str
        :return: The result of ``urllib.request.urlopen``.
        :rtype: UrlOpenT
        :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
        """
        raise NotImplementedError

    @abstractmethod
    def crawl(self, auid: str) -> UrlOpenT:
        """
        Performs the DebugPanel servlet "Force Start Crawl" operation on this
        node for the given AUID.

        :param auid: An AUID.
        :type auid: str
        :return: The result of ``urllib.request.urlopen``.
        :rtype: UrlOpenT
        :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
        """
        raise NotImplementedError

    @abstractmethod
    def crawl_plugins(self) -> UrlOpenT:
        """
        Performs the DebugPanel servlet "Crawl Plugins" operation on this node.

        :return: The result of ``urllib.request.urlopen``.
        :rtype: UrlOpenT
        :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
        """
        raise NotImplementedError

    @abstractmethod
    def deep_crawl(self, auid: str, depth: int = DEFAULT_DEPTH) -> UrlOpenT:
        """
        Performs the DebugPanel servlet "Force Deep Crawl" operation on this
        node for the given AUID, with the given depth (default
        ``DEFAULT_DEPTH``).

        :param auid: An AUID.
        :type auid: str
        :param depth: A strictly positive refetch depth.
        :type auid: int
        :return: The result of ``urllib.request.urlopen``.
        :rtype: UrlOpenT
        :raises ValueError: If depth is negative or zero.
        :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
        """
        raise NotImplementedError

    @abstractmethod
    def disable_indexing(self, auid: str) -> UrlOpenT:
        """
        Performs the DebugPanel servlet "Disable Indexing" operation on this
        node for the given AUID.

        :param auid: An AUID.
        :type auid: str
        :return: The result of ``urllib.request.urlopen``.
        :rtype: UrlOpenT
        :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
        """
        raise NotImplementedError

    @abstractmethod
    def poll(self, auid: str) -> UrlOpenT:
        """
        Performs the DebugPanel servlet "Start V3 Poll" operation on this node
        for the given AUID.

        :param auid: An AUID.
        :type auid: str
        :return: The result of ``urllib.request.urlopen``.
        :rtype: UrlOpenT
        :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
        """
        raise NotImplementedError

    @abstractmethod
    def reindex_metadata(self, auid: str) -> UrlOpenT:
        """
        Performs the DebugPanel servlet "Force Reindex Metadata" operation on
        this node for the given AUID.

        :param auid: An AUID.
        :type auid: str
        :return: The result of ``urllib.request.urlopen``.
        :rtype: UrlOpenT
        :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
        """
        raise NotImplementedError

    @abstractmethod
    def reload_config(self) -> UrlOpenT:
        """
        Performs the DebugPanel servlet "Reload Config" operation on this node.

        :return: The result of ``urllib.request.urlopen``.
        :rtype: UrlOpenT
        :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
        """
        raise NotImplementedError

    @abstractmethod
    def validate_files(self, auid: str) -> UrlOpenT:
        """
        Performs the DebugPanel servlet "Validate Files" operation on this node
        for the given AUID.

        :param auid: An AUID.
        :type auid: str
        :return: The result of ``urllib.request.urlopen``.
        :rtype: UrlOpenT
        :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
        """
        raise NotImplementedError


class _DebugPanelClient1(_DebugPanelClientInterface):
    """
    _DebugPAnelAdapter implementation for LOCKSS 1.x.
    """

    def __init__(self, client: DebugPanelClient) -> None:
        super().__init__()
        self._client: DebugPanelClient = client
        self._basic: Optional[str] = None

    def authenticate(self, u: str, p: str) -> _DebugPanelClient1:
        self._basic: str = b64encode(f'{u}:{p}'.encode('utf-8')).decode('utf-8')
        return self

    def check_substance(self, auid: str) -> UrlOpenT:
        return self._auid_action(auid, 'Check Substance')

    def crawl(self, auid: str) -> UrlOpenT:
        return self._auid_action(auid, 'Force Start Crawl')

    def crawl_plugins(self) -> UrlOpenT:
        return self._node_action('Crawl Plugins')

    def deep_crawl(self, auid: str, depth: int = DEFAULT_DEPTH) -> UrlOpenT:
        if depth < 1:
            raise ValueError(f'depth must be a strictly positive integer, got {depth}')
        return self._auid_action(auid, 'Force Deep Crawl', depth=depth)

    def disable_indexing(self, auid: str) -> UrlOpenT:
        return self._auid_action(auid, 'Disable Indexing')

    def poll(self, auid: str) -> UrlOpenT:
        return self._auid_action(auid, 'Start V3 Poll')

    def reindex_metadata(self, auid: str) -> UrlOpenT:
        return self._auid_action(auid, 'Force Reindex Metadata')

    def reload_config(self) -> UrlOpenT:
        return self._node_action('Reload Config')

    def validate_files(self, auid: str) -> UrlOpenT:
        return self._auid_action(auid, 'Validate Files')

    def _auid_action(self, auid: str, action: str, **kwargs) -> UrlOpenT:
        """
        Performs one AUID-centric action.

        :param auid: An AUID.
        :type auid: str
        :param action: An AUID-oriented DebugPanel servlet action string, e.g.
                       ``Force Deep Crawl``.
        :type action: str
        :param kwargs: Key-value pairs of additional query string arguments.
        :type kwargs: dict[str, Any]
        :return: The result of calling `urllib.request.urlopen`` on an appropriate
                 URL.
        :rtype: RequestUrlOpenT
        :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
        """
        action_encoded = action.replace(" ", "%20")
        auid_encoded = auid.replace('%', '%25').replace('|', '%7C').replace('&', '%26').replace('~', '%7E')
        req = self._make_request(f'action={action_encoded}&auid={auid_encoded}', **kwargs)
        return urlopen(req)

    def _make_request(self, query: str, **kwargs) -> Request:
        """
        Constructs and authenticates an HTTP request.

        :param query: A primary ampersand-separated query string, e.g.
                      ``"action=MyAction&auid=MyAuid"``.
        :type query: str
        :param kwargs: Key-value pairs of additional query string arguments, e.g.
                       ``(..., depth=99)`` to add ``"&depth=99"``.
        :type kwargs: dict[str, Any]
        :return: An authenticated ``Request`` instance (before
                 ``urllib.request.urlopen`` is called).
        :rtype: Request
        """
        for key, val in kwargs.items():
            query = f'{query}&{key}={val}'
        url: str = f'{(ns := self._client._node_spec).protocol.value}://{ns.host}:{ns.ui}/DebugPanel?{query}'
        req: Request = Request(url)
        req.add_header('Authorization', f'Basic {self._basic}')
        return req

    def _node_action(self, action: str, **kwargs) -> UrlOpenT:
        """
        Performs one node-centric action.

        :param action: A node-oriented DebugPanel servlet action string, e.g.
                       ``Reload Config``.
        :type action: str
        :param kwargs: Key-value pairs of additional query string arguments, e.g.
                       ``(..., depth=99)`` to add ``"&depth=99"``.
        :type kwargs: dict[str, Any]
        :return: The result of calling `urllib.request.urlopen`` on an appropriate
                 URL.
        :rtype: RequestUrlOpenT
        :raises Exception: Whatever ``urllib.request.urlopen`` might raise.
        """
        action_encoded: str = action.replace(" ", "%20")
        req: Request = self._make_request(f'action={action_encoded}', **kwargs)
        return urlopen(req)


class _DebugPanelClient2(_DebugPanelClientInterface):
    """
    _DebugPAnelAdapter implementation for LOCKSS 2.x, which raises
    ``NotImplementedError`` for everything.
    """

    def authenticate(self, u: str, p: str) -> _DebugPanelClient2:
        raise NotImplementedError

    def check_substance(self, auid: str) -> UrlOpenT:
        raise NotImplementedError

    def crawl(self, auid: str) -> UrlOpenT:
        raise NotImplementedError

    def crawl_plugins(self) -> UrlOpenT:
        raise NotImplementedError

    def deep_crawl(self, auid: str, depth: int = DEFAULT_DEPTH) -> UrlOpenT:
        raise NotImplementedError

    def disable_indexing(self, auid: str) -> UrlOpenT:
        raise NotImplementedError

    def poll(self, auid: str) -> UrlOpenT:
        raise NotImplementedError

    def reindex_metadata(self, auid: str) -> UrlOpenT:
        raise NotImplementedError

    def reload_config(self) -> UrlOpenT:
        raise NotImplementedError

    def validate_files(self, auid: str) -> UrlOpenT:
        raise NotImplementedError


class DebugPanelClient(_DebugPanelClientInterface):
    """
    A DebugPanel servlet client for either LOCKSS 1.x or 2.x.
    """

    def __init__(self, node_spec: NodeSpec):
        self._node_spec: NodeSpec = node_spec
        match typ := node_spec.type:
            case NodeTypeEnum.V1.value:
                self._impl: _DebugPanelClientInterface = _DebugPanelClient1(self)
            case NodeTypeEnum.V2.value:
                self._impl: _DebugPanelClientInterface = _DebugPanelClient2()
            case _:
                raise InternalError from ValueError(typ)

    def authenticate(self, u: str, p: str) -> DebugPanelClient:
        self._impl.authenticate(u, p)
        return self

    def check_substance(self, auid: str) -> UrlOpenT:
        return self._impl.check_substance(auid)

    def crawl(self, auid: str) -> UrlOpenT:
        return self._impl.crawl(auid)

    def crawl_plugins(self) -> UrlOpenT:
        return self._impl.crawl_plugins()

    def deep_crawl(self, auid: str, depth: int = DEFAULT_DEPTH) -> UrlOpenT:
        return self._impl.deep_crawl(auid, depth=depth)

    def disable_indexing(self, auid: str) -> UrlOpenT:
        return self._impl.disable_indexing(auid)

    def get_id(self) -> NodeIdentifier:
        """
        Returns this client's node identifier, from the node spec.

        :return: This client's node identifier.
        :rtype: NodeIdentifier
        """
        return self.get_node_spec().id

    def get_node_spec(self) -> NodeSpec:
        """
        Returns this client's node spec.

        :return: This client's node spec.
        :rtype: NodeSpec
        """
        return self._node_spec.model_copy()

    def poll(self, auid: str) -> UrlOpenT:
        return self._impl.poll(auid)

    def reindex_metadata(self, auid: str) -> UrlOpenT:
        return self._impl.reindex_metadata(auid)

    def reload_config(self) -> UrlOpenT:
        return self._impl.reload_config()

    def validate_files(self, auid: str) -> UrlOpenT:
        return self._impl.validate_files(auid)
