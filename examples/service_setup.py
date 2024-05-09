# Import the required package
from tinyoscquery.queryservice import OSCQueryService

# Runs the code if this file is executed
if __name__ == '__main__':
    # HTTP and OSC ports can be the same.
    OSC_PORT = 9020  # Find a predefined open port for OSC
    HTTP_PORT = 9020  # Find a predefined open port for the oscjson http server

    # Set up an OSCServer, likely with the python-osc first...

    # Explicitly stops the service after user input
    oscqs = OSCQueryService("Test-Service", HTTP_PORT, OSC_PORT)
    # Do something else, the zeroconf advertising and
    # oscjson server runs in the background
    input("press enter to stop service...")
    oscqs.stop()

    # Automatically stops the service after user input
    with OSCQueryService("Test-Service", HTTP_PORT, OSC_PORT) as oscqs:
        # Do something else, the zeroconf advertising and
        # oscjson server runs in the background
        input("press enter to stop service...")
