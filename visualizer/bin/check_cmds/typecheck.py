import subprocess
import sys


def main():
    result = subprocess.run(
        [
            "mypy",
            "boundary",
            "lib",
            "infra",
            "app.py",
            "config.py",
            "routes.py",
        ],
        capture_output=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
