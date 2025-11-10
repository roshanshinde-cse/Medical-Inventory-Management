from flask import Flask, render_template, request, redirect
import time, os

app = Flask(__name__)

def now(): 
    return time.strftime("[%Y-%m-%d %H:%M:%S]")

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
    with open("inventory.txt","w") as f:
        for m in meds:
            f.write(f"{m['name']},{m['batch']},{m['expiry']},{m['qty']},{m['price']},{m['orig']}\n")

def log(msg):
    with open("history.txt","a") as f:
        f.write(f"{now()} {msg}\n")

@app.route("/")
def menu():
    return render_template("index.html")

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
        return redirect("/inventory")
    return render_template("add.html")

@app.route("/update", methods=["GET","POST"])
def update():
    if request.method=="POST":
        b=request.form["batch"]
        newq=int(request.form["qty"])
        newe=request.form["expiry"]
        meds=read_inventory(); found=False
        for m in meds:
            if m["batch"]==b:
                m["qty"]=newq; m["expiry"]=newe; found=True
                log(f"Updated medicine: {m['name']} ({b}), new qty={newq}")
        write_inventory(meds)
        return redirect("/inventory")
    return render_template("update.html")

@app.route("/remove_expired")
def remove_expired():
    meds=read_inventory(); newlist=[]
    today=time.strftime("%Y-%m-%d")
    for m in meds:
        if m["expiry"]<today:
            log(f"Removed expired: {m['name']} ({m['batch']})")
        else:
            newlist.append(m)
    write_inventory(newlist)
    return redirect("/inventory")

@app.route("/lowstock")
def lowstock():
    meds=[m for m in read_inventory() if m["qty"]<10]
    return render_template("lowstock.html", meds=meds, title="Low Stock Report")

@app.route("/expired")
def expired():
    today=time.strftime("%Y-%m-%d")
    meds=[m for m in read_inventory() if m["expiry"]<today]
    return render_template("expired.html", meds=meds, title="Expired Medicines")

@app.route("/inventory")
def inventory():
    meds=read_inventory()
    return render_template("lowstock.html", meds=meds, title="Full Inventory")

@app.route("/buy", methods=["GET","POST"])
def buy():
    if request.method=="POST":
        b=request.form["batch"]; qty=int(request.form["qty"])
        meds=read_inventory(); total=0; found=False
        for m in meds:
            if m["batch"]==b and m["qty"]>=qty:
                m["qty"]-=qty; total=qty*m["price"]; found=True
                log(f"Bought {qty} of {m['name']} ({b}), total={total}")
        write_inventory(meds)
        if found:
            return f"<h3>Bill Total: ₹{total}</h3><a href='/'>Back to menu</a>"
        else:
            return "<h3>Medicine not found or insufficient stock.</h3><a href='/buy'>Try again</a>"
    return render_template("buy.html")

@app.route("/history")
def history():
    lines=[]
    if os.path.exists("history.txt"):
        with open("history.txt") as f:
            lines=f.readlines()
    return render_template("history.html", lines=lines)

if __name__=="__main__":
    app.run(debug=True)

