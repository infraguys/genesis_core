#!/usr/bin/env python3

import sys


def main():
    if len(sys.argv) != 2:
        print("Usage: conver_multiline_to_oneline.py <file>")
        sys.exit(1)
    file_path = sys.argv[1]
    try:
        with open(file_path, "r") as file:
            content = file.read()
            # Replace newlines with spaces
            oneline_content = content.replace("\n", "\\n").replace('"', '\\"')
            print(oneline_content)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
