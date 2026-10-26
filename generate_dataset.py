"""
Dataset Generator for ETL Pipeline Practical.
Generates a realistic raw CSV dataset containing intentional data quality issues:
- Duplicate records
- Missing/Null values
- Untrimmed whitespace
- Inconsistent casing
- Messy data formats (symbols in numbers, dirty date formats)
"""

import os
import pandas as pd


def generate_raw_csv(filepath: str = None) -> str:
    """Creates a raw dirty student dataset and saves it as CSV."""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), "data", "raw_students_data.csv")

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    raw_data = [
        # student_id, name, age, email, grade, attendance, enrollment_date, fee_paid
        (101, "  Aarav Sharma  ", 20, "Aarav.Sharma@College.Edu", "A", "88.5%", "2023-07-15", "₹25,000"),
        (102, "Priya Nair", 21, "priya.nair@college.edu", "A+", "92.0%", "2023-07-16", "25000"),
        (103, "Rohan Mehta", None, "rohan.mehta@college.edu", "B", "74.0%", "2023-07-18", "25000"),
        (104, "kavya iyer", 22, "KAVYA.IYER@COLLEGE.EDU", "A", None, "2023-07-20", "₹20,000"),
        (105, "Aditya Verma", 19, "aditya.verma@college.edu", "C+", "65.5%", "2023-08-01", "18000"),
        
        # Duplicate row of 101 to test deduplication
        (101, "  Aarav Sharma  ", 20, "Aarav.Sharma@College.Edu", "A", "88.5%", "2023-07-15", "₹25,000"),

        (106, "Vikram Rao", 23, "vikram.rao@college.edu", "A+", "95.0%", "2023-08-05", "25000"),
        (107, "Ananya Patel", 20, "ananya.patel@college.edu", "A", "89.0%", "2023-08-10", "25000"),
        (108, "Siddharth Joshi", None, "siddharth.j@college.edu", None, "58.0%", "2023-08-12", "15000"),
        (109, "Sneha Kulkarni", 21, "sneha.k@college.edu", "B+", "82.5%", "2023-08-15", "22000"),
        (110, "Rahul Deshmukh", 20, "rahul.d@college.edu", "B", "78.0%", "2023-08-18", "20000"),

        # Duplicate row of 106 to test deduplication
        (106, "Vikram Rao", 23, "vikram.rao@college.edu", "A+", "95.0%", "2023-08-05", "25000"),

        (111, "Neha Gupta", 22, "neha.gupta@college.edu", "A", "91.0%", "2023-08-20", "25000"),
        (112, "karan singhania", 21, "KARAN.S@COLLEGE.EDU", "B+", "80.0%", "2023-08-22", "22000"),
        (113, "Tanvi Bhatia", 20, "tanvi.b@college.edu", "A", "87.5%", "2023-08-25", None),
        (114, "Sunita Menon", None, "sunita.m@college.edu", "C", "52.0%", "2023-09-01", "12000"),
        (115, "Deepak Chopra", 22, "deepak.c@college.edu", "B", None, "2023-09-02", "20000"),
        (116, "Pooja Reddy", 19, "pooja.reddy@college.edu", "A+", "96.5%", "2023-09-05", "25000"),
        (117, "Arjun Kapoor", 23, "arjun.k@college.edu", "B+", "79.0%", "2023-09-08", "22000"),
        (118, "Meera Saxena", 20, "meera.s@college.edu", "A", "89.5%", "2023-09-10", "25000"),
        (119, "Varun Malhotra", 21, "varun.m@college.edu", "C+", "63.0%", "2023-09-12", "16000"),
        (120, "Divya Sen", 20, "divya.sen@college.edu", "A+", "94.0%", "2023-09-15", "25000"),

        # Row with missing critical ID
        (None, "Ghost Record", 25, "ghost@college.edu", "F", "10.0%", "2023-09-20", "0")
    ]

    columns = [
        "student_id", "name", "age", "email", "grade",
        "attendance", "enrollment_date", "fee_paid"
    ]

    df = pd.DataFrame(raw_data, columns=columns)
    df.to_csv(filepath, index=False)
    print(f"[✓] Generated raw dataset with {len(df)} rows at: {filepath}")
    return filepath


if __name__ == "__main__":
    generate_raw_csv()
