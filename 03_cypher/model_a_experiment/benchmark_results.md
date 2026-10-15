# Model A versus Model B benchmark results

Measured in Neo4j Desktop 2026.09 (Cypher 25, PIPELINED runtime) with PROFILE.
Database hits are deterministic. Times are from the second run of each query
and vary by a few milliseconds between runs, so they are indicative only.
Screenshots: 05_screenshots/model_a_vs_b/B1_modelA.png to B7_modelB.png.

| Q | Business question | Optimisation | Hops A | Hops B | db hits A | db hits B | Reduction | ms A | ms B |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| B1 | Shelf life of every perishable batch | O1 | 2 | 1 | 4,606 | 4,556 | 1.1% | 27 | 25 |
| B2 | Supplier that consigned each batch | O2, O6 | 4 | 2 | 11,806 | 6,542 | 44.6% | 41 | 15 |
| B3 | Stock count variance | O4 | 2 | 1 | 3,197 | 1,617 | 49.4% | 2 | 4 |
| B4 | Deliveries delayed by each disruption | O4 | 2 | 1 | 250 | 115 | 54.0% | 2 | 3 |
| B5 | Five most ordered products | O5 | 2 | 1 | 16,764 | 7,474 | 55.4% | 32 | 3 |
| B6 | Write off authorisers and their phones | O1, O3 | 3 | 1 | 2,888 | 1,615 | 44.1% | 7 | 27 |
| B7 | Units sold traced to consigning supplier | O2, O6 | 5 | 3 | 29,483 | 24,227 | 17.8% | 19 | 7 |
| **Total** | | | **20** | **10** | **68,994** | **46,146** | **33.1%** | **130** | **84** |
