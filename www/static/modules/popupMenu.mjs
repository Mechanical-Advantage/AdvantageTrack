/** Manages the popup menu lifecycle and contents. */
export class PopupMenu {
    // Elements
    #menu = document.getElementsByClassName("popup-menu")[0];
    #menuDivs = Array.from(this.#menu.children);

    #serverWarnings = [
        this.#menuDivs[0].getElementsByClassName("warning")[0],
        this.#menuDivs[2].getElementsByClassName("warning")[0]
    ];
    #googleWarnings = [
        this.#menuDivs[0].getElementsByClassName("warning")[1],
        this.#menuDivs[2].getElementsByClassName("warning")[1]
    ];

    #signInPeopleTable = this.#menuDivs[0].getElementsByTagName("table")[0];
    #signInPeopleTableBody = this.#signInPeopleTable.firstElementChild;
    #devicesPeopleTable = this.#menuDivs[2].getElementsByTagName("table")[0];
    #devicesPeopleTableBody = this.#devicesPeopleTable.firstElementChild;

    #addAddress = this.#menuDivs[3].getElementsByClassName("add-address")[0];
    #deviceDetailsName = this.#menuDivs[3].getElementsByClassName("title")[0].firstElementChild;
    #deviceDetailsListTitle = this.#menuDivs[3].children[3];
    #deviceDetailsList = this.#menuDivs[3].children[4];

    // Constants
    #slideTransition = "transform 0.3s";
    #peopleColumns = 4;
    #thanksTimeoutLengthMs = 3000;

    // Variables
    #state = -1; // -1 = hidden, 0 = sign in people, 1 = sign in thanks, 2 = manage devices people, 3 = manage devices details
    #connected = false;
    #thanksTimeout = null;
    #lastDeviceDetailsPerson = null;

    constructor() {
        document.addEventListener("configupdate", () => this.#updateTables());
        document.addEventListener("configupdate", () => this.#updateDeviceDetails(null));
        document.addEventListener("dataupdate", () => this.#updateTables());
        document.addEventListener("dataupdate", () => this.#updateDeviceDetails(null));
        document.addEventListener("statusupdate", () => this.#updateStatus());
        Array.from(this.#menu.getElementsByClassName("close-button")).forEach((button) => {
            button.firstElementChild.addEventListener("click", () => this.setState(-1));
        });
        document.addEventListener("addaddressupdate", () => this.#updateAddAddress());
        this.#updateAddAddress();
    }

    /** Sets which page should be displayed */
    setState(newState) {
        if (newState != -1) {
            window.clearTimeout(this.#thanksTimeout);
        }

        // Set transition style
        const transitionStyle = this.#state == -1 ? "" : this.#slideTransition;
        this.#menuDivs.forEach((div) => (div.style.transition = transitionStyle));

        // Hide extra divs
        this.#menuDivs.forEach((div) => (div.style.opacity = 0));
        if (this.#state != -1) this.#menuDivs[this.#state].style.opacity = 1;
        if (newState != -1) this.#menuDivs[newState].style.opacity = 1;

        // Switch page
        switch (newState) {
            case 0:
                this.#menuDivs[0].scrollTo(0, 0);
                this.#menuDivs[0].style.transform = "translate(0%, 0%)";
                this.#menuDivs[1].style.transform = "translate(100%, 0%)";
                this.#menuDivs[2].style.transform = "translate(0%, 100%)";
                this.#menuDivs[3].style.transform = "translate(100%, 100%)";
                break;
            case 1:
                this.#menuDivs[0].style.transform = "translate(-100%, 0%)";
                this.#menuDivs[1].style.transform = "translate(0%, 0%)";
                this.#menuDivs[2].style.transform = "translate(-100%, 100%)";
                this.#menuDivs[3].style.transform = "translate(0%, 100%)";
                break;
            case 2:
                this.#menuDivs[2].scrollTo(0, 0);
                this.#menuDivs[0].style.transform = "translate(0%, -100%)";
                this.#menuDivs[1].style.transform = "translate(100%, -100%)";
                this.#menuDivs[2].style.transform = "translate(0%, 0%)";
                this.#menuDivs[3].style.transform = "translate(100%, 0%)";
                break;
            case 3:
                this.#menuDivs[3].scrollTo(0, 0);
                this.#menuDivs[0].style.transform = "translate(-100%, -100%)";
                this.#menuDivs[1].style.transform = "translate(0%, -100%)";
                this.#menuDivs[2].style.transform = "translate(-100%, 0%)";
                this.#menuDivs[3].style.transform = "translate(0%, 0%)";
                break;
        }

        // Set visible
        this.#menu.classList.remove(newState == -1 ? "visible" : "invisible");
        this.#menu.classList.add(newState == -1 ? "invisible" : "visible");
        this.#menu.style.pointerEvents = newState == -1 ? "none" : "initial";

        // Update state
        this.#state = newState;
    }

    /** Updates the list of names in the tables. */
    #updateTables() {
        while (this.#signInPeopleTableBody.firstChild) {
            this.#signInPeopleTableBody.removeChild(this.#signInPeopleTableBody.firstChild);
        }
        while (this.#devicesPeopleTableBody.firstChild) {
            this.#devicesPeopleTableBody.removeChild(this.#devicesPeopleTableBody.firstChild);
        }

        const allPeople = window.configCache["people"].sort((a, b) => {
            return a["name"].localeCompare(b["name"]);
        });
        var hereNowLookup = {}; // Key = person ID, value = manual
        window.dataCache["here_now"].forEach((x) => {
            hereNowLookup[x["person"]] = x["manual"];
        });
        const signInPeople = allPeople.filter((x) => {
            return x["is_active"] && !(x["id"] in hereNowLookup && hereNowLookup[x["id"]]);
        });

        Array(
            [signInPeople, this.#signInPeopleTableBody, true],
            [allPeople, this.#devicesPeopleTableBody, false]
        ).forEach((entry) => {
            let peopleList = entry[0];
            let tableBody = entry[1];
            let isSignIn = entry[2];

            peopleList.forEach((person, index) => {
                if (index % this.#peopleColumns == 0) {
                    tableBody.appendChild(document.createElement("tr"));
                }
                let cell = document.createElement("td");
                cell.innerText = person["name"];
                if (!person["manual"]) cell.classList.add("auto");
                cell.addEventListener("click", () => {
                    if (this.#connected) {
                        if (isSignIn) {
                            this.setState(1);
                            this.#thanksTimeout = window.setTimeout(() => {
                                this.setState(-1);
                            }, this.#thanksTimeoutLengthMs);
                            document.dispatchEvent(
                                new CustomEvent("sendsignin", {
                                    detail: person["id"]
                                })
                            );
                        } else {
                            this.#updateDeviceDetails(person["id"]);
                            this.setState(3);
                            document.dispatchEvent(
                                new CustomEvent("sendautoadd", {
                                    detail: person["id"]
                                })
                            );
                        }
                    }
                });
                tableBody.lastElementChild.appendChild(cell);
            });
        });
    }

    /** Updates the connection warnings based on the current status. */
    #updateStatus() {
        if (window.serverStatus != 2) {
            this.#connected = false;
            this.#serverWarnings.forEach((x) => (x.hidden = false));
            this.#googleWarnings.forEach((x) => (x.hidden = true));
        } else if (window.googleStatus != 2) {
            this.#connected = false;
            this.#serverWarnings.forEach((x) => (x.hidden = true));
            this.#googleWarnings.forEach((x) => (x.hidden = false));
        } else {
            this.#connected = true;
            this.#serverWarnings.forEach((x) => (x.hidden = true));
            this.#googleWarnings.forEach((x) => (x.hidden = true));
        }
        if (this.#connected) {
            this.#signInPeopleTable.classList.remove("disabled");
            this.#devicesPeopleTable.classList.remove("disabled");
        } else {
            this.#signInPeopleTable.classList.add("disabled");
            this.#devicesPeopleTable.classList.add("disabled");
        }
    }

    /** Updates the displayed address for adding a device. */
    #updateAddAddress() {
        this.#addAddress.innerText = window.addAddress;
    }

    /** Updates the device details page based on a person ID. */
    #updateDeviceDetails(person) {
        if (person == null) {
            // If not specified, update last person
            person = this.#lastDeviceDetailsPerson;
            if (person == null) {
                // No one selected yet
                return;
            }
        }
        this.#lastDeviceDetailsPerson = person;

        // Update title
        this.#deviceDetailsName.innerText = window.configCache["people"].find((x) => x["id"] == person)["name"];

        // Get list of devices
        const devices = window.dataCache["devices"]
            .filter((x) => {
                return x["person"] == person;
            })
            .sort((a, b) => {
                return a["last_seen"] < b["last_seen"];
            });

        // Update list title
        if (devices.length == 0) {
            this.#deviceDetailsListTitle.innerText = "0 devices registered.";
        } else if (devices.length == 1) {
            this.#deviceDetailsListTitle.innerText = "1 device registered:";
        } else {
            this.#deviceDetailsListTitle.innerText = devices.length.toString() + " devices registered:";
        }

        // Update list
        while (this.#deviceDetailsList.firstChild) {
            this.#deviceDetailsList.removeChild(this.#deviceDetailsList.firstChild);
        }
        devices.forEach((device) => {
            let div = document.createElement("div");
            this.#deviceDetailsList.appendChild(div);
            let lastSeen = "XX/XX/XX";
            if (device["last_seen"] != null) {
                lastSeen = new Date(device["last_seen"] * 1000).toLocaleDateString("en-US", {
                    month: "2-digit",
                    day: "2-digit",
                    year: "2-digit"
                });
            }
            div.innerHTML = device["mac"] + " - " + lastSeen + " (<span>Remove</span>)";
            div.firstElementChild.addEventListener("click", () => {
                document.dispatchEvent(
                    new CustomEvent("sendremovedevice", {
                        detail: {
                            person: person,
                            mac: device["mac"]
                        }
                    })
                );
            });
        });
    }
}
