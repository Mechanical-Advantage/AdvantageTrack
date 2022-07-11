import json
import os
import time

from google_interface import GoogleInterface
from util import *
from web_server import WebServer

# Config
CRED_FILE_PATH = "google_credentials.json"
SPREADSHEET_ID = "1eskt0XRDJ1SXpOBCr0fZ0JfxVvGlAnGfaVP7qLbpLMY"
CONFIG_CACHE_FILENAME = "config_cache.json"

# Global variables
config_cache = {"general": {}, "people": []}
data_cache = {"devices": [], "records": []}
web_server = None
google_interface = None


def update_config_cache(new_config):
    '''Callback to update the config cache from Google, writing to disk and pushing to all modules.'''
    global config_cache

    if new_config != config_cache:
        log("Updated config from Google")
        config_cache = new_config
        json.dump(config_cache, open(
            get_absolute_path(CONFIG_CACHE_FILENAME), "w"))
        web_server.new_config()


def update_data_cache(new_data):
    '''Callback to update the data cache from Google, pushing to all modules.'''
    global data_cache

    if new_data != data_cache:
        log("Updated data from Google")
        data_cache = new_data
        web_server.new_data()


if __name__ == "__main__":
    # Read initial config cache
    config_path = get_absolute_path(CONFIG_CACHE_FILENAME)
    if os.path.isfile(config_path):
        config_cache = json.load(open(config_path))

    # Start server
    web_server = WebServer(lambda: config_cache, lambda: data_cache,
                           lambda person: google_interface.add_sign_in(
                               person, True),
                           lambda person: google_interface.add_sign_out(
                               person, True),
                           lambda person, mac: google_interface.add_device(
                               person, mac),
                           lambda person, mac: google_interface.remove_device(person, mac))
    web_server.start()

    # Start Google interface
    google_interface = GoogleInterface(
        CRED_FILE_PATH, SPREADSHEET_ID, web_server.new_google_status, update_config_cache, update_data_cache)
    google_interface.start()

    # Loop forever
    while True:
        time.sleep(1)
