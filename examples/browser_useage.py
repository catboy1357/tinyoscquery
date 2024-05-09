# Import necessary modules, this example requires the python-osc package
import time
from tinyoscquery.query import OSCQueryBrowser, OSCQueryClient
from pythonosc.udp_client import SimpleUDPClient

# Create an instance of OSCQueryBrowser
browser = OSCQueryBrowser()
time.sleep(2)

# Iterate through discovered OSCQuery services
for service_info in browser.get_discovered_oscquery():
    # Gathers info about the service
    client = OSCQueryClient(service_info)

    # Check if host_info is not None and all required information is present
    host_info = client.get_host_info()
    if host_info and all((host_info.osc_ip, host_info.osc_port, host_info.name)):
        print(f"sent to: {host_info.name}")

        # Create and Send an OSC message to the OSC client once found
        osc_client = SimpleUDPClient(host_info.osc_ip, host_info.osc_port)
        osc_client.send_message("/test", [1, 2, 3])
