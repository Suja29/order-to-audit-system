from decimal import Decimal
from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Clear existing data if re-running
if db.query(models.Item).count() == 0:
    # 1. Users
    users = [
        models.User(username="salesman_a", role="salesman"),
        models.User(username="salesman_b", role="salesman"),
        models.User(username="admin", role="admin"),
        models.User(username="supervisor", role="production"),
        models.User(username="auditor", role="auditor"),
        models.User(username="owner", role="owner"),
    ]
    db.add_all(users)

    # 2. Items
    flour = models.Item(name="Flour", category="RAW", unit="kg")
    oil = models.Item(name="Cooking oil", category="RAW", unit="litre")
    spice = models.Item(name="Salt and spice mix", category="RAW", unit="kg")
    pouch = models.Item(name="200 g pouch", category="PACKAGING", unit="piece")
    carton = models.Item(name="Carton (20 pkts)", category="PACKAGING", unit="piece")
    murukku = models.Item(
        name="Murukku 200 g", category="FINISHED", unit="packet",
        hsn_code="21069099", selling_price=Decimal("50.00"), gst_rate=Decimal("5.00")
    )
    db.add_all([flour, oil, spice, pouch, carton, murukku])
    db.commit()

    # 3. BOM for Murukku 200g (1 batch = 200 packets)
    bom = models.BOM(finished_item_id=murukku.id, batch_yield_qty=Decimal("200"))
    db.add(bom)
    db.commit()

    bom_lines = [
        models.BOMLine(bom_id=bom.id, raw_item_id=flour.id, standard_qty=Decimal("40")),
        models.BOMLine(bom_id=bom.id, raw_item_id=oil.id, standard_qty=Decimal("10")),
        models.BOMLine(bom_id=bom.id, raw_item_id=spice.id, standard_qty=Decimal("1.2")),
        models.BOMLine(bom_id=bom.id, raw_item_id=pouch.id, standard_qty=Decimal("200")),
        models.BOMLine(bom_id=bom.id, raw_item_id=carton.id, standard_qty=Decimal("10")),
    ]
    db.add_all(bom_lines)

    # 4. Opening Stock Ledger Entries
    openings = [
        models.StockLedger(item_id=flour.id, qty_change=Decimal("100"), unit_cost=Decimal("42.00"), txn_type="OPENING", ref_doc="OP-01"),
        models.StockLedger(item_id=oil.id, qty_change=Decimal("30"), unit_cost=Decimal("140.00"), txn_type="OPENING", ref_doc="OP-01"),
        models.StockLedger(item_id=spice.id, qty_change=Decimal("5"), unit_cost=Decimal("200.00"), txn_type="OPENING", ref_doc="OP-01"),
        models.StockLedger(item_id=pouch.id, qty_change=Decimal("500"), unit_cost=Decimal("2.50"), txn_type="OPENING", ref_doc="OP-01"),
        models.StockLedger(item_id=carton.id, qty_change=Decimal("30"), unit_cost=Decimal("15.00"), txn_type="OPENING", ref_doc="OP-01"),
        models.StockLedger(item_id=murukku.id, qty_change=Decimal("50"), unit_cost=Decimal("30.00"), txn_type="OPENING", ref_doc="OP-01"),
    ]
    db.add_all(openings)

    # 5. Customers
    customers = [
        models.Customer(name="Retailer A", state="Tamil Nadu", gstin="33AABCU9603R1ZM"),
        models.Customer(name="Distributor B", state="Karnataka", gstin="29AABCU9603R1ZN"),
    ]
    db.add_all(customers)
    db.commit()
    print("✅ Benchmark Seed Data Loaded Successfully!")