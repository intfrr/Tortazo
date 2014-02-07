# coding=utf-8

from stem.descriptor.remote import DescriptorDownloader
from stem import CircStatus
from stem.control import Controller
from stem.connection import MissingPassword, AuthenticationFailure
from getpass import getpass
from stem.util import term
import logging as log
from time import gmtime, strftime
import zlib
import nmap

class Discovery:
	'''
		Class used to list the current "exit-nodes" from the TOR network and perform the nmap scanning to discover the open ports.
	'''
	exitNodes = {}
	cli = None
	scan = None

	def __init__(self, cli):
		self.cli = cli
		if self.cli.verbose:
			log.basicConfig(format="%(levelname)s: %(message)s", level=log.DEBUG)
			log.info(term.format("[+] Verbose mode activated.", term.Color.GREEN))
		else:
			log.basicConfig(format="%(levelname)s: %(message)s")
		log.info(term.format("[+] Process started at "+ strftime("%Y-%m-%d %H:%M:%S", gmtime()), term.Color.GREEN))

	def listAuthorityExitNodes(self):
		'''
			List the Exit Nodes using the filters specified by command-line.
		'''
		log.info(term.format("[+] Try to listing the current Exit-Nodes of TOR.", term.Color.GREEN))
		if self.cli.exitNodeFingerprint != None:
			log.info(term.format("[+] Using the fingerprint: %s " % (self.cli.exitNodeFingerprint), term.Color.GREEN))
		log.info(term.format("[+] Filter by platform: %s." % (self.cli.mode), term.Color.GREEN))
		log.info(term.format("[+] Retrieving the first %d records in the Descriptors." %(self.cli.exitNodesToAttack) , term.Color.GREEN))
		
		if self.cli.useMirror == True:
			log.info(term.format("[+] Using the Directory Mirrors to get the descriptors", term.Color.GREEN))
		downloader = DescriptorDownloader(use_mirrors=self.cli.useMirror)
		if self.cli.exitNodeFingerprint != None:
			descriptors = downloader.get_server_descriptors(fingerprints=[self.cli.exitNodeFingerprint])
		else:
			descriptors = downloader.get_server_descriptors()
		try:
			listDescriptors = descriptors.run()
		except zlib.error:
			log.error(term.format("[-] Error fetching the TOR descriptors. This is something quite common... Try again in a few seconds.", term.Color.RED))
			return
		return self.filterNodes(listDescriptors)

	def listCircuitExitNodes(self):
		listDescriptors = []
		log.info(term.format("[+] Trying to get a list of exit nodes from the already downloaded descriptors from the TOR Client instead of using the authority directories", term.Color.GREEN))
		if self.cli.controllerPort and self.cli.controllerPort.isdigit():
			try:
				controllerPass = getpass("Enter the password for the Local Controller (Empty if the instance doesn't need a password): ")
				controller = Controller.from_port(port = int(self.cli.controllerPort))
				if controllerPass:
					controller.authenticate(controllerPass)
				else:
					controller.authenticate()
				log.info(term.format("[+] TOR Controller Authentication Successful.", term.Color.GREEN))
				for circuit in controller.get_circuits():
					if circuit.status != CircStatus.BUILT:
						continue
					exit_fingerprint, exit_nickname = circuit.path[-1]
					'''
					As of Tor version 0.2.3.25 relays no longer get server descriptors by default. It's advised that you use microdescriptors instead, but if you really need server descriptors then you can get them by setting UseMicrodescriptors 0.				
					'''
					exitNode = controller.get_server_descriptor(exit_fingerprint, None)
					if exitNode:
						listDescriptors.append(exitNode)
					return self.filterNodes(listDescriptors)			
					#exit_address = exit_desc.address if exit_desc else 'unknown'
					#print "Exit relay"
					#print "  fingerprint: %s" % exit_fp
					#print "  nickname: %s" % exit_nickname
					#print "  address: %s" % exit_address
					#print
			except MissingPassword:
				log.warn(term.format("[-] Expected password in the AUTH process... This should not be empty", term.Color.RED))
			except AuthenticationFailure:
				log.warn(term.format("[-] The password specified is invalid.", term.Color.RED))
		else:
			log.warn(term.format("[-] The control port specified is invalid.", term.Color.RED))
	
	def filterNodes(self, listDescriptors):
		
		'''
			List the Exit Nodes using the filters specified by command-line.
		'''
		nodesAlreadyScanned = []
		nm = nmap.PortScanner()
		for descriptor in listDescriptors[0:self.cli.exitNodesToAttack]:
		#for descriptor in parse_file(open("/home/adastra/Escritorio/tor-browser_en-US-Firefox/Data/Tor/cached-consensus")):
			if self.cli.mode.lower() in descriptor.operating_system.lower() and descriptor.exit_policy.is_exiting_allowed():
				#SEARCH FILTERING BY FINGERPRINT
				#Conditions: Fingerprint specified in command-line AND
				#	 Relay Fingerprint equals to the Fingerprint specified in command-line. AND 
				#	 Relay's Operative System equals to the Operative System (option mode) specified in command-line AND
				#	 The Relay is a Exit Node. 	
				if descriptor.address not in nodesAlreadyScanned:
					log.info(term.format("[+] %s System has been found... Nickname: %s - OS Version: %s" % (descriptor.operating_system, descriptor.nickname, descriptor.operating_system), term.Color.YELLOW))
					log.info(term.format("[+] Starting the NMap Scan with the following options: ", term.Color.GREEN))
					log.info(term.format("[+][+] Scan Address: %s " % (descriptor.address), term.Color.GREEN))
					log.info(term.format("[+][+] Scan Arguments: %s " % (self.cli.scanArguments), term.Color.GREEN))
					log.info(term.format("[+][+] Scan Ports: %s " % (self.cli.scanPorts), term.Color.GREEN))
					if self.cli.scanArguments != None:
						nm.scan(descriptor.address, self.cli.scanPorts, arguments=self.cli.scanArguments)
					else:
						nm.scan(descriptor.address, self.cli.scanPorts)	
					self.recordNmapScan(nm)
					log.info(term.format('[+] Scan Ended for %s .' % (descriptor.nickname), term.Color.YELLOW))
					nodesAlreadyScanned.append(descriptor.address)
		if len(self.exitNodes) == 0:
			log.info(term.format("[+] In the first %d records searching for the %s Operating System, there's no results (machines with detected open ports)" %(self.cli.exitNodesToAttack, self.cli.mode.lower()), term.Color.RED))
		return self.exitNodes
	
	
	def recordNmapScan(self, scan):
		'''
			Performs the NMap scan using python-nmap library.
			Returns the exitnodes with the open ports found in the scanning process.
		'''
		entryFile = 'nmapScan.txt'
		nmapFileResults = open(entryFile, 'a')

		for host in scan.all_hosts():
			entry = '------- NMAP SCAN REPORT START FOR %s------- \n' %(host)
			entry += '[+] Host: %s \n' % (host)
			if scan[host].has_key('status'):
				entry += '[+][+]State: %s \n' % (scan[host]['status']['state'])
				entry += '[+][+]Reason: %s \n' % (scan[host]['status']['reason'])
			if scan[host].has_key(self.cli.scanProtocol):
				mapPorts = scan[host][self.cli.scanProtocol].keys()
				for port in mapPorts:
					entry += 'Port: %s \n' % (port)
					entry += 'State: %s \n ' % (scan[host][self.cli.scanProtocol][port]['state'])
					if 'open' in (scan[host][self.cli.scanProtocol][port]['state']):
						self.exitNodes[host] = port
					if scan[host][self.cli.scanProtocol][port].has_key('reason'):
						entry += 'Reason: %s \n ' % (scan[host][self.cli.scanProtocol][port]['reason'])
					if scan[host][self.cli.scanProtocol][port].has_key('name'):
						entry += 'Name: %s \n ' % (scan[host][self.cli.scanProtocol][port]['name'])
			else:
				log.info(term.format("[-] There's no match in the Nmap scan with the specified protocol %s" %(self.cli.scanProtocol), term.Color.RED))
			entry += '------- NMAP SCAN REPORT END ------- \n'
			entry += '\n\n'
			nmapFileResults.write(entry)
		nmapFileResults.close()