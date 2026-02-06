import subprocess
import sys


def main():
    result = subprocess.run(
        [
            "mypy",
            "visualizer/boundary",
            "visualizer/lib",
            "visualizer/infra",
            "visualizer/app.py",
            "visualizer/config.py",
            "visualizer/routes.py",
        ],
        capture_output=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
