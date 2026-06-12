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

"""
Command line tool to interact with the LOCKSS 1.x DebugPanel servlet.
"""

from collections.abc import Callable, Iterator
from concurrent.futures import Executor, Future, ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from dataclasses import dataclass, field
from enum import Enum
from importlib.metadata import entry_points
from inspect import ismethod
from itertools import chain
from pathlib import Path
from typing import Any, Optional, TypeAlias

from click_extra import ChoiceSource, EnumChoice, ExtraContext, Section, TableFormat, color_option, context, echo, group, jobs_option, option, option_group, pass_context, pass_obj, print_table, progressbar, prompt, show_params_option
from click_plugins import with_plugins
from cloup.constraints import mutually_exclusive
from pydantic import ValidationError
import yaml

from lockss.pybasic.cliutil import NonNegativeInt, click_path, compose_decorators, make_extra_context_settings, make_table_format_option
from lockss.pybasic.errorutil import InternalError
from lockss.pybasic.fileutil import file_lines
from lockss.pybasic.nodeutil import NodeIdentifier, NodeSet, get_node_spec_adapter

from . import Node, RequestUrlOpenT, check_substance, crawl, crawl_plugins, deep_crawl, disable_indexing, poll, reload_config, reindex_metadata, validate_files, DEFAULT_DEPTH, __copyright__, __license__, __version__
from ._core import DebugPanelClient, UrlOpenT


YamlT: TypeAlias = Any


class _JobPoolType(Enum):
    """An enum of job pool types."""
    THREAD_POOL = 'thread-pool'
    PROCESS_POOL = 'process-pool'


#: The default ``_JobPoolType``.
_DEFAULT_JOB_POOL_TYPE: _JobPoolType = _JobPoolType.THREAD_POOL


class _DebugPanelCli(object):
    """DebugPanel command line application."""

    @dataclass(kw_only=True)
    class _Opts:
        """Data class to hold parsed command line options."""
        # Node operation
        node_set: tuple[Path, ...] = ()
        node_spec: tuple[str, ...] = ()
        node_specs: tuple[Path, ...] = ()
        username: Optional[str] = None
        password: Optional[str] = field(default=None, repr=False)
        # AUID operation
        auid: tuple[str, ...] = ()
        auids: tuple[Path, ...] = ()
        # Depth
        depth: Optional[int] = None
        # Job pool
        pool_size: Optional[int] = None # DEPRECATED
        # Output
        headings: Optional[bool] = None
        progress: Optional[bool] = None

    def __init__(self, ctx: ExtraContext):
        """
        Constructor.

        :param ctx: The Click Extra context.
        :type ctx: ExtraContext
        """
        super().__init__()
        self._ctx: ExtraContext = ctx
        self._opts: Optional[_DebugPanelCli._Opts] = None
        self._auids: Optional[list[str]] = None
        self._executor: Optional[Executor] = None
        self._nodes: Optional[list[str]] = None
        self._clients: list[DebugPanelClient] = list()

    def check_substance(self) -> None:
        """Implementation of the ``check-substance`` command."""
        self._do_auid_command(check_substance)

    def crawl(self) -> None:
        """Implementation of the ``crawl`` command."""
        self._do_auid_command(crawl)

    def crawl_plugins(self) -> None:
        """Implementation of the ``crawl-plugins`` command."""
        self._do_node_command(DebugPanelClient.crawl_plugins)

    def deep_crawl(self) -> None:
        """Implementation of the ``deep-crawl`` command."""
        self._do_auid_command(deep_crawl, depth=self._opts.depth)

    def disable_indexing(self) -> None:
        """Implementation of the ``disable-indexing`` command."""
        self._do_auid_command(disable_indexing)

    def dispatch(self, method: Callable[[], None], **cli_kwargs) -> None:
        """
        Initializes from the given command line options and invokes the given
        (bound) method.

        :param method: A (bound) method.
        :type method: Callable[[], None]
        :param cli_kwargs: The command line arguments passed by Click Extra.
        :type cli_kwargs: dict[str, Any]
        """
        if not ismethod(method):
            raise InternalError() from ValueError(method)
        self._opts = _DebugPanelCli._Opts(**cli_kwargs)
        method()

    def poll(self) -> None:
        """Implementation of the ``poll`` command."""
        self._do_auid_command(poll)

    def reindex_metadata(self) -> None:
        """Implementation of the ``reindex-metadata`` command."""
        self._do_auid_command(reindex_metadata)

    def reload_config(self) -> None:
        """Implementation of the ``reload-config`` command."""
        self._do_node_command(DebugPanelClient.reload_config)

    def validate_files(self) -> None:
        """Implementation of the ``validate-files`` command."""
        self._do_auid_command(validate_files)

    def _do_auid_command(self,
                         node_auid_func: Callable[[Node, str], RequestUrlOpenT],
                         **kwargs) -> None:
        """
        Performs one AUID-centric command.

        :param node_auid_func: A function that applies to a ``Node`` and an AUID
                               and returns what ``urllib.request.urlopen``
                               returns.
        :type node_auid_func: Callable[[Node, str], RequestUrlOpenT]
        """
        self._initialize_auid_operation()
        opts = self._opts
        node_objects = [Node(node, opts.username, opts.password) for node in self._nodes]
        futures: dict[Future, tuple[str, str]] = {self._executor.submit(node_auid_func, node_object, auid, **kwargs): (node, auid) for auid in self._auids for node, node_object in zip(self._nodes, node_objects)}
        completed: Iterator[Future] = as_completed(futures)
        results: dict[tuple[str, str], Any] = {}
        with progressbar(completed, length=len(futures), label='Progress') if opts.progress else nullcontext(completed) as bar:
            for future in bar:
                node_auid = futures[future]
                try:
                    with future.result() as resp:
                        status: int = resp.status
                        reason: str = resp.reason
                        results[node_auid] = 'Requested' if status == 200 else reason
                except Exception as exc:
                    results[node_auid] = exc
        print_table([[auid, *[results[(node, auid)] for node in self._nodes]] for auid in self._auids],
                    headers=['AUID', *self._nodes] if opts.headings else None,
                    table_format=opts.table_format)

    def _do_node_command(self,
                         func_client: Callable[[DebugPanelClient], UrlOpenT],
                         **kwargs) -> None:
        """
        Performs one node-centric command.

        :param func_client: A function that applies to a ``Node`` and returns
                          what ``urllib.request.urlopen`` returns.
        :type func_client: Callable[[Node], RequestUrlOpenT]
        """
        self._initialize_node_operation()
        opts = self._opts
        #node_objects = [Node(node, opts.username, opts.password) for node in self._nodes]
        #futures: dict[Future, str] = {self._executor.submit(node_func, node_object, **kwargs): node for node, node_object in zip(self._nodes, node_objects)}
        futures: dict[Future, DebugPanelClient] = {self._executor.submit(lambda c: func_client(c), client, **kwargs): client for client in self._clients}
        completed: Iterator[Future] = as_completed(futures)
        results: dict[NodeIdentifier, Any] = {}
        with progressbar(completed, length=len(futures), label='Progress') if opts.progress else nullcontext(completed) as bar:
            for future in bar:
                client: DebugPanelClient = futures[future]
                k = client.get_node_spec().id
                try:
                    with future.result() as resp:
                        status: int = resp.status
                        reason: str = resp.reason
                        results[k] = 'Requested' if status == 200 else reason
                except Exception as exc:
                    results[k] = exc
        print_table([[k, r] for k, r in sorted(results.items())],
                    headers=['Node', 'Result'] if opts.headings else None,
                    table_format=self._ctx.meta[context.TABLE_FORMAT])

    def _initialize_auid_operation(self) -> None:
        """
        Initializes for an AUID-centric operation. Fails if the list of AUIDs
        ends up being empty.
        """
        self._initialize_node_operation()
        self._auids = [*(opts := self._opts).auid, *chain.from_iterable(file_lines(file_path) for file_path in opts.auids)]
        if len(self._auids) == 0:
            self._ctx.fail('The list of AUIDs to process is empty')

    def _initialize_node_operation(self) -> None:
        """
        Initializes for a node-centric operation. Fails if the list of nodes
        ends up being empty.
        """
        # First, process the nodes...
        clients: list[DebugPanelClient] = list()
        # ...first from node sets
        for node_set_path in (opts := self._opts).node_set:
            with node_set_path.open('r') as node_set_input:
                try:
                    node_set_yaml: YamlT = yaml.safe_load(node_set_input)
                    node_set: NodeSet = NodeSet.model_validate(node_set_yaml)
                    for node_spec in node_set.nodes:
                        clients.append(DebugPanelClient(node_spec))
                except (yaml.YAMLError, ValidationError) as exc:
                    self._ctx.fail(str(exc))
        # ...then from compact node specifications
        for compact_node_spec in [*opts.node_spec, *chain.from_iterable(file_lines(file_path) for file_path in opts.node_specs)]:
            try:
                clients.append(DebugPanelClient(get_node_spec_adapter().validate_python(compact_node_spec)))
            except ValidationError as exc:
                self._ctx.fail(str(exc))
        if len(clients) == 0:
            self._ctx.fail('The list of nodes to process is empty')
        self._clients.extend(clients)
        # Then, initialize the thread pool
        self._executor = ThreadPoolExecutor(max_workers=opts.pool_size or self._ctx.meta[context.JOBS])
        # Finally, prompt for credentials
        if opts.username is None:
            opts.username = prompt('UI username')
        if opts.password is None:
            opts.password = prompt('UI password', hide_input=True)


#: The AUID option group: --auid/-a, --auids/-A
_auid_option_group = option_group(
    'AUID options',
    option('--auid', '-a', metavar='AUID', multiple=True, help='Add AUID to the list of AUIDs to process.'),
    option('--auids', '-A', metavar='FILE', type=click_path('ferz'), multiple=True, help='Add the AUIDs in FILE to the list of AUIDs to process.')
)


#: The depth option group: --depth/-d
_depth_option_group = option_group(
    'Depth options',
    option('--depth', '-d', metavar='DEPTH', type=NonNegativeInt, default=DEFAULT_DEPTH, help='Set the crawl depth to DEPTH.')
)


#: The node option group: --node/-n, --nodes/-N, --node-set/-s, --username/-U, --password/-P
_node_option_group = option_group(
    'Node options',
    option('--node-set', '-s', metavar='FILE', multiple=True, help='Add the nodes from the node set in FILE to the list of nodes to process.'),
    option('--node-spec', '--node', '-n', metavar='NODE', multiple=True, help='Add the compact node specification NODE to the list of nodes to process.'),
    option('--node-specs', '--nodes', '-N', metavar='FILE', type=click_path('ferz'), multiple=True, help='Add the compact node specifications in FILE to the list of nodes to process.'),
    option('--username', '-U', metavar='USER', show_default='interactive prompt', help='Set the UI username to USER.'),
    option('--password', '-P', metavar='PASS', show_default='interactive prompt', help='Set the UI password to PASS.'),
)


#: The output option group: --headings/--no-headings, --progress/--no-progress, --table-format/-T
_output_option_group = option_group(
    'Output options',
    option('--headings/--no-headings', is_flag=True, default=True, help='Set whether to include column headings in tabular output.'),
    option('--progress/--no-progress', is_flag=True, default=True, help='Set whether to display a progress bar during processing.'),
    make_table_format_option()
)


#: The job option group: --pool-size, --pool-type
_job_option_group = option_group(
    'Job options',
    jobs_option,
    option('--pool-size', metavar='SIZE', type=Optional[NonNegativeInt], default=None, deprecated='Use --jobs instead.'),
    constraint=mutually_exclusive
)


#: The composite AUID operation decorator.
_auid_operation = compose_decorators(_node_option_group, _auid_option_group, _job_option_group, _output_option_group, pass_obj)


#: The composite node operation decorator.
_node_operation = compose_decorators(_node_option_group, _job_option_group, _output_option_group, pass_obj)


@with_plugins(entry_points(module='click_command_tree')) # adds a 'tree' command
@group('debugpanel', params=None, context_settings=make_extra_context_settings())
@color_option
@show_params_option
@pass_context
def _debugpanel(ctx: ExtraContext, **kwargs):
    """Command line tool to interact with the LOCKSS 1.x DebugPanel servlet."""
    ctx.obj = _DebugPanelCli(ctx)


#: A subcommand section for AUID commands.
_AUID_COMMANDS = Section('AUID commands')


#: A subcommand section for node commands.
_NODE_COMMANDS = Section('Node commands')


@_debugpanel.command('check-substance', aliases=['cs'], section=_AUID_COMMANDS, help='Cause nodes to check the substance of AUs.')
@_auid_operation
def _check_substance(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to check the substance of AUs."""
    cli.dispatch(cli.check_substance, **kwargs)


@_debugpanel.command('copyright', help='Show the copyright and exit.')
def _copyright() -> None:
    """Show the copyright and exit."""
    echo(__copyright__)


@_debugpanel.command('crawl', aliases=['cr'], section=_AUID_COMMANDS, help='Cause nodes to crawl AUs.')
@_auid_operation
def _crawl(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to crawl AUs."""
    cli.dispatch(cli.crawl, **kwargs)


@_debugpanel.command('crawl-plugins', aliases=['cp'], section=_NODE_COMMANDS, help='Cause nodes to crawl plugins.')
@_node_operation
def _crawl_plugins(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to crawl plugins."""
    cli.dispatch(cli.crawl_plugins, **kwargs)


@_debugpanel.command('deep-crawl', aliases=['dc'], section=_AUID_COMMANDS, help='Cause nodes to deep-crawl AUs.')
@compose_decorators(_node_option_group, _auid_option_group, _depth_option_group, _job_option_group, _output_option_group, pass_obj)
def _deep_crawl(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to deep-crawl AUs."""
    cli.dispatch(cli.deep_crawl, **kwargs)


@_debugpanel.command('disable-indexing', aliases=['di'], section=_AUID_COMMANDS, help='Cause nodes to disable metadata indexing for AUs.')
@_auid_operation
def _disable_indexing(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to disable metadata indexing for AUs."""
    cli.dispatch(cli.disable_indexing, **kwargs)


@_debugpanel.command('license', help='Show the software license and exit.')
def license() -> None:
    """Show the software license and exit."""
    echo(__license__)


@_debugpanel.command('poll', aliases=['po'], section=_AUID_COMMANDS, help='Cause nodes to poll AUs.')
@_auid_operation
def _poll(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to poll AUs."""
    cli.dispatch(cli.poll, **kwargs)


@_debugpanel.command('reload-config', aliases=['rc'], section=_NODE_COMMANDS, help='Cause nodes to reload their configuration.')
@_node_operation
def _reload_config(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to reload their configuration."""
    cli.dispatch(cli.reload_config, **kwargs)


@_debugpanel.command('reindex-metadata', aliases=['ri'], section=_AUID_COMMANDS, help='Cause nodes to reindex the metadata of AUs.')
@_auid_operation
def _reindex_metadata(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to reindex the metadata of AUs."""
    cli.dispatch(cli.reindex_metadata, **kwargs)


@_debugpanel.command('validate-files', aliases=['vf'], section=_AUID_COMMANDS, help='Cause nodes to validate the files of AUs.')
@_auid_operation
def _validate_files(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to validate the files of AUs."""
    cli.dispatch(cli.validate_files, **kwargs)


@_debugpanel.command('version', help='Show the version number and exit.')
def version() -> None:
    """Show the version number and exit."""
    echo(__version__)


def main() -> None:
    """Main entry point of the module."""
    _debugpanel()


# Main entry point of the module.
if __name__ == '__main__':
    main()
