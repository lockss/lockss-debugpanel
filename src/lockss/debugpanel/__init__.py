#!/usr/bin/env python3

# Copyright (c) 2000-2023, Board of Trustees of Leland Stanford Jr. University
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

__version__ = '0.7.0-post1'

__copyright__ = '''
Copyright (c) 2000-2023, Board of Trustees of Leland Stanford Jr. University
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

import base64
import urllib.request


DEFAULT_DEPTH = 123


def check_substance(node_object, auid):
    return _auid_action(node_object, auid, 'Check Substance')


def crawl(node_object, auid):
    return _auid_action(node_object, auid, 'Force Start Crawl')


def crawl_plugins(node_object):
    return _node_action(node_object, 'Crawl Plugins')


def deep_crawl(node_object, auid, depth=DEFAULT_DEPTH):
    return _auid_action(node_object, auid, 'Force Deep Crawl', depth=depth)


def disable_indexing(node_object, auid):
    return _auid_action(node_object, auid, 'Disable Indexing')


def node(node_reference, u, p):
    return _Node(node_reference, u, p)


def poll(node_object, auid):
    return _auid_action(node_object, auid, 'Start V3 Poll')


def reindex_metadata(node_object, auid):
    return _auid_action(node_object, auid, 'Force Reindex Metadata')


def reload_config(node_object):
    return _node_action(node_object, 'Reload Config')


def validate_files(node_object, auid):
    return _auid_action(node_object, auid, 'Validate Files')


class _Node(object):

    DEFAULT_PROTOCOL = 'http'

    def __init__(self, node_reference, u, p):
        super().__init__()
        if '://' not in node_reference:
            node_reference = f'{_Node.DEFAULT_PROTOCOL}://{node_reference}'
        if node_reference.endswith('/'):
            node_reference = node_reference[:-1]
        self._url = node_reference
        self._basic = base64.b64encode(f'{u}:{p}'.encode('utf-8')).decode('utf-8')

    def authenticate(self, req):
        req.add_header('Authorization', f'Basic {self._basic}')

    def get_url(self):
        return self._url


def _auid_action(node_object, auid, action, **kwargs):
    action_encoded = action.replace(" ", "%20")
    auid_encoded = auid.replace('%', '%25').replace('|', '%7C').replace('&', '%26').replace('~', '%7E')
    req = _make_request(node_object, f'action={action_encoded}&auid={auid_encoded}', **kwargs)
    return urllib.request.urlopen(req)


def _make_request(node_object, query, **kwargs):
    for key, val in kwargs.items():
        query = f'{query}&{key}={val}'
    url = f'{node_object.get_url()}/DebugPanel?{query}'
    req = urllib.request.Request(url)
    node_object.authenticate(req)
    return req


def _node_action(node_object, action, **kwargs):
    action_encoded = action.replace(" ", "%20")
    req = _make_request(node_object, f'action={action_encoded}', **kwargs)
    return urllib.request.urlopen(req)
