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
from getpass import getpass
from pathlib import Path
from typing import List, Optional

from pydantic.v1 import BaseModel, Field, FilePath, root_validator, validator
from pydantic.v1.types import PositiveInt
import tabulate


from lockss.pybasic.cliutil import BaseCli, StringCommand, at_most_one_from_enum, get_from_enum, COPYRIGHT_DESCRIPTION, LICENSE_DESCRIPTION, VERSION_DESCRIPTION
from lockss.pybasic.fileutil import file_lines, path
from lockss.debugpanel import __copyright__, __license__, __version__
from .app import DebugPanelApp, JobPool


_DEFAULT_OUTPUT_FORMAT = 'simple'


class NodesOptions(BaseModel):
    node: Optional[List[str]] = Field([], aliases=['-n'], description='[nodes] add one or more nodes to the list of nodes to process')
    nodes: Optional[List[FilePath]] = Field([], aliases=['-N'], description='[nodes] add the nodes in one or more files to the list of nodes to process')
    password: Optional[str] = Field(aliases=['-p'], description='[nodes] UI password; interactive prompt if unspecified')
    username: Optional[str] = Field(aliases=['-u'], description='[nodes] UI username; interactive prompt if unspecified')

    @validator('nodes', each_item=True, pre=True)
    def _expand_each_nodes_path(cls, v: Path):
        return path(v)

    def get_nodes(self):
        ret = [*self.node[:], *[file_lines(file_path) for file_path in self.nodes]]
        if len(ret) == 0:
            raise RuntimeError('empty list of nodes')
        return ret


class AuidsOptions(BaseModel):
    auid: Optional[List[str]] = Field([], aliases=['-a'], description='[AUIDs] add one or more AUIDs to the list of AUIDs to process')
    auids: Optional[List[FilePath]] = Field([], aliases=['-A'], description='[AUIDs] add the AUIDs in one or more files to the list of AUIDs to process')

    @validator('auids', each_item=True, pre=True)
    def _expand_each_auids_path(cls, v: Path):
        return path(v)

    def get_auids(self):
        ret = [*self.auid[:], *[file_lines(file_path) for file_path in self.auids]]
        if len(ret) == 0:
            raise RuntimeError('empty list of AUIDs')
        return ret


class DepthOptions(BaseModel):
    depth: Optional[int] = Field(DebugPanelApp.DEFAULT_DEPTH, aliases=['-d'], description='[deep crawl] set crawl depth')


class JobPoolOptions(BaseModel):
    pool_size: Optional[PositiveInt] = Field(description='[job pool] set the job pool size')
    process_pool: Optional[bool] = Field(False, description='[job pool] use a process pool', enum=JobPool)
    thread_pool: Optional[bool] = Field(False, description='[job pool] use a thread pool', enum=JobPool)

    @root_validator
    def _at_most_one_pool_type(cls, values):
        return at_most_one_from_enum(cls, values, JobPool)

    def get_pool_size(self) -> Optional[int]:
        return self.pool_size if hasattr(self, 'pool_size') else DebugPanelApp.DEFAULT_POOL_SIZE

    def get_pool_type(self) -> JobPool:
        return get_from_enum(self, JobPool, DebugPanelApp.DEFAULT_POOL_TYPE)


class OutputFormatOptions(BaseModel):
    debug_cli: Optional[bool] = Field(False, description='print the result of parsing command line arguments')
    output_format: Optional[str] = Field(_DEFAULT_OUTPUT_FORMAT, description=f'[output] set the output format; choices: {', '.join(tabulate.tabulate_formats)}')

    @validator('output_format')
    def _validate_output_format(cls, v: str):
        if v not in tabulate.tabulate_formats:
            raise ValueError(f'must be one of {', '.join(tabulate.tabulate_formats)}; got {v}')
        return v


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


class DebugPanelCli(DebugPanelApp, BaseCli[DebugPanelCommand]):

    def __init__(self):
        DebugPanelApp.__init__(self)
        BaseCli.__init__(self,
                         model=DebugPanelCommand,
                         prog='debugpanel',
                         description='Tool to interact with the LOCKSS 1.x DebugPanel servlet')

    def _check_substance(self, check_substance_command: AuidCommand) -> None:
        self._do_auid_command(check_substance_command, self.check_substance)

    def _copyright(self, copyright_model: StringCommand) -> None:
        self._do_string_command(copyright_model)

    def _cp(self, crawl_plugins_command: NodeCommand) -> None:
        self._crawl_plugins(crawl_plugins_command)

    def _cr(self, crawl_command: AuidCommand) -> None:
        self._crawl(crawl_command)

    def _crawl(self, crawl_command: AuidCommand) -> None:
        self._do_auid_command(crawl_command, self.crawl)

    def _crawl_plugins(self, crawl_plugins_model: NodeCommand) -> None:
        self._do_node_command(crawl_plugins_model, self.crawl_plugins)

    def _cs(self, check_substance_command: AuidCommand) -> None:
        self._check_substance(check_substance_command)

    def _dc(self, deep_crawl_command: DeepCrawlCommand) -> None:
        self._deep_crawl(deep_crawl_command)

    def _deep_crawl(self, deep_crawl_command: DeepCrawlCommand) -> None:
        self._do_auid_command(deep_crawl_command, self.deep_crawl, depth=deep_crawl_command.depth)

    def _di(self, disable_indexing_command: AuidCommand) -> None:
        self._disable_indexing(disable_indexing_command)

    def _disable_indexing(self, disable_indexing_command: AuidCommand) -> None:
        self._do_auid_command(disable_indexing_command, self.disable_indexing)

    def _do_auid_command(self, auid_command: AuidCommand, func: Callable, **kwargs) -> None:
        self.add_auids(*auid_command.get_auids())
        self._do_node_command(auid_command, func, **kwargs)

    def _do_node_command(self, nodes_command: NodeCommand, func: Callable, **kwargs) -> None:
        self.add_nodes(*nodes_command.get_nodes())
        self._initialize_auth(nodes_command)
        self.set_pool_size(nodes_command.get_pool_size())
        self.set_pool_type(nodes_command.get_pool_type())
        func(**kwargs)

    def _do_string_command(self, string_command: StringCommand) -> None:
        string_command.action()

    def _license(self, license_model: StringCommand) -> None:
        self._do_string_command(license_model)

    def _rc(self, node_command: NodeCommand):
        self._reload_config(node_command)

    def _reload_config(self, node_command: NodeCommand):
        self._do_node_command(node_command, self.reload_config)

    def _version(self, version_model: StringCommand) -> None:
        self._do_string_command(version_model)

    def _initialize_auth(self, nodes_model):
        # FIXME someday
        _u = nodes_model.username or input('UI username: ')
        _p = nodes_model.password or getpass('UI password: ')
        self._auth = (_u, _p)


def main():
    DebugPanelCli().run()


if __name__ == '__main__':
    main()
