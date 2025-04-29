const drawSignatureOption = document.getElementById('draw-signature-option');
const uploadSignatureOption = document.getElementById('upload-signature-option');
const drawSignatureSection = document.getElementById('draw-signature-section');
const uploadSignatureSection = document.getElementById('upload-signature-section');
const signatureCanvas = document.getElementById('signature-canvas');
const ctx = signatureCanvas.getContext('2d');
const signatureFileInput = document.getElementById('signature-file');
const signaturePreview = document.getElementById('signature-preview');
let signatureData = null;
let drawing = false;

// Toggle between drawing and uploading signature
drawSignatureOption.addEventListener('change', function () {
    drawSignatureSection.style.display = 'block';
    uploadSignatureSection.style.display = 'none';
});

uploadSignatureOption.addEventListener('change', function () {
    drawSignatureSection.style.display = 'none';
    uploadSignatureSection.style.display = 'block';
});

// Handle signature drawing
signatureCanvas.addEventListener('mousedown', function () {
    drawing = true;
});
signatureCanvas.addEventListener('mouseup', function () {
    drawing = false;
    ctx.beginPath();
});
signatureCanvas.addEventListener('mousemove', function (e) {
    if (!drawing) return;
    const rect = signatureCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.strokeStyle = 'black';

    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y);
});

// Clear canvas
document.getElementById('clear-signature').addEventListener('click', function () {
    ctx.clearRect(0, 0, signatureCanvas.width, signatureCanvas.height);
});

// Save drawn signature
document.getElementById('save-signature').addEventListener('click', function () {
    signatureData = signatureCanvas.toDataURL('image/png');
    alert('Signature saved!');
});

// Preview uploaded signature
signatureFileInput.addEventListener('change', function () {
    const file = this.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            signaturePreview.src = e.target.result;
            signaturePreview.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
});
