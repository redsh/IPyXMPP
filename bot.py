#!/usr/bin/python
# -*- coding: utf-8 -*-

# ipyxmpp: simple hack to have an IPython shell wrapped in a xmpp bot.

# Copyright (c) 2014, Francesco 'redsh' Rossi
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys,os,re
from cStringIO import StringIO
import logging
import getpass
from optparse import OptionParser
import base64
import sleekxmpp

import IPython
from IPython.core.interactiveshell import InteractiveShell, InteractiveShellABC
from IPython.terminal.interactiveshell import TerminalInteractiveShell
#from IPython.terminal.console.interactiveshell import ZMQTerminalInteractiveShell
from IPython.utils.traitlets import (Integer, CBool, CaselessStrEnum, Enum,
                                     List, Unicode, Instance, Type)
from IPython.config.configurable import Configurable
from IPython.config.loader import (
    Config, PyFileConfigLoader, ConfigFileNotFound
)

if sys.version_info < (3, 0):
    from sleekxmpp.util.misc_ops import setdefaultencoding
    setdefaultencoding('utf8')
else:
    raw_input = input

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

#Relays to the xmpp client

class MulticastIO():
    def __init__(self, streams):
        self.streams = streams

    def write(self,what,*args,**kwargs):
        for s in self.streams:
            s.write(what,*args,**kwargs)

    def flush(self):
        for s in self.streams:
            s.flush()

class DummyPublishser(Configurable):
    def publish(self, source, data, metadata=None):
        self.xmpp_client.publish(source,data,metadata)


class XMPPInteractiveShell(InteractiveShell):
    display_pub_class = Type(DummyPublishser)
    prompt_out = ''

    def __init__(self, xmpp_client, *args, **kwargs):

        self.real_stdout = sys.stdout
        self.real_stderr = sys.stderr

        self.stdout = StringIO()
        self.stderr = StringIO()

        sys.stdout = MulticastIO((sys.stdout, self.stdout))
        sys.stderr = MulticastIO((sys.stderr, self.stderr))

        super(XMPPInteractiveShell,self).__init__(*args,**kwargs)
        
        InteractiveShell._instance = self
        self.display_pub.xmpp_client = xmpp_client

        self.prompt_manager.in_template = ''
        self.prompt_manager.in2_template = ''
        self.prompt_manager.out_template = ''

        self.enable_pylab('inline')#'inline')

   
    def __del__(self):
        sys.stdout = self.real_stdout
        sys.stderr = self.stderr

    def enable_gui(self,gui):
        pass

    def flush(self):
        ret = self.stdout.getvalue()
        ret_e = self.stderr.getvalue()
        if ret_e:
            ret_e = 'Error#>'+ret_e
        else:
            ret_e = ''

        self.stdout.truncate(0)
        self.stderr.truncate(0)

        return ret+ret_e

    def put(self,line):
        try:
            self.input_splitter.push(line)
            more = self.input_splitter.push_accepts_more()
        except SyntaxError:
            more = False

        if (self.SyntaxTB.last_syntax_error and
            self.autoedit_syntax):
            self.edit_syntax_error()
    
        source_raw = self.input_splitter.source_raw
        self.input_splitter.reset()
        ret = self.run_cell(source_raw, store_history=True)

        return ret


InteractiveShellABC.register(XMPPInteractiveShell)

class SimplePassphraseSecurity(object):
    def __init__(self,passphrase):
        self.passphrase = passphrase
        self.allowed_jabberids = {}

    def is_authorized(self, msg):
        sender = msg['from']

        if self.passphrase == None:
            return True
        elif self.allowed_jabberids.has_key(sender):
            return True
        elif msg['body'] == self.passphrase:
            self.allowed_jabberids[sender] = 1
            msg.reply(self.reply_prompt+'Passphrase check passed. You can now enter IPython commands.').send()
            return False
        else:
            msg.reply(self.reply_prompt+'Enter the passphrase please.').send()
            return False

class IPyBot(sleekxmpp.ClientXMPP):

    def __init__(self, jid, password, security, reply_prompt='> ', *args, **kwargs):        
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        self.add_event_handler("session_start", self.on_start)
        self.add_event_handler("message", self.on_message)

        self.register_plugin('xep_0030')
        self.register_plugin('xep_0066') # OOB
        self.register_plugin('xep_0231') # BOB

        self.sh = XMPPInteractiveShell(self, *args, **kwargs)
        self.security = security

        self.security.reply_prompt = reply_prompt
        self.reply_prompt = reply_prompt


    def on_start(self, event):
        self.send_presence()
        self.get_roster()
   
    def send_image_bob(self,jid, img, ctype): 
        m = self.Message()
        m['to'] = jid
        m['type'] = 'chat'
        
        cid = self['xep_0231'].set_bob(img, ctype)
        m['body']=self.reply_prompt
        m['html']['body'] = '<img src="cid:%s" />' % cid
        #m['body'] = 'https://plus.google.com/photos/albums/p4kcrshcfkg4lc212julf58nd92794ek8?pid=5987987735848990258&amp;oid=109602992525348911397'
        #m['html']['body'] = '<img src="https://lh6.googleusercontent.com/-riwta-GT3d4/AAAAAAAAAAI/AAAAAAAAHj4/Qu6lGVwCfbY/s24-c-k-no/photo.jpg"/>'
        #m['bob']['cid'] = cid
        #m['bob']['type'] = 'image/png'
        #m['bob']['data'] = img
        #m['html']['body'] = '<a href="data:image/png;base64,%s">image</a>' % base64.b64encode(img)
        
        #m['attachment'] = base64.b64encode(img)
        #m['body'] = 'https://lh6.googleusercontent.com/-riwta-GT3d4/AAAAAAAAAAI/AAAAAAAAHj4/Qu6lGVwCfbY/s24-c-k-no/photo.jpg'
        #m['body'] = 'http://i.stack.imgur.com/0kfu2.png'
        #m['html']['body'] = '<a href="%s">f</a>'%'https://lh6.googleusercontent.com/-riwta-GT3d4/AAAAAAAAAAI/AAAAAAAAHj4/Qu6lGVwCfbY/s24-c-k-no/photo.jpg'
        #print m
        m.send()
 
    def publish(self, source, data, metadata=None):
        for k in data:
            if k == 'text/plain':
                m = self.Message()
                m['to'] = self.last_from
                m['type'] = 'chat'
                m['body'] = self.reply_prompt+data[k]
                m.send()
            else:
                self.send_image_bob(self.last_from, data[k], k)

    #In case we want bots talking to each other
    def do_run_reply_msg(self,msg):
        #implement in subclasses
        return False

    def on_message(self, msg):
        logging.debug(str(('incoming',msg))+'\n')
        
        if not (msg['type'] in ('chat', 'normal')):
            return
        if not self.security.is_authorized(msg):
            return

        src = "%(body)s"%msg

        #In case we want bots talking to each other
        if self.reply_prompt:
            if (src).startswith(self.reply_prompt):
                if not self.do_run_reply_msg(msg):
                    return
                else:
                    src = src[len(self.reply_prompt):]
        
        self.last_from = msg['from']
        ret = self.sh.put(src)
        
        #Get output text and clear term colors
        x = self.sh.flush()
        p = re.compile('\033\[([0-9]+);([0-9]+)m')
        x = p.sub('',x)
        x = x.replace('\033[0m','')
        x = x.replace('\033','')

        self.send_message(self.last_from, self.reply_prompt+x)

    def send_message(self, to_jid, body, html_body=None):
        m = self.Message()
        m['to'] = to_jid
        m['type'] = 'chat'
        m['body'] = body
        if html_body:
            m['html']['body'] = html_body

        logging.debug(str(('sending',m))+'\n')
        
        m.send()

    def run(self):
        self.process(block=True)

def create_ipyxmpp_bot(jid,password,server,passphrase,cls=IPyBot,*args,**kwargs
    ):
    xmpp = cls(jid, password, SimplePassphraseSecurity(passphrase), *args, **kwargs)
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0004') # Data Forms
    xmpp.register_plugin('xep_0060') # PubSub
    xmpp.register_plugin('xep_0199') # XMPP Ping
    
    params = None
    if jid.endswith('gmail.com'):
        params = ('talk.google.com', 5222)
    if server != '' and server:
        params = server.split(':')

    if xmpp.connect(params):
        return xmpp

if __name__ == '__main__':
    # Setup the command line arguments.
    optp = OptionParser()

    # Output verbosity options.
    optp.add_option('-q', '--quiet', help='set logging to ERROR',
                    action='store_const', dest='loglevel',
                    const=logging.ERROR, default=logging.INFO)
    optp.add_option('-d', '--debug', help='set logging to DEBUG',
                    action='store_const', dest='loglevel',
                    const=logging.DEBUG, default=logging.INFO)
    optp.add_option('-v', '--verbose', help='set logging to COMM',
                    action='store_const', dest='loglevel',
                    const=5, default=logging.INFO)

    # JID and password options.
    optp.add_option("-j", "--jid", dest="jid",
                    help="JID to use")
    optp.add_option("-p", "--password", dest="password",
                    help="password to use")
    optp.add_option("-s", "--server", dest="server",
                    help="server hostname:port", default=None)
    optp.add_option("-a", "--passphrase", dest="passphrase", default=None,
                    help="Password that the XMPP peer has to enter in order to run IPython commands.")

    opts, args = optp.parse_args()

    # Setup logging.
    logging.basicConfig(level=opts.loglevel,
                        format='%(levelname)-8s %(message)s')

    if opts.jid is None:
        opts.jid = raw_input("Username: ")
    if opts.password is None:
        opts.password = getpass.getpass("Password: ")

    xmpp = create_ipyxmpp_bot(opts.jid, opts.password, opts.server, opts.passphrase)
    xmpp.run()

