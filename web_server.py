import json
import random
import threading

import cherrypy
import netifaces
from ws4py.messaging import TextMessage
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket

from arp import *
from util import *


class WebServer:
    """Manages the CherryPy server (HTTP and WebSocket)."""

    _PORT = 8000
    _IP_MONITOR_PERIOD_SECS = 5

    _monitor_status = ConnectionStatus.DISCONNECTED
    _google_status = ConnectionStatus.DISCONNECTED
    _ip_address = "127.0.0.1"
    _auto_add_person = None

    def __init__(self, data_folder, background_cache_folder, get_config, get_data, sign_in_callback, sign_out_callback, add_device_callback, remove_device_callback):
        """
        Creates a new WebServer.

        Parameters:
            data_folder: The name of the local folder where data is stored.
            background_cache_folder: The name of the local folder to store backgrounds.
            get_config: A function that returns the current config cache.
            get_data: A function that returns the current data cache.
            sign_in_callback: A function that accepts a person ID.
            sign_out_callback: A function that accepts a person ID.
            add_device_callback: A function that accepts a person ID and MAC address.
            remove_device_callback: A function that accepts a person ID and MAC address.
        """

        self._DATA_FOLDER = data_folder
        self._BACKGROUND_CACHE_FOLDER = background_cache_folder
        self._get_config = get_config
        self._get_data = get_data
        self._sign_in_callback = sign_in_callback
        self._sign_out_callback = sign_out_callback
        self._add_device_callback = add_device_callback
        self._remove_device_callback = remove_device_callback

        self.Root.set_parent(self)
        self.WebSocketHandler.set_parent(self)

    class Root(object):
        """CherryPy server for HTTP requests."""

        @classmethod
        def set_parent(cls, parent):
            cls._parent = parent

        @cherrypy.expose
        def ws(self):
            pass

        @cherrypy.expose
        def add(self):
            # Register device
            mac_address = get_mac_address(cherrypy.request.remote.ip)
            if mac_address != None:
                is_random = random_mac_address_pattern.match(
                    mac_address) != None
                if self._parent._auto_add_person != None and not is_random:
                    google_success = self._parent._add_device_callback(
                        self._parent._auto_add_person, mac_address)

            # Create response
            html = open(get_absolute_path("www/add.html")).read()
            if mac_address == None:
                html = html.replace("$(RESULT)", "FAILURE-GETMAC")
            else:
                html = html.replace("$(MAC)", mac_address)
                if is_random:
                    html = html.replace("$(RESULT)", "FAILURE-RANDOM")
                elif self._parent._auto_add_person == None:
                    html = html.replace("$(RESULT)", "FAILURE-PERSON")
                elif not google_success:
                    html = html.replace("$(RESULT)", "FAILURE-GOOGLE")
                else:
                    html = html.replace("$(RESULT)", "SUCCESS")
            return html

    class WebSocketHandler(WebSocket):
        """WebSocket handler for each connection."""

        @classmethod
        def set_parent(cls, parent):
            cls._parent = parent

        def received_message(self, message):
            message = json.loads(str(message))
            query = message["query"]
            data = message["data"]

            log("Received query \"" + query + "\"",
                before_text=self.peer_address[0])

            if query == "sign_in":
                self._parent._sign_in_callback(data)
            elif query == "sign_out":
                self._parent._sign_out_callback(data)
            elif query == "auto_add":
                self._parent._auto_add_person = data
            elif query == "remove_device":
                self._parent._remove_device_callback(
                    data["person"], data["mac"])

        def opened(self):
            log("WebSocket connection opened",
                before_text=self.peer_address[0])
            self.send(TextMessage(
                self._parent._generate_message("monitor_status")))
            self.send(TextMessage(
                self._parent._generate_message("google_status")))
            self.send(TextMessage(self._parent._generate_message("add_address")))
            self.send(TextMessage(self._parent._generate_message("config")))
            self.send(TextMessage(self._parent._generate_message("data")))
            self.send(TextMessage(self._parent._generate_message("backgrounds")))

        def closed(self, code, _):
            log("WebSocket connection closed (" + str(code) + ")",
                before_text=self.peer_address[0])

    def _generate_message(self, query):
        """Generates the text message to send for the specified query."""
        data = None
        if query == "monitor_status":
            data = self._monitor_status.value
        elif query == "google_status":
            data = self._google_status.value
        elif query == "add_address":
            data = "http://" + self._ip_address + \
                ":" + str(self._PORT) + "/add"
        elif query == "config":
            config_cache = self._get_config()
            welcome_message = ""
            if "welcome_message" in config_cache["general"]:
                welcome_message = config_cache["general"]["welcome_message"]
            data = {
                "welcome_message": welcome_message,
                "people": [{
                    "id": x["id"],
                    "name": x["first_name"] + " " + x["last_name"],
                    "is_active": x["is_active"]
                } for x in config_cache["people"]]
            }
        elif query == "data":
            data_cache = self._get_data()
            data = {
                "devices": data_cache["devices"],
                "here_now": [{
                    "person": x["person"],
                    "manual": x["start_manual"]
                } for x in data_cache["records"] if x["end_time"] == None]
            }
        elif query == "backgrounds":
            is_default = False
            files = os.listdir(get_absolute_path(
                self._DATA_FOLDER, self._BACKGROUND_CACHE_FOLDER))
            files = [x for x in files if x[0] != "."]
            if len(files) == 0:
                is_default = True
                files = os.listdir(get_absolute_path(
                    "default_backgrounds"))
                files = [x for x in files if x[0] != "."]

            random.shuffle(files)
            data = {
                "is_default": is_default,
                "files": files
            }
        return json.dumps({
            "query": query,
            "data": data
        })

    def new_monitor_status(self, status):
        """Sets the monitor status."""
        self._monitor_status = status
        cherrypy.engine.publish("websocket-broadcast",
                                TextMessage(self._generate_message("monitor_status")))

    def new_google_status(self, status):
        """Sets the Google status."""
        self._google_status = status
        cherrypy.engine.publish("websocket-broadcast",
                                TextMessage(self._generate_message("google_status")))

    def new_config(self):
        """Tells the server that the config cache was updated."""
        cherrypy.engine.publish("websocket-broadcast",
                                TextMessage(self._generate_message("config")))

    def new_data(self):
        """Tells the server that the data cache was updated."""
        cherrypy.engine.publish("websocket-broadcast",
                                TextMessage(self._generate_message("data")))

    def new_backgrounds(self):
        """Tells the server that a new set of backgrounds is available."""
        cherrypy.engine.publish("websocket-broadcast",
                                TextMessage(self._generate_message("backgrounds")))

    def _run_server(self):
        """Starts the server and runs forever."""

        WebSocketPlugin(cherrypy.engine).subscribe()
        cherrypy.tools.websocket = WebSocketTool()

        cherrypy.config.update(
            {"server.socket_port": self._PORT, "server.socket_host": "0.0.0.0"})
        cherrypy.quickstart(self.Root(), "/", config={
            "/index": {
                "tools.staticfile.on": True,
                "tools.staticfile.filename": get_absolute_path("www/index.html")
            },
            "/static": {
                "tools.staticdir.on": True,
                "tools.staticdir.dir": get_absolute_path("www/static")
            },
            "/backgrounds/user": {
                "tools.staticdir.on": True,
                "tools.staticdir.dir": get_absolute_path(self._DATA_FOLDER, self._BACKGROUND_CACHE_FOLDER)
            },
            "/backgrounds/default": {
                "tools.staticdir.on": True,
                "tools.staticdir.dir": get_absolute_path("default_backgrounds")
            },
            "/ws": {
                "tools.websocket.on": True,
                "tools.websocket.handler_cls": self.WebSocketHandler
            }
        })

    def _monitor_ip(self):
        """Periodically checks the current IP address."""
        while True:
            new_ip_address = "127.0.0.1"
            for interface_name in netifaces.interfaces():
                address = [x["addr"] for x in netifaces.ifaddresses(
                    interface_name).setdefault(netifaces.AF_INET, [{"addr": None}])][0]
                if address != None and address != "127.0.0.1":
                    new_ip_address = address
                    break

            if new_ip_address != self._ip_address:
                log("Found server IP address: " + new_ip_address)
                self._ip_address = new_ip_address
                cherrypy.engine.publish("websocket-broadcast",
                                        TextMessage(self._generate_message("add_address")))

            time.sleep(self._IP_MONITOR_PERIOD_SECS)

    def start(self):
        """Starts the web server and IP address monitor in a separate threads."""
        threading.Thread(target=self._run_server, daemon=True).start()
        threading.Thread(target=self._monitor_ip, daemon=True).start()
