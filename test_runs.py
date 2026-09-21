import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / "server" / ".env")
except ImportError:
    pass

import sys
sys.path.append(str(Path(__file__).parent / "server"))
from persistence import save_pipeline_run

run_id = save_pipeline_run(
    run_type="full_pipeline",
    config={"test": True},
    results={"dummy": "result"},
    score=0.95,
    email_count=10
)
print("Returned run_id:", run_id)
