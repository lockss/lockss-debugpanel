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

from concurrent.futures import as_completed, Executor, ProcessPoolExecutor, ThreadPoolExecutor
from enum import Enum
from tabulate import tabulate
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

from lockss.pybasic.errorutil import InternalError

import lockss.debugpanel


class JobPool(Enum):
    THREAD_POOL = 'thread-pool'
    PROCESS_POOL = 'process-pool'

    @staticmethod
    def from_member(name: str):
        return JobPool[name.lower()]

    @staticmethod
    def from_option(name: str):
        return JobPool(str.replace('-', '_'))


def _crawl_plugins(node_object):
    return _node_action(node_object, 'Crawl Plugins')


def _make_request(node_object, query, **kwargs):
    for key, val in kwargs.items():
        query = f'{query}&{key}={val}'
    url = f'{node_object.get_url()}/DebugPanel?{query}'
    req = Request(url)
    node_object.authenticate(req)
    return req


def _node_action(node_object, action, **kwargs):
    action_encoded = action.replace(' ', '%20')
    req = _make_request(node_object, f'action={action_encoded}', **kwargs)
    try:
        ret = urlopen(req)
        return ret.status, ret.reason
    except Exception as exc:
        raise Exception(str(exc)).with_traceback(exc.__traceback__)


def _reload_config(node_object):
    return _node_action(node_object, 'Reload Config')


class DebugPanelApp(object):

    DEFAULT_POOL_TYPE: JobPool = JobPool.THREAD_POOL
    DEFAULT_POOL_SIZE: Optional[int] = None

    def __init__(self) -> None:
        super().__init__()
        self._auids: List[str] = list()
        self._auth = None # FIXME
        self._executor: Optional[Executor] = None
        self._pool_size: Optional[int] = DebugPanelApp.DEFAULT_POOL_SIZE
        self._pool_type: JobPool = DebugPanelApp.DEFAULT_POOL_TYPE
        self._nodes: List[str] = list()

    def add_auids(self, *auids: str):
        self._auids.extend(auids)
        return self

    def add_nodes(self, *nodes: str):
        self._nodes.extend(nodes)
        return self

    def set_pool_size(self, pool_size: Optional[int]):
        if pool_size and pool_size <= 0:
            raise ValueError(f'pool size: expected positive value or None, got {pool_size}')
        self._pool_size = pool_size
        return self

    def set_pool_type(self, job_pool: JobPool):
        self._pool_type = job_pool
        return self

    def crawl_plugins(self):
        self._per_node(_crawl_plugins)

    def reload_config(self):
        pass

    def _initialize_executor(self):
        if self._pool_type == JobPool.THREAD_POOL:
            self._executor = ThreadPoolExecutor(max_workers=self._pool_size)
        elif self._pool_type == JobPool.PROCESS_POOL:
            self._executor = ProcessPoolExecutor(max_workers=self._pool_size)
        else:
            raise InternalError()

    def _per_node(self, per_node_func):
        self._initialize_executor()
        node_objects = [lockss.debugpanel.node(node, *self._auth) for node in self._nodes]
        futures = {self._executor.submit(per_node_func, node_object): node for node, node_object in zip(self._nodes, node_objects)}
        results: Dict[str, Any] = {}
        for future in as_completed(futures):
            node = futures[future]
            try:
                res = future.result()
                status, reason = res
                results[node] = 'Requested' if status == 200 else reason
            except Exception as exc:
                #if self._args.verbose:
                #    traceback.print_exc()
                results[node] = exc
        # Output
        print(tabulate([[node, results[node]] for node in self._nodes],
                       headers=['Node', 'Result']))
