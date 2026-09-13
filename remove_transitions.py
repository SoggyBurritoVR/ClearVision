import re
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


TARGET = ".interactive__972a0"


def find_matching_brace(text, opening):
    """Find the closing brace matching the given opening brace."""

    depth = 0
    in_string = None
    in_comment = False
    escape = False

    i = opening

    while i < len(text):
        char = text[i]
        next_char = text[i + 1] if i + 1 < len(text) else ""

        # CSS comment
        if in_comment:
            if char == "*" and next_char == "/":
                in_comment = False
                i += 2
                continue

            i += 1
            continue

        # Start CSS comment
        if not in_string and char == "/" and next_char == "*":
            in_comment = True
            i += 2
            continue

        # String
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == in_string:
                in_string = None

            i += 1
            continue

        # Start string
        if char in ("'", '"'):
            in_string = char
            i += 1
            continue

        if char == "{":
            depth += 1

        elif char == "}":
            depth -= 1

            if depth == 0:
                return i

        i += 1

    raise ValueError("Unmatched opening brace")


def find_target_rules(css):
    """
    Find CSS rules whose selector contains TARGET.

    Examples:

        .interactive__972a0
        .interactive__972a0::before
        .interactive__972a0::after
        .interactive__972a0:hover
        .foo .interactive__972a0::before
    """

    rules = []

    # Match the target anywhere before an opening brace.
    pattern = re.compile(
        re.escape(TARGET) + r"(?=[^{}]*\{)"
    )

    for match in pattern.finditer(css):

        # Find the opening brace belonging to this selector.
        opening = css.find("{", match.end())

        if opening == -1:
            continue

        try:
            closing = find_matching_brace(css, opening)
        except ValueError:
            continue

        rules.append((opening, closing))

    return rules


def modify_rule(css, opening, closing):
    """
    Modify ONLY direct-child transition declarations
    inside one CSS rule.
    """

    block = css[opening + 1:closing]

    result = []
    last = 0

    depth = 0
    in_string = None
    in_comment = False
    escape = False

    # Matches:
    #
    # transition: all 0.15s ease-in-out;
    #
    # It deliberately does NOT match:
    #
    # transition-property:
    # transition-duration:
    # transition-delay:
    #
    transition_pattern = re.compile(
        r"transition\s*:\s*[^;{}]+;"
    )

    i = 0
    changes = 0

    while i < len(block):
        char = block[i]
        next_char = block[i + 1] if i + 1 < len(block) else ""

        # Comment
        if in_comment:
            if char == "*" and next_char == "/":
                in_comment = False
                i += 2
                continue

            i += 1
            continue

        # Start comment
        if not in_string and char == "/" and next_char == "*":
            in_comment = True
            i += 2
            continue

        # String
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == in_string:
                in_string = None

            i += 1
            continue

        # Start string
        if char in ("'", '"'):
            in_string = char
            i += 1
            continue

        # Nested block
        if char == "{":
            depth += 1
            i += 1
            continue

        if char == "}":
            depth -= 1
            i += 1
            continue

        # Only modify transitions directly inside the target rule.
        if depth == 0:

            match = transition_pattern.match(block, i)

            if match:
                # Make sure this is actually a CSS declaration,
                # rather than part of another word.
                before = block[i - 1] if i > 0 else ""

                if not (before.isalnum() or before in "_-"):
                    result.append(block[last:i])

                    original = match.group(0)

                    # Preserve indentation.
                    line_start = block.rfind("\n", 0, i) + 1
                    indentation = block[line_start:i]

                    # If there is only whitespace before transition,
                    # preserve it inside the comment.
                    if indentation.strip() == "":
                        replacement = (
                            indentation
                            + "/* "
                            + original
                            + " */"
                        )
                    else:
                        # Same-line declaration.
                        replacement = (
                            "/* "
                            + original
                            + " */"
                        )

                    result.append(replacement)

                    i = match.end()
                    last = i
                    changes += 1
                    continue

        i += 1

    result.append(block[last:])

    return "".join(result), changes


def process_css(css):
    """Process every matching .interactive__972a0 rule."""

    rules = find_target_rules(css)

    total_changes = 0

    # Work backwards so positions remain valid.
    for opening, closing in reversed(rules):

        modified, changes = modify_rule(
            css,
            opening,
            closing
        )

        css = (
            css[:opening + 1]
            + modified
            + css[closing:]
        )

        total_changes += changes

    return css, len(rules), total_changes


def main():

    # Create hidden Tkinter window.
    root = tk.Tk()
    root.withdraw()

    # Select CSS file.
    file_path = filedialog.askopenfilename(
        title="Select the CSS file to modify",
        filetypes=[
            ("CSS files", "*.css"),
            ("All files", "*.*")
        ]
    )

    if not file_path:
        return

    path = Path(file_path)

    try:

        # Read CSS.
        css = path.read_text(encoding="utf-8")

        # Process CSS.
        modified_css, rule_count, transition_count = process_css(css)

        # Output filename.
        output_path = path.with_name(
            path.stem + "_modified" + path.suffix
        )

        # Save.
        output_path.write_text(
            modified_css,
            encoding="utf-8"
        )

        # Report.
        messagebox.showinfo(
            "Complete",
            (
                f"Done!\n\n"
                f"Matching rules found: {rule_count}\n"
                f"Transitions disabled: {transition_count}\n\n"
                f"Modified file:\n{output_path}"
            )
        )

    except Exception as e:

        messagebox.showerror(
            "Error",
            f"Something went wrong:\n\n{e}"
        )


if __name__ == "__main__":
    main()