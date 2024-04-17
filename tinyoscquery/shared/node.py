from enum import IntEnum
import json
from json import JSONEncoder
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
            obj_dict = {}
            for k, v in vars(o).items():
                if v is None:
                    continue
                if k.lower() == "type_":
                    obj_dict["TYPE"] = Python_Type_List_to_OSC_Type(v)
                if k == "contents":
                    obj_dict["CONTENTS"] = {}
                    for subNode in v:
                        if subNode.full_path is not None:
                            obj_dict["CONTENTS"][subNode.full_path.split("/")[-1]] = subNode
                        else:
                            continue
                else:
                    obj_dict[k.upper()] = v

            # FIXME: I missed something, so here's a hack!

            if "TYPE_" in obj_dict:
                del obj_dict["TYPE_"]
            return obj_dict

        if isinstance(o, type):
            return Python_Type_List_to_OSC_Type([o])

        if isinstance(o, OSCHostInfo):
            obj_dict = {}
            for k, v in vars(o).items():
                if v is None:
                    continue
                obj_dict[k.upper()] = v
            return obj_dict
        
        return json.JSONEncoder.default(self, o)

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

        foundNode = None
        if self.contents is None:
            return None
        
        for subNode in self.contents:
            foundNode = subNode.find_subnode(full_path)
            if foundNode is not None:
                break

        return foundNode

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

        path_split = child.full_path.rsplit("/",1)
        if len(path_split) < 2:
            raise NodeError("Tried to add child node with invalid full path!", path=path_split)

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

    
    def to_json(self) -> dict[str, Any]:
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
            for subNode in self.contents:
                yield from subNode

    def __str__(self) -> str:
        """
        Returns a human-readable representation of the node.
        - @ - Full Path
        - D - Description
        - T - Type
        - V - Value
        """
        return f'<OSCQueryNode @ {self.full_path} (D: "{self.description}" T:{self.type_} V:{self.value})>'

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
    extensions : list[str]
        List of extensions supported by the host.
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
    def __init__(self, name: str, extensions: list[str],
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

def OSC_Type_String_to_Python_Type(typestr: str) -> List[type]:
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
    types = []
    for typevalue in typestr:
        if typevalue == '':
            continue

        if typevalue == "i":
            types.append(int)
        elif typevalue == "f" or typevalue == "h" or typevalue == "d" or typevalue == "t":
            types.append(float)
        elif typevalue == "T" or typevalue == "F":
            types.append(bool)
        elif typevalue == "s":
            types.append(str)
        else:
            raise ValueError(f"Unknown OSC type when converting! {typevalue} -> ???")


    return types


def Python_Type_List_to_OSC_Type(types_: List[type]) -> str:
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
    output = []
    for type_ in types_:
        if type_ == int:
            output.append("i")
        elif type_ == float:
            output.append("f")
        elif type_ == bool:
            output.append("T")
        elif type_ == str:
            output.append("s")
        else:
            raise ValueError(f"Cannot convert {type_} to OSC type!")

    return " ".join(output)


if __name__ == "__main__":
    root = OSCQueryNode("/", description="root node")
    root.add_child_node(OSCQueryNode("/test/node/one"))
    root.add_child_node(OSCQueryNode("/test/node/two"))
    root.add_child_node(OSCQueryNode("/test/othernode/one"))
    root.add_child_node(OSCQueryNode("/test/othernode/three"))

    #print(root)

    for child in root:
        print(child)