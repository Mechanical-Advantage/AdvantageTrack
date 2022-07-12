import subprocess
import threading
from unittest import skip

from charset_normalizer import detect

from arp import get_mac_address
from util import *


class Monitor:
    '''Manages automatic sign-ins and sign-outs by scanning the local network for registered devices'''

    _connection_status = ConnectionStatus.DISCONNECTED
    _last_pings = {}

    def __init__(self, get_config, get_data, status_callback, sign_in_callback, sign_out_callback):
        '''
        Creates a new Monitor.

        Parameters:
            get_config: A function that returns the current config cache.
            get_data: A function that returns the current data cache.
            status_callback: A function that takes a single ConnectionStatus argument.
            sign_in_callback: A function that accepts a person ID and timestamp.
            sign_out_callback: A function that accepts a person ID and timestamp.
        '''

        self._get_config = get_config
        self._get_data = get_data
        self._status_callback = status_callback
        self._sign_in_callback = sign_in_callback
        self._sign_out_callback = sign_out_callback

    def _set_connection_status(self, status):
        '''Sets the current connection status and updates it externally if necessary.'''
        if status != self._connection_status:
            self._connection_status = status
            self._status_callback(self._connection_status)

    def _run(self):
        '''Main thread for scanning the network and triggering sign-ins and sign-outs.'''
        while True:
            time.sleep(self._get_config()["general"]["ping_cycle_delay"])
            current_time = round(time.time())
            config = self._get_config()
            data = self._get_data()

            try:
                # Get list of all IP addresses
                all_ips = []
                ip_range_start = config["general"]["ip_range_start"]
                ip_range_end = config["general"]["ip_range_end"]
                for i in range(int(ip_range_start.split(".")[-1]), int(ip_range_end.split(".")[-1]) + 1):
                    all_ips.append(
                        ".".join(ip_range_start.split(".")[:-1] + [str(i)]))

                # Determine IP addresses to remove
                skipped_ips = []
                for ip_address in all_ips:
                    if ip_address in self._last_pings.keys():
                        if current_time - self._last_pings[ip_address] < config["general"]["ping_backoff_length"]:
                            skipped_ips.append(ip_address)

                # Run flood ping
                log("Running flood ping with " + str(len(skipped_ips)) +
                    " skipped IP address" + ("" if len(skipped_ips) == 1 else "es"))
                ping_list = [x for x in all_ips if x not in skipped_ips]
                fping = subprocess.Popen(
                    ["fping", "-C", "1", "-r", "0", "-t", str(config["general"]["ping_timeout"] * 1000), "-q"] + ping_list, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                fping.wait()
                _, stderr = fping.communicate()
                fping_lines = stderr.decode("utf-8").split("\n")[:-1]

                # Find successful detections
                detected_macs = []
                for line in fping_lines:
                    line_split = line.split(" : ")
                    ip_address = line_split[0].rstrip()
                    success = line_split[1] != "-"

                    if success:
                        mac_address = get_mac_address(ip_address)
                        if mac_address != None:
                            self._last_pings[ip_address] = current_time
                            detected_macs.append(mac_address)
                            log("Found device \"" + mac_address +
                                "\" at \"" + ip_address + "\"")

                # Set status based on device count
                if len(detected_macs) == 0 and len(skipped_ips) == 0:
                    log("No devices found with flood ping. Is there a network problem?")
                    self._set_connection_status(ConnectionStatus.WARNING)
                else:
                    self._set_connection_status(ConnectionStatus.CONNECTED)

            except:
                log("Unknown error during monitor cycle")
                self._set_connection_status(ConnectionStatus.DISCONNECTED)

    def start(self):
        '''Starts the monitor thread.'''
        threading.Thread(target=self._run, daemon=True).start()
