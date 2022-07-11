/** Manages the "Here Now" section of the side bar. */
export class HereNow {
    // Elements
    #serverWarning = document.getElementsByClassName("here-now-warning")[0];
    #googleWarning = document.getElementsByClassName("here-now-warning")[1];
    #table = document.getElementsByClassName("here-now-table")[0];
    #tableBody = this.#table.firstElementChild;

    // Constants
    #columns = 3;

    // Variables
    #connected = false;

    constructor() {
        document.addEventListener("configupdate", () => this.#updateTable());
        document.addEventListener("dataupdate", () => this.#updateTable());
        document.addEventListener("statusupdate", () => this.#updateStatus());
    }

    /** Updates the list of names in the table. */
    #updateTable() {
        while (this.#tableBody.firstChild) {
            this.#tableBody.removeChild(this.#tableBody.firstChild);
        }
        window.dataCache["here_now"]
            .map((x) => {
                return {
                    name: window.configCache["people"].find((y) => y["id"] == x["person"])["name"],
                    person: x["person"],
                    manual: x["manual"]
                };
            })
            .sort((a, b) => {
                if (a["manual"] == b["manual"]) {
                    return a["name"].localeCompare(b["name"]);
                } else if (a["manual"]) {
                    return -1;
                } else {
                    return 1;
                }
            })
            .forEach((person, index) => {
                if (index % this.#columns == 0) {
                    this.#tableBody.appendChild(document.createElement("tr"));
                }
                var cell = document.createElement("td");
                cell.innerText = person["name"];
                if (!person["manual"]) cell.classList.add("auto");
                cell.addEventListener("click", () => {
                    if (this.#connected) {
                        document.dispatchEvent(
                            new CustomEvent("sendsignout", {
                                detail: person["person"]
                            })
                        );
                    }
                });
                this.#tableBody.lastElementChild.appendChild(cell);
            });
    }

    /** Updates the connection warning based on the current status. */
    #updateStatus() {
        if (window.serverStatus != 2) {
            this.#connected = false;
            this.#serverWarning.hidden = false;
            this.#googleWarning.hidden = true;
        } else if (window.googleStatus != 2) {
            this.#connected = false;
            this.#serverWarning.hidden = true;
            this.#googleWarning.hidden = false;
        } else {
            this.#connected = true;
            this.#serverWarning.hidden = true;
            this.#googleWarning.hidden = true;
        }
        if (this.#connected) {
            this.#table.classList.remove("disabled");
        } else {
            this.#table.classList.add("disabled");
        }
    }
}
