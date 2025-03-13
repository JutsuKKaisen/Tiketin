import os
import csv
from flask import Flask, request, jsonify, render_template, redirect, url_for
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

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
        return render_template("checkin.html", role="op")

@app.route("/logout")
@login_required
def logout():
    """ Đăng xuất hệ thống """
    logout_user()
    return redirect(url_for("login"))

@app.route("/view_tickets")
@login_required
def view_tickets():
    """ Hiển thị danh sách vé từ Google Sheets """
    if current_user.role != "admin":
        return "❌ Bạn không có quyền truy cập!", 403

    records = sheet.get_all_records()
    return render_template("view_tickets.html", records=records)

@app.route("/upload_csv", methods=["GET", "POST"])
@login_required
def upload_csv():
    """Admin tải lên file CSV để nhập dữ liệu vé"""
        # Kiểm tra quyền admin
    if current_user.role != "admin":
        return jsonify({"error": "Bạn không có quyền upload file CSV!"}), 403

    if request.method == "GET":
        return render_template("upload_csv.html")  # Hiển thị form upload CSV

    # Kiểm tra có file không
    if "file" not in request.files:
        return jsonify({"error": "Không tìm thấy file trong request!"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "File không có tên!"}), 400

    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Chỉ chấp nhận file CSV!"}), 400

    try:
        # Đọc nội dung CSV
        file_contents = file.read().decode("utf-8").splitlines()
        csv_reader = csv.reader(file_contents)

        # Bỏ qua dòng tiêu đề
        header = next(csv_reader, None)
        expected_columns = ["TEN", "MSSV", "LOP", "MAIL", "SDT"]
        
        if header != expected_columns:
            return jsonify({"error": f"Định dạng CSV không đúng! Cần các cột: {expected_columns}"}), 400

        # Lấy danh sách vé chưa đăng ký (CODE chưa có thông tin)
        records = sheet.get_all_records()
        empty_tickets = [r for r in records if not any(r[k] for k in expected_columns)]

        # Kiểm tra số lượng vé trống có đủ không
        csv_data = list(csv_reader)
        if len(empty_tickets) < len(csv_data):
            return jsonify({"error": "Số lượng vé trống không đủ để đăng ký!"}), 400

        # Ghi dữ liệu lên Google Sheets
        for i, row in enumerate(csv_data):
            row_index = records.index(empty_tickets[i]) + 2  # Hàng trong Google Sheets
            print(f"📌 Ghi dữ liệu vào hàng {row_index}: {row}")  # Debug log
            
            sheet.update(f"B{row_index}:F{row_index}", [row])  # Ghi dữ liệu từ cột B đến F

        return jsonify({"message": "✅ File CSV đã được tải lên thành công!"})

    except Exception as e:
        print(f"❌ Lỗi xử lý CSV: {e}")  # Debug log
        return jsonify({"error": f"Lỗi xử lý CSV: {str(e)}"}), 500

@app.route("/checkin", methods=["GET", "POST"])
@login_required
def checkin():
    """ OP và Admin có thể check-in vé """
    if request.method == "GET":
        return render_template("checkin.html", role=current_user.role)  # Admin & OP đều truy cập

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

        # Nếu là OP, cập nhật trạng thái check-in
        if current_user.role == "op":
            sheet.update(f"G{row_index}", [["đã check in"]])

        return jsonify({
            "message": "Check-in thành công!" if current_user.role == "op" else "Thông tin vé",
            "ten": row_data["TEN"],
            "mssv": row_data["MSSV"],
            "lop": row_data["LOP"],
            "mail": row_data["MAIL"],
            "sdt": row_data["SDT"],
            "trangthai": "Đã Check-in" if current_user.role == "op" else row_data.get("trangthai", "Chưa check-in")
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)