import { ServerInterface } from "./modules/serverInterface.mjs";
import { Backgrounds } from "./modules/backgrounds.mjs";
import { HereNow } from "./modules/hereNow.mjs";
import { PopupMenu } from "./modules/popupMenu.mjs";

const welcomeMessageHeightPercentageTarget = 15;

const welcomeMessageDiv = document.getElementsByClassName("welcome-message")[0];
const signInButton = document.getElementsByClassName("sign-in-button")[0];
const manageDevicesButton = document.getElementsByClassName("manage-devices-button")[0];

const serverStatusElement = document.getElementsByClassName("status-lights")[0].children[0];
const monitorStatusElement = document.getElementsByClassName("status-lights")[0].children[1];
const googleStatusElement = document.getElementsByClassName("status-lights")[0].children[2];

// Status of each connection (0 = disconnected, 1 = error, 2 = connected)
window.serverStatus = 0;
window.monitorStatus = 0;
window.googleStatus = 0;

window.configCache = { welcome_message: "", people: [] };
window.dataCache = { devices: [], here_now: [] };
window.addAddress = "http://127.0.0.1:8000/add";

/** Updates the status lights based on the current status codes. */
function updateStatusLights() {
    Array(
        [serverStatusElement, window.serverStatus],
        [monitorStatusElement, window.monitorStatus],
        [googleStatusElement, window.googleStatus]
    ).forEach((item) => {
        item[0].classList.remove("disconnected");
        item[0].classList.remove("error");
        item[0].classList.remove("connected");
        switch (item[1]) {
            case 0:
                item[0].classList.add("disconnected");
                break;
            case 1:
                item[0].classList.add("error");
                break;
            case 2:
                item[0].classList.add("connected");
                break;
        }
    });
}

/** Sets the welcome message and updates the font size. */
function updateLayout() {
    welcomeMessageDiv.textContent = configCache["welcome_message"];
    welcomeMessageDiv.style.height = "";
    const welcomeMessageHeightPx = window.innerHeight * (welcomeMessageHeightPercentageTarget / 100);
    var fontSize = 200;
    do {
        fontSize--;
        welcomeMessageDiv.style.fontSize = fontSize.toString() + "px";
    } while (
        welcomeMessageDiv.clientHeight > welcomeMessageHeightPx ||
        welcomeMessageDiv.scrollWidth > welcomeMessageDiv.clientWidth
    );
    document.documentElement.style.setProperty(
        "--welcome-message-bottom",
        welcomeMessageDiv.getBoundingClientRect().bottom.toString() + "px"
    );
}

// Initialize on DOM load
window.addEventListener("load", () => {
    window.serverInterface = new ServerInterface();
    window.backgrounds = new Backgrounds();
    window.hereNow = new HereNow();
    window.popupMenu = new PopupMenu();

    signInButton.addEventListener("click", () => window.popupMenu.setState(0));
    manageDevicesButton.addEventListener("click", () => window.popupMenu.setState(2));

    updateLayout();
    window.addEventListener("resize", updateLayout);
    document.addEventListener("configupdate", updateLayout);
    document.addEventListener("statusupdate", updateStatusLights);
});

// If we're still alive, the necessary JS features are supported
window.mainAlive = true;
