# Import necessary modules, this example requires the python-osc package
from tinyoscquery.queryservice import OSCQueryService
from tinyoscquery.utility import get_open_tcp_port, get_open_udp_port
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

# Get open ports for OSC and OSCQuery
OSC_PORT = get_open_udp_port()
HTTP_PORT = get_open_tcp_port()

# Set up OSC listener using python-osc
dispatcher = Dispatcher()
dispatcher.set_default_handler(lambda *args: print(f"Get: {args}"))
osc_server = ThreadingOSCUDPServer(("0.0.0.0", OSC_PORT), dispatcher)

# Run the OSCQuery server within a context manager
with OSCQueryService("Test-Service", HTTP_PORT, OSC_PORT) as oscqs:
    print(f"OSCQueryService running on port {HTTP_PORT}")

    # Advertise an endpoint
    oscqs.advertise_endpoint("/avatar")

    # Run the OSC server
    print(f"OSC server running on port {OSC_PORT}")
    try:
        osc_server.serve_forever()
    except KeyboardInterrupt:
        print("Exiting")
    finally:
        osc_server.shutdown()
