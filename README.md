# Sachin's Sumangal Services - Garage Billing System

A modern, mobile-first garage billing web application built for **Sachin's Sumangal Services (Maruti Servicing Centre)**.

Designed for simplicity: a garage owner can create, generate, and share professional digital bills and PDF invoices directly from an Android mobile phone without complex accounting or technical knowledge, while all billing data is stored securely in an Oracle Database backend with a dedicated Admin Management Dashboard.

---

## 🚀 Key Features

### 1. Owner Mobile Interface (Mobile-First SPA)
- **PIN-Based Login**: Fast, secure 4-digit PIN access without usernames or passwords.
- **Ultra-Simple Billing**: Large touch targets, large fonts, and minimal inputs designed for mobile screens.
- **Auto-Calculations**: Automatic calculation of Subtotal, optional Discounts, Taxes, and final Totals.
- **Sequential Bill Generation**: Automatically assigns sequential invoice numbers (e.g. `SS-2457`, `SS-2458`).
- **One-Click Native Sharing**: Direct WhatsApp sharing via Android's Web Share API, with automatic fallback to download and WhatsApp messaging.
- **Mobile Number Validation**: Strict 10-digit Indian mobile number validation.

### 2. Admin & Developer Dashboard
- **Protected Access**: Separate secure password login for the administrator.
- **Business Statistics**: Real-time Total Revenue, Total Invoices Generated, and Average Ticket Size.
- **Live Search & Filters**: Search bills by Bill Number, Customer Name, Mobile Number, or Vehicle Number, with date range filtering.
- **Customer & Vehicle History**: View complete historical records of any customer or vehicle with one click.
- **Data Export**: Export filtered billing data to CSV with a single click.
- **PDF Re-Generation**: Re-download or view original PDF invoices anytime.

### 3. Professional PDF Invoices
- Styled to closely match the garage's physical bill book layout (clean grid, header with contact details, itemized table, totals box, authorized signatory, and legal terms).
- High-resolution, vector-based PDF generated with Python's `reportlab` library.
- Formatted for crisp mobile viewing and standard A4 printing.

---

## 🛠️ Technology Stack

- **Backend**: Python 3 (Flask REST API)
- **Database**: Oracle Database (XE) using the thin-driver `oracledb` (with connection pooling)
- **PDF Generation**: ReportLab
- **Frontend**: Single Page Application (HTML5, Tailwind CSS via CDN, Vanilla ES6 JavaScript, FontAwesome)
- **Security**: SHA-256 password/PIN hashing, HTTP-only secure session cookies, parameterized SQL queries

---

## 📁 Project Structure

```
garage-billing/
├── config.py              # Application settings and environment reader
├── database.py            # Oracle Database connection pool and schema initialization
├── pdf_generator.py       # ReportLab PDF invoice generator matching physical bill
├── server.py              # Flask server and RESTful API endpoints
├── test_pdf.py            # Standalone PDF generation test script
├── requirements.txt       # Python dependencies (Flask, oracledb, reportlab, python-dotenv)
├── .env.example           # Environment template with default PIN & DB configs
├── .gitignore             # Git ignore configuration
└── static/                # Single Page Application frontend
    ├── index.html         # Owner mobile billing interface
    ├── login.html         # Owner PIN login screen
    ├── admin.html         # Admin dashboard interface
    ├── admin-login.html   # Admin password login screen
    ├── app.js             # Owner client logic & Native Web Share
    ├── admin.js           # Admin client logic, stats & history modals
    └── style.css          # Custom mobile touch & print styles
```

---

## ⚙️ Setup and Installation

### 1. Prerequisites
- Python 3.10+
- Oracle Database XE (or Oracle Database 19c/21c/23ai)

### 2. Clone the Repository
```bash
git clone https://github.com/<your-username>/garage-billing.git
cd garage-billing
```

### 3. Create and Activate a Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Edit `.env` with your database credentials and garage details:
```ini
FLASK_PORT=5000
FLASK_ENV=development
SECRET_KEY=your_secret_key_here

# Credentials (SHA-256 hashes)
# Default owner PIN: 1234
OWNER_PIN_HASH=03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4
# Default admin password: admin123
ADMIN_PASSWORD_HASH=240a10c4c478f77341e97669d5870020a671cf70c14b2d9c02d1373cc4ee61f0

# Oracle Database Connection
DB_USER=system
DB_PASSWORD=your_oracle_password
DB_DSN=localhost/XE

# Garage Details
GARAGE_NAME=Sachin's Sumangal Services
GARAGE_SUBTITLE=Maruti Servicing Centre
GARAGE_PHONES=9422711826, 9834196573
GARAGE_ADDRESS=Near LIC Office, Hingoli Road, Nanded
BILL_START_NUMBER=2457
```

### 6. Run the Application
```bash
python server.py
```

The server will automatically:
1. Initialize connection pooling to Oracle Database.
2. Create the necessary tables (`customers`, `vehicles`, `bills`, `bill_items`) and indexes if they do not already exist.
3. Start the web server at `http://localhost:5000`.

---

## 📱 Usage

1. **Owner Billing Interface**: Open `http://localhost:5000` (or `http://<your-local-ip>:5000` from your mobile device).
   - Enter default PIN: `1234`.
   - Enter customer name, mobile, vehicle number, odometer, and item details.
   - Tap **Generate Bill** and confirm.
   - Tap **Share / Send PDF** to send directly to WhatsApp.
2. **Admin Dashboard**: Open `http://localhost:5000/admin`.
   - Enter default password: `admin123`.
   - View revenue metrics, search invoices, inspect customer/vehicle history, and export records to CSV.

---

## 🌐 Deployment Options

Since this is a full-stack application requiring a Python runtime and an Oracle/SQL database:
- **Cloud VPS / VM (DigitalOcean, AWS EC2, Linode)**: Run with Gunicorn/Waitress behind Nginx with systemd.
- **Container Deployment**: Docker container packaging Python and linking to an Oracle Database service.
- **PaaS (Render / Railway)**: Deploy the Flask backend as a Web Service and connect to a cloud database instance.
