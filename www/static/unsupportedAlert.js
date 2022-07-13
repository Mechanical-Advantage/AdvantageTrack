// Alerts the user if the main code doesn't load properly
window.addEventListener("load", function () {
    if (this.window.mainAlive != true) {
        this.alert("There was a problem loading AdvantageTrack. This browser may be too old.");
    }
});
