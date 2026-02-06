import subprocess
import sys


def main():
    commands = [
        (["python", "-m", "bin.check_cmds.arch"], "Architecture"),
        (["python", "-m", "bin.check_cmds.style"], "Style"),
        (["ruff", "check", "."], "Lint"),
        (["python", "-m", "bin.check_cmds.typecheck"], "Type check"),
        (["python", "-m", "bin.check_cmds.test"], "Tests"),
    ]

    for cmd, name in commands:
        print(f"\n=== {name} ===")
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"\n{name} failed!")
            sys.exit(result.returncode)

    print("\n=== All checks passed ===")


if __name__ == "__main__":
    main()
