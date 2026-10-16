# 00_data_preparation

Why the transaction data was regenerated, and how to reproduce it.

## The problem

An audit of the Assessment 2 sample data against 24 business rules found
**150 violations**. For instance, products were delivered that their purchase order never ordered, stock was sold after its use by date or even before it arrived, and disruptions were recorded as delaying deliveries that took place before the disruption began. See `audit_before_A2_data.txt`.

## What changed

* **Master data is unchanged.** Master data remains the same. Stores, shelf bays and categories, products, perishable and ambient details, suppliers, distribution centres, consignors, employees, phones, role tables and supply disruptions are copied from the Assessment 2 export, byte for byte.

* **Transaction tables were regenerated** (supply agreements, purchase orders
  and lines, deliveries and lines, invoices, disruption impacts, stock batches,
  stock counts, markdowns, sales and lines, write offs). They come from a day by
  day simulation of the four stores from 5 January to 30 August 2026, with a
  fixed random seed.
* The CSV columns were the same, so no changes were required to `import.txt`.
* After regeneration there are **0 violations**. See
  `audit_after_regenerated_data.txt`.

## Files

| File | Purpose |
|:--|:--|
| `a2_original_csv/` | the 29 CSV files exported from the Assessment 2 database (331 rows) |
| `audit.py` | checks any CSV folder against the 24 business rules |
| `generate.py` | rebuilds the transaction tables (reproducible, seed 563) |
| `expected_counts.py` | node and relationship counts `import.txt` must produce |
| `model_a_counts.py` | counts for the naive Model A, for the Model A vs B comparison |
| `update_counts.py` | writes the current counts into import.txt, the model spec and the diagram subtitle |
| `audit_before_A2_data.txt` | audit of the Assessment 2 data: 150 violations |
| `audit_after_regenerated_data.txt` | audit of the regenerated data: 0 violations |

## Reproduce

```
python3 generate.py a2_original_csv ../01_csv
python3 audit.py ../01_csv
python3 expected_counts.py ../01_csv
```

`update_counts.py` is run from the folder that holds `import.txt`, the spec and
the diagram scripts while the documents are being prepared.
