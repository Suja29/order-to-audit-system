from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    role = Column(String)  # salesman, admin, production, auditor, owner

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    category = Column(String)  # RAW, PACKAGING, FINISHED
    unit = Column(String)      # kg, litre, piece, packet
    hsn_code = Column(String, nullable=True)
    selling_price = Column(Numeric(12, 2), default=0)
    gst_rate = Column(Numeric(5, 2), default=5.00)

class BOM(Base):
    __tablename__ = "boms"
    id = Column(Integer, primary_key=True, index=True)
    finished_item_id = Column(Integer, ForeignKey("items.id"))
    batch_yield_qty = Column(Numeric(12, 3))  # e.g., 200 packets
    lines = relationship("BOMLine", back_populates="bom")

class BOMLine(Base):
    __tablename__ = "bom_lines"
    id = Column(Integer, primary_key=True, index=True)
    bom_id = Column(Integer, ForeignKey("boms.id"))
    raw_item_id = Column(Integer, ForeignKey("items.id"))
    standard_qty = Column(Numeric(12, 3))  # e.g., 40 kg flour per batch
    bom = relationship("BOM", back_populates="lines")

class StockLedger(Base):
    __tablename__ = "stock_ledger"
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"))
    qty_change = Column(Numeric(12, 3))      # + for in, - for out
    unit_cost = Column(Numeric(12, 4), default=0)
    txn_type = Column(String)                # OPENING, PURCHASE, PROD_ISSUE, PROD_OUTPUT, DISPATCH
    ref_doc = Column(String)                 # e.g., "PO-001", "RUN-001", "INV-2026-001"
    created_at = Column(DateTime, default=datetime.utcnow)

class ProductionRun(Base):
    __tablename__ = "production_runs"
    id = Column(Integer, primary_key=True, index=True)
    finished_item_id = Column(Integer, ForeignKey("items.id"))
    expected_qty = Column(Numeric(12, 3))
    actual_good_qty = Column(Numeric(12, 3))
    damaged_qty = Column(Numeric(12, 3), default=0)
    labour_cost = Column(Numeric(12, 2), default=0)
    overhead_cost = Column(Numeric(12, 2), default=0)
    total_batch_cost = Column(Numeric(12, 2), default=0)
    cost_per_packet = Column(Numeric(12, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    state = Column(String)  # "Tamil Nadu" or "Karnataka"
    gstin = Column(String)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    salesman_name = Column(String)
    item_id = Column(Integer, ForeignKey("items.id"))
    qty = Column(Numeric(12, 3))
    unit_price = Column(Numeric(12, 2))
    status = Column(String, default="SUBMITTED")  # SUBMITTED, APPROVED, DISPATCHED
    created_at = Column(DateTime, default=datetime.utcnow)

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String, unique=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    taxable_value = Column(Numeric(12, 2))
    cgst = Column(Numeric(12, 2), default=0)
    sgst = Column(Numeric(12, 2), default=0)
    igst = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2))
    paid_amount = Column(Numeric(12, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)