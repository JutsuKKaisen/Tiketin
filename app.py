import os
import csv
from flask import Flask, request, jsonify, render_template, redirect, url_for
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)

load_dotenv()
app.secret_key = os.getenv("key.env")
app.secret_key = "a113649be1203ff3702f3e06fa91178718cf1551f6c88b1eb677988f6e9168cd"

# Cấu hình Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Kết nối Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("database_gculaw_tiketin").sheet1  # Cập nhật tên sheet

# Tài khoản hệ thống
users = {
    "admin": {"password": "admin123", "role": "admin"},
    "operator": {"password": "op123", "role": "op"},
}

class User(UserMixin):
    def __init__(self, username, role):
        self.id = username
        self.role = role

@login_manager.user_loader
def load_user(username):
    user_data = users.get(username)
    if user_data:
        return User(username, user_data["role"])
    return None

@app.route("/login", methods=["GET", "POST"])
def login():
    """ Đăng nhập hệ thống """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user_data = users.get(username)
        if user_data and user_data["password"] == password:
            user = User(username, user_data["role"])
            login_user(user)

            # Kiểm tra nếu có `next` thì chuyển hướng đến đó
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))

        return "Sai tài khoản hoặc mật khẩu!", 403

    return render_template("login.html")

@app.route("/")
@login_required
def dashboard():
    """ Điều hướng theo phân quyền """
    if current_user.role == "admin":
        return render_template("admin.html", role="admin")
    else:
        return render_template("op.html", role="op")

@app.route("/logout")
@login_required
def logout():
    """ Đăng xuất hệ thống """
    logout_user()
    return redirect(url_for("login"))

@app.route("/import-csv", methods=["POST"])
@login_required
def import_csv():
    """ Chỉ Admin có quyền tải file CSV lên """
    if current_user.role != "admin":
        return jsonify({"error": "Bạn không có quyền truy cập!"}), 403

    try:
        if "file" not in request.files:
            return jsonify({"error": "Thiếu file CSV!"}), 400

        file = request.files["file"]
        if not file.filename.endswith(".csv"):
            return jsonify({"error": "File phải có định dạng .csv"}), 400

        csv_data = list(csv.reader(file.read().decode("utf-8").splitlines()))
        headers = csv_data[0]
        rows = csv_data[1:]

        required_fields = ["Tên", "MSSV", "Lớp", "Email", "SĐT"]
        if not all(field in headers for field in required_fields):
            return jsonify({"error": "Thiếu cột dữ liệu trong file CSV"}), 400

        # Lấy dữ liệu hiện tại từ Google Sheets
        all_records = sheet.get_all_records()

        # Xác định các vé chưa đăng ký
        unregistered_qrs = [
            row for row in all_records
            if row["CODE"] and not any(row[field] for field in ["TEN", "MSSV", "LỚP", "MAIL", "SDT"])
        ]

        if len(unregistered_qrs) < len(rows):
            return jsonify({"error": "Số lượng QR chưa đăng ký không đủ"}), 400

        # Gán dữ liệu từ CSV vào QR chưa đăng ký
        updates = []
        for index, row in enumerate(rows):
            qr_code = unregistered_qrs[index]["CODE"]
            updates.append([
                qr_code, row[0], row[1], row[2], row[3], row[4], "đã mua vé"
            ])

        # Cập nhật dữ liệu Google Sheets
        sheet.update(f"A2:G{len(updates) + 1}", updates)
        return jsonify({"message": f"Đã cập nhật {len(updates)} vé!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/checkin", methods=["GET", "POST"])
@login_required
def checkin():
    if request.method == "GET":
        return render_template("op.html")  # Trả về trang quét QR cho Admin
    
    """ OP có quyền check-in vé """
    try:
        data = request.json
        code = data.get("code", "").strip()

        if not code:
            return jsonify({"error": "Mã QR không hợp lệ!"}), 400

        records = sheet.get_all_records()

        # Tìm hàng chứa QR Code
        row_data = next((row for row in records if row["CODE"] == code), None)

        if not row_data:
            return jsonify({"error": f"Không tìm thấy mã CODE `{code}` trong Google Sheets!"}), 404

        row_index = records.index(row_data) + 2  # Hàng trong Google Sheets

        # Cập nhật trạng thái check-in
        sheet.update(f"G{row_index}", [["đã check in"]])

        return jsonify({
            "message": "Check-in thành công!",
            "ten": row_data["TEN"],
            "mssv": row_data["MSSV"],
            "lop": row_data["LỚP"],
            "mail": row_data["MAIL"],
            "sdt": row_data["SDT"],
            "trangthai": "Đã Check-in"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)