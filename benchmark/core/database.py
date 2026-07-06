import sqlite3
from benchmark.config import DATABASE_PATH


def get_connection():
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(str(DATABASE_PATH))


def initialize_database():
    """Initializes the SQLite database and dynamically migrates columns."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create experiments table mapping to the Experiment dataclass and CSV headers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            workload TEXT NOT NULL,
            strategy TEXT NOT NULL,
            repetition INTEGER,
            dockerfile TEXT NOT NULL,
            image_tag TEXT NOT NULL,
            build_type TEXT NOT NULL,
            build_time REAL DEFAULT 0.0,
            image_size_mb REAL DEFAULT 0.0,
            layer_count INTEGER,
            startup_time_seconds REAL,
            critical_vulnerabilities INTEGER,
            high_vulnerabilities INTEGER,
            medium_vulnerabilities INTEGER,
            low_vulnerabilities INTEGER,
            unknown_vulnerabilities INTEGER,
            build_status TEXT,
            startup_status TEXT,
            security_scan_status TEXT,
            overall_status TEXT,
            notes TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    
    # Check for missing columns (migration)
    cursor.execute("PRAGMA table_info(experiments)")
    columns = [row[1] for row in cursor.fetchall()]
    
    required_columns = {
        "run_id": "TEXT",
        "repetition": "INTEGER",
        "layer_count": "INTEGER",
        "startup_time_seconds": "REAL",
        "critical_vulnerabilities": "INTEGER",
        "high_vulnerabilities": "INTEGER",
        "medium_vulnerabilities": "INTEGER",
        "low_vulnerabilities": "INTEGER",
        "unknown_vulnerabilities": "INTEGER",
        "build_status": "TEXT",
        "startup_status": "TEXT",
        "security_scan_status": "TEXT",
        "overall_status": "TEXT"
    }
    
    for col_name, col_type in required_columns.items():
        if col_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE experiments ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass
                
    conn.commit()
    conn.close()