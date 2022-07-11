// Alerts the user if the main code doesn't load properly
window.addEventListener("load", function () {
    if (this.window.mainAlive != true) {
        this.alert("This browser is too old to run AdvantageTrack :(");
    }
});
