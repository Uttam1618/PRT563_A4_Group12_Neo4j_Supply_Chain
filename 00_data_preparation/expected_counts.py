"""Expected Neo4j node and relationship counts for a CSV folder,
following exactly the mapping used by import.txt (Model B)."""
import sys, pandas as pd
F = sys.argv[1]
r = lambda n: pd.read_csv(f"{F}/{n}.csv")
t = {n: r(n) for n in ["store","shelf_bay","product_category","product","perishable_product","ambient_product",
     "supplier","distribution_centre","employee","ordering_officer","replenishment_assistant","duty_manager",
     "purchase_order","po_line","delivery","invoice","supply_disruption","disruption_impact","stock_batch",
     "stock_count","batch_count","sale","sale_line","markdown","write_off","supply_agreement"]}
N = {"Store": len(t["store"]), "ShelfBay": len(t["shelf_bay"]), "ProductCategory": len(t["product_category"]),
     "Product": len(t["product"]), "Supplier": len(t["supplier"]), "DistributionCentre": len(t["distribution_centre"]),
     "Employee": len(t["employee"]), "PurchaseOrder": len(t["purchase_order"]), "Delivery": len(t["delivery"]),
     "Invoice": len(t["invoice"]), "SupplyDisruption": len(t["supply_disruption"]), "StockBatch": len(t["stock_batch"]),
     "StockCount": len(t["stock_count"]), "Sale": len(t["sale"]), "SaleLine": len(t["sale_line"]),
     "Markdown": len(t["markdown"]), "WriteOff": len(t["write_off"]), "SupplyAgreement": len(t["supply_agreement"])}
EXTRA = {"Perishable": len(t["perishable_product"]), "Ambient": len(t["ambient_product"]),
         "OrderingOfficer": len(t["ordering_officer"]), "ReplenishmentAssistant": len(t["replenishment_assistant"]),
         "DutyManager": len(t["duty_manager"])}
sb, sl, d = t["stock_batch"], t["sale_line"], t["delivery"]
R = {"BELONGS_TO": len(t["product"]), "LOCATED_IN": len(t["shelf_bay"]),
     "PLACED_WITH": len(t["purchase_order"]), "FOR_STORE": len(t["purchase_order"]), "RAISED_BY": len(t["purchase_order"]),
     "ORDERS": len(t["po_line"]), "FULFILS": int(d.po_id.notna().sum()), "CONSIGNED_BY": len(d),
     "BILLS": len(t["invoice"]), "AFFECTS": len(t["disruption_impact"]), "DELIVERED": len(sb),
     "OF_PRODUCT": len(sb), "STORED_IN": int(sb.bay_code.notna().sum()), "COUNTED": len(t["batch_count"]),
     "PERFORMED_BY": len(t["stock_count"]), "OCCURS_AT": len(t["sale"]), "HAS_LINE": len(sl),
     "DRAWS_FROM": len(sl), "APPLIED_TO": int(sl.markdown_id.notna().sum()), "MARKS_DOWN": len(t["markdown"]),
     "MARKED_BY": len(t["markdown"]), "WRITES_OFF": len(t["write_off"]), "AUTHORISED_BY": len(t["write_off"]),
     "OFFERS": len(t["supply_agreement"]), "COVERS": len(t["supply_agreement"]), "SUPPLIES_TO": len(t["supply_agreement"])}
print("NODES per label (Check 1)")
for k, v in sorted({**N, **EXTRA}.items()): print(f"  {k:<24}{v:>7}")
print(f"  total nodes {sum(N.values())}, labels {len(N)+len(EXTRA)}")
print("RELATIONSHIPS per type (Check 2)")
for k, v in sorted(R.items()): print(f"  {k:<24}{v:>7}")
print(f"  total relationships {sum(R.values())}, types {len(R)}")
