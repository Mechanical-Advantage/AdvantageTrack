/** Manages the connection to the server. */
export class ServerInterface {
    // Constants
    #retryDelayMs = 3000;

    // Variables
    #webSocket = null;

    constructor() {
        this.#createWebSocket();
    }

    /** Starts the WebSocket connection. */
    #createWebSocket() {
        this.#webSocket = new WebSocket("ws://" + location.host + "/ws");
        window.webSocket = this.#webSocket;
        this.#webSocket.addEventListener("open", () => this.#handleOpen());
        this.#webSocket.addEventListener("close", () => this.#handleClose());
        this.#webSocket.addEventListener("message", (event) => this.#handleMessage(event.data));

        document.addEventListener("sendsignin", (event) => this.#sendData(event));
        document.addEventListener("sendsignout", (event) => this.#sendData(event));
        document.addEventListener("sendautoadd", (event) => this.#sendData(event));
        document.addEventListener("sendremovedevice", (event) => this.#sendData(event));
    }

    /** Called when the WebSocket is opened successfully. */
    #handleOpen() {
        window.serverStatus = 2;
        document.dispatchEvent(new Event("statusupdate"));
    }

    /** Called when the WebSocket is closed. */
    #handleClose() {
        window.serverStatus = 0;
        window.monitorStatus = 0;
        window.googleStatus = 0;
        document.dispatchEvent(new Event("statusupdate"));
        window.setTimeout(() => this.#createWebSocket(), this.#retryDelayMs);
    }

    /** Handles a new message from the server. */
    #handleMessage(message) {
        message = JSON.parse(message);
        var query = message["query"];
        var data = message["data"];

        console.log('Received message "' + query + '"', data);

        switch (query) {
            case "monitor_status":
                window.monitorStatus = data;
                document.dispatchEvent(new Event("statusupdate"));
                break;
            case "google_status":
                window.googleStatus = data;
                document.dispatchEvent(new Event("statusupdate"));
                break;
            case "add_address":
                window.addAddress = data;
                document.dispatchEvent(new Event("addaddressupdate"));
                break;
            case "config":
                window.configCache = data;
                document.dispatchEvent(new Event("configupdate"));
                break;
            case "data":
                window.dataCache = data;
                document.dispatchEvent(new Event("dataupdate"));
                break;
            case "backgrounds":
                window.backgroundList = data;
                document.dispatchEvent(new Event("backgroundupdate"));
        }
    }

    /** Sends the data from an event to the server. */
    #sendData(event) {
        const query = {
            sendsignin: "sign_in",
            sendsignout: "sign_out",
            sendautoadd: "auto_add",
            sendremovedevice: "remove_device"
        }[event.type];

        if (window.serverStatus == 2) {
            this.#webSocket.send(
                JSON.stringify({
                    query: query,
                    data: event.detail
                })
            );
            console.log('Sent message "' + query + '"');
        }
    }
}
