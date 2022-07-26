import datetime
import subprocess
import threading

from arp import get_mac_address
from util import *


class Monitor:
    """Manages automatic sign-ins and sign-outs by scanning the local network for registered devices."""

    _connection_status = ConnectionStatus.DISCONNECTED
    _last_seen_ips = {}
    _last_seen_people = {}

    def __init__(self, get_config, get_data, status_callback, sign_in_callback, sign_out_callback, update_last_seen_callback):
        """
        Creates a new Monitor.

        Parameters:
            get_config: A function that returns the current config cache.
            get_data: A function that returns the current data cache.
            status_callback: A function that takes a single ConnectionStatus argument.
            sign_in_callback: A function that accepts a person ID and timestamp.
            sign_out_callback: A function that accepts a person ID and timestamp.
            update_last_seen_callback: A funcation that accepts a person ID and MAC address.
        """

        self._get_config = get_config
        self._get_data = get_data
        self._status_callback = status_callback
        self._sign_in_callback = sign_in_callback
        self._sign_out_callback = sign_out_callback
        self._update_last_seen_callback = update_last_seen_callback

    def _set_connection_status(self, status):
        """Sets the current connection status and updates it externally if necessary."""
        if status != self._connection_status:
            self._connection_status = status
            self._status_callback(self._connection_status)

    def _run(self):
        """Main thread for scanning the network and triggering sign-ins and sign-outs."""
        while True:
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
                    if ip_address in self._last_seen_ips.keys():
                        if current_time - self._last_seen_ips[ip_address] < config["general"]["ping_backoff_length_secs"]:
                            skipped_ips.append(ip_address)

                # Run flood ping
                log("Running flood ping with " + str(len(skipped_ips)) +
                    " skipped IP address" + ("" if len(skipped_ips) == 1 else "es"))
                ping_list = [x for x in all_ips if x not in skipped_ips]
                fping = subprocess.Popen(
                    ["fping", "-C", "1", "-r", "0", "-t", str(config["general"]["ping_timeout_secs"] * 1000), "-q"] + ping_list, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                fping.wait()
                _, stderr = fping.communicate()
                fping_lines = stderr.decode("utf-8").split("\n")[:-1]

                # Find successful detections
                detected_macs = set()
                detected_people = set()
                for line in fping_lines:
                    line_split = line.split(" : ")
                    ip_address = line_split[0].rstrip()
                    success = line_split[1] != "-"

                    if success:
                        mac_address = get_mac_address(ip_address)
                        if mac_address != None:
                            self._last_seen_ips[ip_address] = current_time
                            detected_macs.add(mac_address)

                            for device in data["devices"]:
                                if device["mac"] == mac_address:
                                    detected_people.add(device["person"])

                            log("Found device \"" + mac_address +
                                "\" at \"" + ip_address + "\"")

                # Set status based on device count
                if len(detected_macs) == 0 and len(skipped_ips) == 0:
                    log("No devices found with flood ping. Is there a network problem?")
                    self._set_connection_status(ConnectionStatus.WARNING)
                else:
                    self._set_connection_status(ConnectionStatus.CONNECTED)

                # Update last seen time for Google
                for device in data["devices"]:
                    if device["mac"] in detected_macs:
                        if device["last_seen"] == None or datetime.datetime.fromtimestamp(device["last_seen"]).date() != datetime.datetime.today().date():
                            self._update_last_seen_callback(
                                device["person"], device["mac"])

                # Update local list based on active visits from Google
                active_people_google = [
                    x["person"] for x in data["records"] if x["end_time"] == None and not x["start_manual"]]
                for person in active_people_google:  # Add new people
                    if person not in self._last_seen_people.keys():
                        self._last_seen_people[person] = current_time
                last_seen_people_keys = list(
                    self._last_seen_people.keys()).copy()
                for person in last_seen_people_keys:  # Remove old people
                    if person not in active_people_google:
                        del self._last_seen_people[person]

                # Sign in / update last seen times based on detected people
                for person in detected_people:
                    if person in self._last_seen_people.keys():  # Already signed in, update time
                        self._last_seen_people[person] = current_time

                    else:  # Not signed in, check for manual grace
                        last_manual_sign_out = None
                        for record in data["records"]:
                            if record["person"] == person and record["end_time"] != None and record["end_manual"]:
                                last_manual_sign_out = record["end_time"]
                                break

                        if last_manual_sign_out == None or current_time - last_manual_sign_out > (config["general"]["auto_grace_period_mins"] * 60):
                            # Not in manual grace, sign in
                            self._sign_in_callback(person, current_time)
                            self._last_seen_people[person] = current_time

                # Sign out anyone who hasn't been seen recently
                for person, last_seen in self._last_seen_people.items():
                    if current_time - last_seen > (config["general"]["auto_timeout_mins"] * 60):
                        # Don't remove from local cache, so the request is repeated if it fails
                        self._sign_out_callback(
                            person, last_seen + (config["general"]["auto_extension_mins"] * 60))

                # Trigger manual timeouts
                manual_timeouts = [x for x in data["records"] if x["start_manual"] and x["end_time"] ==
                                   None and current_time - x["start_time"] > config["general"]["manual_timeout_hours"] * 3600]
                for record in manual_timeouts:
                    self._sign_out_callback(
                        record["person"], record["start_time"] + (config["general"]["manual_extension_hours"] * 3600))

            except:
                log("Unknown error during monitor cycle")
                self._set_connection_status(ConnectionStatus.DISCONNECTED)

            time.sleep(self._get_config()["general"]
                       ["ping_cycle_delay_secs"])

    def start(self):
        """Starts the monitor thread."""
        threading.Thread(target=self._run, daemon=True).start()
