/** Manages the scrolling background images. */
export class Backgrounds {
    // Elements
    #canvas = document.getElementById("backgroundCanvas");
    #blurredCanvas = document.getElementById("blurredBackgroundCanvas");
    #imagesContainer = document.getElementById("backgroundImages");

    // Constants
    #scrollRate = 0.1;

    constructor() {
        var periodic = () => {
            this.#updateCanvas();
            window.requestAnimationFrame(periodic);
        };
        window.requestAnimationFrame(periodic);

        document.addEventListener("backgroundupdate", () => {
            while (this.#imagesContainer.firstChild) {
                this.#imagesContainer.removeChild(this.#imagesContainer.firstChild);
            }
            window.backgroundData["files"].forEach((background) => {
                let image = document.createElement("img");
                image.src =
                    "/backgrounds/" + (window.backgroundData["is_default"] ? "default" : "user") + "/" + background;
                this.#imagesContainer.appendChild(image);
            });
        });
    }

    /** Redraw the canvas. */
    #updateCanvas() {
        const images = Array.from(this.#imagesContainer.children);

        // Initialize canvases
        const devicePixelRatio = window.devicePixelRatio;
        var context = this.#canvas.getContext("2d");
        var canvasWidth = this.#canvas.clientWidth;
        var canvasHeight = this.#canvas.clientHeight;
        this.#canvas.width = canvasWidth * devicePixelRatio;
        this.#canvas.height = canvasHeight * devicePixelRatio;
        context.scale(devicePixelRatio, devicePixelRatio);
        context.clearRect(0, 0, canvasWidth, canvasHeight);

        var blurredContext = this.#blurredCanvas.getContext("2d");
        var blurredCanvasWidth = this.#blurredCanvas.clientWidth;
        var blurredCanvasHeight = this.#blurredCanvas.clientHeight;
        this.#blurredCanvas.width = blurredCanvasWidth * devicePixelRatio;
        this.#blurredCanvas.height = blurredCanvasHeight * devicePixelRatio;
        blurredContext.scale(devicePixelRatio, devicePixelRatio);
        blurredContext.clearRect(0, 0, blurredCanvasWidth, blurredCanvasHeight);

        // Check if all images are loaded
        var allLoaded = true;
        images.forEach((image) => {
            if (!image.complete || image.naturalHeight == 0) {
                allLoaded = false;
            }
        });
        if (images.length == 0) {
            allLoaded = false;
        }
        if (!allLoaded) {
            return;
        }

        // Calculate pixel offset
        var totalWidthRelative = images.reduce((width, image) => width + image.width / image.height, 0);
        var wrapPeriod = totalWidthRelative / this.#scrollRate;
        var timeWrapped = (new Date().getTime() / 1000) % wrapPeriod;
        var positionRelative = (timeWrapped / wrapPeriod) * totalWidthRelative;
        var pixelOffset = positionRelative * canvasHeight;

        // Concatenate duplicate copies of the array
        function addDuplicates(array, duplicates) {
            var newArray = array;
            for (let i = 0; i < duplicates; i++) {
                newArray = newArray.concat(array);
            }
            return newArray;
        }

        // Render images
        var adjustedWidths = images.map((image) => (image.width / image.height) * canvasHeight);
        var duplicates = Math.ceil(canvasWidth / adjustedWidths.reduce((a, b) => a + b, 0));
        adjustedWidths = addDuplicates(adjustedWidths, duplicates);
        addDuplicates(images, duplicates).forEach((image, index) => {
            var startX = adjustedWidths.slice(0, index).reduce((a, b) => a + b, 0) - pixelOffset;
            if (startX > canvasWidth || startX + adjustedWidths[index] < 0) {
                // Not visible
                return;
            }
            context.drawImage(image, startX, 0, Math.ceil(adjustedWidths[index]), canvasHeight);
        });

        // Add blurred version
        blurredContext.drawImage(
            this.#canvas,
            0,
            0,
            blurredCanvasWidth * devicePixelRatio,
            blurredCanvasHeight * devicePixelRatio,
            0,
            0,
            blurredCanvasWidth,
            blurredCanvasHeight
        );
    }
}
