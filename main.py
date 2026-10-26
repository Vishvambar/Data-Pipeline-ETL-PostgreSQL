"""
Interactive Command Line Interface (CLI) for Task 2: PostgreSQL ETL Data Pipeline.
Allows interactive execution of ETL steps, raw vs. clean comparison,
database querying, and visual analytics generation.
"""

import os
import sys
import pandas as pd
import sqlalchemy as sa
from tabulate import tabulate

from config import get_engine, DEFAULT_TARGET_TABLE
from etl_pipeline import run_pipeline, extract, transform, load, verify
from generate_dataset import generate_raw_csv
from visualize_pipeline import generate_pipeline_visualizations

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "raw_students_data.csv")


def clear_screen():
    print("\n" + "-" * 75)


def get_input(prompt: str, default: str = None) -> str:
    val = input(f"{prompt} " + (f"[{default}]: " if default else ": ")).strip()
    return val if val else (default if default is not None else "")


def print_table(df: pd.DataFrame, title: str = None, limit: int = 15):
    if title:
        print(f"\n--- {title} ---")
    if df.empty:
        print("[!] No records to display.")
        return
    print(tabulate(df.head(limit), headers="keys", tablefmt="fancy_grid", showindex=False))
    if len(df) > limit:
        print(f"... displaying first {limit} of {len(df)} total rows.")


def show_analytics():
    engine = get_engine()
    query = f"""
        SELECT 
            grade,
            COUNT(*) AS student_count,
            ROUND(AVG(age)::numeric, 1) AS avg_age,
            ROUND(AVG(attendance_pct)::numeric, 1) AS avg_attendance_pct,
            ROUND(SUM(fee_paid)::numeric, 2) AS total_fees_collected
        FROM {DEFAULT_TARGET_TABLE}
        GROUP BY grade
        ORDER BY student_count DESC;
    """
    with engine.connect() as conn:
        df = pd.read_sql_query(sa.text(query), conn)

    print("\n" + "=" * 80)
    print("      POSTGRESQL ANALYTICS: STUDENT METRICS BY GRADE")
    print("=" * 80)
    print(tabulate(df, headers="keys", tablefmt="fancy_grid", showindex=False))
    print("=" * 80 + "\n")


def main():
    clear_screen()
    print("=" * 75)
    print("   TASK 2: BUILD DATA PIPELINE WITH SQL / POSTGRESQL (ETL)")
    print("   Extract (CSV) -> Transform (Pandas) -> Load (SQLAlchemy/PostgreSQL)")
    print("=" * 75)

    if not os.path.exists(DATA_FILE):
        generate_raw_csv(DATA_FILE)

    while True:
        clear_screen()
        print("                     === PIPELINE CONTROL PANEL ===")
        print("  [1] Run Full ETL Pipeline  (Extract -> Clean -> Load -> Verify)")
        print("  [2] View Raw Source CSV    (Inspect dirty / uncleaned data)")
        print("  [3] View Cleaned Data in DB(Query 'students_cleaned' from PostgreSQL)")
        print("  [4] View Pipeline Analytics(Grade-wise stats & fee aggregations)")
        print("  [5] Generate Visual Charts (Matplotlib & Seaborn pipeline dashboard)")
        print("  [6] Reset / Re-seed CSV    (Regenerate raw test CSV dataset)")
        print("  [0] Exit")
        print("-" * 75)

        choice = get_input("Select an option (0-6)")
        if choice == "0":
            print("\nExiting Data Pipeline System. Goodbye!\n")
            break
        elif choice == "1":
            run_pipeline(DATA_FILE)
            input("\nPress Enter to continue...")
        elif choice == "2":
            raw_df = pd.read_csv(DATA_FILE)
            print_table(raw_df, title=f"RAW DATASET ({len(raw_df)} Rows)")
            input("\nPress Enter to continue...")
        elif choice == "3":
            engine = get_engine()
            with engine.connect() as conn:
                df = pd.read_sql_query(sa.text(f"SELECT * FROM {DEFAULT_TARGET_TABLE};"), conn)
            print_table(df, title=f"CLEANED DATA IN POSTGRESQL ({len(df)} Rows)")
            input("\nPress Enter to continue...")
        elif choice == "4":
            show_analytics()
            input("\nPress Enter to continue...")
        elif choice == "5":
            charts = generate_pipeline_visualizations()
            print(f"\n[✓] Generated {len(charts)} chart figures in visualizations/ folder.")
            input("\nPress Enter to continue...")
        elif choice == "6":
            generate_raw_csv(DATA_FILE)
            input("\nPress Enter to continue...")
        else:
            print("[!] Invalid option. Please enter 0 to 6.")


if __name__ == "__main__":
    main()
