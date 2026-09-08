from pathlib import Path

INPUT_FOLDER = Path('/Users/unique.rajak/Downloads/Knight Cons')


def combine_txt_files(input_folder: Path) -> Path:
    output_file = input_folder / "combined.txt"
    txt_files = sorted(
        f for f in input_folder.glob("*.TXT")
        if f.resolve() != output_file.resolve()
    )

    with output_file.open("w", encoding="utf-8") as outfile:
        for txt_file in txt_files:
            print(f"Processing: {txt_file.name}")
            outfile.write(f"{'=' * 80}\n")
            outfile.write(f"FILE: {txt_file.name}\n")
            outfile.write(f"{'=' * 80}\n")
            outfile.write(txt_file.read_text(encoding="utf-8"))
            outfile.write("\n\n")

    print(f"Combined {len(txt_files)} files into {output_file}")
    return output_file


if __name__ == "__main__":
    combine_txt_files(INPUT_FOLDER)
