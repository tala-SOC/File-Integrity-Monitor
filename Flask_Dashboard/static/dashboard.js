
document.addEventListener("DOMContentLoaded", () => {
    const particleContainer = document.getElementById("particles");
    const fileInput = document.getElementById("file");
    const dropZone = document.getElementById("drop-zone");
    const preview = document.getElementById("file-preview");
    const fileName = document.getElementById("file-name");
    const fileSize = document.getElementById("file-size");
    const fileIcon = document.getElementById("file-icon");
    const removeButton = document.getElementById("remove-file");
    const form = document.getElementById("upload-form");
    const analyzeButton = document.getElementById("analyze-button");

    // Floating background particles
    if (particleContainer) {
        const count = window.matchMedia("(max-width: 600px)").matches ? 14 : 32;
        const fragment = document.createDocumentFragment();

        for (let i = 0; i < count; i++) {
            const particle = document.createElement("span");
            particle.className = "particle";
            particle.style.left = `${Math.random() * 100}%`;
            particle.style.top = `${Math.random() * 100}%`;
            particle.style.setProperty("--duration", `${9 + Math.random() * 14}s`);
            particle.style.setProperty("--delay", `${-Math.random() * 20}s`);
            fragment.appendChild(particle);
        }

        particleContainer.appendChild(fragment);
    }

    if (!fileInput || !dropZone || !form) return;

    function formatSize(bytes) {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        if (bytes < 1024 * 1024 * 1024) {
            return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
        }
        return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }

    function displayFile(file) {
        if (!file) return;

        fileName.textContent = file.name;
        fileSize.textContent = formatSize(file.size);

        const extension = file.name.includes(".")
            ? file.name.split(".").pop().slice(0, 5).toUpperCase()
            : "FILE";

        fileIcon.textContent = extension || "FILE";
        preview.hidden = false;
        dropZone.classList.add("has-file");
    }

    fileInput.addEventListener("change", () => {
        displayFile(fileInput.files[0]);
    });

    // Drag-and-drop behavior
    ["dragenter", "dragover"].forEach((eventName) => {
        dropZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropZone.classList.add("drag-over");
        });
    });

    ["dragleave", "drop"].forEach((eventName) => {
        dropZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropZone.classList.remove("drag-over");
        });
    });

    dropZone.addEventListener("drop", (event) => {
        const files = event.dataTransfer.files;
        if (!files || files.length === 0) return;

        const transfer = new DataTransfer();
        transfer.items.add(files[0]);
        fileInput.files = transfer.files;

        displayFile(files[0]);
    });

    // Remove the selected file
    if (removeButton) {
        removeButton.addEventListener("click", () => {
            fileInput.value = "";
            preview.hidden = true;
            dropZone.classList.remove("has-file");
            fileInput.focus();
        });
    }

    // Prevent empty submissions and indicate the submission state.
    form.addEventListener("submit", (event) => {
        if (!fileInput.files || fileInput.files.length === 0) {
            event.preventDefault();
            fileInput.reportValidity();
            return;
        }

        if (analyzeButton) {
            analyzeButton.disabled = true;
            analyzeButton.querySelector("span:nth-child(2)").textContent =
                "Uploading File...";
        }
    });
});
