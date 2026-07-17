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

from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from dataclasses import dataclass, field
from itertools import chain
from pathlib import Path
from typing import Any, Concatenate, Optional, ParamSpec, TypeAlias, TypeVar, Union

from click_extra import Context, ProgressOption, Section, accessible_option, color_option, echo, group, jobs_option, no_color_option, option, option_group, pass_context, print_table, progressbar, prompt, show_params_option, table_format_option, timer_option, tree_option
from click_extra.context import JOBS, PROGRESS, TABLE_FORMAT
from click_extra.decorators import decorator_factory
from pydantic import ValidationError
import yaml

from lockss.pybasic.cliutil import NonNegativeInt, click_path, compose_decorators
from lockss.pybasic.fileutil import file_lines
from lockss.pybasic.nodeutil import NodeSet, get_node_spec_adapter

from . import __copyright__, __license__, __version__
from ._core import DebugPanelClient, UrlOpenT, DEFAULT_DEPTH


_OpInput = TypeVar('_OpInput')
_OpResult = TypeVar('_OpResult')
_ResultKey = TypeVar('_ResultKey')
_ResultValue = TypeVar('_ResultValue')


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

    def __init__(self, ctx: Context, **cli_kwargs) -> None:
        """
        Constructor.

        :param ctx: The Click Extra context.
        :type ctx: ExtraContext
        """
        super().__init__()
        self._ctx = ctx
        self._opts = _DebugPanelCli._Opts(**cli_kwargs)

    def check_substance(self) -> None:
        """Implementation of the ``check-substance`` command."""
        self._generic_auid_action(DebugPanelClient.check_substance)

    def crawl(self) -> None:
        """Implementation of the ``crawl`` command."""
        self._generic_auid_action(DebugPanelClient.crawl)

    def crawl_plugins(self) -> None:
        """Implementation of the ``crawl-plugins`` command."""
        self._generic_node_action(DebugPanelClient.crawl_plugins)

    def deep_crawl(self) -> None:
        """Implementation of the ``deep-crawl`` command."""
        self._generic_auid_action(DebugPanelClient.deep_crawl, depth=self._opts.depth)

    def disable_indexing(self) -> None:
        """Implementation of the ``disable-indexing`` command."""
        self._generic_auid_action(DebugPanelClient.disable_indexing)

    def poll(self) -> None:
        """Implementation of the ``poll`` command."""
        self._generic_auid_action(DebugPanelClient.poll)

    def reindex_metadata(self) -> None:
        """Implementation of the ``reindex-metadata`` command."""
        self._generic_auid_action(DebugPanelClient.reindex_metadata)

    def reload_config(self) -> None:
        """Implementation of the ``reload-config`` command."""
        self._generic_node_action(DebugPanelClient.reload_config)

    def validate_files(self) -> None:
        """Implementation of the ``validate-files`` command."""
        self._generic_auid_action(DebugPanelClient.validate_files)

    def _generic_action(self,
                        func: Callable[Concatenate[_OpInput, dict[str, Any]], _OpResult],
                        get_tuples: Callable[[], Iterable[tuple[_OpInput, Optional[dict[str, Any]]]]],
                        get_result: Callable[[_OpResult], _ResultValue],
                        init_funcs: Optional[list[Callable[[], None]]] = None,
                        transform_key: Optional[Callable[[_OpInput], _ResultKey]] = None,
                        progress_bar_item: Optional[Callable[[Optional[_OpInput]], Optional[str]]] = None) \
            -> dict[_ResultKey, _ResultValue]:
        for init_func in init_funcs or []:
            init_func()
        results: dict[_ResultKey, _ResultValue] = {}
        with ThreadPoolExecutor(max_workers=(meta := self._ctx.meta)[JOBS]) as executor:
            futures: dict[Future[_OpResult], _OpInput] = {executor.submit(func, *a, **(k or {})): a for a, k in get_tuples()}
            completed: Iterator[Future[_OpResult]] = as_completed(futures)
            xform: Callable[[_OpInput], _ResultKey] = transform_key or (lambda x: x)
            itemlbl: Callable[[Optional[_OpInput]], Optional[str]] = lambda f: (progress_bar_item if progress_bar_item else str)(futures[f]) if f else None
            with progressbar(completed, length=len(futures), label='Progress', item_show_func=itemlbl) if self._ctx.meta[PROGRESS] else nullcontext(completed) as bar:
                for future in bar:
                    key: _ResultKey = xform(futures[future])
                    try:
                        results[key] = get_result(future.result())
                    except Exception as exc:
                        results[key] = str(exc)
        return results

    def _generic_auid_action(self,
                             func: Callable[Concatenate[tuple[DebugPanelClient, str], dict[str, Any]], UrlOpenT],
                             **kwargs) -> None:
        results: dict[tuple[str, str], str] = \
            self._generic_action(func,
                                 lambda: [((client, auid), kwargs) for auid in self._auids for client in self._clients],
                                 self._process_urlopent,
                                 init_funcs=[self._initialize_clients, self._initialize_auids, self._initialize_auth],
                                 transform_key=lambda t: (t[0].get_id(), t[1]),
                                 progress_bar_item=lambda t: f'{t[0].get_id()} {t[1]}' if t else None)
        sorted_nodes: list[str] = sorted(c.get_id() for c in self._clients)
        sorted_auids: list[str] = sorted(self._auids)
        print_table([[a, *[results[(n, a)] for n in sorted_nodes]] for a in sorted_auids],
                    ['AUID', *sorted(n for n in sorted_nodes)],
                    table_format=self._ctx.meta[TABLE_FORMAT])

    def _generic_node_action(self,
                             func: Callable[Concatenate[tuple[DebugPanelClient], dict[str, Any]], UrlOpenT],
                             **kwargs) -> None:
        results: dict[tuple[str], str] = \
            self._generic_action(func,
                                 lambda: [((client,), kwargs) for client in self._clients],
                                 self._process_urlopent,
                                 init_funcs=[self._initialize_clients, self._initialize_auth],
                                 transform_key=lambda t: (t[0].get_id(),),
                                 progress_bar_item=lambda t: f'{t[0].get_id()}' if t else None)
        sorted_nodes: list[str] = sorted(c.get_id() for c in self._clients)
        print_table([[n, str(results[(n,)])] for n in sorted_nodes],
                    ['Node', 'Result'])

    def _initialize_auids(self) -> None:
        """
        Initializes the list of AUIDs. Fails if the list of AUIDs ends up being
        empty.
        """
        self._auids = [*(opts := self._opts).auid, *chain.from_iterable(file_lines(file_path) for file_path in opts.auids)]
        if len(self._auids) == 0:
            self._ctx.fail('The list of AUIDs to process is empty')

    def _initialize_auth(self) -> None:
        u = opts.username if (opts := self._opts).username else prompt('UI username')
        p, opts.password = opts.password if opts.password else prompt('UI password', hide_input=True), None
        for client in self._clients:
            client.authenticate(u, p)

    def _initialize_clients(self) -> None:
        """
        Initializes the list of clients. Fails if the list of nodes ends up
        being empty.
        """
        clients: list[DebugPanelClient] = list()
        # First from node sets
        for node_set_path in (opts := self._opts).node_set:
            with node_set_path.open('r') as node_set_input:
                try:
                    node_set_yaml: YamlT = yaml.safe_load(node_set_input)
                    node_set: NodeSet = NodeSet.model_validate(node_set_yaml)
                    for node_spec in node_set.nodes:
                        clients.append(DebugPanelClient(node_spec))
                except (yaml.YAMLError, ValidationError) as exc:
                    self._ctx.fail(str(exc))
        # Then from compact node specifications
        for compact_node_spec in [*opts.node_spec, *chain.from_iterable(file_lines(file_path) for file_path in opts.node_specs)]:
            try:
                clients.append(DebugPanelClient(get_node_spec_adapter().validate_python(compact_node_spec)))
            except ValidationError as exc:
                self._ctx.fail(str(exc))
        # Fail if empty
        if len(clients) == 0:
            self._ctx.fail('The list of nodes to process is empty')
        self._clients = clients

    def _process_urlopent(self, urlopent: UrlOpenT) -> str:
        with urlopent as resp:
            return 'Requested' if resp.status == 200 else resp.reason


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


#: The job option group: --jobs, --pool-size
_job_option_group = option_group(
    'Job options',
    jobs_option('--jobs', '--pool-size', deprecated='--pool-size is deprecated, use --jobs')
)


#: The display option group: --accessible, --color, --no-color, --progress/--no-progress
_display_option_group = option_group(
    'Display options',
    accessible_option,
    color_option,
    no_color_option,
    progress_option,
)


#: The debug option group: --show-params, --time/--no-time
_debug_option_group = option_group(
    'Debug options',
    show_params_option,
    timer_option
)


#: The composite AUID operation decorator.
_auid_operation = compose_decorators(_node_option_group, _auid_option_group, _job_option_group, _tabular_output_option_group, _display_option_group, _debug_option_group, pass_context)


#: The composite node operation decorator.
_node_operation = compose_decorators(_node_option_group, _job_option_group, _tabular_output_option_group, _display_option_group, _debug_option_group, pass_context)


@group(params=None)
@tree_option
@pass_context
def debugpanel(ctx: Context, **kwargs) -> None:
    pass


@debugpanel.command(help='Show the copyright and exit.')
def copyright(**kwargs) -> None:
    echo(__copyright__)


@debugpanel.command(help='Show the software license and exit.')
def license(**kwargs) -> None:
    echo(__license__)


@debugpanel.command('version', help='Show the version number and exit.')
def version(**kwargs) -> None:
    echo(__version__)


#: A subcommand section for node commands.
_NODE_COMMANDS = Section('Node commands')


@debugpanel.command(aliases=['cp'], section=_NODE_COMMANDS, help='Cause nodes to crawl plugins.')
@_node_operation
def crawl_plugins(ctx: Context, **kwargs) -> None:
    _DebugPanelCli(ctx, **kwargs).crawl_plugins()


@debugpanel.command(aliases=['rc'], section=_NODE_COMMANDS, help='Cause nodes to reload their configuration.')
@_node_operation
def reload_config(ctx: Context, **kwargs) -> None:
    _DebugPanelCli(ctx, **kwargs).reload_config()


#: A subcommand section for AUID commands.
_AUID_COMMANDS = Section('AUID commands')


@debugpanel.command(aliases=['cs'], section=_AUID_COMMANDS, help='Cause nodes to check the substance of AUs.')
@_auid_operation
def check_substance(ctx: Context, **kwargs) -> None:
    _DebugPanelCli(ctx, **kwargs).check_substance()


@debugpanel.command(aliases=['cr'], section=_AUID_COMMANDS, help='Cause nodes to crawl AUs.')
@_auid_operation
def crawl(ctx: Context, **kwargs) -> None:
    _DebugPanelCli(ctx, **kwargs).crawl()


@debugpanel.command(aliases=['dc'], section=_AUID_COMMANDS, help='Cause nodes to deep-crawl AUs.')
@compose_decorators(_node_option_group, _auid_option_group, _depth_option_group, _job_option_group, _tabular_output_option_group, _display_option_group, _debug_option_group, pass_context)
def deep_crawl(ctx: Context, **kwargs) -> None:
    _DebugPanelCli(ctx, **kwargs).deep_crawl()


@debugpanel.command(aliases=['di'], section=_AUID_COMMANDS, help='Cause nodes to disable metadata indexing for AUs.')
@_auid_operation
def disable_indexing(ctx: Context, **kwargs) -> None:
    _DebugPanelCli(ctx, **kwargs).disable_indexing()


@debugpanel.command(aliases=['po'], section=_AUID_COMMANDS, help='Cause nodes to poll AUs.')
@_auid_operation
def poll(ctx: Context, **kwargs) -> None:
    _DebugPanelCli(ctx, **kwargs).poll()


@debugpanel.command(aliases=['ri'], section=_AUID_COMMANDS, help='Cause nodes to reindex the metadata of AUs.')
@_auid_operation
def reindex_metadata(ctx: Context, **kwargs) -> None:
    _DebugPanelCli(ctx, **kwargs).reindex_metadata()


@debugpanel.command(aliases=['vf'], section=_AUID_COMMANDS, help='Cause nodes to validate the files of AUs.')
@_auid_operation
def validate_files(ctx: Context, **kwargs) -> None:
    _DebugPanelCli(ctx, **kwargs).validate_files()


def main() -> None:
    """Main entry point of the module."""
    debugpanel()
