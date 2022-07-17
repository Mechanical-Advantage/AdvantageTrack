import platform
import re
import subprocess


valid_mac_address_pattern = re.compile(r"^([0-9a-f]{2}[:]){5}([0-9a-f]{2})$")
random_mac_address_pattern = re.compile(r"^.[26ae]")


def get_mac_address(ip_address):
    """Uses arp to retrieve the MAC address for the specified IP address (Linux, macOS, and Windows)."""

    mac_address = None

    # Run arp command
    args = ["arp", "-a", ip_address] if platform.system() == "Windows" else ["arp",
                                                                             ip_address]
    try:
        output = subprocess.check_output(
            args, stderr=subprocess.DEVNULL).decode("utf-8")
    except subprocess.CalledProcessError:
        pass
    else:
        # Parse arp output
        output = output.split("\r\n" if platform.system()
                              == "Windows" else "\n")
        if platform.system() == "Linux":
            if len(output) >= 2:
                words = [x for x in output[1].split(" ") if len(x) > 0]
                if len(words) >= 3:
                    mac_address = words[2]

        elif platform.system() == "Darwin":
            if len(output) >= 1:
                words = output[0].split(" ")
                if len(words) >= 4:
                    mac_address = words[3]

        elif platform.system() == "Windows":
            if len(output) >= 4:
                words = [x for x in output[3].split(" ") if len(x) > 0]
                if len(words) >= 2:
                    mac_address = words[1]

    # Clean up & verify result
    if mac_address != None:
        mac_address = mac_address.lower().replace("-", ":")
        mac_address = ":".join([x.zfill(2) for x in mac_address.split(":")])
        if valid_mac_address_pattern.match(mac_address) == None:
            mac_address = None

    return mac_address
