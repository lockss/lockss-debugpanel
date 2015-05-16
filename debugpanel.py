#!/usr/bin/env python

# $Id$

#
# Copyright (c) 2000-2015 Board of Trustees of Leland Stanford Jr. University,
# all rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# STANFORD UNIVERSITY BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
# IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# Except as contained in this notice, the name of Stanford University shall not
# be used in advertising or otherwise to promote the sale, use or other dealings
# in this Software without prior written authorization from Stanford University.
#

#
# A script to interact with DebugPanel.
#
# Usage examples:
#
# debugpanel.py --host=lockss.university.edu:8081 --reload-config
#   Causes lockss.university.edu:8081 to reload its config. (Prompts for a UI
#   username and password.)
#
# debugpanel.py --host=lockss.university.edu:8081 --reload-config --username=UUU
#   Same, but uses UUU as the UI username (and prompts for a UI password).
#
# debugpanel.py --hosts=myhosts.txt --reload-config
#   Causes each host listed in myhosts.txt to reload its config. (Prompts for a
#   UI username and password once, used for all hosts.) Lines that are empty,
#   are all white space, or begin with the character '#' are ignored, other
#   lines are expected to be a host.
#
# debugpanel.py --hosts=myhosts.txt --crawl-plugins
#   Causes each host listed in myhosts.txt to crawl its plugin registries.
#
# debugpanel.py --hosts=myhosts.txt --crawl 'auid1' 'auid2' 'auid3'
#   Causes each host listed in myhosts.txt to request a crawl of the AUs
#   identified by the AUIDs auid1, auid2 and auid3. Quoting recommended (AUIDs
#   have ampersands, which conflict with shell commands.)
#
# debugpanel.py --hosts=myhosts.txt --crawl --auids=myauids.txt
#   Causes each host listed in myhosts.txt to request a crawl of the AUs
#   identified by the AUIDS listed in myauids.txt. Lines in the latter that are
#   empty, are all white space, or begin with the character '#' are ignored,
#   other lines are expected to be an AUID.
#
# debugpanel.py --hosts=myhosts.txt --deep-crawl --auids=myauids.txt
#   Causes each host listed in myhosts.txt to request a deep crawl of the AUs
#   identified by the AUIDS listed in myauids.txt (using some large depth).
#
# debugpanel.py --hosts=myhosts.txt --deep-crawl --auids=myauids.txt --depth=DDD
#   Causes each host listed in myhosts.txt to request a deep crawl of the AUs
#   identified by the AUIDS listed in myauids.txt (using the integer depth DDD).
#
# debugpanel.py --hosts=myhosts.txt --poll --auids=myauids.txt
#   Causes each host listed in myhosts.txt to request a poll of the AUs
#   identified by the AUIDS listed in myauids.txt.
#
# debugpanel.py --hosts=myhosts.txt --poll --auids=myauids.txt --wait=WWW
#   Same, but waits WWW seconds between each request (recommended for all
#   actions requiring a per-AU request like --crawl, --deep-crawl or --poll).
#
# Multiple --host and --hosts are allowed, compounding to an overall list of
# hosts to be processed. Likewise, multiple --auids and command line AUIDs are
# allowed, compounding to an overall list of AUIDs to be processed.
#

__version__ = '0.1.3'

import base64
import getpass
import optparse
import sys
import time
import urllib2

class Options(object):
  DEPTH = 123
  WAIT = 0
  def __init__(self):
    super(Options, self).__init__()
    self.__auth = None
    self.__auids = list()
    self.__crawl = False
    self.__crawl_plugins = False
    self.__deep_crawl = False
    self.__depth = Options.DEPTH
    self.__hosts = list()
    self.__poll = False
    self.__reload_config = False
    self.__wait = Options.WAIT
  def add_auids(self, auids): self.__auids.extend(auids)
  def get_auids(self): return self.__auids
  def set_auth(self, auth): self.__auth = auth
  def get_auth(self): return self.__auth
  def set_crawl(self, crawl): self.__crawl = crawl
  def is_crawl(self): return self.__crawl
  def set_crawl_plugins(self, crawl_plugins): self.__crawl_plugins = crawl_plugins
  def is_crawl_plugins(self): return self.__crawl_plugins
  def set_deep_crawl(self, deep_crawl): self.__deep_crawl = deep_crawl
  def is_deep_crawl(self): return self.__deep_crawl
  def set_depth(self, depth): self.__depth = depth
  def get_depth(self): return self.__depth
  def add_hosts(self, hosts): self.__hosts.extend(hosts)
  def get_hosts(self): return self.__hosts
  def set_poll(self, poll): self.__poll = poll
  def is_poll(self): return self.__poll
  def set_reload_config(self, reload_config): self.__reload_config = reload_config
  def is_reload_config(self): return self.__reload_config
  def set_wait(self, wait): self.__wait = wait
  def get_wait(self): return self.__wait

# Global
must_sleep = False

def make_parser():
  parser = optparse.OptionParser(version=__version__, usage='%prog [--host=HOST] [--hosts=HFILE] [OPTIONS] [--auids=AFILE] [AUID...]')
  parser.add_option('--auids', action='append', default=list(), metavar='AFILE', help='adds AUIDs from AFILE to the list of AUIDs')
  parser.add_option('--crawl', action='store_true', default=False, help='requests crawl of selected AUs')
  parser.add_option('--crawl-plugins', action='store_true', default=False, help='causes plugin registries to be crawled')
  parser.add_option('--deep-crawl', action='store_true', default=False, help='requests deep crawl of selected AUs')
  parser.add_option('--depth', type='int', default=Options.DEPTH, help='depth of deep crawls (default %default)')
  parser.add_option('--host', action='append', default=list(), help='adds host name and port to the list of hosts')
  parser.add_option('--hosts', action='append', default=list(), metavar='HFILE', help='adds host names and ports from HFILE to the list of hosts')
  parser.add_option('--password', metavar='PASS', help='UI password')
  parser.add_option('--poll', action='store_true', default=False, help='calls poll on selected AUs')
  parser.add_option('--reload-config', action='store_true', default=False, help='causes the config to be reloaded')
  parser.add_option('--username', metavar='USER', help='UI username')
  parser.add_option('--wait', type='int', default=Options.WAIT, metavar='SEC', help='wait SEC seconds between requests (default %default)')
  return parser

def process_options(opts, args):
  options = Options()
  if len(filter(None, [opts.crawl, opts.crawl_plugins, opts.deep_crawl, opts.poll, opts.reload_config])) == 0:
    sys.exit('Error: at least one of --crawl, --crawl-plugins, --deep-crawl, --poll, --reload-config is required')
  if len(opts.host) + len(opts.hosts) == 0: sys.exit('Error: at least one host is required')
  options.add_hosts(opts.host)
  for f in opts.hosts: options.add_hosts(file_lines(f))
  options.set_crawl(opts.crawl)
  options.set_crawl_plugins(opts.crawl_plugins)
  options.set_deep_crawl(opts.deep_crawl)
  options.set_poll(opts.poll)
  options.set_reload_config(opts.reload_config)
  if len(filter(None, [opts.crawl, opts.deep_crawl, opts.poll])) > 0 and len(args) + len(opts.auids) == 0:
    sys.exit('Error: for --crawl, --deep-crawl, --poll, at least one AUID is required')
  options.add_auids(args)
  for f in opts.auids: options.add_auids(file_lines(f))
  if opts.username is None: u = raw_input('UI username: ')
  else: u = opts.username
  if opts.password is None: p = getpass.getpass('UI password: ')
  else: p = opts.password
  options.set_auth(base64.encodestring('%s:%s' % (u, p)).replace('\n', ''))
  options.set_depth(opts.depth)
  options.set_wait(opts.wait)
  return options

def do_crawl_plugins(options, host):
  do_per_host(options, host, 'Crawl Plugins')

def do_reload_config(options, host):
  do_per_host(options, host, 'Reload Config')

def do_per_host(options, host, action):
  maybe_sleep(options)
  action_enc = action.replace(' ', '%20')
  req = make_request(options, host, 'action=%s' % (action_enc,))
  execute_request(req, host)

def do_crawl(options, host, auid):
  do_per_auid(options, host, 'Force Start Crawl', auid)

def do_deep_crawl(options, host, auid):
  do_per_auid(options, host, 'Force Deep Crawl', auid, depth=options.get_depth())

def do_poll(options, host, auid):
  do_per_auid(options, host, 'Start V3 Poll', auid)

def do_per_auid(options, host, action, auid, **kwargs):
  maybe_sleep(options)
  action_enc = action.replace(' ', '%20')
  auid_enc = auid.replace('%', '%25').replace('|', '%7C').replace('&', '%26').replace('~', '%7E')
  req = make_request(options, host, 'action=%s&auid=%s' % (action_enc, auid_enc), **kwargs)
  execute_request(req, host)

def maybe_sleep(options):
  global must_sleep
  if must_sleep: time.sleep(options.get_wait())
  must_sleep = True

def make_request(options, host, query, **kwargs):
  for k, v in kwargs.iteritems(): query = '%s&%s=%s' % (query, k, v)
  req = urllib2.Request('http://%s/DebugPanel?%s' % (host, query))
  req.add_header('Authorization', 'Basic %s' % options.get_auth())
  return req

def execute_request(req, host):
  try: return urllib2.urlopen(req)
  except urllib2.URLError as e:
    sys.exit('Error: %s: %s' % (host, e.reason))
  except urllib2.HTTPError as e:
    if e.code == 401: sys.exit('Error: %s: bad username or password (HTTP 401)' % (host,))
    else: sys.exit('Error: %s: HTTP %d' % (host, e.code,))

def file_lines(filestr):
  ret = [line.strip() for line in open(filestr).readlines() if not (line.isspace() or line.startswith('#'))]
  if len(ret) == 0: sys.exit('Error: %s contains no meaningful lines' % (filestr,))
  return ret

if __name__ == '__main__':
  parser = make_parser()
  (opts, args) = parser.parse_args()
  options = process_options(opts, args)
  for host in options.get_hosts():
    if options.is_crawl_plugins(): do_crawl_plugins(options, host)
    if options.is_reload_config(): do_reload_config(options, host)
    for auid in options.get_auids():
      if options.is_crawl(): do_crawl(options, host, auid)
      if options.is_deep_crawl(): do_deep_crawl(options, host, auid)
      if options.is_poll(): do_poll(options, host, auid)

