# coding=utf-8
'''
Created on 22/01/2014

#Author: Adastra.
#twitter: @jdaanial

BasePlugin.py

BasePlugin is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

BasePlugin is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Tortazo; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
'''

import logging as log
from stem.util import term
from IPython.config.loader import Config
from IPython.terminal.embed import InteractiveShellEmbed
import socks
import socket
import config
from prettytable import PrettyTable

class BasePlugin():
    '''
    Every plugin in Tortazo should inher
    '''

    def __init__(self, torNodes, pluginLoaded):
        '''
        Constructor for the Base plugin class.
        '''
        self.logger = log
        self.torNodes = []
        self.pluginArguments = {}
        self.logger.basicConfig(format="%(levelname)s: %(message)s", level=log.DEBUG)
        self.torNodes = torNodes
        self.pluginLoaded = pluginLoaded

    def info(self, message):
         self.logger.info(term.format(message, term.Color.YELLOW))

    def error(self, message):
        self.logger.warn(term.format(message, term.Color.RED))

    def debug(self, message):
        self.logger.debug(term.format(message, term.Color.GREEN))

    def printRelaysFound(self):
        #tableRelays = PrettyTable(["Host", "State", "Reason", "NickName", "Open Ports"])
        tableRelays = PrettyTable(["NickName", "Host", "State", "Reason", "Open Ports"])
        tableRelays.padding_width = 1
        openPorts = None

        for torNode in self.torNodes:
            for port in torNode.openPorts:
                openPorts = ''
                openPorts += str(port.reason)+':'+str(port.port)

            if openPorts is None:
                tableRelays.add_row([torNode.nickName,torNode.host,torNode.state,torNode.reason,'No open ports found'])
            else:
                tableRelays.add_row([torNode.nickName,torNode.host,torNode.state,torNode.reason,openPorts])
            openPorts = None
        print tableRelays.get_string(sortby='NickName')

    def runPlugin(self):
        '''
        The most simplest plugin! Just prints the tor data structure.
        '''
        try:
            get_ipython
        except NameError:
            nested = 0
            cfg = Config()
            prompt_config = cfg.PromptManager
            prompt_config.in_template = 'Tortazo Plugin <%s> : ' %(self.pluginLoaded)
            prompt_config.in2_template = "Type 'self.help()' to get information about the functions available in this plugin :"
        else:
            cfg = Config()
            nested = 1
        tortazoShell = InteractiveShellEmbed(config=cfg,banner1 = 'Loading Tortazo plugin interpreter... ',banner2="Plugin %s loaded successfully! Type self.help() to get information about this plugin and exit() to finish the execution. "%(self.pluginLoaded), exit_msg = 'Leaving Tortazo plugin interpreter.')
        tortazoShell()

    def create_connection(self, address, timeout=None, source_address=None):
        sock = socks.socksocket()
        sock.connect(address)
        return sock

    def setSocksProxy(self):
        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5 , config.socksHost, config.socksPort, True)
        socket.socket = socks.socksocket
        socket.create_connection = self.create_connection

    def help(self):
        pass