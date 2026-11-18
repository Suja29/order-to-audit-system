from fastapi import FastAPI, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from decimal import Decimal

from database import SessionLocal, engine
import models

app = FastAPI(title="Order-to-Audit ERP System")
templates = Jinja2Templates(directory="templates")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})

@app.post("/login")
def login(username: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return RedirectResponse("/", status_code=303)
    if user.role == "salesman":
        return RedirectResponse(f"/salesman?user={user.username}", status_code=303)
    elif user.role == "admin":
        return RedirectResponse("/admin", status_code=303)
    elif user.role == "production":
        return RedirectResponse("/production", status_code=303)
    elif user.role == "auditor":
        return RedirectResponse("/auditor", status_code=303)
    elif user.role == "owner":
        return RedirectResponse("/owner", status_code=303)
    return RedirectResponse("/", status_code=303)

@app.get("/salesman", response_class=HTMLResponse)
def salesman_dashboard(request: Request, user: str = "salesman_a", db: Session = Depends(get_db)):
    items = db.query(models.Item).all()
    customers = db.query(models.Customer).all()
    orders = db.query(models.Order).filter(models.Order.salesman_name == user).all()
    return templates.TemplateResponse(request, "salesman.html", {"user": user, "items": items, "customers": customers, "orders": orders})

@app.post("/salesman/order")
def create_order(
    customer_id: int = Form(...),
    salesman_name: str = Form(...),
    item_id: int = Form(...),
    qty: Decimal = Form(...),
    db: Session = Depends(get_db)
):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    order = models.Order(
        customer_id=customer_id,
        salesman_name=salesman_name,
        item_id=item_id,
        qty=qty,
        unit_price=item.selling_price,
        status="SUBMITTED"
    )
    db.add(order)
    db.commit()
    return RedirectResponse(f"/salesman?user={salesman_name}", status_code=303)

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    orders = db.query(models.Order).filter(models.Order.status == "SUBMITTED").all()
    
    # Calculate available stock for each order's item to show warnings in admin UI
    order_stock_map = {}
    for order in orders:
        ledger_entries = db.query(models.StockLedger).filter(models.StockLedger.item_id == order.item_id).all()
        total_stock = sum([e.qty_change for e in ledger_entries], Decimal("0.00"))
        order_stock_map[order.id] = total_stock
        
    return templates.TemplateResponse(request, "admin.html", {"orders": orders, "order_stock_map": order_stock_map})

@app.get("/admin/approve/{order_id}", response_class=HTMLResponse)
def approve_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        return RedirectResponse("/admin", status_code=303)
        
    # Backend Safety Check: Verify stock before approving
    ledger_entries = db.query(models.StockLedger).filter(models.StockLedger.item_id == order.item_id).all()
    total_stock = sum([e.qty_change for e in ledger_entries], Decimal("0.00"))
    
    if order.qty > total_stock:
        raise HTTPException(status_code=400, detail=f"Cannot Approve! Stock Insufficient. Available: {total_stock}, Ordered: {order.qty}")

    order.status = "APPROVED"
    # Generate Invoice & Tax Ledger
    item = db.query(models.Item).filter(models.Item.id == order.item_id).first()
    customer = db.query(models.Customer).filter(models.Customer.id == order.customer_id).first()
    
    taxable = order.qty * order.unit_price
    gst = taxable * (item.gst_rate / Decimal("100"))
    cgst = sgst = igst = Decimal("0.00")
    
    if customer and customer.state.lower() == "tamil nadu":
        cgst = gst / Decimal("2")
        sgst = gst / Decimal("2")
    else:
        igst = gst
        
    total = taxable + gst
    invoice_no = f"INV-{order.id:04d}"
    
    invoice = models.Invoice(
        invoice_no=invoice_no,
        order_id=order.id,
        taxable_value=taxable,
        cgst=cgst,
        sgst=sgst,
        igst=igst,
        total_amount=total
    )
    db.add(invoice)
    
    # Deduct Finished Stock Ledger entry
    stock_out = models.StockLedger(
        item_id=item.id,
        qty_change=-order.qty,
        unit_cost=item.selling_price * Decimal("0.6"), # estimated cost
        txn_type="DISPATCH",
        ref_doc=invoice_no
    )
    db.add(stock_out)
    order.status = "DISPATCHED"
    db.commit()
    
    return RedirectResponse("/admin", status_code=303)

@app.get("/production", response_class=HTMLResponse)
def production_dashboard(request: Request, db: Session = Depends(get_db)):
    items = db.query(models.Item).filter(models.Item.category == "FINISHED").all()
    runs = db.query(models.ProductionRun).all()
    return templates.TemplateResponse(request, "production.html", {"items": items, "runs": runs})

@app.post("/production/run")
def create_production_run(
    finished_item_id: int = Form(...),
    batches: Decimal = Form(...),
    labour_cost: Decimal = Form(...),
    overhead_cost: Decimal = Form(...),
    db: Session = Depends(get_db)
):
    bom = db.query(models.BOM).filter(models.BOM.finished_item_id == finished_item_id).first()
    if bom:
        yield_per_batch = bom.batch_yield_qty
        total_good_qty = batches * yield_per_batch
        
        bom_lines = db.query(models.BOMLine).filter(models.BOMLine.bom_id == bom.id).all()
        raw_material_total_cost = Decimal("0.00")
        
        for line in bom_lines:
            qty_needed = line.standard_qty * batches
            latest_ledger = db.query(models.StockLedger).filter(models.StockLedger.item_id == line.raw_item_id).order_by(models.StockLedger.id.desc()).first()
            u_cost = latest_ledger.unit_cost if latest_ledger else Decimal("0.00")
            raw_material_total_cost += (qty_needed * u_cost)
            
            issue_entry = models.StockLedger(
                item_id=line.raw_item_id,
                qty_change=-qty_needed,
                unit_cost=u_cost,
                txn_type="PROD_ISSUE",
                ref_doc="PROD-BATCH"
            )
            db.add(issue_entry)
            
        total_batch_cost = raw_material_total_cost + labour_cost + overhead_cost
        cost_per_pkt = total_batch_cost / total_good_qty if total_good_qty > 0 else Decimal("0.00")
        
        finished_entry = models.StockLedger(
            item_id=finished_item_id,
            qty_change=total_good_qty,
            unit_cost=cost_per_pkt,
            txn_type="PROD_OUTPUT",
            ref_doc="PROD-BATCH"
        )
        db.add(finished_entry)
        
        run = models.ProductionRun(
            finished_item_id=finished_item_id,
            expected_qty=total_good_qty,
            actual_good_qty=total_good_qty,
            damaged_qty=Decimal("0.00"),
            labour_cost=labour_cost,
            overhead_cost=overhead_cost,
            total_batch_cost=total_batch_cost,
            cost_per_packet=cost_per_pkt
        )
        db.add(run)
        db.commit()
        
    return RedirectResponse("/production", status_code=303)

@app.get("/auditor", response_class=HTMLResponse)
def auditor_dashboard(request: Request, db: Session = Depends(get_db)):
    ledger = db.query(models.StockLedger).all()
    invoices = db.query(models.Invoice).all()
    return templates.TemplateResponse(request, "auditor.html", {"ledger": ledger, "invoices": invoices})

@app.get("/owner", response_class=HTMLResponse)
def owner_dashboard(request: Request, db: Session = Depends(get_db)):
    invoices = db.query(models.Invoice).all()
    total_sales = sum([inv.total_amount for inv in invoices], Decimal("0.00"))
    return templates.TemplateResponse(request, "owner.html", {"total_sales": total_sales, "invoices": invoices})