# PRT563 Advanced Data Management, Assessment 4, Group 12

**Migrating a perishable supply chain database to Neo4j**

This repository holds everything needed to rebuild and check our Assessment 4 work: the CSV data, the Cypher scripts, the evidence screenshots and the final report. It continues our Assessment 2 relational database for a supermarket chain with four Northern Territory stores (Darwin City, Casuarina, Palmerston and Alice Springs).

## Required submission files

* `03_cypher/import.txt` : Cypher scripts for Task 2 (constraints, indexes, nodes, relationships, verification checks)
* `01_csv/` : all 29 CSV files needed to build the graph
* `03_cypher/queries.txt` : Cypher scripts for the four Task 3 query use cases

## Repository structure

```
00_data_preparation/     data audit (24 business rules) and the reproducible data generator
    a2_original_csv/     the 29 tables exported from the Assessment 2 database
01_csv/                  the 29 CSV files imported into Neo4j (16,786 rows)
02_graph_model/          graph data model diagram (.png and .drawio) and specification
03_cypher/
    import.txt           Task 2: migration and indexes
    queries.txt          Task 3: four query use cases
    algorithms_task4.txt Task 4: centrality use case (Graph Data Science)
    algorithms_task5.txt Task 5: similarity use case (Graph Data Science)
    model_a_experiment/  naive Model A import and the Model A versus Model B benchmark
05_screenshots/          evidence that every script ran, one folder per task
06_report/               final report (.docx) and the three report charts
PROJECT_LOG.md           decisions, progress, reviews and individual contributions
```

## How to reproduce

Tested on Neo4j Desktop 2026.09 (Cypher 25) with the Graph Data Science 2026.09 plugin.

1. Create a local instance and copy all 29 files from `01_csv/` into its `import` folder (Neo4j Desktop, instance menu, Open, Instance folder, import).
2. Run `03_cypher/import.txt` part by part. Every statement uses MERGE on a constrained key, so it is safe to run again. Check 3 should return 12,727 nodes and 27,681 relationships, and Checks 4 and 4b should return only zeros.
3. Run each query in `03_cypher/queries.txt` on its own.
4. Install the Graph Data Science plugin, then run `algorithms_task4.txt` and `algorithms_task5.txt` in order. Each starts by building an in memory projection.
5. Optional: build Model A in a second database with `model_a_experiment/importA.txt` and compare it with `benchmark.txt`.

To regenerate the data and rerun the audit (Python 3):

```
cd 00_data_preparation
python3 generate.py a2_original_csv ../01_csv
python3 audit.py ../01_csv
python3 expected_counts.py ../01_csv
```

## Key results

* Model B (optimised) holds the same data as the naive Model A in 24% fewer nodes and 13% fewer relationships, and needs 33.1% fewer database hits across seven benchmark questions.
* Weighted centrality ranks real supply risk with a Spearman correlation of 0.936 and identifies Berrimah Regional DC as the most critical node.
* Jaccard Node Similarity predicts joint purchases in unseen baskets about three times better than chance.

## Team

* Uttam Shrestha (S396560): data audit and regeneration, Task 2 import, report assembly and submission
* Sarin Uprety (S394012): Task 4 centrality
* Abhisek Tamang (S396739): Task 3 queries, Model A versus Model B experiment, report charts, repository and project log
* Yogesh Basnet (S394043): Task 1 graph model, Task 5 similarity, formatting and number checks

Charles Darwin University, October 2026.
