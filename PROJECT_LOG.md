# Project log: PRT563 Assessment 4, Group 12

This log records the team's progress, the decisions we made and why, the checks and reviews we ran, and who contributed what. It is kept with the code so every decision can be traced to the files it affected.

## Team and responsibilities

* **Uttam Shrestha (S396560):** data audit and regeneration, Task 2 import and indexes; Introduction, Methodology, Import and References; team channel; report assembly and submission
* **Sarin Uprety (S394012):** Task 4 centrality; Centrality section
* **Abhisek Tamang (S396739):** Task 3 queries, Model A versus Model B experiment; Executive Summary, Experiment, Queries and Conclusion; report charts; GitHub repository, this log and the final report upload
* **Yogesh Basnet (S394043):** Task 1 graph model, Task 5 similarity; Graph Model, Similarity and Discussion sections; formatting and the final number check

## Progress timeline

**11 Oct 2026, planning**
* Read the assessment brief and marking rubric; agreed to aim for the High Distinction criteria in every category.
* Agreed one shared folder structure (now this repository) and the Neo4j environment: Neo4j Desktop 2026.09, Cypher 25, GDS 2026.09.

**12 Oct 2026, data, model and import**
* Audited the Assessment 2 data against 24 business rules: 150 violations found (`00_data_preparation/audit_before_A2_data.txt`).
* Regenerated the transaction tables with a day by day simulation (seed 563): 16,786 rows, 0 violations (`audit_after_regenerated_data.txt`).
* Designed the naive Model A and the optimised Model B with seven optimisations (`02_graph_model/graph_model_spec.md`).
* Wrote `import.txt` with 18 uniqueness constraints, range, text, relationship and full text indexes, and verification checks.

**13 Oct 2026, implementation, queries and algorithms**
* Imported the data and verified it: 12,727 nodes, 27,681 relationships, all integrity and audit checks 0.
* Wrote and verified the four query use cases (`queries.txt`).
* Ran the centrality use case: eight configurations, evaluated with Spearman correlation against a ground truth of supply risk.
* Ran the similarity use case: four methods, evaluated on held out July and August baskets against a best seller baseline.
* Built Model A in a second database and benchmarked seven questions on both models (`model_a_experiment/benchmark_results.md`).
* First full draft of the report with three charts.

**14 Oct 2026, report review and repository**
* Replaced code text in the report with Neo4j screenshots, and the Q2 and Q4 result tables with full output screenshots.
* Agreed the division of work and wrote the individual contribution statements.
* Full review of the report against the brief and rubric; fixed line spacing, one overstated significance claim and two grammar slips.
* Split the algorithms script into `algorithms_task4.txt` and `algorithms_task5.txt`; prepared this repository.

## Decisions

1. **Regenerate the transaction data.** The Assessment 2 sample broke 24 business rules 150 times and was too small for graph algorithms. Master data was kept byte for byte; only transaction tables were regenerated, with the same columns. Justified in Report Section 2.
2. **Optimise the graph model (Model B).** Seven optimisations: subclass tables to labels, CONSIGNOR removed, phones as a list, associative and weak entities to relationships with properties, 1:1 delivery line collapsed, foreign key columns dropped. Each applied only after its precondition passed on the data.
3. **Keep four structures as nodes.** SupplyAgreement and SaleLine are hyperedges, Markdown is the target of a relationship (EER aggregation), and WriteOff is a business event auditors look up directly.
4. **Measure the optimisation, not just argue it.** Model A was built and both models were profiled; database hits were used instead of milliseconds because timings are noisy on a small graph.
5. **Fair timeliness measure in Q2.** On time is measured against each purchase order's required date, so distribution centre deliveries are not penalised by supplier lead times.
6. **Use Cypher 25 map comprehension** instead of the deprecated `apoc.map.fromPairs`, so the scripts need no APOC plugin.
7. **Betweenness left unweighted,** because GDS treats a weight as a distance.
8. **Evaluate algorithms against independent evidence:** Spearman correlation against supply risk computed from transactions (Task 4) and a temporal hold out split on 1 July (Task 5).
9. **Recommendations:** weighted Degree as the supply risk score with Betweenness as a chokepoint alarm; Jaccard Node Similarity for product bundles.

## Checks and reviews

* Every reported number was calculated independently in Python from the CSV files and compared with the Neo4j output.
* `import.txt` contains its own verification (Checks 1 to 5); all results are in `05_screenshots/task2_import_verification`.
* Both models returned identical answers for all seven benchmark questions.
* The report was reviewed against every requirement in the brief and every rubric criterion before paraphrasing.

## Individual contributions

The full statements, written by each member, are in the final section of the report (`06_report`). The commit history of this repository shows each member pushing the files for their own part.

## Team meetings

<!-- Add one entry per meeting: date, who attended, what was decided, actions and owners. -->
