"""
PostgreSQL ETL Data Pipeline.
Implements Extract, Transform, Load (ETL) and Verification functions
using Pandas, SQLAlchemy, and psycopg2 with comprehensive Logging.

Flow:
CSV File -> Extract -> Transform/Clean -> Load -> PostgreSQL -> Verify
"""

import os
import time
import pandas as pd
import numpy as np
import sqlalchemy as sa
from sqlalchemy.engine import Engine
from tabulate import tabulate
from typing import Tuple

from config import get_engine, setup_logger, DEFAULT_TARGET_TABLE

# Initialize standardized pipeline logger
logger = setup_logger("ETL_Pipeline")


# ==============================================================================
# 1. EXTRACT FUNCTION
# ==============================================================================
def extract(file_path: str) -> pd.DataFrame:
    """
    Extracts raw data from a source CSV file into a Pandas DataFrame.
    
    Args:
        file_path (str): Path to the source CSV file.
        
    Returns:
        pd.DataFrame: Raw extracted data.
    """
    logger.info(">>> STEP 1: EXTRACT - Starting CSV extraction from: %s", file_path)
    
    if not os.path.exists(file_path):
        logger.error("Extraction failed: Source file '%s' does not exist.", file_path)
        raise FileNotFoundError(f"Source file '{file_path}' not found.")
        
    try:
        df = pd.read_csv(file_path)
        logger.info(
            "Extract Success: Extracted %d rows and %d columns from CSV.",
            len(df), len(df.columns)
        )
        return df
    except Exception as e:
        logger.error("Extract Error: Failed to parse CSV file: %s", e)
        raise


# ==============================================================================
# 2. TRANSFORM FUNCTION
# ==============================================================================
def transform(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and transforms raw DataFrame:
    - Removes duplicate rows
    - Handles missing/null values (imputation & dropping unrecoverable records)
    - Strips whitespace and standardizes casing
    - Cleans messy formatting (currency symbols, percentages)
    - Enforces proper PostgreSQL-compatible data types
    - Appends audit/metadata timestamp column
    
    Args:
        df_raw (pd.DataFrame): Raw input DataFrame.
        
    Returns:
        pd.DataFrame: Cleaned and structured DataFrame ready for database loading.
    """
    logger.info(">>> STEP 2: TRANSFORM - Starting data cleaning & transformation...")
    df = df_raw.copy()
    initial_count = len(df)
    
    # 2.1 Deduplication
    dup_count = df.duplicated().sum()
    if dup_count > 0:
        df = df.drop_duplicates().reset_index(drop=True)
        logger.info("Transform [Deduplication]: Removed %d exact duplicate row(s).", dup_count)
    else:
        logger.info("Transform [Deduplication]: No duplicate rows found.")
        
    # 2.2 Drop records missing critical primary identifiers (student_id)
    missing_id_count = df['student_id'].isna().sum()
    if missing_id_count > 0:
        df = df.dropna(subset=['student_id']).reset_index(drop=True)
        logger.info("Transform [Integrity]: Dropped %d row(s) missing primary key 'student_id'.", missing_id_count)
        
    # 2.3 String Cleaning & Standardization (Whitespace & Casing)
    if 'name' in df.columns:
        df['name'] = df['name'].astype(str).str.strip().str.title()
    if 'email' in df.columns:
        df['email'] = df['email'].astype(str).str.strip().str.lower()
    if 'grade' in df.columns:
        df['grade'] = df['grade'].fillna('Ungraded').astype(str).str.strip().str.upper()
        
    # 2.4 Numeric & Currency Formatting: 'attendance' (strip %, cast to float)
    if 'attendance' in df.columns:
        df['attendance_pct'] = (
            df['attendance']
            .astype(str)
            .str.replace('%', '', regex=False)
            .str.strip()
        )
        df['attendance_pct'] = pd.to_numeric(df['attendance_pct'], errors='coerce')
        # Impute missing attendance with column mean
        avg_att = round(df['attendance_pct'].mean(), 1)
        missing_att = df['attendance_pct'].isna().sum()
        if missing_att > 0:
            df['attendance_pct'] = df['attendance_pct'].fillna(avg_att)
            logger.info("Transform [Null Handling]: Imputed %d missing attendance with mean (%.1f%%).", missing_att, avg_att)
        df.drop(columns=['attendance'], inplace=True, errors='ignore')
        
    # 2.5 Currency Formatting: 'fee_paid' (strip ₹, $, comma, cast to float)
    if 'fee_paid' in df.columns:
        df['fee_paid'] = (
            df['fee_paid']
            .astype(str)
            .str.replace('₹', '', regex=False)
            .str.replace('$', '', regex=False)
            .str.replace(',', '', regex=False)
            .str.strip()
        )
        df['fee_paid'] = pd.to_numeric(df['fee_paid'], errors='coerce')
        missing_fee = df['fee_paid'].isna().sum()
        if missing_fee > 0:
            median_fee = float(df['fee_paid'].median())
            df['fee_paid'] = df['fee_paid'].fillna(median_fee)
            logger.info("Transform [Null Handling]: Imputed %d missing fee_paid with median (₹%.2f).", missing_fee, median_fee)

    # 2.6 Impute missing age with median age
    if 'age' in df.columns:
        df['age'] = pd.to_numeric(df['age'], errors='coerce')
        missing_age = df['age'].isna().sum()
        if missing_age > 0:
            median_age = int(round(df['age'].median()))
            df['age'] = df['age'].fillna(median_age)
            logger.info("Transform [Null Handling]: Imputed %d missing age values with median (%d years).", missing_age, median_age)

    # 2.7 Date Parsing
    if 'enrollment_date' in df.columns:
        df['enrollment_date'] = pd.to_datetime(df['enrollment_date'], errors='coerce').dt.date

    # 2.8 Enforce Explicit Schema Data Types
    type_conversions = {
        'student_id': 'int64',
        'age': 'int32',
        'attendance_pct': 'float64',
        'fee_paid': 'float64',
        'name': 'string',
        'email': 'string',
        'grade': 'string'
    }
    for col, dtype in type_conversions.items():
        if col in df.columns:
            df[col] = df[col].astype(dtype)

    # 2.9 Add Audit Metadata
    df['loaded_at'] = pd.Timestamp.now()

    final_count = len(df)
    logger.info(
        "Transform Success: Cleaned data from %d raw rows down to %d valid rows (Net removed: %d).",
        initial_count, final_count, (initial_count - final_count)
    )
    return df


# ==============================================================================
# 3. LOAD FUNCTION
# ==============================================================================
def load(
    df: pd.DataFrame,
    table_name: str = DEFAULT_TARGET_TABLE,
    engine: Engine = None,
    if_exists: str = "replace"
) -> int:
    """
    Connects to PostgreSQL using SQLAlchemy engine and writes DataFrame to target table.
    Creates table if it does not exist.
    
    Args:
        df (pd.DataFrame): Transformed DataFrame.
        table_name (str): Target table name in PostgreSQL.
        engine (Engine): SQLAlchemy engine instance (defaults to config.get_engine()).
        if_exists (str): Action if table exists ('replace', 'append', 'fail').
        
    Returns:
        int: Number of rows successfully written.
    """
    logger.info(">>> STEP 3: LOAD - Connecting to PostgreSQL via SQLAlchemy...")
    if engine is None:
        engine = get_engine()

    try:
        start_time = time.time()
        # Define SQLAlchemy explicit column types if needed
        dtype_mapping = {
            'student_id': sa.Integer(),
            'name': sa.VARCHAR(100),
            'age': sa.Integer(),
            'email': sa.VARCHAR(150),
            'grade': sa.VARCHAR(10),
            'attendance_pct': sa.Float(),
            'enrollment_date': sa.Date(),
            'fee_paid': sa.Numeric(10, 2),
            'loaded_at': sa.TIMESTAMP()
        }

        with engine.begin() as connection:
            df.to_sql(
                name=table_name,
                con=connection,
                if_exists=if_exists,
                index=False,
                dtype=dtype_mapping
            )
            
        elapsed = time.time() - start_time
        logger.info(
            "Load Success: Written %d records to PostgreSQL table '%s' in %.3f seconds.",
            len(df), table_name, elapsed
        )
        return len(df)
    except Exception as e:
        logger.error("Load Error: Failed loading DataFrame to table '%s': %s", table_name, e)
        raise


# ==============================================================================
# 4. VERIFY FUNCTION
# ==============================================================================
def verify(table_name: str = DEFAULT_TARGET_TABLE, engine: Engine = None) -> pd.DataFrame:
    """
    Verifies data in PostgreSQL by querying back the table and printing summary statistics.
    
    Args:
        table_name (str): Table name in PostgreSQL.
        engine (Engine): SQLAlchemy engine instance.
        
    Returns:
        pd.DataFrame: Retrieved DataFrame from PostgreSQL.
    """
    logger.info(">>> STEP 4: VERIFICATION - Querying PostgreSQL database to verify loaded rows...")
    if engine is None:
        engine = get_engine()

    query = sa.text(f"SELECT * FROM {table_name} ORDER BY student_id ASC;")
    
    with engine.connect() as conn:
        verified_df = pd.read_sql_query(query, conn)

    row_count = len(verified_df)
    logger.info("Verification Success: Successfully retrieved %d rows from PostgreSQL table '%s'!", row_count, table_name)
    
    # Print formatted sample records to console
    print("\n" + "=" * 90)
    print(f"       POSTGRESQL TABLE VERIFICATION PREVIEW: '{table_name}' ({row_count} Total Rows)")
    print("=" * 90)
    preview = verified_df.head(10).copy()
    if 'fee_paid' in preview.columns:
        preview['fee_paid'] = preview['fee_paid'].apply(lambda v: f"₹{float(v):,.2f}")
    if 'attendance_pct' in preview.columns:
        preview['attendance_pct'] = preview['attendance_pct'].apply(lambda v: f"{float(v):.1f}%")
    print(tabulate(preview, headers="keys", tablefmt="fancy_grid", showindex=False))
    print("=" * 90 + "\n")

    return verified_df


# ==============================================================================
# 5. PIPELINE DRIVER FUNCTION
# ==============================================================================
def run_pipeline(
    csv_file: str,
    table_name: str = DEFAULT_TARGET_TABLE
) -> Tuple[pd.DataFrame, int]:
    """
    Orchestrates the entire ETL workflow:
    CSV File -> EXTRACT -> TRANSFORM -> LOAD -> PostgreSQL -> VERIFY
    
    Args:
        csv_file (str): Path to input raw CSV file.
        table_name (str): Target table name in PostgreSQL.
        
    Returns:
        Tuple[pd.DataFrame, int]: (verified_df, loaded_row_count)
    """
    total_start = time.time()
    logger.info("=" * 70)
    logger.info("STARTING POSTGRESQL DATA PIPELINE EXECUTION (ETL WORKFLOW)")
    logger.info("=" * 70)
    
    try:
        engine = get_engine()
        
        # 1. EXTRACT
        raw_df = extract(csv_file)
        
        # 2. TRANSFORM
        cleaned_df = transform(raw_df)
        
        # 3. LOAD
        rows_loaded = load(cleaned_df, table_name=table_name, engine=engine, if_exists="replace")
        
        # 4. VERIFY
        verified_df = verify(table_name=table_name, engine=engine)
        
        total_time = time.time() - total_start
        logger.info("=" * 70)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY in %.3f seconds!", total_time)
        logger.info("Summary: %d extracted -> %d cleaned -> %d loaded into '%s'.",
                    len(raw_df), len(cleaned_df), rows_loaded, table_name)
        logger.info("=" * 70)
        
        return verified_df, rows_loaded
    except Exception as e:
        logger.error("PIPELINE FAILED with error: %s", e)
        raise


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    source_csv = os.path.join(current_dir, "data", "raw_students_data.csv")
    
    if not os.path.exists(source_csv):
        from generate_dataset import generate_raw_csv
        generate_raw_csv(source_csv)
        
    run_pipeline(source_csv)
