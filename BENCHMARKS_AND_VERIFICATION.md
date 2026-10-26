# Production Verification & Pipeline Audit Report
## Automated Python & PostgreSQL ETL Data Pipeline

- **Pipeline Type**: Automated Batch ETL (Extract, Transform, Load)
- **Database Engine**: PostgreSQL 18 via SQLAlchemy connection pooling
- **Data Manipulation**: Pandas (Statistical Imputation, Deduplication, Formatting)
- **Observability**: Structured Logging with timestamped stage tracing

---

## 1. ETL Architecture Flowchart

```text
[ Raw CSV File ]  -> 23 Records with duplicates, missing values & messy formatting
        │
   ( EXTRACT )    -> Reads CSV into Pandas DataFrame (Logged: 23 rows)
        │
  ( TRANSFORM )   -> Deduplicates (2 removed) -> Drops missing ID (1 removed)
                  -> Imputes missing age, attendance, fee -> Normalizes text
        │
    ( LOAD )      -> Connects via SQLAlchemy Engine -> Writes to PostgreSQL
        │
 [ PostgreSQL ]   -> Table: students_cleaned (20 clean records)
        │
   ( VERIFY )     -> SQL SELECT query reads back records & logs verification
```

---

## 2. Pipeline Execution Console Logs (Traceability)

```text
2026-10-26 23:51:22 | INFO    | STARTING POSTGRESQL DATA PIPELINE EXECUTION (ETL WORKFLOW)
2026-10-26 23:51:22 | INFO    | >>> STEP 1: EXTRACT - Starting CSV extraction from: data/raw_students_data.csv
2026-10-26 23:51:22 | INFO    | Extract Success: Extracted 23 rows and 8 columns from CSV.
2026-10-26 23:51:22 | INFO    | >>> STEP 2: TRANSFORM - Starting data cleaning & transformation...
2026-10-26 23:51:22 | INFO    | Transform [Deduplication]: Removed 2 exact duplicate row(s).
2026-10-26 23:51:22 | INFO    | Transform [Integrity]: Dropped 1 row(s) missing primary key 'student_id'.
2026-10-26 23:51:22 | INFO    | Transform [Null Handling]: Imputed 2 missing attendance with mean (80.8%).
2026-10-26 23:51:22 | INFO    | Transform [Null Handling]: Imputed 1 missing fee_paid with median (₹22000.00).
2026-10-26 23:51:22 | INFO    | Transform [Null Handling]: Imputed 3 missing age values with median (21 years).
2026-10-26 23:51:22 | INFO    | Transform Success: Cleaned data from 23 raw rows down to 20 valid rows (Net removed: 3).
2026-10-26 23:51:22 | INFO    | >>> STEP 3: LOAD - Connecting to PostgreSQL via SQLAlchemy...
2026-10-26 23:51:23 | INFO    | Load Success: Written 20 records to PostgreSQL table 'students_cleaned' in 0.165 seconds.
2026-10-26 23:51:23 | INFO    | >>> STEP 4: VERIFICATION - Querying PostgreSQL database to verify loaded rows...
2026-10-26 23:51:23 | INFO    | Verification Success: Successfully retrieved 20 rows from PostgreSQL table 'students_cleaned'!
2026-10-26 23:51:23 | INFO    | PIPELINE COMPLETED SUCCESSFULLY in 0.654 seconds!
```

---

## 3. Database Verification: Sample Records in PostgreSQL

Output of verification query `SELECT * FROM students_cleaned ORDER BY student_id ASC LIMIT 8;`:

```text
╒══════════════╤═════════════════╤═══════╤══════════════════════════╤══════════╤═══════════════════╤════════════╤══════════════════╕
│   student_id │ name            │   age │ email                    │ grade    │ enrollment_date   │ fee_paid   │ attendance_pct   │
╞══════════════╪═════════════════╪═══════╪══════════════════════════╪══════════╪═══════════════════╪════════════╪══════════════════╡
│          101 │ Aarav Sharma    │    20 │ aarav.sharma@college.edu │ A        │ 2023-07-15        │ ₹25,000.00 │ 88.5%            │
│          102 │ Priya Nair      │    21 │ priya.nair@college.edu   │ A+       │ 2023-07-16        │ ₹25,000.00 │ 92.0%            │
│          103 │ Rohan Mehta     │    21 │ rohan.mehta@college.edu  │ B        │ 2023-07-18        │ ₹25,000.00 │ 74.0%            │
│          104 │ Kavya Iyer      │    22 │ kavya.iyer@college.edu   │ A        │ 2023-07-20        │ ₹20,000.00 │ 80.8%            │
│          105 │ Aditya Verma    │    19 │ aditya.verma@college.edu │ C+       │ 2023-08-01        │ ₹18,000.00 │ 65.5%            │
│          106 │ Vikram Rao      │    23 │ vikram.rao@college.edu   │ A+       │ 2023-08-05        │ ₹25,000.00 │ 95.0%            │
│          107 │ Ananya Patel    │    20 │ ananya.patel@college.edu │ A        │ 2023-08-10        │ ₹25,000.00 │ 89.0%            │
│          108 │ Siddharth Joshi │    21 │ siddharth.j@college.edu  │ UNGRADED │ 2023-08-12        │ ₹15,000.00 │ 58.0%            │
╘══════════════╧═════════════════╧═══════╧══════════════════════════╧══════════╧═══════════════════╧════════════╧══════════════════╛
```

### Aggregate SQL Verification
```sql
SELECT COUNT(*) AS total_students, ROUND(AVG(attendance_pct)::numeric, 1) AS avg_attendance, 
       ROUND(SUM(fee_paid)::numeric, 2) AS total_fees FROM students_cleaned;
-- Result: total_students = 20 | avg_attendance = 80.8% | total_fees = ₹434,000.00
```

---

## 4. Evaluator Quick Q&A (Viva Summary)

- **Q1: Why use SQLAlchemy alongside Pandas instead of raw psycopg2 queries?**  
  *Answer:* SQLAlchemy provides a high-level DB-API abstraction (`Engine`), dialect handling, and automated DataFrame-to-SQL mapping (`df.to_sql()`), generating the table schema and handling data type mapping automatically.
- **Q2: How does the pipeline handle null/missing values during Transform?**  
  *Answer:* Numerical attributes (`age`, `fee_paid`) are imputed using column medians, continuous metrics (`attendance`) using column means, and categorical values (`grade`) filled with `'UNGRADED'`. Records missing essential unique identifiers (`student_id`) are dropped.
- **Q3: How does the pipeline ensure traceability?**  
  *Answer:* Using Python's standard `logging` library configured with timestamps and log levels (`INFO`, `ERROR`) to record row counts at each stage (23 extracted $\rightarrow$ 20 cleaned $\rightarrow$ 20 loaded) and audit timestamps (`loaded_at`).
- **Q4: How do you verify that data is accurately loaded into PostgreSQL?**  
  *Answer:* The `verify()` function immediately queries back the table using `pd.read_sql_query()`, checking the row count against the loaded count and verifying aggregate calculations.

---
**Verified & Tested by:** Student  
**System Status:** Operational | Pipeline Verified | 100% Tests Passing
