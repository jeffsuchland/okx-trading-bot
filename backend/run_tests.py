"""Helper script to run tests and capture output."""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/exchange/test_okx_client.py", "-v", "--tb=short"],
    capture_output=True,
    text=True,
)
print(result.stdout)
print(result.stderr)
print(f"Return code: {result.returncode}")
