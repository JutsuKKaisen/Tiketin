document.addEventListener("DOMContentLoaded", function () {
    if (document.getElementById("qr-reader")) {
        startQRScanner();
    }
});

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
        (errorMessage) => { /* Xử lý lỗi quét (nếu cần) */ }
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
            alert("❌ " + data.error);
        } else {
            document.getElementById("ticket-info").style.display = "block";
            document.getElementById("ticket-name").innerText = data.ten;
            document.getElementById("ticket-mssv").innerText = data.mssv;
            document.getElementById("ticket-class").innerText = data.lop;
            document.getElementById("ticket-email").innerText = data.mail;
            document.getElementById("ticket-phone").innerText = data.sdt;
            document.getElementById("ticket-status").innerText = "✅ Đã Check-in";
            alert("✅ Check-in thành công!");
            startQRScanner();
        }
    })
    .catch(error => alert("Lỗi: " + error));
}