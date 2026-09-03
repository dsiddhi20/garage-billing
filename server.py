import os
import hashlib
import csv
from io import StringIO
from datetime import datetime
from flask import Flask, request, jsonify, session, send_from_directory, make_response, redirect, url_path_join
import database
from config import Config
from pdf_generator import generate_bill_pdf

app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = Config.SECRET_KEY

# Configure session cookies
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=86400 # 24 hours
)

def get_sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def is_owner_logged_in():
    return session.get('role') == 'owner'

def is_admin_logged_in():
    return session.get('role') == 'admin'

# --- Middleware Auths ---
def require_owner(f):
    def decorator(*args, **kwargs):
        if not is_owner_logged_in():
            return jsonify({"error": "Unauthorized. Owner login required."}), 401
        return f(*args, **kwargs)
    decorator.__name__ = f.__name__
    return decorator

def require_admin(f):
    def decorator(*args, **kwargs):
        if not is_admin_logged_in():
            return jsonify({"error": "Unauthorized. Admin login required."}), 401
        return f(*args, **kwargs)
    decorator.__name__ = f.__name__
    return decorator

def require_any_auth(f):
    def decorator(*args, **kwargs):
        if not is_owner_logged_in() and not is_admin_logged_in():
            return jsonify({"error": "Unauthorized. Login required."}), 401
        return f(*args, **kwargs)
    decorator.__name__ = f.__name__
    return decorator

# --- Static Routes ---
@app.route('/')
def index():
    if not is_owner_logged_in():
        return redirect('/login.html')
    return send_from_directory('static', 'index.html')

@app.route('/admin')
def admin():
    if not is_admin_logged_in():
        return redirect('/admin-login.html')
    return send_from_directory('static', 'admin.html')

# --- API Authentication Routes ---
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    pin = data.get('pin', '')
    if not pin:
        return jsonify({"error": "PIN is required"}), 400
        
    pin_hash = get_sha256(pin)
    if pin_hash == Config.OWNER_PIN_HASH:
        session.clear()
        session['role'] = 'owner'
        session.permanent = True
        return jsonify({"success": True, "message": "Login successful", "role": "owner"})
        
    return jsonify({"error": "Invalid PIN"}), 401

@app.route('/api/auth/admin-login', methods=['POST'])
def api_admin_login():
    data = request.get_json() or {}
    password = data.get('password', '')
    if not password:
        return jsonify({"error": "Password is required"}), 400
        
    pwd_hash = get_sha256(password)
    if pwd_hash == Config.ADMIN_PASSWORD_HASH:
        session.clear()
        session['role'] = 'admin'
        session.permanent = True
        return jsonify({"success": True, "message": "Admin login successful", "role": "admin"})
        
    return jsonify({"error": "Invalid admin password"}), 401

@app.route('/api/auth/status', methods=['GET'])
def api_auth_status():
    return jsonify({
        "logged_in": is_owner_logged_in() or is_admin_logged_in(),
        "role": session.get('role', None)
    })

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})

# --- Billing API Routes ---
@app.route('/api/bills/next-number', methods=['GET'])
@require_any_auth
def api_next_bill_number():
    try:
        res = database.execute_fetch_one("SELECT COALESCE(MAX(bill_id), 0) as max_id FROM bills")
        max_id = res['max_id'] if res else 0
        next_bill_number = f"SS-{Config.BILL_START_NUMBER + max_id}"
        return jsonify({"bill_number": next_bill_number})
    except Exception as e:
        app.logger.error(f"Error fetching next bill number: {e}")
        return jsonify({"error": "Something went wrong. Please try again."}), 500

@app.route('/api/bills', methods=['POST'])
@require_owner
def api_create_bill():
    data = request.get_json() or {}
    
    cust_data = data.get('customer', {})
    veh_data = data.get('vehicle', {})
    bill_date_str = data.get('bill_date', '')
    km = data.get('km', '')
    discount = float(data.get('discount', 0) or 0)
    tax = float(data.get('tax', 0) or 0)
    items = data.get('items', [])

    # Validation
    if not cust_data.get('name') or not cust_data.get('mobile'):
        return jsonify({"error": "Customer Name and Mobile are required."}), 400
    if not veh_data.get('vehicle_number'):
        return jsonify({"error": "Vehicle Number is required."}), 400
    if not bill_date_str:
        return jsonify({"error": "Bill date is required."}), 400
    if km == '' or int(km) < 0:
        return jsonify({"error": "Valid KM reading is required."}), 400
    if not items or len(items) == 0:
        return jsonify({"error": "At least one bill item is required."}), 400
    if discount < 0 or tax < 0:
        return jsonify({"error": "Discount and Tax cannot be negative."}), 400

    # Validate mobile
    mobile = str(cust_data['mobile']).strip()
    if len(mobile) != 10 or not mobile.isdigit():
        return jsonify({"error": "Valid 10-digit mobile number is required."}), 400

    conn = database.get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Save or update customer
        cursor.execute("SELECT customer_id FROM customers WHERE mobile = :1", [mobile])
        cust_row = cursor.fetchone()
        if cust_row:
            customer_id = cust_row[0]
            cursor.execute(
                "UPDATE customers SET name = :1, address = :2, updated_at = CURRENT_TIMESTAMP WHERE customer_id = :3",
                [cust_data['name'].strip(), cust_data.get('address', '').strip(), customer_id]
            )
        else:
            # Oracle returning clause needs output variable
            id_var = cursor.var(int)
            cursor.execute(
                "INSERT INTO customers (name, mobile, address) VALUES (:1, :2, :3) RETURNING customer_id INTO :4",
                [cust_data['name'].strip(), mobile, cust_data.get('address', '').strip(), id_var]
            )
            customer_id = id_var.getvalue()[0]

        # 2. Save or update vehicle
        veh_num = str(veh_data['vehicle_number']).strip().upper()
        cursor.execute("SELECT vehicle_id FROM vehicles WHERE vehicle_number = :1", [veh_num])
        veh_row = cursor.fetchone()
        if veh_row:
            vehicle_id = veh_row[0]
            cursor.execute(
                "UPDATE vehicles SET customer_id = :1, make = :2, model = :3 WHERE vehicle_id = :4",
                [customer_id, veh_data.get('make', '').strip(), veh_data.get('model', '').strip(), vehicle_id]
            )
        else:
            id_var = cursor.var(int)
            cursor.execute(
                "INSERT INTO vehicles (customer_id, vehicle_number, make, model) VALUES (:1, :2, :3, :4) RETURNING vehicle_id INTO :5",
                [customer_id, veh_num, veh_data.get('make', '').strip(), veh_data.get('model', '').strip(), id_var]
            )
            vehicle_id = id_var.getvalue()[0]

        # 3. Calculations
        subtotal = 0.0
        for item in items:
            amount = float(item.get('amount', 0) or 0)
            if amount < 0:
                raise ValueError("Item amount cannot be negative.")
            subtotal += amount
            
        total = subtotal - discount + tax
        if total < 0:
            total = 0.0

        # Parse Date
        bill_date = datetime.strptime(bill_date_str, "%Y-%m-%d").date()

        # 4. Insert bill with placeholder number first
        bill_id_var = cursor.var(int)
        cursor.execute(
            """INSERT INTO bills (bill_number, customer_id, vehicle_id, bill_date, km, subtotal, discount, tax, total)
               VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9) RETURNING bill_id INTO :10""",
            ["TEMP-PLACEHOLDER", customer_id, vehicle_id, bill_date, int(km), subtotal, discount, tax, total, bill_id_var]
        )
        bill_id = bill_id_var.getvalue()[0]

        # 5. Compute actual sequential bill number and update
        bill_number = f"SS-{Config.BILL_START_NUMBER + bill_id - 1}"
        cursor.execute("UPDATE bills SET bill_number = :1 WHERE bill_id = :2", [bill_number, bill_id])

        # 6. Insert items
        for item in items:
            cursor.execute(
                "INSERT INTO bill_items (bill_id, description, amount) VALUES (:1, :2, :3)",
                [bill_id, item['description'].strip(), float(item['amount'])]
            )

        # Commit transaction
        conn.commit()

        # Create dictionaries to feed into PDF generator
        bill_dict = {
            'bill_number': bill_number,
            'bill_date': bill_date,
            'km': km,
            'subtotal': subtotal,
            'discount': discount,
            'tax': tax,
            'total': total,
            'garage_phones': Config.GARAGE_PHONES
        }
        customer_dict = {
            'name': cust_data['name'].strip(),
            'mobile': mobile,
            'address': cust_data.get('address', '').strip()
        }
        vehicle_dict = {
            'vehicle_number': veh_num,
            'model': veh_data.get('model', '').strip()
        }
        items_dict = [
            {'description': item['description'].strip(), 'amount': float(item['amount'])} for item in items
        ]

        # 7. Generate PDF
        pdf_filename = f"{bill_number}.pdf"
        pdf_path = os.path.join(Config.PDF_FOLDER, pdf_filename)
        generate_bill_pdf(bill_dict, customer_dict, vehicle_dict, items_dict, pdf_path)

        return jsonify({
            "success": True, 
            "bill_id": bill_id, 
            "bill_number": bill_number, 
            "pdf_url": f"/api/bills/{bill_id}/pdf"
        })

    except Exception as e:
        conn.rollback()
        app.logger.error(f"Error creating bill: {e}")
        return jsonify({"error": "Something went wrong. Please try again."}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/bills/<int:bill_id>/pdf', methods=['GET'])
@require_any_auth
def api_get_pdf(bill_id):
    try:
        # Fetch bill details
        bill = database.execute_fetch_one("SELECT * FROM bills WHERE bill_id = :1", [bill_id])
        if not bill:
            return jsonify({"error": "Bill not found"}), 404
            
        bill_number = bill['bill_number']
        pdf_filename = f"{bill_number}.pdf"
        pdf_path = os.path.join(Config.PDF_FOLDER, pdf_filename)

        # If PDF file does not exist, regenerate it on the fly
        if not os.path.exists(pdf_path):
            customer = database.execute_fetch_one("SELECT * FROM customers WHERE customer_id = :1", [bill['customer_id']])
            vehicle = database.execute_fetch_one("SELECT * FROM vehicles WHERE vehicle_id = :1", [bill['vehicle_id']])
            items = database.execute_fetch_all("SELECT * FROM bill_items WHERE bill_id = :1 ORDER BY item_id ASC", [bill_id])
            
            bill_dict = {
                'bill_number': bill_number,
                'bill_date': bill['bill_date'],
                'km': bill['km'],
                'subtotal': bill['subtotal'],
                'discount': bill['discount'],
                'tax': bill['tax'],
                'total': bill['total'],
                'garage_phones': Config.GARAGE_PHONES
            }
            generate_bill_pdf(bill_dict, customer, vehicle, items, pdf_path)

        return send_from_directory(Config.PDF_FOLDER, pdf_filename, as_attachment=False)
    except Exception as e:
        app.logger.error(f"Error serving PDF: {e}")
        return jsonify({"error": "Something went wrong. Please try again."}), 500

# --- Admin API Dashboard Routes ---
@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def api_admin_stats():
    try:
        # Revenue statistics
        rev_res = database.execute_fetch_one("SELECT COALESCE(SUM(total), 0) as total_rev, COUNT(*) as total_bills FROM bills")
        avg_res = database.execute_fetch_one("SELECT COALESCE(AVG(total), 0) as avg_ticket FROM bills")
        
        return jsonify({
            "total_revenue": float(rev_res['total_rev']),
            "total_bills": int(rev_res['total_bills']),
            "average_ticket": float(avg_res['avg_ticket'])
        })
    except Exception as e:
        app.logger.error(f"Error fetching stats: {e}")
        return jsonify({"error": "Something went wrong. Please try again."}), 500

@app.route('/api/admin/bills', methods=['GET'])
@require_admin
def api_admin_bills():
    try:
        search = request.args.get('search', '').strip().upper()
        start_date_str = request.args.get('start_date', '').strip()
        end_date_str = request.args.get('end_date', '').strip()

        query = """
            SELECT b.bill_id, b.bill_number, b.bill_date, b.total, b.km,
                   b.customer_id, b.vehicle_id,
                   c.name as customer_name, c.mobile as customer_mobile,
                   v.vehicle_number, v.model as vehicle_model
            FROM bills b
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN vehicles v ON b.vehicle_id = v.vehicle_id
            WHERE 1=1
        """
        params = {}
        param_counter = 1

        if search:
            query += f"""
                AND (
                    UPPER(b.bill_number) LIKE :{param_counter}
                    OR UPPER(c.name) LIKE :{param_counter+1}
                    OR c.mobile LIKE :{param_counter+2}
                    OR UPPER(v.vehicle_number) LIKE :{param_counter+3}
                )
            """
            search_param = f"%{search}%"
            params[str(param_counter)] = search_param
            params[str(param_counter+1)] = search_param
            params[str(param_counter+2)] = search_param
            params[str(param_counter+3)] = search_param
            param_counter += 4

        if start_date_str:
            query += f" AND b.bill_date >= TO_DATE(:{param_counter}, 'YYYY-MM-DD')"
            params[str(param_counter)] = start_date_str
            param_counter += 1

        if end_date_str:
            query += f" AND b.bill_date <= TO_DATE(:{param_counter}, 'YYYY-MM-DD')"
            params[str(param_counter)] = end_date_str
            param_counter += 1

        query += " ORDER BY b.bill_date DESC, b.bill_id DESC"
        
        results = database.execute_fetch_all(query, params)
        
        # Clean up date strings for JSON response
        for row in results:
            if hasattr(row['bill_date'], 'strftime'):
                row['bill_date'] = row['bill_date'].strftime('%Y-%m-%d')
            else:
                row['bill_date'] = str(row['bill_date']).split(' ')[0]
            row['total'] = float(row['total'])
            
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error fetching bills list: {e}")
        return jsonify({"error": "Something went wrong. Please try again."}), 500

@app.route('/api/admin/customers/<int:customer_id>/history', methods=['GET'])
@require_admin
def api_customer_history(customer_id):
    try:
        cust = database.execute_fetch_one("SELECT * FROM customers WHERE customer_id = :1", [customer_id])
        if not cust:
            return jsonify({"error": "Customer not found"}), 404
            
        bills = database.execute_fetch_all(
            """SELECT b.bill_id, b.bill_number, b.bill_date, b.total, v.vehicle_number
               FROM bills b
               JOIN vehicles v ON b.vehicle_id = v.vehicle_id
               WHERE b.customer_id = :1
               ORDER BY b.bill_date DESC""",
            [customer_id]
        )
        for b in bills:
            if hasattr(b['bill_date'], 'strftime'):
                b['bill_date'] = b['bill_date'].strftime('%Y-%m-%d')
            b['total'] = float(b['total'])
            
        return jsonify({
            "customer": cust,
            "bills": bills
        })
    except Exception as e:
        app.logger.error(f"Error fetching customer history: {e}")
        return jsonify({"error": "Something went wrong. Please try again."}), 500

@app.route('/api/admin/vehicles/<int:vehicle_id>/history', methods=['GET'])
@require_admin
def api_vehicle_history(vehicle_id):
    try:
        veh = database.execute_fetch_one(
            """SELECT v.*, c.name as customer_name, c.mobile as customer_mobile 
               FROM vehicles v
               JOIN customers c ON v.customer_id = c.customer_id
               WHERE v.vehicle_id = :1""", 
            [vehicle_id]
        )
        if not veh:
            return jsonify({"error": "Vehicle not found"}), 404
            
        bills = database.execute_fetch_all(
            """SELECT b.bill_id, b.bill_number, b.bill_date, b.total, c.name as customer_name
               FROM bills b
               JOIN customers c ON b.customer_id = c.customer_id
               WHERE b.vehicle_id = :1
               ORDER BY b.bill_date DESC""",
            [vehicle_id]
        )
        for b in bills:
            if hasattr(b['bill_date'], 'strftime'):
                b['bill_date'] = b['bill_date'].strftime('%Y-%m-%d')
            b['total'] = float(b['total'])
            
        return jsonify({
            "vehicle": veh,
            "bills": bills
        })
    except Exception as e:
        app.logger.error(f"Error fetching vehicle history: {e}")
        return jsonify({"error": "Something went wrong. Please try again."}), 500

@app.route('/api/admin/export/csv', methods=['GET'])
@require_admin
def api_export_csv():
    try:
        search = request.args.get('search', '').strip().upper()
        start_date_str = request.args.get('start_date', '').strip()
        end_date_str = request.args.get('end_date', '').strip()

        query = """
            SELECT b.bill_number, b.bill_date, b.total, b.km,
                   c.name as customer_name, c.mobile as customer_mobile,
                   v.vehicle_number, v.model as vehicle_model
            FROM bills b
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN vehicles v ON b.vehicle_id = v.vehicle_id
            WHERE 1=1
        """
        params = {}
        param_counter = 1

        if search:
            query += f"""
                AND (
                    UPPER(b.bill_number) LIKE :{param_counter}
                    OR UPPER(c.name) LIKE :{param_counter+1}
                    OR c.mobile LIKE :{param_counter+2}
                    OR UPPER(v.vehicle_number) LIKE :{param_counter+3}
                )
            """
            search_param = f"%{search}%"
            params[str(param_counter)] = search_param
            params[str(param_counter+1)] = search_param
            params[str(param_counter+2)] = search_param
            params[str(param_counter+3)] = search_param
            param_counter += 4

        if start_date_str:
            query += f" AND b.bill_date >= TO_DATE(:{param_counter}, 'YYYY-MM-DD')"
            params[str(param_counter)] = start_date_str
            param_counter += 1

        if end_date_str:
            query += f" AND b.bill_date <= TO_DATE(:{param_counter}, 'YYYY-MM-DD')"
            params[str(param_counter)] = end_date_str
            param_counter += 1

        query += " ORDER BY b.bill_date DESC, b.bill_id DESC"
        results = database.execute_fetch_all(query, params)

        # Write to memory buffer
        si = StringIO()
        cw = csv.writer(si)
        # Header Row
        cw.writerow(["Bill Number", "Date", "Customer Name", "Customer Mobile", "Vehicle Number", "Model", "KM Reading", "Total Amount (₹)"])
        
        for row in results:
            bill_date = row['bill_date']
            if hasattr(bill_date, 'strftime'):
                bill_date = bill_date.strftime('%Y-%m-%d')
            else:
                bill_date = str(bill_date).split(' ')[0]
            cw.writerow([
                row['bill_number'],
                bill_date,
                row['customer_name'],
                row['customer_mobile'],
                row['vehicle_number'],
                row['vehicle_model'] or '',
                row['km'],
                f"{float(row['total']):.2f}"
            ])
            
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=billing_export.csv"
        output.headers["Content-type"] = "text/csv; charset=utf-8"
        return output
    except Exception as e:
        app.logger.error(f"Error exporting CSV: {e}")
        return "Internal server error", 500

if __name__ == '__main__':
    # Initialize application configurations
    Config.init_app()
    # Initialize DB tables
    database.init_db()
    
    print(f"Starting server on port {Config.FLASK_PORT}...")
    app.run(host='0.0.0.0', port=Config.FLASK_PORT, debug=(Config.FLASK_ENV == 'development'))
