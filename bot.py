#!/usr/bin/python
# -*- coding: utf-8 -*-

# ipyxmpp: hack to have an IPython shell 

#Copyright (c) 2014, Francesco 'redsh' Rossi
#All rights reserved.

#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the <organization> nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
#DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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
from IPython.terminal.console.interactiveshell import ZMQTerminalInteractiveShell
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


class DummyPublishser(Configurable):

    def publish(self, source, data, metadata=None):
        #print 'SOURCE,DATA',source, data
        self.xmpp_service.publish(source,data,metadata)

class XMPPInteractiveShell(InteractiveShell):
    display_pub_class = Type(DummyPublishser)
    prompt_out = ''

    def __init__(self, xmpp_service):

        self.real_stdout = sys.stdout
        self.real_stderr = sys.stderr

        self.stdout = StringIO()
        self.stderr = StringIO()

        sys.stdout = self.stdout
        sys.stderr = self.stderr

        import IPython.kernel.inprocess
        super(XMPPInteractiveShell,self).__init__()
        InteractiveShell._instance = self
        self.display_pub.xmpp_service = xmpp_service

        self.prompt_manager.in_template = ''
        self.prompt_manager.in2_template = ''
        self.prompt_manager.out_template = ''


        sys.stdout = self.real_stdout
        sys.stderr = self.real_stderr

        self.enable_pylab('inline')#'inline')
        
        sys.stdout = self.stdout
        sys.stderr = self.stderr

        self.real_stdout.write( self.flush() )
    
    def enable_gui(self,whu):
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
            #print line
            self.input_splitter.push(line)
            #print line
            more = self.input_splitter.push_accepts_more()
            #print more
        except SyntaxError:
            more = False

        if (self.SyntaxTB.last_syntax_error and
            self.autoedit_syntax):
            self.edit_syntax_error()
    
        if not more:
            source_raw = self.input_splitter.raw_reset()
            ret = self.run_cell(source_raw, store_history=True)

            #print '-----'

        return ret


InteractiveShellABC.register(XMPPInteractiveShell)


class EchoBot(sleekxmpp.ClientXMPP):

    """
    A simple SleekXMPP bot that will echo messages it
    receives, along with a short thank you message.
    """

    def __init__(self, jid, password):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        self.sh = XMPPInteractiveShell(self)
        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start)

        self.add_event_handler("message", self.message)

        self.register_plugin('xep_0030')
        self.register_plugin('xep_0066') # OOB
        self.register_plugin('xep_0231') # BOB

    def start(self, event):
        self.send_presence()
        self.get_roster()
   
    def send_image_bob(self,jid, img, ctype): 
        m = self.Message()
        m['to'] = jid
        m['type'] = 'chat'
        
        cid = self['xep_0231'].set_bob(img, ctype)
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
                m['body'] = data[k]
                m.send()
            else:
                self.send_image_bob(self.last_from, data[k], k)

    def message(self, msg):
        self.sh.real_stdout.write(str(('incoming',msg)))
        self.sh.real_stdout.write('\n')
        self.sh.real_stdout.flush()

        p = re.compile('\033\[([0-9]+);([0-9]+)m')

        if msg['type'] in ('chat', 'normal'):
            self.last_from = msg['from']
            
            ret = self.sh.put("%(body)s"%msg)

            if isinstance(ret, matplotlib.figure.Figure):
                print 'figure',dir(ret)
            #
            x = self.sh.flush()

            x = p.sub('',x)
            x = x.replace('\033[0m','')
            x = x.replace('\033','')

            self.sh.real_stdout.write(x)
            self.sh.real_stdout.write('\n')
            self.sh.real_stdout.flush()

            m = self.Message()
            m['to'] = self.last_from
            m['type'] = 'chat'
            m['body'] = x
            #m['html']['body'] = '<p><span style="color: #ff0000;">'+x+'</span></p>'
            m.send()


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

    opts, args = optp.parse_args()

    # Setup logging.
    logging.basicConfig(level=opts.loglevel,
                        format='%(levelname)-8s %(message)s')

    if opts.jid is None:
        opts.jid = raw_input("Username: ")
    if opts.password is None:
        opts.password = getpass.getpass("Password: ")

    xmpp = EchoBot(opts.jid, opts.password)
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0004') # Data Forms
    xmpp.register_plugin('xep_0060') # PubSub
    xmpp.register_plugin('xep_0199') # XMPP Ping
    
    params = None
    if opts.jid.endswith('gmail.com') and False:
        params = ('talk.google.com', 5222)

    if xmpp.connect(params):
        # If you do not have the dnspython library installed, you will need
        # to manually specify the name of the server if it does not match
        # the one in the JID. For example, to use Google Talk you would
        # need to use:
        #
        # if xmpp.connect(('talk.google.com', 5222)):
        #     ...
        xmpp.process(threaded=False)




