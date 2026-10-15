"""Regenerate the transaction tables of the PRT563 Group 12 data set.

Master data (stores, shelf bays, categories, products and their
perishable / ambient details, suppliers, distribution centres, consignors,
employees, phones, role tables, supply disruptions) is copied unchanged
from the Assessment 2 CSV export. Every transaction table is rebuilt by a
day by day simulation of the four stores, so that each record obeys the
business rules checked by audit.py.

    python3 generate.py <a2_csv_folder> <output_folder>

The random seed is fixed, so the output is identical on every run.
"""
import sys, math, random, shutil, csv, os
from datetime import date, datetime, timedelta
from collections import defaultdict

SRC, OUT = sys.argv[1], sys.argv[2]
rng = random.Random(563)            # fixed seed: reproducible output

START, END = date(2026, 1, 5), date(2026, 8, 30)
def d(s): return date.fromisoformat(s)
def days(a, b): return (b - a).days
def iso(x): return x.isoformat()

def read(name):
    with open(f"{SRC}/{name}.csv", newline="") as f:
        return list(csv.DictReader(f))
def write(name, header, rows):
    with open(f"{OUT}/{name}.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow(["" if v is None else v for v in r])

# --------------------------------------------------------------------------
# 1. Master data, copied unchanged
# --------------------------------------------------------------------------
MASTER = ["store", "shelf_bay", "product_category", "product", "perishable_product",
          "ambient_product", "supplier", "distribution_centre", "consignor", "employee",
          "employee_phone", "ordering_officer", "replenishment_assistant", "duty_manager",
          "supply_disruption"]
os.makedirs(OUT, exist_ok=True)
for n in MASTER:
    shutil.copyfile(f"{SRC}/{n}.csv", f"{OUT}/{n}.csv")

PRODUCTS = {int(r["product_id"]): r for r in read("product")}
PERISH = {int(r["product_id"]): r for r in read("perishable_product")}
PRICE = {k: float(v["current_retail_price"]) for k, v in PRODUCTS.items()}
CAT = {k: int(v["category_id"]) for k, v in PRODUCTS.items()}
SHELF = {k: int(v["shelf_life_days"]) for k, v in PERISH.items()}
TEMP = {k: float(v["storage_temp_c"]) for k, v in PERISH.items()}
TRIGGER = {k: int(v["markdown_trigger_days"]) for k, v in PERISH.items()}
CONS_LEAD = {int(r["consignor_id"]): int(r["default_lead_time_days"]) for r in read("consignor")}
SUP_CONS = {int(r["supplier_id"]): (int(r["consignor_id"]) if r["consignor_id"] else None) for r in read("supplier")}
DC_CONS = {int(r["dc_id"]): (int(r["consignor_id"]) if r["consignor_id"] else None) for r in read("distribution_centre")}
OFFICER_LIMIT = {int(r["employee_id"]): float(r["ordering_limit_aud"]) for r in read("ordering_officer")}
DM_LIMIT = {int(r["employee_id"]): float(r["approval_limit_aud"]) for r in read("duty_manager")}
DISRUPTIONS = [(int(r["disruption_id"]), d(r["start_date"]), d(r["end_date"]) if r["end_date"] else None)
               for r in read("supply_disruption")]
STORES = [1, 2, 3, 4]
TOP_END = [1, 2, 3]
BERRIMAH, ADELAIDE = DC_CONS[1], DC_CONS[2]          # consignor ids 6 and 7
HOUSEHOLD = {p for p, c in CAT.items() if c == 6}     # 10% GST, everything else GST free

def bay_for(p):
    """Temperature rule (audit R06): coldest bay for <= 1 C, chilled below 8 C,
    fresh ambient lines at the front (A12), pantry and household in D21."""
    if p in TEMP:
        if TEMP[p] <= 1.0: return "C09"
        if TEMP[p] < 8.0:  return "B04"
        return "A12"
    return "D21"

# --------------------------------------------------------------------------
# 2. Who supplies what (realistic catalogue) and the supply agreements
# --------------------------------------------------------------------------
# supplier for each (store, product) and the date the arrangement starts
def route(store, p, on):
    if p in (1, 2):                       # bananas, mangoes
        return 6 if store in TOP_END else 1
    if p in (3, 4):  return 1             # spinach, tomatoes
    if p in (5, 6, 7): return 2           # dairy
    if p in (8, 9):  return 3             # bakery
    if p in (10, 11): return 4            # seafood
    if p == 12:      return 8             # beef
    if p in HOUSEHOLD: return 5
    # pantry: Nationwide for Darwin City and Casuarina, Southern Packaged
    # (through a DC) for Palmerston and Alice Springs; Casuarina switches to
    # Southern Packaged from 1 May after Nationwide's slow deliveries
    if store == 2 and on >= date(2026, 5, 1): return 7
    return 5 if store in (1, 2) else 7

def consignor_for(supplier, store):
    """Direct suppliers consign their own deliveries; the others go through
    Berrimah DC (Top End stores) or Adelaide National DC (Alice Springs)."""
    if SUP_CONS[supplier] is not None:
        return SUP_CONS[supplier]
    return BERRIMAH if store in TOP_END else ADELAIDE

def agreed_lead(supplier, store):
    if SUP_CONS[supplier] is not None:
        lead = CONS_LEAD[SUP_CONS[supplier]]
        if store == 4 and supplier in (1, 2, 3, 4):
            lead += 2                     # Darwin to Alice Springs by road
        return lead
    return 3 if store in TOP_END else 5   # supplier to DC, then DC to store

COST_RATIO = {1: 0.58, 2: 0.60, 3: 0.55, 4: 0.62, 5: 0.66, 6: 0.60}   # by category
def base_cost(p, supplier, store):
    c = PRICE[p] * COST_RATIO[CAT[p]]
    c *= {1: 1.00, 2: 1.02, 3: 0.99, 4: 1.04}[store]          # freight to the store
    if supplier == 7: c *= 0.97                               # Southern Packaged is cheaper
    return round(c, 2)

def pack_size(p, store):
    """Minimum order quantity (case size): about half a week of demand for
    fresh lines and two weeks for ambient lines, never below 2."""
    weeks = 0.5 if p in PERISH else 2
    return max(2, round(EXPECTED[(store, p)] * 7 * weeks))

# --------------------------------------------------------------------------
# 3. Shopping behaviour: basket missions give realistic co purchase patterns
# --------------------------------------------------------------------------
MISSIONS = {  # mission: [(product, probability it is in the basket)]
    "breakfast": [(5, .85), (8, .6), (1, .5), (6, .35), (9, .2), (17, .15)],
    "fresh_dinner": [(3, .6), (4, .65), (10, .3), (11, .3), (13, .3), (15, .2), (2, .25)],
    "bbq": [(12, .9), (9, .55), (4, .45), (7, .3), (3, .2)],
    "pantry": [(13, .5), (14, .6), (16, .6), (15, .3), (17, .35), (7, .25)],
    "cleaning": [(18, .55), (19, .6), (20, .65)],
    "top_up": [(5, .7), (8, .5), (1, .3), (20, .15), (6, .15)],
}
STORE_MIX = {   # how often each mission occurs in each store
    1: {"breakfast": .22, "fresh_dinner": .20, "bbq": .10, "pantry": .14, "cleaning": .09, "top_up": .25},
    2: {"breakfast": .20, "fresh_dinner": .25, "bbq": .12, "pantry": .15, "cleaning": .10, "top_up": .18},
    3: {"breakfast": .25, "fresh_dinner": .14, "bbq": .16, "pantry": .17, "cleaning": .12, "top_up": .16},
    4: {"breakfast": .22, "fresh_dinner": .06, "bbq": .28, "pantry": .20, "cleaning": .12, "top_up": .12},
}
BASKETS_PER_DAY = {1: 2.4, 2: 2.9, 3: 2.2, 4: 1.7}
DOW = [0.9, 0.85, 0.9, 1.0, 1.15, 1.35, 1.1]          # Monday .. Sunday

def qty_for(p):
    u = PRODUCTS[p]["unit_of_measure"]
    if u == "kg": return rng.choice([1, 1, 1, 2])
    return rng.choices([1, 2, 3], [0.72, 0.23, 0.05])[0]

def make_basket(store):
    mission = rng.choices(list(STORE_MIX[store]), list(STORE_MIX[store].values()))[0]
    items = {p: qty_for(p) for p, pr in MISSIONS[mission] if rng.random() < pr}
    if not items:
        p, _ = max(MISSIONS[mission], key=lambda t: t[1])
        items[p] = qty_for(p)
    if rng.random() < 0.18:                                  # impulse item
        p = rng.randint(1, 20)
        items.setdefault(p, 1)
    return items

# expected units per day for each (store, product), used for ordering
def expected_demand():
    e = defaultdict(float)
    for s in STORES:
        for mission, w in STORE_MIX[s].items():
            for p, pr in MISSIONS[mission]:
                avg_q = 1.25 if PRODUCTS[p]["unit_of_measure"] == "kg" else 1.33
                e[(s, p)] += BASKETS_PER_DAY[s] * w * pr * avg_q
        for p in range(1, 21):
            e[(s, p)] += BASKETS_PER_DAY[s] * 0.18 / 20
    return e
EXPECTED = expected_demand()

# supply agreements: one per (supplier, product, store) actually used;
# some are repriced on 1 July, giving a closed and an open version
AGREEMENTS = []           # (supplier, product, store, valid_from, cost, lead, moq, valid_to)
def build_agreements():
    seen = set()
    for s in STORES:
        for p in range(1, 21):
            for on in (date(2026, 1, 1), date(2026, 5, 1)):
                sup = route(s, p, on)
                if (sup, p, s) in seen: continue
                seen.add((sup, p, s))
                vf = date(2025, 7, 1) if on == date(2026, 1, 1) else on
                cost, lead, moq = base_cost(p, sup, s), agreed_lead(sup, s), pack_size(p, s)
                ended = (s == 2 and p in (13, 14, 15, 16, 17) and sup == 5)
                if ended:   # Casuarina pantry moves to Southern Packaged
                    AGREEMENTS.append([sup, p, s, vf, cost, lead, moq, date(2026, 4, 30)])
                elif rng.random() < 0.35:   # price review on 1 July
                    AGREEMENTS.append([sup, p, s, vf, cost, lead, moq, date(2026, 6, 30)])
                    AGREEMENTS.append([sup, p, s, date(2026, 7, 1),
                                       round(cost * rng.uniform(1.02, 1.06), 2), lead, moq, None])
                else:
                    AGREEMENTS.append([sup, p, s, vf, cost, lead, moq, None])
build_agreements()
def agreement(sup, p, s, on):
    for a in AGREEMENTS:
        if a[0] == sup and a[1] == p and a[2] == s and a[3] <= on and (a[7] is None or on <= a[7]):
            return a
    raise KeyError((sup, p, s, on))

# --------------------------------------------------------------------------
# 4. Staff on each store (used for markdowns, write offs and counts)
# --------------------------------------------------------------------------
OFFICER = {1: 1, 2: 2, 3: 3, 4: 1}              # who raises the store's POs
ASSISTANT = {1: 4, 2: 5, 3: 6, 4: 7}             # replenishment assistant
GENERAL = {1: 10, 2: 11, 3: 12, 4: 12}           # staff without a special role
DUTY = {1: 3, 2: 8, 3: 8, 4: 9}                  # duty manager on site

def authoriser(store, value):
    for e in [DUTY[store]] + sorted(DM_LIMIT, key=DM_LIMIT.get):
        if DM_LIMIT[e] >= value:
            return e
    return max(DM_LIMIT, key=DM_LIMIT.get)

# --------------------------------------------------------------------------
# 5. Simulation state
# --------------------------------------------------------------------------
pos, po_lines, deliveries, del_lines, batches = [], [], [], [], []
invoices, impacts, markdowns, writeoffs, sales, sale_lines = [], [], [], [], [], []
counts, batch_counts = [], []
on_order = defaultdict(int)              # (store, product) -> units ordered, not yet delivered
pending = defaultdict(list)              # arrival date -> list of delivery dicts
by_sp = defaultdict(list)                # (store, product) -> its batches

def disruption_delay(cons, sup, store, sched, has_cold):
    """Return [(disruption_id, delay_days)] for a delivery scheduled on `sched`."""
    out = []
    for did, s, e in DISRUPTIONS:
        if not (s <= sched and (e is None or sched <= e)): continue
        if did == 1:   # cyclone, Stuart Highway closed: road freight from the south
            if cons in (ADELAIDE,) or sup in (5, 7, 6) or store == 4:
                out.append((did, days(sched, e) + rng.randint(1, 3)))
        elif did == 2:  # Berrimah DC refrigeration failure: chilled lines via Berrimah
            if cons == BERRIMAH and has_cold:
                out.append((did, rng.randint(1, 3)))
        elif did == 3:  # national carrier industrial action: interstate freight
            if cons == ADELAIDE or sup == 5:
                if rng.random() < 0.6:
                    out.append((did, rng.randint(1, 2)))
    return out

def arrival_temp(cons, lines, when):
    cold = [p for p, _ in lines if p in TEMP and TEMP[p] < 8]
    if not cold:
        return None                       # ambient only: not measured
    # the truck is set for the coldest line it carries
    t = min(TEMP[p] for p in cold) + abs(rng.gauss(0.9, 0.6))
    if cons == BERRIMAH and date(2026, 4, 18) <= when <= date(2026, 4, 24):
        t = rng.uniform(6.5, 9.0)         # DC refrigeration failure
    elif rng.random() < 0.05:
        t += rng.uniform(2.5, 4.0)        # occasional truck fault
    return round(min(max(t, 0.5), 10.0), 1)

# --------------------------------------------------------------------------
# 6. Ordering: weekly for fresh routes, every four weeks for ambient routes
# --------------------------------------------------------------------------
def stock_position(store, p, by):
    """Units on hand that will still be sellable on `by`, plus units on order."""
    have = sum(bt["on_hand"] for bt in by_sp[(store, p)]
               if bt["on_hand"] > 0
               and (bt["use_by"] is None or bt["use_by"] >= by))
    return have + on_order[(store, p)]

def cycle_for(p):
    """Review cycle in days: short life lines twice a week, other fresh
    lines weekly, ambient lines every four weeks."""
    if p in PERISH:
        return 3 if SHELF[p] <= 5 else 7
    return 28

def place_orders(today):
    groups = defaultdict(list)            # (store, supplier) -> products due today
    for s in STORES:
        for p in range(1, 21):
            sup = route(s, p, today)
            fresh = p in PERISH
            cycle = cycle_for(p)
            offset = (s * 2 + sup) % cycle
            if (days(START, today) - offset) % cycle != 0 and today != START:
                continue
            groups[(s, sup)].append(p)
    for (s, sup), prods in sorted(groups.items()):
        lines = []
        for p in prods:
            a = agreement(sup, p, s, today)
            lead, moq = a[5], a[6]
            rate = EXPECTED[(s, p)]
            if p in PERISH:      # cover until the next delivery, never past shelf life
                cover = min(cycle_for(p), SHELF[p]) * 1.15
            else:                # ambient: the cycle plus one week of safety stock
                cover = cycle_for(p) + 7
            arriving = stock_position(s, p, today + timedelta(days=lead)) - on_order[(s, p)]
            projected = max(0.0, arriving - rate * lead) + on_order[(s, p)]
            need = rate * cover - projected
            if need < 0.5: continue
            qty = max(moq, round(need / moq) * moq)
            lines.append((p, qty, a[4]))
        if not lines: continue
        value = sum(q * c for _, q, c in lines)
        officer = OFFICER[s]
        if OFFICER_LIMIT[officer] < value:
            officer = max(OFFICER_LIMIT, key=OFFICER_LIMIT.get)
        lead = max(agreement(sup, p, s, today)[5] for p, _, _ in lines)
        po = {"id": None, "order": today, "required": today + timedelta(days=lead),
              "supplier": sup, "officer": officer, "store": s, "lines": lines,
              "status": "SENT"}
        pos.append(po)
        for p, q, _ in lines:
            on_order[(s, p)] += q
        if today >= date(2026, 8, 27):
            po["status"] = rng.choice(["DRAFT", "SENT"])
            if po["status"] == "DRAFT":
                for p, q, _ in lines: on_order[(s, p)] -= q
                continue
        # cyclone: a few orders for southern freight are cancelled outright
        southern = sup in (5, 6, 7) or s == 4
        if southern and date(2026, 2, 2) <= today <= date(2026, 2, 8) and rng.random() < 0.5:
            po["status"] = "CANCELLED"
            for p, q, _ in lines: on_order[(s, p)] -= q
            continue
        schedule_delivery(po, lines, today)

def schedule_delivery(po, lines, today):
    cons = consignor_for(po["supplier"], po["store"])
    noise = rng.choices([-1, 0, 1, 2], [0.05, 0.72, 0.18, 0.05])[0]
    sched = max(today + timedelta(days=1), po["required"] + timedelta(days=noise))
    has_cold = any(p in TEMP and TEMP[p] < 8 for p, _, _ in lines)
    hits = disruption_delay(cons, po["supplier"], po["store"], sched, has_cold)
    arrive = sched + timedelta(days=sum(x[1] for x in hits))
    # 4% of orders are split: part now, the rest two to four days later
    late = today >= date(2026, 8, 20)
    if len(lines) > 1 and rng.random() < (0.3 if late else 0.04):
        k = rng.randint(1, len(lines) - 1)
        first, rest = lines[:k], lines[k:]
        gap = rng.randint(5, 8) if late else rng.randint(2, 4)
        pending[arrive].append({"po": po, "cons": cons, "lines": first, "hits": hits})
        pending[arrive + timedelta(days=gap)].append({"po": po, "cons": cons, "lines": rest, "hits": []})
    else:
        pending[arrive].append({"po": po, "cons": cons, "lines": lines, "hits": hits})

# --------------------------------------------------------------------------
# 7. Receiving: delivery, delivery lines, stock batches, invoices
# --------------------------------------------------------------------------
def receive(today):
    for dv in pending.pop(today, []):
        po, cons = dv["po"], dv["cons"]
        lines = [(p, q) for p, q, _ in dv["lines"]] if po else dv["lines"]
        temp = arrival_temp(cons, lines, today)
        delivery = {"id": None, "date": today, "temp": temp, "cons": cons, "po": po,
                    "hits": dv["hits"], "lines": []}
        for i, (p, q, *rest) in enumerate(dv["lines"], start=1):
            store = po["store"] if po else dv["store"]
            cost = rest[0] if rest else dv["costs"][p]
            delivered = q
            if po and rng.random() < 0.05 and q > 3:
                delivered = q - rng.randint(1, max(1, q // 4))      # short shipped
            rejected = 0
            if temp is not None and p in TEMP and temp - TEMP[p] > 3.0:
                rejected = max(1, round(delivered * rng.uniform(0.5, 0.8)))    # QA reject
            elif rng.random() < 0.03:
                rejected = 1                                                   # damaged
            rejected = min(rejected, delivered - 1)
            bt = {"id": None, "received": today, "store": store, "product": p,
                  "use_by": today + timedelta(days=SHELF[p]) if p in SHELF else None,
                  "qty": delivered - rejected, "on_hand": delivered - rejected,
                  "cost": cost, "bay": bay_for(p), "delivery": delivery, "line": i,
                  "markdown": None}
            batches.append(bt)
            by_sp[(store, p)].append(bt)
            delivery["lines"].append((i, delivered, rejected, bt))
            on_order[(store, p)] -= q          # PO line or transfer has arrived
        deliveries.append(delivery)

def transfers(today):
    """Berrimah / Adelaide DC send emergency stock (no PO) when an ambient
    line runs out during the cyclone or a carrier strike."""
    if not (date(2026, 2, 3) <= today <= date(2026, 2, 14) or date(2026, 6, 9) <= today <= date(2026, 6, 30)):
        return
    for s in STORES:
        out = [p for p in range(13, 21)
               if stock_position(s, p, today) == 0 and on_order[(s, p)] == 0]
        if not out or rng.random() < 0.5: continue
        lines, costs = [], {}
        for p in out[:3]:
            q = max(2, math.ceil(EXPECTED[(s, p)] * 10))
            lines.append((p, q))
            costs[p] = agreement(route(s, p, today), p, s, today)[4]
            on_order[(s, p)] += q
        cons = BERRIMAH if s in TOP_END else ADELAIDE
        arrive = today + timedelta(days=1 if s in TOP_END else 2)
        pending[arrive].append({"po": None, "cons": cons, "lines": lines, "hits": [],
                                "store": s, "costs": costs})

# --------------------------------------------------------------------------
# 8. Trading day: sales, markdowns, expiry, damage
# --------------------------------------------------------------------------
recalled = set()
def sellable(store, p, when):
    return sorted((bt for bt in by_sp[(store, p)]
                   if bt["on_hand"] > 0 and bt["received"] <= when.date()
                   and (bt["use_by"] is None or bt["use_by"] >= when.date())
                   and id(bt) not in recalled),
                  key=lambda bt: (bt["use_by"] or date.max, bt["received"]))

def apply_markdowns(today):
    when = datetime.combine(today, datetime.min.time()).replace(hour=16, minute=30)
    for bt in batches:
        if bt["use_by"] is None or bt["markdown"] or bt["on_hand"] <= 0: continue
        p = bt["product"]
        if bt["use_by"] - timedelta(days=TRIGGER[p]) != today or bt["received"] > today: continue
        if id(bt) in recalled: continue
        reason = "End of day clearance" if TRIGGER[p] == 1 else "Approaching use by date"
        factor = 0.5 if TRIGGER[p] == 1 else rng.choice([0.6, 0.7])
        reduced = round(round(PRICE[p] * factor / 0.05) * 0.05, 2)
        who = rng.choice([ASSISTANT[bt["store"]], GENERAL[bt["store"]], DUTY[bt["store"]]])
        mk = {"id": None, "at": when, "orig": PRICE[p], "reduced": reduced,
              "reason": reason, "emp": who, "batch": bt}
        bt["markdown"] = mk
        markdowns.append(mk)

def trade(today):
    for s in STORES:
        n = poisson(BASKETS_PER_DAY[s] * DOW[today.weekday()])
        times = sorted(datetime.combine(today, datetime.min.time())
                       + timedelta(minutes=rng.randint(7 * 60, 21 * 60 + 59)) for _ in range(n))
        for t in times:
            lines = []
            for p, q in make_basket(s).items():
                for bt in sellable(s, p, t):
                    if q == 0: break
                    take = min(q, bt["on_hand"])
                    mk = bt["markdown"] if bt["markdown"] and t >= bt["markdown"]["at"] else None
                    price = mk["reduced"] if mk else PRICE[p]
                    lines.append((take, price, bt, mk))
                    bt["on_hand"] -= take
                    q -= take
            if lines:
                sales.append({"id": None, "at": t, "store": s,
                              "pay": rng.choices(["CARD", "CASH", "ACCOUNT", "GIFT"], [0.6, 0.15, 0.2, 0.05])[0],
                              "reg": rng.randint(1, {1: 6, 2: 8, 3: 5, 4: 4}[s]), "lines": lines})

def poisson(lam):
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= L: return k
        k += 1

def write_off(bt, when, qty, reason):
    value = qty * bt["cost"]
    writeoffs.append({"id": None, "date": when, "qty": qty, "reason": reason,
                      "batch": bt, "emp": authoriser(bt["store"], value)})
    bt["on_hand"] -= qty

def expire_and_damage(today):
    for bt in batches:
        if bt["use_by"] is not None and bt["on_hand"] > 0 and bt["use_by"] == today - timedelta(days=1):
            write_off(bt, today, bt["on_hand"], "EXPIRED")
    for s in STORES:
        if rng.random() < 0.04:
            live = [bt for bt in batches if bt["store"] == s and bt["on_hand"] > 0
                    and bt["received"] <= today and (bt["use_by"] is None or bt["use_by"] >= today)]
            if live:
                bt = rng.choice(live)
                write_off(bt, today, min(bt["on_hand"], rng.randint(1, 2)), "DAMAGED")

def recall(today):
    """20 July: Top End Fresh Produce recalls Baby Spinach supplied 13 to 19 July."""
    if today != date(2026, 7, 20): return
    for bt in batches:
        po = bt["delivery"]["po"]
        if (bt["product"] == 3 and po and po["supplier"] == 1
                and date(2026, 7, 13) <= bt["received"] <= date(2026, 7, 19)):
            recalled.add(id(bt))
            if bt["on_hand"] > 0:
                write_off(bt, today, bt["on_hand"], "RECALL")

# --------------------------------------------------------------------------
# 9. Stock counts: monthly cycle counts, one spot count, and the 30 June
#    full stocktake at Casuarina, Palmerston and Alice Springs
# --------------------------------------------------------------------------
def count(today, store, kind, emp, sample=None):
    live = [bt for bt in batches if bt["store"] == store and bt["on_hand"] > 0
            and bt["received"] <= today and (bt["use_by"] is None or bt["use_by"] >= today)
            and id(bt) not in recalled]
    if sample: live = rng.sample(live, min(sample, len(live)))
    if not live: return
    c = {"id": None, "date": today, "type": kind, "emp": emp, "lines": []}
    counts.append(c)
    for bt in sorted(live, key=lambda b: (b["received"], b["product"])):
        system = bt["on_hand"]
        short = rng.choices([0, 1, 2], [0.86, 0.11, 0.03])[0]
        short = min(short, system)
        c["lines"].append((bt, system - short, system))
        if short:
            write_off(bt, today, short, "SHRINKAGE")

def counts_for(today):
    if today.day == 28:
        for s in STORES:
            count(today, s, "CYCLE", ASSISTANT[s], sample=8)
    if today == date(2026, 6, 30):
        for s in (2, 3, 4):
            count(today, s, "FULL", DUTY[s])
    if today == date(2026, 4, 22):            # after the DC refrigeration failure
        count(today, 1, "SPOT", DUTY[1], sample=6)

# --------------------------------------------------------------------------
# 10. Run the simulation
# --------------------------------------------------------------------------
day = START
while day <= END:
    expire_and_damage(day)          # morning: yesterday's expired stock comes off
    receive(day)                    # deliveries arrive before opening
    recall(day)
    if day <= date(2026, 8, 30):
        place_orders(day)
    transfers(day)
    apply_markdowns(day)
    trade(day)
    counts_for(day)                 # after close
    day += timedelta(days=1)

# deliveries still on the road at the end stay SENT; others become CLOSED / PART
for dv_list in pending.values():
    for dv in dv_list:
        if dv["po"]: dv["po"]["_open"] = True
for po in pos:
    if po["status"] in ("DRAFT", "CANCELLED"): continue
    got = [dv for dv in deliveries if dv["po"] is po]
    if not got: po["status"] = "SENT"
    elif po.get("_open"): po["status"] = "PART"
    else: po["status"] = "CLOSED"

# --------------------------------------------------------------------------
# 11. Number everything in date order and write the CSV files
# --------------------------------------------------------------------------
pos.sort(key=lambda x: (x["order"], x["store"], x["supplier"]))
for i, x in enumerate(pos, 1): x["id"] = i
deliveries.sort(key=lambda x: (x["date"], x["po"]["id"] if x["po"] else 10**6, x["cons"]))
for i, x in enumerate(deliveries, 1): x["id"] = i
bid = 0
for dv in deliveries:
    for (_, _, _, bt) in dv["lines"]:
        bid += 1; bt["id"] = bid
for coll, key in ((markdowns, "at"), (writeoffs, "date"), (sales, "at"), (counts, "date")):
    coll.sort(key=lambda x: (x[key], x.get("store", 0)))
    for i, x in enumerate(coll, 1): x["id"] = i

write("supply_agreement",
      ["supplier_id", "product_id", "store_id", "valid_from", "agreed_unit_cost", "lead_time_days", "min_order_qty", "valid_to"],
      [[a[0], a[1], a[2], iso(a[3]), f"{a[4]:.2f}", a[5], a[6], iso(a[7]) if a[7] else None]
       for a in sorted(AGREEMENTS, key=lambda a: (a[0], a[1], a[2], a[3]))])
write("purchase_order", ["po_id", "order_date", "required_date", "po_status", "supplier_id", "employee_id", "store_id"],
      [[x["id"], iso(x["order"]), iso(x["required"]), x["status"], x["supplier"], x["officer"], x["store"]] for x in pos])
write("po_line", ["po_id", "line_no", "product_id", "ordered_qty", "agreed_unit_cost"],
      [[x["id"], i, p, q, f"{c:.2f}"] for x in pos for i, (p, q, c) in enumerate(x["lines"], 1)])
write("delivery", ["delivery_id", "delivery_date", "consignment_note", "temp_on_arrival_c", "consignor_id", "po_id"],
      [[x["id"], iso(x["date"]), f"CN-2026-{4100 + x['id']}", x["temp"], x["cons"], x["po"]["id"] if x["po"] else None]
       for x in deliveries])
write("delivery_line", ["delivery_id", "line_no", "delivered_qty", "rejected_qty"],
      [[x["id"], i, dq, rq] for x in deliveries for (i, dq, rq, _) in x["lines"]])
write("stock_batch", ["batch_id", "received_date", "use_by_date", "qty_received", "qty_on_hand", "cost_price",
                      "product_id", "delivery_id", "line_no", "store_id", "bay_code"],
      [[bt["id"], iso(bt["received"]), iso(bt["use_by"]) if bt["use_by"] else None, bt["qty"], bt["on_hand"],
        f"{bt['cost']:.2f}", bt["product"], dv["id"], i, bt["store"], bt["bay"]]
       for dv in deliveries for (i, _, _, bt) in dv["lines"]])
inv_rows, iid = [], 0
for dv in deliveries:
    if not dv["po"]: continue                       # transfers are not invoiced
    when = dv["date"] + timedelta(days=rng.randint(0, 3))
    if when > END - timedelta(days=4): continue     # not yet invoiced at the cut off
    amount = sum(bt["qty"] * bt["cost"] for (_, _, _, bt) in dv["lines"])
    gst = sum(bt["qty"] * bt["cost"] for (_, _, _, bt) in dv["lines"] if bt["product"] in HOUSEHOLD) * 0.10
    iid += 1
    inv_rows.append([iid, iso(when), f"{amount:.2f}", f"{gst:.2f}", iso(when + timedelta(days=30)), dv["id"]])
write("invoice", ["invoice_id", "invoice_date", "amount_ex_gst", "gst_amount", "due_date", "delivery_id"], inv_rows)
write("disruption_impact", ["disruption_id", "delivery_id", "delay_days"],
      sorted([[did, dv["id"], dd] for dv in deliveries for did, dd in dv["hits"]]))
write("stock_count", ["count_id", "count_date", "count_type", "employee_id"],
      [[c["id"], iso(c["date"]), c["type"], c["emp"]] for c in counts])
write("batch_count", ["count_id", "batch_id", "counted_qty", "system_qty"],
      [[c["id"], bt["id"], cq, sq] for c in counts for (bt, cq, sq) in c["lines"]])
write("markdown", ["markdown_id", "applied_at", "original_price", "reduced_price", "reason", "employee_id", "batch_id"],
      [[m["id"], m["at"].strftime("%Y-%m-%d %H:%M:%S"), m["orig"], f"{m['reduced']:.2f}", m["reason"], m["emp"], m["batch"]["id"]]
       for m in markdowns])
write("sale", ["sale_id", "sale_datetime", "payment_method", "register_no", "store_id"],
      [[x["id"], x["at"].strftime("%Y-%m-%d %H:%M:%S"), x["pay"], x["reg"], x["store"]] for x in sales])
write("sale_line", ["sale_id", "line_no", "qty_sold", "unit_price_charged", "batch_id", "markdown_id"],
      [[x["id"], i, q, f"{pr:.2f}", bt["id"], mk["id"] if mk else None]
       for x in sales for i, (q, pr, bt, mk) in enumerate(x["lines"], 1)])
write("write_off", ["writeoff_id", "writeoff_date", "qty", "reason", "batch_id", "employee_id"],
      [[w["id"], iso(w["date"]), w["qty"], w["reason"], w["batch"]["id"], w["emp"]] for w in writeoffs])

print("purchase orders", len(pos), "| deliveries", len(deliveries), "| batches", bid,
      "| sales", len(sales), "| sale lines", sum(len(x["lines"]) for x in sales),
      "| markdowns", len(markdowns), "| write offs", len(writeoffs),
      "| counts", len(counts), "| invoices", len(inv_rows), "| agreements", len(AGREEMENTS))
