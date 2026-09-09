import re
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


def find_matching_brace(text, opening_pos):
    depth = 0
    in_string = None
    in_comment = False
    escape = False

    for i in range(opening_pos, len(text)):
        char = text[i]
        next_char = text[i + 1] if i + 1 < len(text) else ""

        # Inside CSS comment
        if in_comment:
            if char == "*" and next_char == "/":
                in_comment = False
            continue

        # Start of CSS comment
        if not in_string and char == "/" and next_char == "*":
            in_comment = True
            continue

        # Inside string
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == in_string:
                in_string = None
            continue

        if char in ('"', "'"):
            in_string = char

        elif char == "{":
            depth += 1

        elif char == "}":
            depth -= 1

            if depth == 0:
                return i

    raise ValueError("Unmatched opening brace")


def process_css(css):
    selector_pattern = re.compile(
        r'(?<![\w-])\.interactive__972a0(?![\w-])'
    )

    ranges = []

    # Find every .interactive__972a0
    for match in selector_pattern.finditer(css):
        opening = css.find("{", match.end())

        if opening == -1:
            continue

        try:
            closing = find_matching_brace(css, opening)
        except ValueError:
            continue

        ranges.append((opening + 1, closing))

    # Merge overlapping ranges
    ranges.sort()
    merged = []

    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = (
                merged[-1][0],
                max(merged[-1][1], end)
            )
        else:
            merged.append((start, end))

    # Find transition declarations
    transition_pattern = re.compile(
        r'(?m)^([ \t]*)(transition\s*:\s*[^;{}]+;)'
    )

    result = css

    # Process backwards so positions don't change
    for start, end in reversed(merged):
        block = result[start:end]

        block = transition_pattern.sub(
            lambda m: f"{m.group(1)}/* {m.group(2)} */",
            block
        )

        result = result[:start] + block + result[end:]

    return result


def main():
    # Hide the main tkinter window
    root = tk.Tk()
    root.withdraw()

    # Ask the user to select a CSS file
    file_path = filedialog.askopenfilename(
        title="Select the CSS file to modify",
        filetypes=[
            ("CSS files", "*.css"),
            ("All files", "*.*")
        ]
    )

    # User clicked Cancel
    if not file_path:
        return

    path = Path(file_path)

    try:
        css = path.read_text(encoding="utf-8")
        modified_css = process_css(css)

        # Save as a new file
        output_path = path.with_name(
            path.stem + "_modified" + path.suffix
        )

        output_path.write_text(
            modified_css,
            encoding="utf-8"
        )

        messagebox.showinfo(
            "Complete",
            f"Done!\n\nModified file:\n{output_path}"
        )

    except Exception as e:
        messagebox.showerror(
            "Error",
            f"Something went wrong:\n\n{e}"
        )


if __name__ == "__main__":
    main()
