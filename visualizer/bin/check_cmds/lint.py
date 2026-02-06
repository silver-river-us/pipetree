import subprocess
import sys


def main():
    result = subprocess.run(["ruff", "check", "."], capture_output=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
