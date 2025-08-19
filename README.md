# Tiketin

**Tiketin** is a Flask-based **ticket management self-hosted system** designed for Indie events.  
It integrates with **Google Sheets** and **Google Drive** for storage, and provides both **Admin** and **Operator** roles to manage tickets efficiently.

## ✨ Features

### 🔑 Authentication & Roles
- Secure login system with role-based access control (Admin / Operator).  
- Admins have full control, while operators can only handle check-in.  

### 🎟 Ticket Management
- Upload participant data via **CSV**.  
- Automatically generate **unique ticket codes**.  
- Create **QR codes** for each ticket and place them on a template image.  
- Upload generated tickets to **Google Drive** and store links in Google Sheets.  

### 📋 Admin Dashboard
- View all tickets stored in Google Sheets.  
- Search and sort ticket lists by code, name, email, or status.  
- Upload new participant lists in bulk via CSV.  
- Send confirmation emails with ticket QR attachments.  

### ✅ Check-in System
- QR scanner interface for operators.  
- Validate ticket codes in real-time against Google Sheets.  
- Update ticket status to **Checked-in** automatically.  

### 📧 Email Integration
- Send customized confirmation emails with attached QR ticket images.  
- Prevent duplicate sending (tracks email status in Google Sheets).  
- Multi-threaded sending for better performance.  

## 📖 How It Works
1. **Login** as Admin or Operator.  
2. **Admins** can:  
   - Upload CSV files with participant info.  
   - Generate tickets with QR codes and save them to Google Drive.  
   - View and manage the ticket list.  
   - Send confirmation emails.  
3. **Operators** can:  
   - Use the QR scanner to check in participants.  
   - Verify ticket details in real-time.  

## 🔧 Installation

### 1. Clone the repository
```bash
git clone https://github.com/JutsuKKaisen/Tiketin.git
cd Tiketin
````

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup environment

* Create a `.env` file and configure:

  ```env
  SECRET_KEY=your_flask_secret_key
  SHEET_NAME=your_google_sheet_name
  USERS=admin,op
  ADMIN_PASSWORD=your_admin_password
  ADMIN_ROLE=admin
  OP_PASSWORD=your_operator_password
  OP_ROLE=op
  DRIVE_FOLDER_ID=your_google_drive_folder_id
  TEMPLATE_PATH=template.png
  ```
* Place your `credentials.json` for Google Sheets & Drive API in the project root.
* Generate a Flask secret key (example: `python Key_generator.py`).

### 4. Run the app

```bash
python app.py
```

App will be available at: `http://localhost:5000`

## 📂 Project Structure

```
Tiketin/
│── app.py                # Main Flask app
│── Key_generator.py      # Secret key generator
│── templates/            # HTML templates
│   ├── login.html
│   ├── admin.html
│   ├── checkin.html
│   ├── upload_csv.html
│   ├── send_emails.html
│   ├── view_tickets.html
│── static/               # CSS & JS files
│── requirements.txt
│── .env
│── credentials.json
```

## 🚀 Demo Flow

* **Admin**:

  1. Login → Admin Dashboard.
  2. Upload CSV → Generate QR tickets.
  3. View ticket list → Send confirmation emails.
* **Operator**:

  1. Login → Check-in page.
  2. Scan QR code → Verify ticket → Mark as checked-in.

## ⚠️ Disclaimer

This project is intended for **educational and organizational event purposes only**.
Please make sure you comply with your institution’s or organization’s policies before using it in production.

---

Made with ❤️ by \JutsuKKaisen
