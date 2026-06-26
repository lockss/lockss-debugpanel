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
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from inspect import ismethod
from itertools import chain
from pathlib import Path
from typing import Any, Optional, TypeAlias

from click_extra import Context, ProgressOption, Section, accessible_option, color_option, echo, group, jobs_option, no_color_option, option, option_group, pass_context, pass_obj, print_table, progressbar, prompt, show_params_option, table_format_option, timer_option
from click_extra.context import JOBS, PROGRESS, TABLE_FORMAT
from click_extra.decorators import decorator_factory
from click_plugins import with_plugins
from pydantic import ValidationError
import yaml

from lockss.pybasic.cliutil import NonNegativeInt, click_path, compose_decorators
from lockss.pybasic.errorutil import InternalError
from lockss.pybasic.fileutil import file_lines
from lockss.pybasic.nodeutil import NodeIdentifier, NodeSet, get_node_spec_adapter

from . import __copyright__, __license__, __version__
from ._core import DebugPanelClient, UrlOpenT, DEFAULT_DEPTH


YamlT: TypeAlias = Any


progress_option = decorator_factory(dec=option, cls=ProgressOption)


class _DebugPanelCli(object):
    """DebugPanel command line application."""

    @dataclass(kw_only=True)
    class _Opts:
        """Data class to hold parsed command line options."""
        # Node options
        node_set: tuple[Path, ...] = ()
        node_spec: tuple[str, ...] = ()
        node_specs: tuple[Path, ...] = ()
        username: Optional[str] = None
        password: Optional[str] = field(default=None, repr=False)
        # AUID options
        auid: tuple[str, ...] = ()
        auids: tuple[Path, ...] = ()
        # Depth options
        depth: Optional[int] = None
        # Tabular output options
        headings: Optional[bool] = None

    _ctx: Context
    _opts: _DebugPanelCli._Opts
    _auids: list[str]
    _clients: list[DebugPanelClient]

    def __init__(self, ctx: Context) -> None:
        """
        Constructor.

        :param ctx: The Click Extra context.
        :type ctx: ExtraContext
        """
        super().__init__()
        self._ctx = ctx

    def check_substance(self) -> None:
        """Implementation of the ``check-substance`` command."""
        self._do_auid_command(DebugPanelClient.check_substance)

    def crawl(self) -> None:
        """Implementation of the ``crawl`` command."""
        self._do_auid_command(DebugPanelClient.crawl)

    def crawl_plugins(self) -> None:
        """Implementation of the ``crawl-plugins`` command."""
        self._do_node_command(DebugPanelClient.crawl_plugins)

    def deep_crawl(self) -> None:
        """Implementation of the ``deep-crawl`` command."""
        self._do_auid_command(DebugPanelClient.deep_crawl, depth=self._opts.depth)

    def disable_indexing(self) -> None:
        """Implementation of the ``disable-indexing`` command."""
        self._do_auid_command(DebugPanelClient.disable_indexing)

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
        self._do_auid_command(DebugPanelClient.poll)

    def reindex_metadata(self) -> None:
        """Implementation of the ``reindex-metadata`` command."""
        self._do_auid_command(DebugPanelClient.reindex_metadata)

    def reload_config(self) -> None:
        """Implementation of the ``reload-config`` command."""
        self._do_node_command(DebugPanelClient.reload_config)

    def validate_files(self) -> None:
        """Implementation of the ``validate-files`` command."""
        self._do_auid_command(DebugPanelClient.validate_files)

    def _do_auid_command(self,
                         func_client_auid: Callable[[DebugPanelClient, str], UrlOpenT],
                         **kwargs) -> None:
        """
        Performs one AUID-centric command.

        :param func_client_auid: A function that applies to a
                                 ``DebugPanelClient`` and an AUID and returns
                                  what ``urllib.request.urlopen`` returns.
        :type func_client_auid: Callable[[DebugPanelClient, str], UrlOpenT]
        """
        self._initialize_auid_operation()
        results: dict[tuple[NodeIdentifier, str], str] = {}
        with ThreadPoolExecutor(max_workers=(meta := self._ctx.meta)[JOBS]) as executor:
            futures: dict[Future[UrlOpenT], tuple[DebugPanelClient, str]] = {executor.submit(func_client_auid, client, auid, **kwargs): (client, auid) for auid in self._auids for client in self._clients}
            completed: Iterator[Future[UrlOpenT]] = as_completed(futures)
            with progressbar(completed, length=len(futures), label='Progress', item_show_func=lambda f: f and futures[f][0].get_id() or None) if (meta := self._ctx.meta)[PROGRESS] else nullcontext(completed) as bar:
                for future in bar:
                    client, auid = futures[future]
                    k: tuple[NodeIdentifier, str] = (client.get_id(), auid)
                    try:
                        with future.result() as resp:
                            status: int = resp.status
                            reason: str = resp.reason
                            results[k] = 'Requested' if status == 200 else reason
                    except Exception as exc:
                        results[k] = str(exc)
        sorted_nodes: list[NodeIdentifier] = sorted(client.get_id() for client in self._clients)
        print_table([[a, *[results[(i, a)] for i in sorted_nodes]] for a in sorted(self._auids)],
                    headers=('AUID', *sorted_nodes),
                    table_format=meta[TABLE_FORMAT])

    def _do_node_command(self,
                         func_client: Callable[[DebugPanelClient], UrlOpenT],
                         **kwargs) -> None:
        """
        Performs one node-centric command.

        :param func_client: A function that applies to a ``DebugPanelClient`` and
                            returns what ``urllib.request.urlopen`` returns.
        :type func_client: Callable[[DebugPanelClient], UrlOpenT]
        """
        self._initialize_node_operation()
        results: dict[NodeIdentifier, str] = {}
        with ThreadPoolExecutor(max_workers=(meta := self._ctx.meta)[JOBS]) as executor:
            futures: dict[Future[UrlOpenT], DebugPanelClient] = {executor.submit(func_client, client, **kwargs): client for client in self._clients}
            completed: Iterator[Future[UrlOpenT]] = as_completed(futures)
            with progressbar(completed, length=len(futures), label='Progress', item_show_func=lambda f: f and futures[f][0].get_id() or None) if meta[PROGRESS] else nullcontext(completed) as bar:
                for future in bar:
                    client: DebugPanelClient = futures[future]
                    k: NodeIdentifier = client.get_id()
                    try:
                        with future.result() as resp:
                            status: int = resp.status
                            reason: str = resp.reason
                            results[k] = 'Requested' if status == 200 else reason
                    except Exception as exc:
                        results[k] = str(exc)
        print_table([[node, result] for node, result in sorted(results.items())],
                    headers=['Node', 'Result'],
                    table_format=meta[TABLE_FORMAT])

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
        # Finally, authenticate
        u, opts.username = opts.username if opts.username else prompt('UI username'), None
        p, opts.password = opts.password if opts.password else prompt('UI password', hide_input=True), None
        for client in clients:
            client.authenticate(u, p)
        self._clients = clients


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


#: The node option group: --node-set/-s, --node-spec/-n, --node-specs/-N, --username/-U, --password/-P
_node_option_group = option_group(
    'Node options',
    option('--node-set', '-s', metavar='FILE', type=click_path('ferz'), multiple=True, help='Add the nodes from the node set in FILE to the list of nodes to process.'),
    option('--node-spec', '--node', '-n', metavar='NODE', multiple=True, help='Add the compact node specification NODE to the list of nodes to process.'),
    option('--node-specs', '--nodes', '-N', metavar='FILE', type=click_path('ferz'), multiple=True, help='Add the compact node specifications in FILE to the list of nodes to process.'),
    option('--username', '-U', metavar='USER', show_default='interactive prompt', help='Set the UI username to USER.'),
    option('--password', '-P', metavar='PASS', show_default='interactive prompt', help='Set the UI password to PASS.')
)


#: The tabular output option group: --headings/--no-headings, --table-format/-T
_tabular_output_option_group = option_group(
    'Tabular output options',
    option('--headings/--no-headings', is_flag=True, default=True, help='Set whether to include column headings in tabular output.'),
    table_format_option('--table-format', '-T')
)


#: The job option group: --pool-size, --pool-type
_job_option_group = option_group(
    'Job options',
    jobs_option('--jobs', '--pool-size', deprecated='--pool-size is deprecated, use --jobs')
)


#: The display option group: --accessible, --color/--no-color --progress/--no-progress, --time
_display_option_group = option_group(
    'Display options',
    accessible_option,
    color_option,
    no_color_option,
    progress_option,
    timer_option
)


#: The composite AUID operation decorator.
_auid_operation = compose_decorators(_node_option_group, _auid_option_group, _job_option_group, _tabular_output_option_group, _display_option_group, pass_obj)


#: The composite node operation decorator.
_node_operation = compose_decorators(_node_option_group, _job_option_group, _tabular_output_option_group, _display_option_group, pass_obj)


@with_plugins(entry_points(module='click_command_tree')) # adds a 'tree' command
@group(params=None)
@show_params_option
@pass_context
def debugpanel(ctx: Context, **kwargs):
    """Command line tool to interact with the LOCKSS 1.x DebugPanel servlet."""
    ctx.obj = _DebugPanelCli(ctx)


@debugpanel.command(help='Show the copyright and exit.')
def copyright(cli: _DebugPanelCli, **kwargs) -> None:
    """Show the copyright and exit"""
    echo(__copyright__)


@debugpanel.command(help='Show the software license and exit.')
def license(cli: _DebugPanelCli, **kwargs) -> None:
    """Show the software license and exit"""
    echo(__license__)


@debugpanel.command('version', help='Show the version number and exit.')
def version(cli: _DebugPanelCli, **kwargs) -> None:
    """Show the version number and exit"""
    echo(__version__)


#: A subcommand section for node commands.
_NODE_COMMANDS = Section('Node commands')


@debugpanel.command(aliases=['cp'], section=_NODE_COMMANDS, help='Cause nodes to crawl plugins.')
@_node_operation
def crawl_plugins(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to crawl plugins"""
    cli.dispatch(cli.crawl_plugins, **kwargs)


@debugpanel.command(aliases=['rc'], section=_NODE_COMMANDS, help='Cause nodes to reload their configuration.')
@_node_operation
def reload_config(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to reload their configuration"""
    cli.dispatch(cli.reload_config, **kwargs)


#: A subcommand section for AUID commands.
_AUID_COMMANDS = Section('AUID commands')


@debugpanel.command(aliases=['cs'], section=_AUID_COMMANDS, help='Cause nodes to check the substance of AUs.')
@_auid_operation
def check_substance(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to check the substance of AUs"""
    cli.dispatch(cli.check_substance, **kwargs)


@debugpanel.command(aliases=['cr'], section=_AUID_COMMANDS, help='Cause nodes to crawl AUs.')
@_auid_operation
def crawl(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to crawl AUs"""
    cli.dispatch(cli.crawl, **kwargs)


@debugpanel.command(aliases=['dc'], section=_AUID_COMMANDS, help='Cause nodes to deep-crawl AUs.')
@compose_decorators(_node_option_group, _auid_option_group, _depth_option_group, _job_option_group, _tabular_output_option_group, _display_option_group, pass_obj)
def deep_crawl(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to deep-crawl AUs"""
    cli.dispatch(cli.deep_crawl, **kwargs)


@debugpanel.command(aliases=['di'], section=_AUID_COMMANDS, help='Cause nodes to disable metadata indexing for AUs.')
@_auid_operation
def disable_indexing(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to disable metadata indexing for AUs"""
    cli.dispatch(cli.disable_indexing, **kwargs)


@debugpanel.command(aliases=['po'], section=_AUID_COMMANDS, help='Cause nodes to poll AUs.')
@_auid_operation
def poll(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to poll AUs"""
    cli.dispatch(cli.poll, **kwargs)


@debugpanel.command(aliases=['ri'], section=_AUID_COMMANDS, help='Cause nodes to reindex the metadata of AUs.')
@_auid_operation
def reindex_metadata(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to reindex the metadata of AUs"""
    cli.dispatch(cli.reindex_metadata, **kwargs)


@debugpanel.command(aliases=['vf'], section=_AUID_COMMANDS, help='Cause nodes to validate the files of AUs.')
@_auid_operation
def validate_files(cli: _DebugPanelCli, **kwargs) -> None:
    """Cause nodes to validate the files of AUs"""
    cli.dispatch(cli.validate_files, **kwargs)


def main() -> None:
    """Main entry point of the module."""
    debugpanel()
