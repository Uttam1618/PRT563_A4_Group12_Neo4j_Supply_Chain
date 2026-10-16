# PRT563 Assessment 4, Group 12
# Step 5: The graph model (Model A baseline and Model B optimised)

Every count in this document was computed from the 29 CSV files in `01_csv`.
Master data is exactly as exported from `PRT563_A2_Group12.sql` (Assessment 2);
the transaction tables were regenerated so that every row passes the 24
business rules in `00_data_preparation/audit.py`. Nothing is estimated.

---

## 1. Headline comparison

| Measure | Model A (naive) | Model B (optimised) | Change |
|:--|--:|--:|--:|
| Node labels | 29 | 18 primary + 5 role labels | fewer node kinds |
| Relationship types | 38 | 26 | -12 |
| Nodes | 16,786 | **12,727** | **-4,059 (-24%)** |
| Relationships | 31,740 | **27,681** | **-4,059 (-13%)** |
| Hops across 7 benchmark questions (section 6) | 20 | **10** | **-50%** |

Every one of the 16,786 relational rows is still represented in Model B. Rows
that disappear as nodes reappear as relationships, relationship properties,
extra labels, or list properties. No data is lost.

---

## 2. Model A, the baseline (general conversion rules)

Each table turns into a label, each row into a node, each column into a property and each foreign key into a relationship. This is correct and complete – and this is the starting point the optimisations are measured against.

29 labels, 38 relationship types, 16,786 nodes, 31,740 relationships.

---

## 3. The seven optimisations that turn Model A into Model B

Before being applied, each one is verified from the data. A check that fails would mean the optimisation is unsafe.

| # | Optimisation | Model A | Model B | Precondition checked | Nodes saved | Rels saved |
|--:|:--|:--|:--|:--|--:|--:|
| O1 | **Subclass tables become extra labels** | `Product` and `PerishableProduct` are two nodes joined by `IS_A` | one node `:Product:Perishable`, subclass properties merged in | every product is in exactly one subclass: 0 violations | 20 | 20 |
| O1 | (same, employees) | `Employee` plus `OrderingOfficer`, `ReplenishmentAssistant`, `DutyManager` nodes | one node with role labels, e.g. `:Employee:OrderingOfficer:DutyManager` | overlapping specialisation: 1 employee holds 2 roles, 3 hold none; multiple labels represent both cases exactly | 10 | 10 |
| O2 | **Categorisation node removed** | `Delivery -> Consignor <- Supplier` | `Delivery -[:CONSIGNED_BY]-> Supplier` or `-> DistributionCentre` directly | every consignor resolves to exactly one supplier or one DC: 0 violations | 7 | 7 |
| O3 | **Multi valued attribute becomes a list property** | 16 `EmployeePhone` nodes | `Employee.phones = ['04..', '08..']` | at most 2 phones per employee | 16 | 16 |
| O4 | **Associative entity becomes a relationship with properties** (count) | `StockCount <- BatchCount -> StockBatch` | `StockCount -[:COUNTED {countedQty, systemQty}]-> StockBatch` | BATCH_COUNT has no other references | 316 | 316 |
| O4 | (same, disruption) | `SupplyDisruption <- DisruptionImpact -> Delivery` | `SupplyDisruption -[:AFFECTS {delayDays}]-> Delivery` | DISRUPTION_IMPACT has no other references | 27 | 27 |
| O5 | **Weak entity with two links becomes a relationship** | `PurchaseOrder <- PoLine -> Product` | `PurchaseOrder -[:ORDERS {lineNo, orderedQty, agreedUnitCost}]-> Product` | no foreign key anywhere points at PO_LINE | 1,858 | 1,858 |
| O6 | **1:1 total relationship collapsed** | `Delivery <- DeliveryLine <- StockBatch` | `Delivery -[:DELIVERED {lineNo, deliveredQty, rejectedQty}]-> StockBatch` | 1,805 lines, 1,805 batches, each line creates exactly one batch, 0 orphans | 1,805 | 1,805 |
| O7 | **Foreign key columns dropped** | `stockBatch.productId` stored *and* linked | link only | n/a | 0 | 0 |
| | **Total** | | | | **4,059** | **4,059** |

### What deliberately stays a node, and why

Three candidates were considered for collapsing and kept as nodes. Explaining
these is as important as the optimisations themselves.

| Kept as node | Why it cannot become a relationship |
|:--|:--|
| `SupplyAgreement` | It links **three** things: supplier, product and store. A Neo4j relationship joins exactly two nodes. This is the graph form of our ternary relationship, the same limitation noted in Assessment 2. |
| `SaleLine` | It links **three** things: sale, stock batch and (sometimes) a markdown. If it's collapsed, it wouldn't be associated with the markdown that priced it. |
| `Markdown` | It is pointed to by `SaleLine` and a relationship can't be the target of another relationship. This is the graph representation of our EER aggregation.
 |
| `WriteOff` | Could technically become a relationship (it links two things only), but it is a business **event** with its own identity, date and reason that auditors look up directly. Kept as a node for clarity. Discussed as an alternative. |

---

## 4. Model B, node labels

| Label | Extra labels | Key | Properties | Nodes |
|:--|:--|:--|:--|--:|
| `Store` | | `storeId` | storeName, street, suburb, postcode, region, openedDate, lastFullStocktake | 4 |
| `ShelfBay` | | `bayId` = storeId:bayCode (surrogate of the composite key) | bayCode, aisleCode, capacityFacings, tempZone | 16 |
| `ProductCategory` | | `categoryId` | categoryName, department | 6 |
| `Product` | `:Perishable` (12) or `:Ambient` (8); `product_type` column not stored, the label replaces it | `productId` | barcode, productName, unitOfMeasure, packSize, currentRetailPrice; perishable: shelfLifeDays, storageTempC, markdownTriggerDays; ambient: minStockCoverDays | 20 |
| `Supplier` | | `supplierId` | supplierName, abnNumber, contactEmail, isLocalNt, defaultLeadTimeDays (from CONSIGNOR, O2) | 8 |
| `DistributionCentre` | | `dcId` | dcName, city, state, defaultLeadTimeDays (from CONSIGNOR, O2) | 3 |
| `Employee` | `:OrderingOfficer` (3), `:ReplenishmentAssistant` (4), `:DutyManager` (3) | `employeeId` | firstName, lastName, dateOfBirth, hireDate, **phones (list)**; role properties: orderingLimitAud, assignedAisle, approvalLimitAud | 12 |
| `PurchaseOrder` | | `poId` | orderDate, requiredDate, poStatus | 977 |
| `Delivery` | | `deliveryId` | deliveryDate, consignmentNote, tempOnArrivalC | 977 |
| `Invoice` | | `invoiceId` | invoiceDate, amountExGst, gstAmount, dueDate | 948 |
| `SupplyDisruption` | | `disruptionId` | startDate, endDate, cause, severity | 3 |
| `StockBatch` | | `batchId` | receivedDate, useByDate, qtyReceived, qtyOnHand, costPrice | 1,805 |
| `StockCount` | | `countId` | countDate, countType | 36 |
| `Sale` | | `saleId` | saleDatetime, paymentMethod, registerNo | 2,082 |
| `SaleLine` | | `saleLineId` = saleId:lineNo (surrogate of the composite key) | lineNo, qtySold, unitPriceCharged | 4,504 |
| `Markdown` | | `markdownId` | appliedAt, originalPrice, reducedPrice, reason | 704 |
| `WriteOff` | | `writeoffId` | writeoffDate, qty, reason | 514 |
| `SupplyAgreement` | | `agreementId` = supplierId:productId:storeId:validFrom | agreedUnitCost, leadTimeDays, minOrderQty, validFrom, validTo | 108 |
| **Total** | | | | **12,727** |

---

### Keys for weak and associative entities

Neo4j uniqueness constraints work best on a single property. ShelfBay, SaleLine
and SupplyAgreement had composite primary keys in SQL, so each gets one
surrogate key built from those columns (for example bay `1:A12`). This maintains one property constraint per node type and the owner key is still correctly represented by the relationship (`LOCATED_IN`, `HAS_LINE`, `OFFERS`).

## 5. Model B, relationships

| Relationship | From | To | Properties | Source in SQL | Count |
|:--|:--|:--|:--|:--|--:|
| `BELONGS_TO` | Product | ProductCategory | | PRODUCT.category_id | 20 |
| `LOCATED_IN` | ShelfBay | Store | | SHELF_BAY.store_id | 16 |
| `PLACED_WITH` | PurchaseOrder | Supplier | | PURCHASE_ORDER.supplier_id | 977 |
| `FOR_STORE` | PurchaseOrder | Store | | PURCHASE_ORDER.store_id | 977 |
| `RAISED_BY` | PurchaseOrder | Employee:OrderingOfficer | | PURCHASE_ORDER.employee_id | 977 |
| `ORDERS` | PurchaseOrder | Product | lineNo, orderedQty, agreedUnitCost | **PO_LINE (O5)** | 1,858 |
| `FULFILS` | Delivery | PurchaseOrder | | DELIVERY.po_id | 971 |
| `CONSIGNED_BY` | Delivery | Supplier or DistributionCentre | | **DELIVERY.consignor_id via CONSIGNOR (O2)** | 977 |
| `BILLS` | Invoice | Delivery | | INVOICE.delivery_id | 948 |
| `AFFECTS` | SupplyDisruption | Delivery | delayDays | **DISRUPTION_IMPACT (O4)** | 27 |
| `DELIVERED` | Delivery | StockBatch | lineNo, deliveredQty, rejectedQty | **DELIVERY_LINE (O6)** | 1,805 |
| `OF_PRODUCT` | StockBatch | Product | | STOCK_BATCH.product_id | 1,805 |
| `STORED_IN` | StockBatch | ShelfBay | | STOCK_BATCH.store_id + bay_code | 1,805 |
| `COUNTED` | StockCount | StockBatch | countedQty, systemQty | **BATCH_COUNT (O4)** | 316 |
| `PERFORMED_BY` | StockCount | Employee | | STOCK_COUNT.employee_id | 36 |
| `OCCURS_AT` | Sale | Store | | SALE.store_id | 2,082 |
| `HAS_LINE` | Sale | SaleLine | | SALE_LINE.sale_id | 4,504 |
| `DRAWS_FROM` | SaleLine | StockBatch | | SALE_LINE.batch_id | 4,504 |
| `APPLIED_TO` | Markdown | SaleLine | | SALE_LINE.markdown_id | 316 |
| `MARKS_DOWN` | Markdown | StockBatch | | MARKDOWN.batch_id | 704 |
| `MARKED_BY` | Markdown | Employee | | MARKDOWN.employee_id | 704 |
| `WRITES_OFF` | WriteOff | StockBatch | | WRITE_OFF.batch_id | 514 |
| `AUTHORISED_BY` | WriteOff | Employee:DutyManager | | WRITE_OFF.employee_id | 514 |
| `OFFERS` | Supplier | SupplyAgreement | | SUPPLY_AGREEMENT.supplier_id | 108 |
| `COVERS` | SupplyAgreement | Product | | SUPPLY_AGREEMENT.product_id | 108 |
| `SUPPLIES_TO` | SupplyAgreement | Store | | SUPPLY_AGREEMENT.store_id | 108 |
| **Total** | | | | | **27,681** |

Relationship names follow the verbs of the Assessment 2 EER diagram wherever
one existed (belongs to, placed with, raised by, fulfils, affects, stored in,
draws from, applied to, marks down, authorised by), so the graph model can be
traced back to the conceptual model.

---

## 6. Efficiency benchmark: hops per question

A "hop" is one relationship traversed. Fewer hops means fewer lookups at query
time and simpler Cypher. The intent of Step 11 is: load both models into two databases and execute them both with `PROFILE` to compare the actual hits in the databases and to turn this table from a design argument to a measured result.

| # | Business question | Model A path | A | Model B path | B |
|--:|:--|:--|--:|:--|--:|
| 1 | What is this batch's shelf life? | StockBatch→Product←PerishableProduct | 2 | StockBatch→Product:Perishable | 1 |
| 2 | Who sent the delivery that created this batch? | StockBatch→DeliveryLine→Delivery→Consignor←Supplier | 4 | StockBatch←Delivery→Supplier | 2 |
| 3 | Which batches were counted, with variance? | StockCount←BatchCount→StockBatch | 2 | StockCount→StockBatch | 1 |
| 4 | Which deliveries did this disruption delay? | SupplyDisruption←DisruptionImpact→Delivery | 2 | SupplyDisruption→Delivery | 1 |
| 5 | Which products are on this purchase order? | PurchaseOrder←PoLine→Product | 2 | PurchaseOrder→Product | 1 |
| 6 | Who authorised this write off, and how do we call them? | WriteOff→DutyManager→Employee←EmployeePhone | 3 | WriteOff→Employee (phones on node) | 1 |
| 7 | Trace a sale line back to its supplier | SaleLine→StockBatch→DeliveryLine→Delivery→Consignor←Supplier | 5 | SaleLine→StockBatch←Delivery→Supplier | 3 |
| | **Total** | | **20** | | **10** |

---

