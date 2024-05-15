from enum import IntEnum
import json
from json import JSONEncoder
from types import MappingProxyType
from typing import Any, List


class OSCNodeEncoder(JSONEncoder):
    """
    Custom JSON encoder for OSCQueryNode and OSCHostInfo objects.

    Description
    -----------
    OSCNodeEncoder is a custom JSON encoder designed to serialize
    OSCQueryNode and OSCHostInfo objects into JSON format. It overrides the
    default behavior of JSONEncoder to handle custom serialization of:
        - OSCQueryNode
        - OSCHostInfo
        - Python type objects

    """

    def default(self, o: Any) -> dict[str, Any] | str:
        """
        Overrides the default method of JSONEncoder to customize serialization behavior
        for specific types.

        Parameters
        ----------
        o : OSCQueryNode or OSCHostInfo or type
            The object to be serialized.

        Returns
        -------
        dict or str
            The serialized representation of the object.
        """
        if isinstance(o, OSCQueryNode):
            return self._serialize_osc_query_node(o)

        if isinstance(o, type):
            return Python_Type_List_to_OSC_Type([o])

        if isinstance(o, OSCHostInfo):
            return self._serialize_osc_host_info(o)

        return super().default(o)

    def _serialize_osc_query_node(self, o: "OSCQueryNode") -> dict[str, Any]:
        """
        Serialize an OSCQueryNode object into a JSON-compatible dictionary.

        Parameters
        ----------
        o : OSCQueryNode
            The OSCQueryNode object to be serialized.

        Returns
        -------
        dict
            The serialized representation of the OSCQueryNode object.
        """
        # Dictionary comprehension to filter out None values and "type_"
        obj_dict = {
            k.upper(): v
            for k, v in vars(o).items()
            if v is not None and k.lower() != "type_"
        }

        # Set the "TYPE" key to represent the type of the OSCQueryNode
        obj_dict["TYPE"] = Python_Type_List_to_OSC_Type(
            o.type_
        ) if o.type_ else None

        # If the OSCQueryNode has contents, add them to the dictionary
        if o.contents:
            obj_dict["CONTENTS"] = {
                sub_node.full_path.split("/")[-1]: sub_node
                for sub_node in o.contents
                if sub_node.full_path is not None
            }

        # # FIXME: I missed something, so here's a hack!
        # This comment suggests a missing functionality or an overlooked issue.
        # Unclear what exactly needs to be fixed or why this comment exists.
        # Referring to removing "TYPE_" from the dict?
        # Further investigation is needed to address this properly.

        # Remove "TYPE_" key if it exists
        obj_dict.pop("TYPE_", None)

        return obj_dict

    def _serialize_osc_host_info(self, o: "OSCHostInfo") -> dict[str, Any]:
        """
        Serialize an OSCHostInfo object into a JSON-compatible dictionary.

        Parameters
        ----------
        o : OSCHostInfo
            The OSCHostInfo object to be serialized.

        Returns
        -------
        dict
            The serialized representation of the OSCHostInfo object.
        """
        # Direct dictionary comprehension
        return {
            # Uppercase version of attribute name (k) with value (v)
            k.upper(): v
            # Iterate over each attribute (k) and value (v) in the object 'o'
            for k, v in vars(o).items()
            # Filtering out attributes with 'None' values
            if v is not None
        }


class OSCAccess(IntEnum):
    """
    Enumeration representing access levels for OSC query nodes.
    """
    NO_VALUE = 0
    READONLY_VALUE = 1
    WRITEONLY_VALUE = 2
    READWRITE_VALUE = 3


class OSCQueryNode():
    """
    Represents a node in the OSCQuery structure.

    Description
    -----------
    OSCQueryNode represents a node in the OSCQuery structure, containing information such as
    its full path, contents, access type, data type, description, value, and host information.
    It provides methods for finding subnodes, adding child nodes, converting to JSON format,
    and iteration over its contents.

    Attributes
    ----------
    full_path : str or None, optional
        The full path of the node within the OSCQuery structure.
    contents : list[OSCQueryNode] or None, optional
        A list of child nodes contained within this node.
    type_ : list[type] or None, optional
        The data type(s) associated with the node's value.
    access : OSCAccess or None, optional
        The access type of the node, indicating its read and write permissions.
    description : str or None, optional
        A description of the node.
    value : list or None, optional
        The value(s) associated with the node.
    host_info : OSCHostInfo or None, optional
        Information about the host associated with the node.
    """

    def __init__(self, full_path: str | None = None,
                 contents: List['OSCQueryNode'] | None = None,
                 type_: List[type] | None = None, access: OSCAccess | None = None,
                 description: str | None = None, value: list | None = None,
                 host_info: 'OSCHostInfo | None' = None) -> None:
        self.contents = contents
        self.full_path = full_path
        self.access = access
        self.type_ = type_
        # Value is always an array!
        self.value = value
        self.description = description
        self.host_info = host_info

    def find_subnode(self, full_path: str) -> 'OSCQueryNode | None':
        """
        Finds a subnode within the node's contents based on its full path.

        Parameters
        ----------
        full_path : str
            The full path of the subnode to find.

        Returns
        -------
        OSCQueryNode or None
            The subnode if found, otherwise None.
        """
        if self.full_path == full_path:
            return self

        found_node = None
        if self.contents is None:
            return None

        for sub_node in self.contents:
            found_node = sub_node.find_subnode(full_path)
            if found_node is not None:
                break

        return found_node

    def add_child_node(self, child: 'OSCQueryNode') -> None:
        """
        Adds a node as a child node to this node's contents.
        Potential Raises: NodeError, ValueError

        Parameters
        ----------
        child : OSCQueryNode
            The child node to add.
        """
        if child == self:
            return

        path_split = child.full_path.rsplit("/", 1)
        if len(path_split) < 2:
            raise NodeError(
                "Tried to add child node with invalid full path!",
                path=path_split
            )

        parent_path = path_split[0]

        if parent_path == '':
            parent_path = "/"

        parent = self.find_subnode(parent_path)

        if parent is None:
            parent = OSCQueryNode(parent_path)
            self.add_child_node(parent)

        if parent.contents is None:
            parent.contents = []
        parent.contents.append(child)

    def to_json(self) -> str:
        """Converts the node and its contents to a JSON string."""
        return json.dumps(self, cls=OSCNodeEncoder)

    def __iter__(self):
        """
        Recursively iterates over the node and its contents

        Yields
        ------
        OSCQueryNode
            The current node being iterated over.
        """
        yield self
        if self.contents is not None:
            for sub_node in self.contents:
                yield from sub_node

    def __str__(self) -> str:
        """
        Returns a human-readable representation of the node.
        - @ - Full Path
        - D - Description
        - T - Type
        - V - Value
        - C - Child Node
        - A - Access
        """
        return_parts = [
            f'@: {self.full_path} ' if self.full_path else '',
            f'D: "{self.description}" ' if self.description else '',
            f'T:{self.type_} ' if self.type_ else '',
            f'V:{self.value} ' if self.value else '',
            f'C:{len(self.contents)} ' if self.contents else '',
            f'A:{self.access} ' if self.access else '',
        ]
        return f'<OSCQueryNode: ( {"".join(return_parts)})>'


class NodeError(ValueError):
    """
    Exception raised for errors related to OSCQuery nodes.

    Attributes
    ----------
    path : str or None
        The path of the node where the error occurred, if available.
    """

    def __init__(self, *args, **kwargs) -> None:
        self.path = kwargs.pop('path', None)
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        msg = super().__str__()
        # Add kwargs to the return message
        if self.path is not None:
            msg += f' "{self.path}"'
        return msg


class OSCHostInfo():
    """
    Represents information about an OSCQuery host.

    Description
    -----------
    OSCHostInfo provides a convenient way to store and manipulate information
    about an OSCQuery host. It allows access to various attributes such as the
    host's name, IP address, port numbers, transport protocols, WebSocket.

    Attributes
    ----------
    name : str
        The name of the host.
    extensions : dict[str, bool]
        dictionary of extensions supported by the host.
    osc_ip : str or None, optional
        The IP address for OSC communication.
    osc_port : int or None, optional
        The port number for OSC communication.
    osc_transport : str or None, optional
        The transport protocol for OSC communication.
    ws_ip : str or None, optional
        The IP address for WebSocket communication.
    ws_port : int or None, optional
        The port number for WebSocket communication.
    """

    def __init__(self, name: str, extensions: dict[str, bool],
                 osc_ip: str | None = None, osc_port: int | None = None,
                 osc_transport: str | None = None, ws_ip: str | None = None,
                 ws_port: int | None = None) -> None:
        self.name = name
        self.osc_ip = osc_ip
        self.osc_port = osc_port
        self.osc_transport = osc_transport
        self.ws_ip = ws_ip
        self.ws_port = ws_port
        self.extensions = extensions

    def to_json(self) -> str:
        """Converts the OSCHostInfo object to a JSON string."""
        return json.dumps(self, cls=OSCNodeEncoder)

    def __str__(self) -> str:
        """Converts the OSCHostInfo object to a JSON string."""
        return json.dumps(self, cls=OSCNodeEncoder)


class TypeMappings:
    """
    Data class to cache the type lookups for osc or python conversions.
    Contains dictionaries mapping OSC types to Python types and vice versa.
    """
    _OSC_TO_PYTHON_TYPES = {
        'i': int,
        'f': float, 'h': float, 'd': float, 't': float,
        'T': bool, 'F': bool,
        's': str
    }

    _PYTHON_TO_OSC_TYPES = {
        int: 'i',
        float: 'f',
        bool: 'T',
        str: 's'
    }

    # Using MappingProxyType to create read-only views of dictionaries
    OSC_TO_PYTHON_TYPES = MappingProxyType(_OSC_TO_PYTHON_TYPES)
    PYTHON_TO_OSC_TYPES = MappingProxyType(_PYTHON_TO_OSC_TYPES)


def OSC_Type_String_to_Python_Type(
    typestr: str,
    type_map: MappingProxyType[str, type] = TypeMappings.OSC_TO_PYTHON_TYPES
) -> List[type]:
    """
    Convert an OSC type string to a list of corresponding Python types.
    Potential Raises: ValueError

    Parameters
    ----------
    typestr : str
        The OSC type string to convert.

    Returns
    -------
    list[type]
        A list of Python types corresponding to the OSC type string.
    """
    try:
        # Using list comprehension for efficient mapping lookup
        return [type_map[typevalue] for typevalue in typestr]

    except KeyError as e:
        raise ValueError(
            f"Unknown OSC type when converting! {e.args[0]} -> ???"
        ) from e


def Python_Type_List_to_OSC_Type(
    types_: List[type],
    type_map: MappingProxyType[type, str] = TypeMappings.PYTHON_TO_OSC_TYPES
) -> str:
    """
    Convert a list of Python types to a corresponding OSC type string.
    Potential Raises: ValueError

    Parameters
    ----------
    types_ : list[type]
        The list of Python types to convert.

    Returns
    -------
    str
        The OSC type string corresponding to the Python types.
    """
    try:
        osc_types = ''
        for type_ in types_:  # loop was tested faster then comprehension here
            # Concatenating OSC type strings directly for performance
            osc_types += type_map[type_]
        return osc_types

    except KeyError as e:
        raise ValueError(f"Cannot convert {e.args[0]} to OSC type!") from e


if __name__ == "__main__":
    root = OSCQueryNode("/", description="root node")
    root.add_child_node(OSCQueryNode("/test/node/one"))
    root.add_child_node(OSCQueryNode("/test/node/two"))
    root.add_child_node(OSCQueryNode("/test/othernode/one"))
    root.add_child_node(OSCQueryNode("/test/othernode/three"))

    # print(root)

    for child in root:
        print(child)
