"""Write the current expected counts into import.txt, the graph model spec
and the diagram subtitle, so documentation always matches the CSV files."""
import re, sys, subprocess, csv, glob
CSV = sys.argv[1]
out = subprocess.run(["python3", "gen/expected_counts.py", CSV], capture_output=True, text=True).stdout
cnt = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\s+(\w+)\s+(\d+)$", out, re.M)}
N = int(re.search(r"total nodes (\d+)", out).group(1)); R = int(re.search(r"total relationships (\d+)", out).group(1))
rows = sum(sum(1 for _ in csv.reader(open(f))) - 1 for f in glob.glob(f"{CSV}/*.csv"))
ma = subprocess.run(["python3", "gen/model_a_counts.py", CSV], capture_output=True, text=True).stdout
AN, AR = map(int, re.search(r"(\d+) nodes, (\d+) relationships", ma).groups())
saved = {k.strip(): int(v) for k, v in re.findall(r"^\s+(O\d [\w_]+)\s+(\d+)$", ma, re.M)}
f = lambda n: f"{n:,}"

# ---- import.txt -------------------------------------------------------------
s = open("import.txt").read()
s = re.sub(r"//  Source   : 29 CSV files, [\d,]+ rows\.", f"//  Source   : 29 CSV files, {f(rows)} rows.", s)
s = re.sub(r"//  Result   : [\d,]+ nodes, [\d,]+ relationships,", f"//  Result   : {f(N)} nodes, {f(R)} relationships,", s)
s = re.sub(r"\(\d[\d,]* nodes, plus extra labels and lists\)", f"({f(N)} nodes, plus extra labels and lists)", s)
s = re.sub(r"\(\d[\d,]* relationships\)\n", f"({f(R)} relationships)\n", s)
def head(m):
    num, label, rest = m.group(1), m.group(2), m.group(3)
    new = f"// ---- {num} {label} ({f(cnt[label])}){rest}"
    return (new + " " + "-" * 80)[:78].rstrip() if rest.strip(" -") == "" else new.split(" ---")[0] + " " + "-" * max(3, 77 - len(new.split(" ---")[0]))
for label in ["PurchaseOrder", "Delivery", "Invoice", "StockBatch", "StockCount", "Sale", "SaleLine", "Markdown", "WriteOff", "SupplyAgreement"]:
    s = re.sub(rf"(// ---- 3\.\d+ {label} )\([\d,]+\)", lambda m: f"{m.group(1)}({f(cnt[label])})", s)
s = re.sub(r"ReplenishmentAssistant 4, DutyManager 3\), PurchaseOrder \d+,\n// Delivery \d+, Invoice \d+, SupplyDisruption 3, StockBatch \d+,\n// StockCount \d+, Sale \d+, SaleLine \d+, Markdown \d+, WriteOff \d+,",
           f"ReplenishmentAssistant 4, DutyManager 3), PurchaseOrder {cnt['PurchaseOrder']},\n// Delivery {cnt['Delivery']}, Invoice {cnt['Invoice']}, SupplyDisruption 3, StockBatch {cnt['StockBatch']},\n// StockCount {cnt['StockCount']}, Sale {cnt['Sale']}, SaleLine {cnt['SaleLine']}, Markdown {cnt['Markdown']}, WriteOff {cnt['WriteOff']},", s)
s = re.sub(r"// SupplyAgreement \d+\n", f"// SupplyAgreement {cnt['SupplyAgreement']}\n", s)
s = re.sub(r"\(26 types, [\d,]+ in total\)", f"(26 types, {f(R)} in total)", s)
s = re.sub(r"Expected: [\d,]+ nodes, [\d,]+ relationships", f"Expected: {f(N)} nodes, {f(R)} relationships", s)
open("import.txt", "w").write(s)

# ---- graph model spec ------------------------------------------------------
m = open("A4_step5_graph_model.md").read()
tot = sum(saved.values())
m = re.sub(r"\| Nodes \| [\d,]+ \| \*\*[\d,]+\*\* \| \*\*-[\d,]+ \(-\d+%\)\*\* \|",
           f"| Nodes | {f(AN)} | **{f(N)}** | **-{f(tot)} (-{round(100*tot/AN)}%)** |", m)
m = re.sub(r"\| Relationships \| [\d,]+ \| \*\*[\d,]+\*\* \| \*\*-[\d,]+ \(-\d+%\)\*\* \|",
           f"| Relationships | {f(AR)} | **{f(R)}** | **-{f(tot)} (-{round(100*tot/AR)}%)** |", m)
m = re.sub(r"Every one of the [\d,]+ relational rows", f"Every one of the {f(AN)} relational rows", m)
m = re.sub(r"29 labels, 38 relationship types, [\d,]+ nodes, [\d,]+ relationships\.", f"29 labels, 38 relationship types, {f(AN)} nodes, {f(AR)} relationships.", m)
m = re.sub(r"(BATCH_COUNT has no other references) \| [\d,]+ \| [\d,]+ \|", lambda x: f"{x.group(1)} | {f(saved['O4 batch_count'])} | {f(saved['O4 batch_count'])} |", m)
m = re.sub(r"(DISRUPTION_IMPACT has no other references) \| [\d,]+ \| [\d,]+ \|", lambda x: f"{x.group(1)} | {f(saved['O4 disruption_impact'])} | {f(saved['O4 disruption_impact'])} |", m)
m = re.sub(r"(no foreign key anywhere points at PO_LINE) \| [\d,]+ \| [\d,]+ \|", lambda x: f"{x.group(1)} | {f(saved['O5 po_line'])} | {f(saved['O5 po_line'])} |", m)
dl = saved["O6 delivery_line"]
m = re.sub(r"\| [\d,]+ lines, [\d,]+ batches, each line creates exactly one batch, 0 orphans \| [\d,]+ \| [\d,]+ \|",
           f"| {f(dl)} lines, {f(dl)} batches, each line creates exactly one batch, 0 orphans | {f(dl)} | {f(dl)} |", m)
m = re.sub(r"\| \| \*\*Total\*\* \| \| \| \| \*\*[\d,]+\*\* \| \*\*[\d,]+\*\* \|", f"| | **Total** | | | | **{f(tot)}** | **{f(tot)}** |", m)
lines = m.split("\n"); sec = None
for i, l in enumerate(lines):
    if l.startswith("## 4."): sec = 4
    elif l.startswith("## 5."): sec = 5
    elif l.startswith("## 6."): sec = None
    mm = re.match(r"\| `(\w+)` \|", l)
    if sec and mm and mm.group(1) in cnt:
        c = l.split("|"); c[-2] = f" {f(cnt[mm.group(1)])} "; lines[i] = "|".join(c)
    if sec == 4 and l.startswith("| **Total**"): lines[i] = re.sub(r"\*\*[\d,]+\*\* \|$", f"**{f(N)}** |", l)
    if sec == 5 and l.startswith("| **Total**"): lines[i] = re.sub(r"\*\*[\d,]+\*\* \|$", f"**{f(R)}** |", l)
open("A4_step5_graph_model.md", "w").write("\n".join(lines))

# ---- diagram subtitle ------------------------------------------------------
for fn in ("gm_render.py", "gm_drawio.py"):
    t = open(fn).read()
    t = re.sub(r"[\d,]+ nodes, [\d,]+ relationships", f"{f(N)} nodes, {f(R)} relationships", t)
    open(fn, "w").write(t)
print("updated:", f(rows), "rows,", f(N), "nodes,", f(R), "relationships; Model A", f(AN), f(AR))
