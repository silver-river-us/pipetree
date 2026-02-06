import subprocess
import sys

MIN_COVERAGE = 100


def main():
    result = subprocess.run(
        [
            "pytest",
            "--cov=lib",
            f"--cov-fail-under={MIN_COVERAGE}",
            "--cov-report=term-missing",
        ],
        capture_output=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
