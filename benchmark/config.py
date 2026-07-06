from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT_DIR / "data"
DATABASE_DIR = DATA_DIR / "database"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
FIGURES_DIR = DATA_DIR / "figures"
SYSTEM_DIR = DATA_DIR / "system"

BUILD_LOGS_DIR = RAW_DIR / "build_logs"
TRIVY_DIR = RAW_DIR / "trivy"
REGISTRY_DIR = RAW_DIR / "registry"

# Ensure all folders exist
for folder in [DATABASE_DIR, RAW_DIR, PROCESSED_DIR, FIGURES_DIR, BUILD_LOGS_DIR, TRIVY_DIR, REGISTRY_DIR, SYSTEM_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "containerbench.db"
CSV_EXPORT_PATH = RAW_DIR / "experiments.csv"
SYSTEM_ENV_PATH = SYSTEM_DIR / "environment.json"
PROCESSED_SUMMARY_PATH = PROCESSED_DIR / "benchmark_summary.csv"
PROCESSED_STATS_PATH = PROCESSED_DIR / "statistics.csv"
