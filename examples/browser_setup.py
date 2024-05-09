# Import necessary modules
import time
from tinyoscquery.query import OSCQueryBrowser, OSCQueryClient

# Create an instance of OSCQueryBrowser
browser = OSCQueryBrowser()
time.sleep(2)  # Wait for discovery

# Iterate through discovered OSCQuery services
for service_info in browser.get_discovered_oscquery():
    client = OSCQueryClient(service_info)

    # Check if host_info is not None and all required information is present
    host_info = client.get_host_info()
    if host_info and all((host_info.name, host_info.osc_ip, host_info.osc_port)):
        print(f"Found OSC Host: {host_info.name}",
              f"with ip {host_info.osc_ip}:{host_info.osc_port}")

    # Check if node is not None and all required information is present
    node = client.query_node("/test/node")
    if node and all((node.type_, node.value)):
        print(f"Node is a {node.type_} with value {node.value}")
