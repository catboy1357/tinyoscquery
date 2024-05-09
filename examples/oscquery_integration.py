# Import necessary modules, this example requires the python-osc package
import time
import threading
from tinyoscquery.query import OSCQueryBrowser, OSCQueryClient
from tinyoscquery.queryservice import OSCQueryService
from tinyoscquery.utility import get_open_tcp_port, get_open_udp_port
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient


# Function to handle OSC messages received by the OSC server
def osc_message_handler(address, *args):
    print(f"Received OSC message: {args[0]}: {args[1:]}",
          f"from {address[0]}:{address[1]}")


# Function to send an OSC message to the discovered OSC service
def send_osc_message(host_info):
    if host_info and all((host_info.osc_ip, host_info.osc_port, host_info.name)):
        print(f"Sent to OSC Host: {host_info.name} ",
              f"at {host_info.osc_ip}:{host_info.osc_port}")

        # Create and Send an OSC message to the discovered OSC service
        osc_client = SimpleUDPClient(host_info.osc_ip, host_info.osc_port)
        osc_client.send_message("/test", [1, 2, 3])


# Function to run OSC server in a separate thread
def run_osc_server():
    # Set up OSC listener using python-osc
    dispatcher = Dispatcher()
    dispatcher.set_default_handler(osc_message_handler, True)
    osc_server = ThreadingOSCUDPServer(("0.0.0.0", OSC_PORT), dispatcher)

    print(f"OSC server running on port {OSC_PORT}")
    osc_server.serve_forever()


# Get open ports for OSC and OSCQuery
OSC_PORT = get_open_udp_port()
HTTP_PORT = get_open_tcp_port()

# Run the OSCQuery service within a context manager
with OSCQueryService("Test-Service", HTTP_PORT, OSC_PORT) as oscqs:
    print(f"OSCQueryService running on port {HTTP_PORT}")

    # Advertise an endpoint
    oscqs.advertise_endpoint("/avatar")

    # Start the OSC server in a separate thread
    osc_server_thread = threading.Thread(target=run_osc_server, daemon=True)
    osc_server_thread.start()

    # Create an instance of OSCQueryBrowser
    browser = OSCQueryBrowser()
    time.sleep(2)  # Wait for discovery

    # Iterate through discovered OSCQuery services
    for service_info in browser.get_discovered_oscquery():
        # Gathers info about the service
        client = OSCQueryClient(service_info)

        # Get host information
        host_info = client.get_host_info()
        send_osc_message(host_info)

    # hold main thread open
    time.sleep(1)
    input("Press enter to exit..\n")
