from typing import Any, Type
from zeroconf import ServiceInfo, Zeroconf
from http.server import SimpleHTTPRequestHandler, HTTPServer
from .shared.node import OSCQueryNode, OSCHostInfo, OSCAccess
import json, threading


class OSCQueryService(object):
    """
    A class providing an OSCQuery service. Automatically sets up a oscjson http server
    and advertises the oscjson server and osc server on zeroconf.
    
    Description
    -----------
    OSCQueryService is a class designed to facilitate an OSCQuery service.
    It automatically sets up an oscjson HTTP server and advertises the oscjson
    server and osc server on zeroconf. This class allows adding nodes to the 
    OSCQueryService and advertising endpoints with given addresses and optional values.

    Attributes
    ----------
    serverName : str
        Name of your OSC Service
    httpPort : int
        Desired TCP port number for the oscjson HTTP server
    oscPort : int
        Desired UDP port number for the osc server
    oscIP : str
        The IP address used for OSC communication. Defaults to LocalHost if not specified.
    """
    def __init__(self, serverName: str, httpPort: int, oscPort: int, oscIp="127.0.0.1") -> None:
        self.serverName = serverName
        self.httpPort = httpPort
        self.oscPort = oscPort
        self.oscIp = oscIp

        self.root_node = OSCQueryNode("/", description="root node")
        self.host_info = OSCHostInfo(
            serverName,
            {"ACCESS":True,"CLIPMODE":False,"RANGE":True,"TYPE":True,"VALUE":True},
            self.oscIp, self.oscPort, "UDP"
        )

        self._zeroconf = Zeroconf()
        self._startOSCQueryService()
        self._advertiseOSCService()
        self.http_server = OSCQueryHTTPServer(
            self.root_node, self.host_info, ('', self.httpPort), OSCQueryHTTPHandler
        )
        self.http_thread = threading.Thread(target=self._startHTTPServer)
        self.http_thread.start()

    def __del__(self) -> None:
        self._zeroconf.unregister_all_services()

    def add_node(self, node: OSCQueryNode) -> None:
        """
        Add a node to the OSCQueryService.

        Parameters
        ----------
        node : OSCQueryNode
            The node to be added
        """
        self.root_node.add_child_node(node)

    def advertise_endpoint(self, address: str, value: list[Any]|Any = None,
                           access:OSCAccess = OSCAccess.READWRITE_VALUE) -> None:
        """
        Advertise an endpoint with a given address and optional value.

        Parameters
        ----------
        address : str
            The address of the endpoint.
        value : Any, optional
            The value of the endpoint. represents one or multiple values (default: None).
        access : OSCAccess, optional
            The access level of the endpoint (default: READWRITE_VALUE).
        """
        new_node = OSCQueryNode(full_path=address, access=access)
        if value is not None:
            if not isinstance(value, list):
                new_node.value = [value]
                new_node.type_ = [type(value)]
            else:
                new_node.value = value
                new_node.type_ = [type(v) for v in value]
        self.add_node(new_node)

    def _startOSCQueryService(self) -> None:
        """Starts the OSCQuery service by registering OSCQuery service information."""
        oscqsDesc = {'txtvers': 1}
        oscqsInfo = ServiceInfo(
            "_oscjson._tcp.local.", "%s._oscjson._tcp.local." % self.serverName, self.httpPort,
            0, 0, oscqsDesc, "%s.oscjson.local." % self.serverName, addresses=["127.0.0.1"]
        )
        self._zeroconf.register_service(oscqsInfo)


    def _startHTTPServer(self) -> None:
        """Starts the HTTP server by serving requests forever."""
        self.http_server.serve_forever()

    def _advertiseOSCService(self) -> None:
        """Advertises the OSC service by registering OSC service information."""
        oscDesc = {'txtvers': 1}
        oscInfo = ServiceInfo(
            "_osc._udp.local.", "%s._osc._udp.local." % self.serverName, self.oscPort,
            0, 0, oscDesc, "%s.osc.local." % self.serverName, addresses=["127.0.0.1"]
        )

        self._zeroconf.register_service(oscInfo)


class OSCQueryHTTPServer(HTTPServer):
    """
    Custom HTTP server for OSCQuery service.
    
    Attributes
    ----------
    root_node : OSCQueryNode
        The root node of the OSCQuery service.
    host_info : OSCHostInfo
        Information about the host.
    server_address : tuple[str, int]
        A tuple containing the IP address and port number.
    RequestHandlerClass : Type[SimpleHTTPRequestHandler]
        The class to handle incoming requests.
    bind_and_activate : bool
        A boolean indicating whether to bind and activate the server.
    """
    def __init__(
        self,
        root_node: OSCQueryNode,
        host_info: OSCHostInfo,
        server_address: tuple[str, int],
        RequestHandlerClass: Type[SimpleHTTPRequestHandler],
        bind_and_activate: bool = True
    ) -> None:

        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        self.root_node = root_node
        self.host_info = host_info


class OSCQueryHTTPHandler(SimpleHTTPRequestHandler):
    """HTTP request handler for OSCQuery service."""

    def do_GET(self) -> None:
        """
        Handle GET requests.
        If the requested path is 'HOST_INFO', returns host information as JSON.
        If the requested path is a valid OSCQuery node, returns node information as JSON.
        Otherwise, returns a 404 error.
        """
        if 'HOST_INFO' in self.path:
            self.send_response(200)
            self.send_header("Content-type", "text/json")
            self.end_headers()
            self.wfile.write(bytes(str(self.server.host_info.to_json()), 'utf-8'))
            return
        node = self.server.root_node.find_subnode(self.path)
        if node is None:
            self.send_response(404)
            self.send_header("Content-type", "text/json")
            self.end_headers()
            self.wfile.write(bytes("OSC Path not found", 'utf-8'))
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/json")
            self.end_headers()
            self.wfile.write(bytes(str(node.to_json()), 'utf-8'))

    def log_message(self, format: str, *args) -> None:
        """Override default log message behavior."""
        pass
