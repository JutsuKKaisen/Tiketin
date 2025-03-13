document.addEventListener("DOMContentLoaded", function () {
    if (document.getElementById("qr-reader")) {
        startQRScanner();
    }

    if (document.getElementById("upload-form")) {
        setupCSVUpload();
    }
});

/* ===================== QUÉT QR & CHECK-IN ===================== */
function startQRScanner() {
    let html5QrCode = new Html5Qrcode("qr-reader");
    let qrBoxSize = { width: 300, height: 300 };

    html5QrCode.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: qrBoxSize },
        (decodedText) => {
            html5QrCode.stop().then(() => {
                checkIn(decodedText);
            }).catch(err => console.log("Lỗi dừng camera:", err));
        },
        (errorMessage) => { /* Xử lý lỗi quét nếu cần */ }
    ).catch(err => console.log("Lỗi khởi động camera:", err));
}

function checkIn(qrCode) {
    fetch("/checkin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: qrCode })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            document.getElementById("ticket-status").innerText = "❌ " + data.error;
            document.getElementById("ticket-status").style.color = "red";
        } else {
            document.getElementById("ticket-info").style.display = "block";
            document.getElementById("ticket-name").innerText = data.ten;
            document.getElementById("ticket-mssv").innerText = data.mssv;
            document.getElementById("ticket-class").innerText = data.lop;
            document.getElementById("ticket-email").innerText = data.mail;
            document.getElementById("ticket-phone").innerText = data.sdt;
            document.getElementById("ticket-status").innerText = data.trangthai;
            document.getElementById("ticket-status").style.color = data.trangthai === "Đã Check-in" ? "green" : "black";
        }
        setTimeout(startQRScanner, 1000);
    })
    .catch(error => console.error("Lỗi check-in:", error));
}

/* ===================== UPLOAD CSV ===================== */
function setupCSVUpload() {
    document.getElementById("upload-form").addEventListener("submit", function (event) {
        event.preventDefault();
        
        let fileInput = document.getElementById("csv-file");
        let uploadStatus = document.getElementById("upload-status");

        if (fileInput.files.length === 0) {
            uploadStatus.innerText = "❌ Vui lòng chọn một file CSV!";
            uploadStatus.style.color = "red";
            return;
        }

        let file = fileInput.files[0];
        if (!file.name.endsWith(".csv")) {
            uploadStatus.innerText = "❌ Chỉ chấp nhận file CSV!";
            uploadStatus.style.color = "red";
            return;
        }

        let formData = new FormData();
        formData.append("file", file);

        uploadStatus.innerText = "🔄 Đang tải lên...";
        uploadStatus.style.color = "blue";

        fetch("/upload_csv", {
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            console.log("📩 Response từ server:", data);  // Debug log
            uploadStatus.innerText = data.error || data.message;
            uploadStatus.style.color = data.error ? "red" : "green";
        })
        .catch(error => {
            uploadStatus.innerText = "❌ Lỗi hệ thống! Vui lòng thử lại.";
            uploadStatus.style.color = "red";
            console.error("Lỗi upload file:", error);
        });
    });
}