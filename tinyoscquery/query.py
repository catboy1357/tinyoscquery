import time
from typing import Any
from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf
import requests

from .shared.node import OSCQueryNode, OSC_Type_String_to_Python_Type, OSCAccess, OSCHostInfo


class OSCQueryListener(ServiceListener):
    """
    Listens for OSCQuery services on the network and maintains a list of discovered services.

    Description
    -----------
    This class listens for OSCQuery services on the network using Zeroconf and maintains
    two dictionaries to track discovered services:
        - `osc_services` for OSC services 
        - `oscjson_services` for OSCJSON services.
    """

    def __init__(self) -> None:
        self.osc_services = {}
        self.oscjson_services = {}

        super().__init__()

    def remove_service(self, zc: 'Zeroconf', type_: str, name: str) -> None:
        """
        Removes a service from the list of discovered services.

        Parameters
        ----------
        zc : Zeroconf
            The Zeroconf instance.
        type_ : str
            The type of the service.
        name : str
            The name of the service.
        """
        if name in self.osc_services:
            del self.osc_services[name]

        if name in self.oscjson_services:
            del self.oscjson_services[name]

    def add_service(self, zc: 'Zeroconf', type_: str, name: str) -> None:
        """
        Adds a service to the list of discovered services.

        Parameters
        ----------
        zc : Zeroconf
            The Zeroconf instance.
        type_ : str
            The type of the service.
        name : str
            The name of the service.
        """
        if type_ == '_osc._udp.local.':
            self.osc_services[name] = zc.get_service_info(type_, name)
        elif type_ == '_oscjson._tcp.local.':
            self.oscjson_services[name] = zc.get_service_info(type_, name)

    def update_service(self, zc: 'Zeroconf', type_: str, name: str) -> None:
        """
        Updates the information of a discovered service.

        Parameters
        ----------
        zc : Zeroconf
            The Zeroconf instance.
        type_ : str
            The type of the service.
        name : str
            The name of the service.
        """
        if type_ == '_osc._udp.local.':
            self.osc_services[name] = zc.get_service_info(type_, name)
        elif type_ == '_oscjson._tcp.local.':
            self.oscjson_services[name] = zc.get_service_info(type_, name)


class OSCQueryBrowser(object):
    """
    A class for browsing OSCQuery services on the network.

    Description
    -----------
    This class allows users to discover OSCQuery services on the network and perform operations
    such as finding services by name and querying nodes by endpoint address.
    """

    def __init__(self) -> None:
        self.listener = OSCQueryListener()
        self.zc = Zeroconf()
        self.browser = ServiceBrowser(
            self.zc, [
                "_oscjson._tcp.local.",
                "_osc._udp.local."],
            self.listener
        )

    def get_discovered_osc(self) -> list[ServiceInfo]:
        """
        Retrieves a list of discovered OSC services.

        Returns
        -------
        list[ServiceInfo]
            A list of discovered OSC services.
        """
        return [oscsvc[1] for oscsvc in self.listener.osc_services.items()]

    def get_discovered_oscquery(self) -> list[ServiceInfo]:
        """
        Retrieves a list of discovered OSCQuery services.

        Returns
        -------
        list[ServiceInfo]
            A list of discovered OSCQuery services.
        """
        return [oscjssvc[1] for oscjssvc in self.listener.oscjson_services.items()]

    def find_service_by_name(self, name: str) -> ServiceInfo | None:
        """
        Finds an OSCQuery service by its name.

        Parameters
        ----------
        name : str
            The name of the service to find.

        Returns
        -------
        ServiceInfo or None
            The discovered service information, if found. Otherwise, returns None.
        """
        for svc in self.get_discovered_oscquery():
            client_ = OSCQueryClient(svc)
            if name in client_.get_host_info().name:
                return svc

        return None

    def find_nodes_by_endpoint_address(
        self, address: str
    ) -> list[tuple[ServiceInfo, OSCHostInfo, OSCQueryNode]]:
        """
        Finds nodes by their endpoint address.

        Parameters
        ----------
        address : str
            The endpoint address to search for.

        Returns
        -------
        list[tuple[ServiceInfo, OSCHostInfo, OSCQueryNode]]
            A list of tuples containing service information, host information, and queried nodes.
        """
        svcs = []
        for svc in self.get_discovered_oscquery():
            client_ = OSCQueryClient(svc)
            hi = client_.get_host_info()
            if hi is None:
                continue
            node_ = client_.query_node(address)
            if node_ is not None:
                svcs.append((svc, hi, node_))

        return svcs


class OSCQueryClient(object):
    """
    Represents a client for interacting with an OSCQuery service.
    Potential Raises: TypeError, ValueError

    Description
    -----------
    OSCQueryClient provides functionality to communicate with an OSCQuery service.
    It allows querying information about specific nodes, retrieving host information,
    and constructing OSCQueryNode objects from JSON representations.

    Attributes
    ----------
    service_info: ServiceInfo
        Information about the OSCQuery service.
    """

    def __init__(self, service_info_: ServiceInfo) -> None:
        if not isinstance(service_info_, ServiceInfo):
            raise TypeError("service_info isn't a ServiceInfo class!")

        if service_info_.type != "_oscjson._tcp.local.":
            raise ValueError(
                "service_info does not represent an OSCQuery service!"
            )

        self.service_info = service_info_
        self.last_json = None

    def _get_query_root(self) -> str:
        """Constructs the root URL for querying the OSCQuery service from the ServiceInfo object."""
        return f"http://{self._get_ip_str()}:{self.service_info.port}"

    def _get_ip_str(self) -> str:
        """Converts the ServiceInfo address byte representation of an IP address into a string."""
        return '.'.join([str(int(num)) for num in self.service_info.addresses[0]])

    def _handle_request(self, url: str) -> requests.Response | None:
        """
        Handles an HTTP GET request to the specified URL and returns the response.

        Parameters
        ----------
        url : str
            The URL to send the GET request to.

        Returns
        -------
        requests.Response or None
            The response object if the request is successful, otherwise None.
        """
        response = None
        try:
            response = requests.get(url, timeout=10)
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            exception_type = type(e).__name__
            print(f'Type: {exception_type} ->', e)

        if response is None or response.status_code == 404:
            return None

        if response.status_code != 200:
            raise requests.HTTPError(
                f"Node query error: (HTTP {response.status_code}) {
                    response.content}"
            )

        return response

    def query_node(self, node_: str = "/") -> OSCQueryNode | None:
        """
        Retrieves information about a specific node path from the OSCQuery service.
        Potential Raises: requests.HTTPError

        Parameters
        ----------
        node : str, optional
            The path of the node to query. Defaults to the root node ("/").

        Returns
        -------
        OSCQueryNode or None
            An OSCQueryNode object representing the path queried.
        """
        url = self._get_query_root() + node_
        response = self._handle_request(url)
        if response is None:
            return None

        self.last_json = response.json()
        return self._make_node_from_json(self.last_json)

    def get_host_info(self) -> OSCHostInfo | None:
        """
        Retrieves information about the host from the OSCQuery service. Service can contain details;
        such as the host name, IP address, port number, and transport protocol.
        Potential Raises: requests.HTTPError

        Returns
        -------
        OSCHostInfo or None
            An OSCHostInfo object representing the host information if available
        """
        url = self._get_query_root() + "/HOST_INFO"
        response = self._handle_request(url)
        if response is None:
            return None

        json: dict[str, Any] = response.json()
        hi = OSCHostInfo(json["NAME"], json.get('EXTENSIONS', []))
        hi.osc_ip = json.get('OSC_IP', self._get_ip_str)
        hi.osc_port = json.get('OSC_PORT', self.service_info.port)
        hi.osc_transport = json.get('OSC_TRANSPORT', 'UDP')

        return hi

    def _make_node_from_json(self, json: dict[str, Any]) -> OSCQueryNode:
        """
        This private method parses the provided JSON object and creates an OSCQueryNode instance
        Potential Raises: ValueError

        Parameters
        ----------
        json dict[str, Any]
            The JSON object representing the OSCQueryNode.

        Returns
        -------
        OSCQueryNode
            An OSCQueryNode object constructed from the JSON (dict) representation.
        """
        values = json.get("VALUE")
        # This should always be an array... throw an exception here?
        if values is not None and not isinstance(values, list):
            raise ValueError(
                "OSCQuery JSON Value is not List / Array? Out-of-spec?"
            )

        # full_path *should* be required but some implementations don't have it
        new_node = OSCQueryNode()
        new_node.full_path = json.get("FULL_PATH")
        new_node.access = json.get("ACCESS")
        new_node.description = json.get("DESCRIPTION")

        new_node.contents = [
            self._make_node_from_json(json["CONTENTS"][sub_nodes])
            for sub_nodes in json.get("CONTENTS", [])
        ]

        new_node.type_ = (
            OSC_Type_String_to_Python_Type(json["TYPE"])
            if "TYPE" in json else None
        )

        # According to the spec, if there is not yet a value,
        # the return will be an empty JSON object
        new_node.value = [
            new_node.type_[i](v) for i, v in enumerate(json.get("VALUE", []))
            if not (isinstance(v, dict) and not v) and new_node.type_
        ] if "VALUE" in json and isinstance(json["VALUE"], list) else []

        # # FIXME does this apply to all values in the value array always...? I assume it does here
        # This comment is a carry over addressing the "isinstance(v, dict) and not v"
        # The line, I assume, is correct. As I haven't encountered an issue with it yet.
        # Further testing may be needed to confirm it always applies.

        return new_node


if __name__ == "__main__":
    browser = OSCQueryBrowser()
    time.sleep(2)  # Wait for discovery

    for service_info in browser.get_discovered_oscquery():
        client = OSCQueryClient(service_info)

        # Find host info
        host_info = client.get_host_info()
        print(f"Found OSC Host: {host_info.name} with ip {host_info.osc_ip}:{host_info.osc_port}")

        # Query a node and print its value
        node = client.query_node("/test/node")
        print(f"Node is a {node.type_} with value {node.value}")
