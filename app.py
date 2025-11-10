from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response
from datetime import datetime
import os
import time
import csv
import io
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_in_production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def now(): 
    return time.strftime("[%Y-%m-%d %H:%M:%S]")

def is_expired(expiry_date):
    today = datetime.today()
    expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
    return expiry < today

def read_inventory():
    meds=[]
    if not os.path.exists("inventory.txt"): return meds
    with open("inventory.txt") as f:
        for line in f:
            if line.strip():
                n,b,e,q,p,oq=line.strip().split(",")
                meds.append({
                    "name":n.strip(),
                    "batch":b.strip(),
                    "expiry":e.strip(),
                    "qty":int(q),
                    "price":float(p),
                    "orig":int(oq)
                })
    return meds

def write_inventory(meds):
    valid = [m for m in meds if all(k in m for k in ("name", "batch", "expiry", "qty", "price", "orig"))]
    with open("inventory.txt", "w") as f:
        for m in valid:
            f.write(f"{m['name']},{m['batch']},{m['expiry']},{m['qty']},{m['price']},{m['orig']}\n")

def load_inventory():
    if not os.path.exists('inventory.txt'):
        return []
    with open('inventory.txt', 'r') as file:
        lines = file.readlines()
    medicines = []
    for line in lines:
        if line.strip():
            name, batch, expiry, qty, price, orig = line.strip().split(',')
            medicines.append({
                'name': name,
                'batch': batch,
                'expiry': expiry,
                'quantity': int(qty),
                'price': float(price),
                'orig': int(orig),
                'expired': is_expired(expiry)
            })
    return medicines

def save_inventory(medicines):
    with open('inventory.txt', 'w') as file:
        for med in medicines:
            file.write(f"{med['name']},{med['batch']},{med['expiry']},{med['quantity']},{med['price']},{med['orig']}\n")

def load_history():
    if not os.path.exists('history.txt'):
        return []
    with open('history.txt', 'r') as file:
        lines = file.readlines()
    
    history_records = []
    for i, line in enumerate(lines):
        if line.strip():
            # Parse the log line to extract transaction details
            # Format: "[timestamp] message"
            parts = line.strip()
            history_records.append({
                'index': i + 1,
                'timestamp': parts[1:20] if parts.startswith('[') else 'N/A',
                'message': parts[21:] if len(parts) > 21 else parts,
                'full_text': parts
            })
    return history_records

def log(msg):
    with open("history.txt","a") as f:
        f.write(f"{now()} {msg}\n")

@app.route("/")
def index():
    medicines = load_inventory()
    expired_count = sum(1 for med in medicines if is_expired(med['expiry']))
    return render_template('index.html', medicines=medicines, expired_count=expired_count)

@app.route("/add", methods=["GET","POST"])
def add():
    if request.method=="POST":
        n=request.form["name"]
        b=request.form["batch"]
        e=request.form["expiry"]
        q=int(request.form["qty"])
        p=float(request.form["price"])
        meds=read_inventory()
        meds.append({"name":n,"batch":b,"expiry":e,"qty":q,"price":p,"orig":q})
        write_inventory(meds)
        log(f"Added medicine: {n} ({b}), qty={q}, price={p}")
        flash('Medicine added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template("add.html")

@app.route("/update", methods=["GET","POST"])
def update():
    medicines = load_inventory()
    if request.method == 'POST':
        b=request.form["batch"]
        newq=int(request.form["qty"])
        newe=request.form["expiry"]
        meds=read_inventory(); found=False
        for m in meds:
            if m["batch"]==b:
                m["qty"]=newq; m["expiry"]=newe; found=True
                log(f"Updated medicine: {m['name']} ({b}), new qty={newq}")
        write_inventory(meds)
        flash('Stock updated successfully!', 'success')
        return redirect(url_for('index'))
    return render_template("update.html", medicines=medicines)

@app.route("/remove_expired")
def remove_expired():
    meds=read_inventory(); removed_count=0
    today=time.strftime("%Y-%m-%d")
    for m in meds:
        if m["expiry"]<today and m["qty"] > 0:
            log(f"Marked as expired (qty set to 0): {m['name']} ({m['batch']}), previous qty={m['qty']}")
            m["qty"] = 0  # Set quantity to 0 instead of removing
            removed_count += 1
    write_inventory(meds)
    if removed_count > 0:
        flash(f'Successfully marked {removed_count} expired medicine(s) as out of stock (quantity set to 0).', 'success')
    else:
        flash('No expired medicines with stock found.', 'info')
    return redirect("/")

@app.route("/lowstock")
def lowstock():
    medicines = load_inventory()
    low_stock = [med for med in medicines if med['quantity'] <= 10]
    return render_template('lowstock.html', low_stock=low_stock)

@app.route("/expired")
def expired():
    medicines = load_inventory()
    expired = [med for med in medicines if is_expired(med['expiry'])]
    return render_template('expired.html', expired=expired)

@app.route("/buy", methods=["GET","POST"])
def buy():
    medicines = load_inventory()
    if request.method == 'POST':
        b=request.form["batch"]; qty=int(request.form["qty"])
        meds=read_inventory(); total=0; found=False
        for m in meds:
            if m["batch"]==b:
                if m["qty"]>=qty:
                    m["qty"]-=qty; total=qty*m["price"]; found=True
                    log(f"Bought {qty} of {m['name']} ({b}), total={total}")
                else:
                    flash(f'Insufficient stock. Available: {m["qty"]} units.', 'danger')
                    return redirect(url_for('buy'))
                break
        if not found:
            flash('Medicine not found.', 'danger')
            return redirect(url_for('buy'))
        write_inventory(meds)
        flash(f'Purchase successful! Total: ₹{total:.2f}', 'success')
        return redirect(url_for('index'))
    return render_template("buy.html", medicines=medicines)

@app.route("/restock", methods=["GET","POST"])
def restock():
    """Route to restock expired or low stock medicines"""
    medicines = load_inventory()
    if request.method == 'POST':
        b=request.form["batch"]
        add_qty=int(request.form["qty"])
        newe=request.form.get("expiry", None)
        meds=read_inventory(); found=False
        for m in meds:
            if m["batch"]==b:
                old_qty = m["qty"]
                m["qty"] += add_qty
                if newe:
                    m["expiry"] = newe
                found=True
                log(f"Restocked medicine: {m['name']} ({b}), added qty={add_qty}, new total={m['qty']}, new expiry={newe if newe else 'unchanged'}")
                break
        write_inventory(meds)
        if found:
            flash(f'Medicine restocked successfully! Added {add_qty} units.', 'success')
        else:
            flash('Medicine not found.', 'danger')
        return redirect(url_for('index'))
    return render_template("restock.html", medicines=medicines)

@app.route("/history")
def history():
    history_records = load_history()
    return render_template('history.html', history=history_records)

@app.route("/api/medicines")
def api_medicines():
    """API endpoint to get all medicines as JSON"""
    medicines = load_inventory()
    return jsonify(medicines)

@app.route("/api/medicine/<batch>")
def api_medicine(batch):
    """API endpoint to get a specific medicine by batch number"""
    medicines = load_inventory()
    for med in medicines:
        if med['batch'] == batch:
            return jsonify(med)
    return jsonify({"error": "Medicine not found"}), 404

@app.route("/backup")
def backup():
    """Display backup page with download option"""
    medicines = load_inventory()
    return render_template("backup.html", medicines=medicines)

@app.route("/download_backup")
def download_backup():
    """Generate and download inventory as CSV file"""
    try:
        medicines = load_inventory()
        
        # Create CSV in memory
        si = io.StringIO()
        writer = csv.writer(si)
        
        # Write header
        writer.writerow(['Medicine Name', 'Batch Number', 'Expiry Date', 'Quantity', 'Price', 'Original Quantity'])
        
        # Write data
        for med in medicines:
            writer.writerow([
                med['name'],
                med['batch'],
                med['expiry'],
                med['quantity'],
                med['price'],
                med['orig']
            ])
        
        # Create response
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=inventory_backup_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        output.headers["Content-type"] = "text/csv"
        
        log(f"Inventory backup downloaded - {len(medicines)} medicines exported")
        flash('Inventory backup downloaded successfully!', 'success')
        
        return output
        
    except Exception as e:
        flash(f'Error creating backup: {str(e)}', 'danger')
        return redirect(url_for('backup'))

@app.route("/restore", methods=["GET", "POST"])
def restore():
    """Display restore page and handle CSV upload"""
    if request.method == "POST":
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file selected!', 'danger')
            return redirect(url_for('restore'))
        
        file = request.files['file']
        
        # Check if file has a name
        if file.filename == '':
            flash('No file selected!', 'danger')
            return redirect(url_for('restore'))
        
        # Check if file is CSV
        if not allowed_file(file.filename):
            flash('Invalid file type! Please upload a CSV file.', 'danger')
            return redirect(url_for('restore'))
        
        try:
            # Read CSV file
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.reader(stream)
            
            # Read header
            header = next(csv_reader)
            
            # Validate header
            expected_header = ['Medicine Name', 'Batch Number', 'Expiry Date', 'Quantity', 'Price', 'Original Quantity']
            if header != expected_header:
                flash('Invalid CSV format! Header must be: Medicine Name, Batch Number, Expiry Date, Quantity, Price, Original Quantity', 'danger')
                return redirect(url_for('restore'))
            
            # Parse and validate data
            new_medicines = []
            row_num = 1
            
            for row in csv_reader:
                row_num += 1
                
                if len(row) != 6:
                    flash(f'Invalid data at row {row_num}: Expected 6 columns, got {len(row)}', 'danger')
                    return redirect(url_for('restore'))
                
                try:
                    # Validate and parse data
                    name = row[0].strip()
                    batch = row[1].strip()
                    expiry = row[2].strip()
                    quantity = int(row[3])
                    price = float(row[4])
                    orig_qty = int(row[5])
                    
                    # Validate expiry date format
                    datetime.strptime(expiry, '%Y-%m-%d')
                    
                    # Validate numeric values
                    if quantity < 0 or price < 0 or orig_qty < 0:
                        flash(f'Invalid data at row {row_num}: Negative values not allowed', 'danger')
                        return redirect(url_for('restore'))
                    
                    new_medicines.append({
                        'name': name,
                        'batch': batch,
                        'expiry': expiry,
                        'qty': quantity,
                        'price': price,
                        'orig': orig_qty
                    })
                    
                except ValueError as e:
                    flash(f'Invalid data at row {row_num}: {str(e)}', 'danger')
                    return redirect(url_for('restore'))
            
            # Check if we have any medicines
            if not new_medicines:
                flash('CSV file is empty or contains no valid data!', 'warning')
                return redirect(url_for('restore'))
            
            # Backup current inventory before overwriting
            current_medicines = read_inventory()
            backup_filename = f"inventory_backup_{time.strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(backup_filename, 'w') as backup_file:
                for med in current_medicines:
                    backup_file.write(f"{med['name']},{med['batch']},{med['expiry']},{med['qty']},{med['price']},{med['orig']}\n")
            
            # Write new inventory
            write_inventory(new_medicines)
            
            log(f"Inventory restored from CSV - {len(new_medicines)} medicines imported (backup saved as {backup_filename})")
            flash(f'Inventory restored successfully! {len(new_medicines)} medicines imported. Previous inventory backed up as {backup_filename}', 'success')
            
            return redirect(url_for('index'))
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'danger')
            return redirect(url_for('restore'))
    
    return render_template("restore.html")

@app.route("/backup_history")
def backup_history():
    """Download transaction history as text file"""
    try:
        if not os.path.exists('history.txt'):
            flash('No history file found!', 'warning')
            return redirect(url_for('history'))
        
        log("Transaction history backup downloaded")
        return send_file(
            'history.txt',
            as_attachment=True,
            download_name=f'history_backup_{time.strftime("%Y%m%d_%H%M%S")}.txt',
            mimetype='text/plain'
        )
        
    except Exception as e:
        flash(f'Error downloading history: {str(e)}', 'danger')
        return redirect(url_for('history'))

if __name__=="__main__":
    app.run(debug=True)

