import json
import os
import time

from google_interface import GoogleInterface
from monitor import Monitor
from util import *
from web_server import WebServer

# Config
CRED_FILE_PATH = "google_credentials.json"
SPREADSHEET_ID = "1eskt0XRDJ1SXpOBCr0fZ0JfxVvGlAnGfaVP7qLbpLMY"
CONFIG_CACHE_FILENAME = "config_cache.json"

# Global variables
config_cache = {"general": {}, "people": []}
data_cache = {"devices": [], "records": []}
google_interface = None
web_server = None
monitor = None

# The status lights on the main page indicate DISCONNECTED, WARNING, or CONNECTED:
#
# "Server": DISCONNECTED = The WebSocket connection is currently closed
#           CONNECTED = The WebSocket connection is currently open
#
# "Monitor": DISCONNECTED = Data is unavailable due to an error.
#            WARNING = No devices are visible on the network (might be disconnected).
#            CONNECTED = At least one device is visible on the network.
#
# "Google": DISCONNECTED = There was an error with the connection or authentication.
#           WARNING = There was an unknown error, possibly due to unexpected data in the sheet.
#           CONNECTED = There are no issues with the connection.


def update_config_cache(new_config):
    '''Callback to update the config cache from Google, writing to disk and pushing to all modules.'''
    global config_cache

    if new_config != config_cache:
        log("Config cache has changed, saving to file and sending to web server")
        config_cache = new_config
        json.dump(config_cache, open(
            get_absolute_path(CONFIG_CACHE_FILENAME), "w"))
        web_server.new_config()


def update_data_cache(new_data):
    '''Callback to update the data cache from Google, pushing to all modules.'''
    global data_cache

    if new_data != data_cache:
        log("Data cache has changed, sending to web sever")
        data_cache = new_data
        web_server.new_data()


if __name__ == "__main__":
    # Read initial config cache
    config_path = get_absolute_path(CONFIG_CACHE_FILENAME)
    if os.path.isfile(config_path):
        config_cache = json.load(open(config_path))

    # Instantiate components
    google_interface = GoogleInterface(CRED_FILE_PATH, SPREADSHEET_ID,
                                       lambda status: web_server.new_google_status(
                                           status),
                                       lambda new_config: update_config_cache(
                                           new_config),
                                       lambda new_data: update_data_cache(new_data))
    web_server = WebServer(lambda: config_cache,
                           lambda: data_cache,
                           lambda person: google_interface.add_sign_in(
                               person, True),
                           lambda person: google_interface.add_sign_out(
                               person, True),
                           lambda person, mac: google_interface.add_device(
                               person, mac),
                           lambda person, mac: google_interface.remove_device(person, mac))
    monitor = Monitor(lambda: config_cache,
                      lambda: data_cache,
                      lambda status: web_server.new_monitor_status(status),
                      lambda person, event_time: google_interface.add_sign_in(
                          person, False, event_time),
                      lambda person, event_time: google_interface.add_sign_out(
                          person, False, event_time),
                      lambda person, mac: google_interface.update_device_last_seen(person, mac))
    # Start components
    google_interface.start()
    web_server.start()
    monitor.start()

    # Loop forever
    while True:
        time.sleep(1)
