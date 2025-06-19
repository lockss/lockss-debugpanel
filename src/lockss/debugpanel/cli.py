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

from collections.abc import Callable
from concurrent.futures import Executor, Future, ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from enum import Enum
from getpass import getpass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic.v1 import BaseModel, Field, FilePath, root_validator, validator
from pydantic.v1.types import PositiveInt
from tabulate import tabulate

from lockss.pybasic.cliutil import BaseCli, StringCommand, at_most_one_from_enum, get_from_enum, COPYRIGHT_DESCRIPTION, LICENSE_DESCRIPTION, VERSION_DESCRIPTION
from lockss.pybasic.errorutil import InternalError
from lockss.pybasic.fileutil import file_lines, path
from lockss.pybasic.outpututil import OutputFormatOptions
from . import Node, check_substance, crawl, crawl_plugins, deep_crawl, disable_indexing, poll, reload_config, reindex_metadata, validate_files, DEFAULT_DEPTH, __copyright__, __license__, __version__


class JobPool(Enum):
    thread_pool = 'thread-pool'
    process_pool = 'process-pool'

    @staticmethod
    def from_option(name: str):
        return JobPool(name.replace('-', '_'))


DEFAULT_POOL_SIZE: Optional[int] = None
DEFAULT_POOL_TYPE: JobPool = JobPool.thread_pool


class NodesOptions(BaseModel):
    node: Optional[List[str]] = Field([], aliases=['-n'], description='[nodes] add one or more nodes to the set of nodes to process')
    nodes: Optional[List[FilePath]] = Field([], aliases=['-N'], description='[nodes] add the nodes listed in one or more files to the set of nodes to process')
    password: Optional[str] = Field(aliases=['-p'], description='[nodes] UI password; interactive prompt if not specified')
    username: Optional[str] = Field(aliases=['-u'], description='[nodes] UI username; interactive prompt if not unspecified')

    @validator('nodes', each_item=True, pre=True)
    def _expand_each_nodes_path(cls, v: Path):
        return path(v)

    def get_nodes(self):
        ret = [*self.node[:], *[file_lines(file_path) for file_path in self.nodes]]
        if len(ret) == 0:
            raise RuntimeError('empty list of nodes')
        return ret


class AuidsOptions(BaseModel):
    auid: Optional[List[str]] = Field([], aliases=['-a'], description='[AUIDs] add one or more AUIDs to the set of AUIDs to process')
    auids: Optional[List[FilePath]] = Field([], aliases=['-A'], description='[AUIDs] add the AUIDs listed in one or more files to the set of AUIDs to process')

    @validator('auids', each_item=True, pre=True)
    def _expand_each_auids_path(cls, v: Path):
        return path(v)

    def get_auids(self):
        ret = [*self.auid[:], *[file_lines(file_path) for file_path in self.auids]]
        if len(ret) == 0:
            raise RuntimeError('empty list of AUIDs')
        return ret


class DepthOptions(BaseModel):
    depth: Optional[int] = Field(DEFAULT_DEPTH, aliases=['-d'], description='[deep crawl] set crawl depth')


class JobPoolOptions(BaseModel):
    pool_size: Optional[PositiveInt] = Field(description='[job pool] set the job pool size')
    process_pool: Optional[bool] = Field(False, description='[job pool] use a process pool', enum=JobPool)
    thread_pool: Optional[bool] = Field(False, description='[job pool] use a thread pool', enum=JobPool)

    @root_validator
    def _at_most_one_pool_type(cls, values):
        return at_most_one_from_enum(cls, values, JobPool)

    def get_pool_size(self) -> Optional[int]:
        return self.pool_size if hasattr(self, 'pool_size') else DEFAULT_POOL_SIZE

    def get_pool_type(self) -> JobPool:
        return get_from_enum(self, JobPool, DEFAULT_POOL_TYPE)


class NodeCommand(OutputFormatOptions, JobPoolOptions, NodesOptions): pass
class AuidCommand(NodeCommand, OutputFormatOptions, JobPoolOptions, AuidsOptions, NodesOptions): pass
class DeepCrawlCommand(AuidCommand, OutputFormatOptions, JobPoolOptions, DepthOptions, AuidsOptions, NodesOptions): pass


class DebugPanelCommand(BaseModel):
    check_substance: Optional[AuidCommand] = Field(description='cause nodes to check the substance of AUs', alias='check-substance')
    copyright: Optional[StringCommand.type(__copyright__)] = Field(description=COPYRIGHT_DESCRIPTION)
    cp: Optional[NodeCommand] = Field(description='synonym for: crawl-plugins')
    cr: Optional[AuidCommand] = Field(description='synonym for: crawl')
    crawl: Optional[AuidCommand] = Field(description='cause nodes to crawl AUs')
    crawl_plugins: Optional[NodeCommand] = Field(description='cause nodes to crawl plugins', alias='crawl-plugins')
    cs: Optional[AuidCommand] = Field(description='synonym for: check-substance')
    dc: Optional[DeepCrawlCommand] = Field(description='synonym for: deep-crawl')
    deep_crawl: Optional[DeepCrawlCommand] = Field(description='cause nodes to deeply crawl AUs', alias='deep-crawl')
    di: Optional[AuidCommand] = Field(description='synonym for: disable-indexing')
    disable_indexing: Optional[AuidCommand] = Field(description='cause nodes to disable indexing for AUs', alias='disable-indexing')
    license: Optional[StringCommand.type(__license__)] = Field(description=LICENSE_DESCRIPTION)
    po: Optional[AuidCommand] = Field(description='synonym for: poll')
    poll: Optional[AuidCommand] = Field(description='cause nodes to poll AUs')
    rc: Optional[NodeCommand] = Field(description='synonym for: reload-config')
    reindex_metadata: Optional[AuidCommand] = Field(description='cause nodes to reindex the metadata of AUs', alias='reindex-metadata')
    reload_config: Optional[NodeCommand] = Field(description='cause nodes to reload their configuration', alias='reload-config')
    ri: Optional[AuidCommand] = Field(description='synonym for: reindex-metadata')
    validate_files: Optional[AuidCommand] = Field(description='cause nodes to validate the files of AUs', alias='validate-files')
    vf: Optional[AuidCommand] = Field(description='synonym for: validate-files')
    version: Optional[StringCommand.type(__version__)] = Field(description=VERSION_DESCRIPTION)


class DebugPanelCli(BaseCli[DebugPanelCommand]):

    def __init__(self):
        super().__init__(model=DebugPanelCommand,
                         prog='debugpanel',
                         description='Tool to interact with the LOCKSS 1.x DebugPanel servlet')
        self._auids: Optional[List[str]] = None
        self._auth: Optional[Any] = None
        self._executor: Optional[Executor] = None
        self._nodes: Optional[List[str]] = None

    def _check_substance(self, auid_command: AuidCommand) -> None:
        self._do_auid_command(auid_command, check_substance)

    def _copyright(self, string_command: StringCommand) -> None:
        self._do_string_command(string_command)

    def _cp(self, node_command: NodeCommand) -> None:
        self._crawl_plugins(node_command)

    def _cr(self, auid_command: AuidCommand) -> None:
        self._crawl(auid_command)

    def _crawl(self, auid_command: AuidCommand) -> None:
        self._do_auid_command(auid_command, crawl)

    def _crawl_plugins(self, node_command: NodeCommand) -> None:
        self._do_node_command(node_command, crawl_plugins)

    def _cs(self, auid_command: AuidCommand) -> None:
        self._check_substance(auid_command)

    def _dc(self, deep_crawl_command: DeepCrawlCommand) -> None:
        self._deep_crawl(deep_crawl_command)

    def _deep_crawl(self, deep_crawl_command: DeepCrawlCommand) -> None:
        self._do_auid_command(deep_crawl_command, deep_crawl, depth=deep_crawl_command.depth)

    def _di(self, auid_command: AuidCommand) -> None:
        self._disable_indexing(auid_command)

    def _disable_indexing(self, auid_command: AuidCommand) -> None:
        self._do_auid_command(auid_command, disable_indexing)

    def _do_auid_command(self, auid_command: AuidCommand, node_auid_func: Callable[[Node, str], Any], **kwargs) -> None:
        self._initialize_auth(auid_command)
        self._initialize_executor(auid_command)
        self._nodes = auid_command.get_nodes()
        self._auids = auid_command.get_auids()
        node_objects = [Node(node, *self._auth) for node in self._nodes]
        futures: Dict[Future, Tuple[str, str]] = {self._executor.submit(node_auid_func, node_object, auid, **kwargs): (node, auid) for auid in self._auids for node, node_object in zip(self._nodes, node_objects)}
        results: Dict[Tuple[str, str], Any] = {}
        for future in as_completed(futures):
            node_auid = futures[future]
            try:
                resp = future.result()
                status, reason = resp.status, resp.reason
                results[node_auid] = 'Requested' if status == 200 else reason
            except Exception as exc:
                results[node_auid] = exc
        print(tabulate([[auid, *[results[(node, auid)] for node in self._nodes]] for auid in self._auids],
                       headers=['AUID', *self._nodes],
                       tablefmt=auid_command.output_format))

    def _do_node_command(self, node_command: NodeCommand, node_func: Callable[[Node], Any], **kwargs) -> None:
        self._initialize_auth(node_command)
        self._initialize_executor(node_command)
        self._nodes = node_command.get_nodes()
        node_objects = [Node(node, *self._auth) for node in self._nodes]
        futures: Dict[Future, str] = {self._executor.submit(node_func, node_object): node for node, node_object in zip(self._nodes, node_objects)}
        results: Dict[str, Any] = {}
        for future in as_completed(futures):
            node = futures[future]
            try:
                resp = future.result()
                status, reason = resp.status, resp.reason
                results[node] = 'Requested' if status == 200 else reason
            except Exception as exc:
                results[node] = exc
        print(tabulate([[node, results[node]] for node in self._nodes],
                       headers=['Node', 'Result'],
                       tablefmt=node_command.output_format))

    def _do_string_command(self, string_command: StringCommand) -> None:
        string_command()

    def _initialize_auth(self, nodes_options: NodesOptions):
        _u = nodes_options.username or input('UI username: ')
        _p = nodes_options.password or getpass('UI password: ')
        self._auth = (_u, _p)

    def _initialize_executor(self, job_pool_options: JobPoolOptions):
        if job_pool_options.get_pool_type() == JobPool.thread_pool:
            self._executor = ThreadPoolExecutor(max_workers=job_pool_options.get_pool_size())
        elif job_pool_options.get_pool_type() == JobPool.process_pool:
            self._executor = ProcessPoolExecutor(max_workers=job_pool_options.get_pool_size())
        else:
            raise InternalError()

    def _license(self, string_command: StringCommand) -> None:
        self._do_string_command(string_command)

    def _po(self, auid_command: AuidCommand) -> None:
        self._poll(auid_command)

    def _poll(self, auid_command: AuidCommand) -> None:
        self._do_auid_command(auid_command, poll)

    def _rc(self, node_command: NodeCommand):
        self._reload_config(node_command)

    def _reload_config(self, node_command: NodeCommand):
        self._do_node_command(node_command, reload_config)

    def _validate_files(self, auid_command: AuidCommand) -> None:
        self._do_auid_command(auid_command, validate_files)

    def _vf(self, auid_command: AuidCommand) -> None:
        self._validate_files(auid_command)

    def _version(self, string_command: StringCommand) -> None:
        self._do_string_command(string_command)

def main():
    DebugPanelCli().run()


if __name__ == '__main__':
    main()
