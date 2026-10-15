"""Model A (naive conversion) counts: one node per row, one relationship per foreign key value."""
import sys, glob, os, pandas as pd
F = sys.argv[1]
r = lambda n: pd.read_csv(f"{F}/{n}.csv")
nodes = sum(len(pd.read_csv(f)) for f in glob.glob(f"{F}/*.csv"))
nn = lambda t, c: int(r(t)[c].notna().sum())
fks = [("supplier","consignor_id"),("distribution_centre","consignor_id"),("product","category_id"),
       ("perishable_product","product_id"),("ambient_product","product_id"),("employee_phone","employee_id"),
       ("ordering_officer","employee_id"),("replenishment_assistant","employee_id"),("duty_manager","employee_id"),
       ("purchase_order","supplier_id"),("purchase_order","employee_id"),("purchase_order","store_id"),
       ("po_line","po_id"),("po_line","product_id"),("delivery","consignor_id"),("delivery","po_id"),
       ("delivery_line","delivery_id"),("invoice","delivery_id"),("disruption_impact","disruption_id"),
       ("disruption_impact","delivery_id"),("shelf_bay","store_id"),("stock_batch","product_id"),
       ("stock_batch","delivery_id"),("stock_batch","bay_code"),("stock_count","employee_id"),
       ("batch_count","count_id"),("batch_count","batch_id"),("markdown","employee_id"),("markdown","batch_id"),
       ("sale","store_id"),("sale_line","sale_id"),("sale_line","batch_id"),("sale_line","markdown_id"),
       ("write_off","batch_id"),("write_off","employee_id"),("supply_agreement","supplier_id"),
       ("supply_agreement","product_id"),("supply_agreement","store_id")]
rels = sum(nn(t, c) for t, c in fks)
print(f"Model A: {len(glob.glob(F+'/*.csv'))} labels, {len(fks)} relationship types, {nodes} nodes, {rels} relationships")
saved = {"O1 products": len(r("perishable_product")) + len(r("ambient_product")),
         "O1 employees": len(r("ordering_officer")) + len(r("replenishment_assistant")) + len(r("duty_manager")),
         "O2 consignor": len(r("consignor")), "O3 phones": len(r("employee_phone")),
         "O4 batch_count": len(r("batch_count")), "O4 disruption_impact": len(r("disruption_impact")),
         "O5 po_line": len(r("po_line")), "O6 delivery_line": len(r("delivery_line"))}
for k, v in saved.items(): print(f"  {k:<22}{v:>6}")
print("  saved total", sum(saved.values()), "-> Model B nodes", nodes - sum(saved.values()), "rels", rels - sum(saved.values()))
