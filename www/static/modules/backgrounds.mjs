/** Manages the scrolling background images. */
export class Backgrounds {
    // Elements
    #mainImagesContainer = document.getElementsByClassName("main-background-images")[0];
    #blurredImagesContainer = document.getElementsByClassName("blurred-background-images")[0];
    #referenceContainer = document.getElementById("backgroundImagesReference");

    // Constants
    #scrollRate = 0.1;

    constructor() {
        var periodic = () => {
            this.#updateBackgroundContainer(this.#mainImagesContainer, this.#blurredImagesContainer.clientWidth);
            this.#updateBackgroundContainer(this.#blurredImagesContainer, 0);
            window.requestAnimationFrame(periodic);
        };
        window.requestAnimationFrame(periodic);
    }

    /** Update a single background container. */
    #updateBackgroundContainer(container, offset) {
        var images = Array.from(this.#referenceContainer.children);

        // Calculate pixel offset
        var totalWidthRelative = images.reduce((width, image) => width + image.width / image.height, 0);
        var wrapPeriod = totalWidthRelative / this.#scrollRate;
        var timeWrapped = (new Date().getTime() / 1000) % wrapPeriod;
        var positionRelative = (timeWrapped / wrapPeriod) * totalWidthRelative;
        var pixelOffset = positionRelative * container.clientHeight + offset;

        // Calculate required duplicate cycles
        var renderWidths = images.map((image) => (image.width / image.height) * container.clientHeight);
        var duplicateCycles = Math.ceil((container.clientWidth + offset) / renderWidths.reduce((a, b) => a + b, 0));

        // Copy images
        var currentUrls = Array.from(container.children).map((image) => image.src);
        var targetUrls = this.#addDuplicates(
            images.map((image) => image.src),
            duplicateCycles
        );
        if (JSON.stringify(currentUrls) != JSON.stringify(targetUrls)) {
            while (container.firstChild) {
                container.removeChild(container.firstChild);
            }
            this.#addDuplicates(images, duplicateCycles).forEach((image) => {
                container.appendChild(image.cloneNode(false));
            });
        }

        // Set scroll
        const devicePixelRatio = window.devicePixelRatio;
        container.scrollTo(Math.floor(pixelOffset * devicePixelRatio) / devicePixelRatio, 0);
    }

    /** Utility function to concatenate duplicate copies of an array. */
    #addDuplicates(array, duplicates) {
        var newArray = array;
        for (let i = 0; i < duplicates; i++) {
            newArray = newArray.concat(array);
        }
        return newArray;
    }
}
