import time

from tinyoscquery.queryservice import OSCQueryService
from tinyoscquery.shared.node import OSCQueryNode

if __name__ == "__main__":
    oscqs = OSCQueryService("Test-Service", 9020, 9020)
    print(oscqs.root_node)

    oscqs.add_node(OSCQueryNode("/testing/is/cool"))

    print(oscqs.root_node)

    input("Press enter to stop service...")

    oscqs.stop()
