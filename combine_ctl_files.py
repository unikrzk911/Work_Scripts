import csv
import json
import os
from pathlib import Path

# Folder containing txt files
input_folder = Path('/Users/unique.rajak/Downloads/Knight Cons')

output_file = input_folder / "combined.txt"  # or Path("combined.txt")

txt_files = [
    f for f in input_folder.glob("*.TXT")
    if f.resolve() != output_file.resolve()
]
print(txt_files)

with output_file.open("w", encoding="utf-8") as outfile:
    for txt_file in sorted(txt_files):
        print(f"Processing: {txt_file.name}")

        with txt_file.open("r", encoding="utf-8") as infile:
            outfile.write(f"{'=' * 80}\n")
            outfile.write(f"FILE: {txt_file.name}\n")
            outfile.write(f"{'=' * 80}\n")
            outfile.write(infile.read())
            outfile.write("\n\n")

print(f"Combined {len(txt_files)} files into {output_file}")
