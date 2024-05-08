import socket
import threading
from typing import Any, Type
from http.server import SimpleHTTPRequestHandler, HTTPServer
from zeroconf import ServiceInfo, Zeroconf
from .shared.node import OSCQueryNode, OSCHostInfo, OSCAccess


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
    start : bool
        Choose if the class automatically starts the services. Defaults to True
    """

    def __init__(
        self, serverName: str, httpPort: int, oscPort: int,
        oscIp: str = "127.0.0.1", start: bool = True
    ) -> None:
        self.serverName = serverName
        self.httpPort = httpPort
        self.oscPort = oscPort
        self.oscIp = oscIp

        self.root_node = OSCQueryNode("/", description="root node")
        self.host_info = OSCHostInfo(
            serverName,
            {
                "ACCESS": True, "CLIPMODE": False,
                "RANGE": True, "TYPE": True, "VALUE": True
            },
            self.oscIp, self.oscPort, "UDP"
        )

        self._zeroconf = None
        self.http_server = None
        self.http_thread = None
        if start:
            self.start()

    def __enter__(self) -> "OSCQueryService":
        """Set up method to create a context manager"""
        return self

    def __exit__(self, *args):
        """Stops all active services when the context manager closes"""
        self.stop()

    def start(self) -> None:
        """
        Start the services required by the class.
        Potential Raises: ValueError

        This method initializes Zeroconf and HTTP services.
        """
        self._zeroconf = Zeroconf()
        self._startOSCQueryService()
        self._advertiseOSCService()
        self.http_server = OSCQueryHTTPServer(
            self.root_node, self.host_info, (
                '', self.httpPort
            ), OSCQueryHTTPHandler
        )
        self.http_thread = threading.Thread(target=self._startHTTPServer)
        self.http_thread.start()

    def stop(self) -> None:
        """
        Stop the services managed by the class.

        This method stops all services initiated by the `start` method.
        It includes unregistering services from Zeroconf,
        shutting down the HTTP server, and joining the HTTP server thread.
        """
        if self._zeroconf:
            self._zeroconf.unregister_all_services()
            self._zeroconf.close()
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
        if self.http_thread:
            self.http_thread.join()

    def add_node(self, node: OSCQueryNode) -> None:
        """
        Add a node to the OSCQueryService.

        Parameters
        ----------
        node : OSCQueryNode
            The node to be added
        """
        self.root_node.add_child_node(node)

    def advertise_endpoint(
        self, address: str, value: list[Any] | Any = None,
        access: OSCAccess = OSCAccess.READWRITE_VALUE
    ) -> None:
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

    def _register_service(
        self, service_name: str, name_suffix: str,
        port: int, desc: dict[str, int], ip: str = "127.0.0.1"
    ) -> None:
        """
        Registers a service with the provided parameters using Zeroconf.
        The service will be available for discovery on the network.
        Potential Raises: ValueError

        Parameters
        ----------
        service_name : str
            The name of the service.
        name_suffix : str
            The suffix to be appended to the service name.
        port : int
            The port on which the service is running.
        desc : dict[str, int]
            A dictionary containing descriptive information about the service.
        ip : str, optional
            The IP address on which the service will be available. Default is "127.0.0.1".
        """
        if not self._zeroconf:
            raise ValueError(
                "Zeroconf was not initialized. Failed to register service."
            )

        self._zeroconf.register_service(ServiceInfo(
            service_name,
            f"{self.serverName}.{service_name}",
            port, 0, 0, desc,
            f"{self.serverName}.{name_suffix}",
            addresses=[socket.inet_pton(socket.AF_INET, ip)]
        ))

    def _startOSCQueryService(self) -> None:
        """Starts the OSCQuery service by registering OSCQuery service information."""
        oscqs_desc = {'txtvers': 1}
        self._register_service(
            "_oscjson._tcp.local.",
            "oscjson.local.",
            self.httpPort,
            oscqs_desc
        )

    def _startHTTPServer(self) -> None:
        """Starts the HTTP server by serving requests forever."""
        if not self.http_server:
            raise ValueError(
                "HTTP Server was not initialized. Failed to serve."
            )
        self.http_server.serve_forever()

    def _advertiseOSCService(self) -> None:
        """Advertises the OSC service by registering OSC service information."""
        osc_desc = {'txtvers': 1}
        self._register_service(
            "_osc._udp.local.",
            "osc.local.",
            self.oscPort,
            osc_desc
        )


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
    # Used for static type checking
    # must be 'server' to use the super class variable
    server: 'OSCQueryService'  # FIXME # type: ignore

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
            self.wfile.write(bytes(str(
                self.server.host_info.to_json()
            ), 'utf-8'))
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
