"""Business rule audit for the PRT563 Group 12 supply chain data set.

Usage: python3 audit.py <csv_folder>
Prints every violation, grouped by rule, and a summary table.
The same script is run on the original Assessment 2 data and on the
regenerated data, so the two results can be compared like for like.
"""
import sys, collections
import pandas as pd

F = sys.argv[1]
def r(n):
    return pd.read_csv(f"{F}/{n}.csv", dtype={"postcode": str, "barcode": str, "abn_number": str})

b = r("stock_batch"); d = r("delivery"); dl = r("delivery_line"); po = r("purchase_order")
pol = r("po_line"); inv = r("invoice"); di = r("disruption_impact"); sd = r("supply_disruption")
m = r("markdown"); w = r("write_off"); sc = r("stock_count"); bc = r("batch_count")
sa = r("sale"); sl = r("sale_line"); ag = r("supply_agreement"); p = r("product")
pp = r("perishable_product"); bay = r("shelf_bay"); st = r("store"); oo = r("ordering_officer")
dm = r("duty_manager"); sup = r("supplier"); dc = r("distribution_centre")

V = collections.OrderedDict()
def add(rule, msg):
    V.setdefault(rule, []).append(msg)

RULES = collections.OrderedDict([
 ("R01", "Batch received date equals its delivery date"),
 ("R02", "Batch product is a product ordered on the delivery's purchase order"),
 ("R03", "Batch qty received equals delivered minus rejected on its delivery line"),
 ("R04", "Perishable use by date is within the product's shelf life; ambient has none"),
 ("R05", "Batch is shelved in the store its purchase order was raised for"),
 ("R06", "Batch is shelved in a bay whose temperature zone suits the product"),
 ("R07", "Delivery is on or after its purchase order date, and only for a sent PO"),
 ("R08", "PO status agrees with its deliveries (SENT/DRAFT/CANCELLED have none)"),
 ("R09", "Invoice is dated on or after the delivery and only for PO deliveries"),
 ("R10", "Invoice amount equals units accepted times agreed cost"),
 ("R11", "A disruption only affects deliveries scheduled during the disruption"),
 ("R12", "PO line cost equals the supply agreement valid on the order date"),
 ("R13", "PO value is within the raising officer's ordering limit"),
 ("R14", "Sale is at the store where the batch is shelved"),
 ("R15", "Sale is on or after the batch was received"),
 ("R16", "Sale is on or before the batch use by date"),
 ("R17", "Marked down sale line uses its markdown's batch, time and price"),
 ("R18", "Markdown is applied while the batch is on shelf (received to use by)"),
 ("R19", "Write off is on or after receipt; EXPIRED only after use by, perishable only"),
 ("R20", "Write off value is within the authorising duty manager's limit"),
 ("R21", "Stock count only counts batches on shelf (received, not expired)"),
 ("R22", "Counted quantity does not exceed system quantity"),
 ("R23", "Qty on hand equals received minus sold minus written off"),
 ("R24", "Store last full stocktake matches a FULL count covering that store"),
])

bd = b.merge(d, on="delivery_id", how="left")
for _, q in bd.iterrows():
    if q.received_date != q.delivery_date:
        add("R01", f"batch {q.batch_id}: received {q.received_date}, delivery {q.delivery_id} on {q.delivery_date}")
    if pd.notna(q.po_id):
        prods = set(pol[pol.po_id == q.po_id].product_id)
        if q.product_id not in prods:
            add("R02", f"batch {q.batch_id}: product {q.product_id} not on PO {int(q.po_id)} (ordered {sorted(prods)})")
        pst = po[po.po_id == q.po_id].store_id.iloc[0]
        if pd.notna(q.store_id) and q.store_id != pst:
            add("R05", f"batch {q.batch_id}: shelved in store {int(q.store_id)}, PO {int(q.po_id)} is for store {pst}")
x = b.merge(dl, on=["delivery_id", "line_no"], how="left")
for _, q in x.iterrows():
    if pd.isna(q.delivered_qty) or q.qty_received != q.delivered_qty - q.rejected_qty or q.qty_received <= 0:
        add("R03", f"batch {q.batch_id}: received {q.qty_received}, line delivered {q.delivered_qty} rejected {q.rejected_qty}")
x = b.merge(pp, on="product_id", how="left")
for _, q in x.iterrows():
    if pd.notna(q.shelf_life_days):
        if pd.isna(q.use_by_date):
            add("R04", f"batch {q.batch_id}: perishable with no use by date")
        else:
            days = (pd.Timestamp(q.use_by_date) - pd.Timestamp(q.received_date)).days
            if days > q.shelf_life_days or days < 0:
                add("R04", f"batch {q.batch_id}: use by {days} days after receipt, shelf life {int(q.shelf_life_days)}")
    elif pd.notna(q.use_by_date):
        add("R04", f"batch {q.batch_id}: ambient product with a use by date")
def zone_ok(prod, zone):
    row = pp[pp.product_id == prod]
    if row.empty:
        return zone == "AMBIENT"
    t = row.storage_temp_c.iloc[0]
    if t <= 1.0:  return zone in ("FROZEN", "CHILLED")
    if t < 8.0:   return zone == "CHILLED"
    return zone == "AMBIENT"
x = b.merge(bay, on=["store_id", "bay_code"], how="left")
for _, q in x.iterrows():
    if pd.notna(q.temp_zone) and not zone_ok(q.product_id, q.temp_zone):
        add("R06", f"batch {q.batch_id}: product {q.product_id} in {q.temp_zone} bay {q.store_id}:{q.bay_code}")
x = d.merge(po, on="po_id", how="inner")
for _, q in x.iterrows():
    if q.delivery_date < q.order_date:
        add("R07", f"delivery {q.delivery_id} on {q.delivery_date} before PO {q.po_id} order {q.order_date}")
    if q.po_status in ("DRAFT", "CANCELLED", "SENT"):
        add("R08", f"delivery {q.delivery_id} exists for PO {q.po_id} with status {q.po_status}")
delivered_pos = set(d.po_id.dropna().astype(int))
for _, q in po.iterrows():
    if q.po_status in ("CLOSED", "PART") and q.po_id not in delivered_pos:
        add("R08", f"PO {q.po_id} is {q.po_status} but has no delivery")
x = inv.merge(d, on="delivery_id", how="left")
for _, q in x.iterrows():
    if q.invoice_date < q.delivery_date:
        add("R09", f"invoice {q.invoice_id} dated {q.invoice_date} before delivery {q.delivery_id} on {q.delivery_date}")
    if pd.isna(q.po_id):
        add("R09", f"invoice {q.invoice_id} bills delivery {q.delivery_id}, a stock transfer with no PO")
    lines = b[b.delivery_id == q.delivery_id]
    expect = round((lines.qty_received * lines.cost_price).sum(), 2)
    if abs(expect - q.amount_ex_gst) > 0.05:
        add("R10", f"invoice {q.invoice_id}: amount {q.amount_ex_gst}, accepted units x cost = {expect}")
x = di.merge(sd, on="disruption_id").merge(d, on="delivery_id")
for _, q in x.iterrows():
    sched = (pd.Timestamp(q.delivery_date) - pd.Timedelta(days=int(q.delay_days))).strftime("%Y-%m-%d")
    end = q.end_date if isinstance(q.end_date, str) else "9999-12-31"
    if not (q.start_date <= sched <= end):
        add("R11", f"disruption {q.disruption_id} ({q.start_date} to {q.end_date if isinstance(q.end_date,str) else 'ongoing'}) delays delivery {q.delivery_id}, scheduled {sched}")
x = pol.merge(po, on="po_id")
for _, q in x.iterrows():
    a = ag[(ag.supplier_id == q.supplier_id) & (ag.product_id == q.product_id) & (ag.store_id == q.store_id)
           & (ag.valid_from <= q.order_date) & (ag.valid_to.isna() | (ag.valid_to.fillna("9999") >= q.order_date))]
    if a.empty:
        add("R12", f"PO {q.po_id} line {q.line_no}: no agreement for supplier {q.supplier_id}, product {q.product_id}, store {q.store_id} on {q.order_date}")
    elif abs(a.agreed_unit_cost.iloc[0] - q.agreed_unit_cost) > 0.001:
        add("R12", f"PO {q.po_id} line {q.line_no}: cost {q.agreed_unit_cost}, agreement says {a.agreed_unit_cost.iloc[0]}")
val = pol.assign(v=pol.ordered_qty * pol.agreed_unit_cost).groupby("po_id").v.sum()
for _, q in po.iterrows():
    lim = oo[oo.employee_id == q.employee_id].ordering_limit_aud
    if lim.empty or val.get(q.po_id, 0) > lim.iloc[0]:
        add("R13", f"PO {q.po_id}: value {val.get(q.po_id,0):.2f} by employee {q.employee_id} (limit {lim.iloc[0] if not lim.empty else 'not an ordering officer'})")
x = sl.merge(sa, on="sale_id").merge(b, on="batch_id", suffixes=("", "_b"))
x["day"] = x.sale_datetime.str[:10]
for _, q in x.iterrows():
    tag = f"sale {q.sale_id} line {q.line_no} (batch {q.batch_id})"
    if q.store_id != q.store_id_b:
        add("R14", f"{tag}: sold at store {q.store_id}, batch shelved at store {q.store_id_b}")
    if q.day < q.received_date:
        add("R15", f"{tag}: sold {q.day}, received {q.received_date}")
    if isinstance(q.use_by_date, str) and q.day > q.use_by_date:
        add("R16", f"{tag}: sold {q.day}, use by {q.use_by_date}")
    if pd.notna(q.markdown_id):
        mk = m[m.markdown_id == q.markdown_id].iloc[0]
        if mk.batch_id != q.batch_id or q.sale_datetime.replace(" ", "T") < mk.applied_at.replace(" ", "T") or abs(mk.reduced_price - q.unit_price_charged) > 0.001:
            add("R17", f"{tag}: markdown {int(q.markdown_id)} is batch {mk.batch_id} at {mk.applied_at} for {mk.reduced_price}; line sold {q.sale_datetime} at {q.unit_price_charged}")
x = m.merge(b, on="batch_id")
for _, q in x.iterrows():
    day = q.applied_at[:10]
    if day < q.received_date or (isinstance(q.use_by_date, str) and day > q.use_by_date):
        add("R18", f"markdown {q.markdown_id} on {day}, batch {q.batch_id} on shelf {q.received_date} to {q.use_by_date}")
x = w.merge(b, on="batch_id")
for _, q in x.iterrows():
    if q.writeoff_date < q.received_date:
        add("R19", f"write off {q.writeoff_id} on {q.writeoff_date}, batch {q.batch_id} received {q.received_date}")
    if q.reason == "EXPIRED" and (not isinstance(q.use_by_date, str) or q.writeoff_date <= q.use_by_date):
        add("R19", f"write off {q.writeoff_id} EXPIRED on {q.writeoff_date}, batch {q.batch_id} use by {q.use_by_date}")
    lim = dm[dm.employee_id == q.employee_id].approval_limit_aud
    if lim.empty or q.qty * q.cost_price > lim.iloc[0]:
        add("R20", f"write off {q.writeoff_id}: value {q.qty*q.cost_price:.2f}, employee {q.employee_id}")
x = bc.merge(sc, on="count_id").merge(b, on="batch_id")
for _, q in x.iterrows():
    if q.count_date < q.received_date or (isinstance(q.use_by_date, str) and q.count_date > q.use_by_date):
        add("R21", f"count {q.count_id} on {q.count_date} counts batch {q.batch_id} on shelf {q.received_date} to {q.use_by_date}")
    if q.counted_qty > q.system_qty:
        add("R22", f"count {q.count_id} batch {q.batch_id}: counted {q.counted_qty} > system {q.system_qty}")
sold = sl.groupby("batch_id").qty_sold.sum(); wo = w.groupby("batch_id").qty.sum()
for _, q in b.iterrows():
    exp = q.qty_received - sold.get(q.batch_id, 0) - wo.get(q.batch_id, 0)
    if exp != q.qty_on_hand:
        add("R23", f"batch {q.batch_id}: on hand {q.qty_on_hand}, received {q.qty_received} - sold {sold.get(q.batch_id,0)} - written off {wo.get(q.batch_id,0)} = {exp}")
full = bc.merge(sc[sc.count_type == "FULL"], on="count_id").merge(b, on="batch_id")
for _, q in st.iterrows():
    covered = full[full.store_id == q.store_id]
    if isinstance(q.last_full_stocktake, str):
        if covered[covered.count_date == q.last_full_stocktake].empty:
            add("R24", f"store {q.store_id}: last full stocktake {q.last_full_stocktake} but no FULL count of its batches that day")
    elif not covered.empty:
        add("R24", f"store {q.store_id}: has FULL counts but no last full stocktake date")

total = 0
print(f"AUDIT OF {F}\n")
print(f"{'Rule':<5} {'Violations':>10}  Description")
for k, desc in RULES.items():
    n = len(V.get(k, [])); total += n
    print(f"{k:<5} {n:>10}  {desc}")
print(f"{'ALL':<5} {total:>10}\n")
for k in RULES:
    for msg in V.get(k, []):
        print(f"[{k}] {msg}")
