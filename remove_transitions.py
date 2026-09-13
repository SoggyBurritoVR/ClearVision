import re
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


TARGET = "972a0"


def find_matching_brace(text, opening):
    """Find the closing brace matching opening {."""

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
            else:
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

        if char == "{":
            depth += 1

        elif char == "}":
            depth -= 1

            if depth == 0:
                return i

        i += 1

    return -1


def find_rules_containing_target(css):
    """
    Find every CSS rule containing '972a0' anywhere
    in its selector.

    Works on completely minified one-line CSS.
    """

    rules = []

    search_from = 0

    while True:

        target_pos = css.find(TARGET, search_from)

        if target_pos == -1:
            break

        # ---------------------------------------------------------
        # Find the opening { after 972a0.
        # ---------------------------------------------------------

        i = target_pos + len(TARGET)

        in_string = None
        in_comment = False
        escape = False

        opening = -1

        while i < len(css):

            char = css[i]
            next_char = (
                css[i + 1]
                if i + 1 < len(css)
                else ""
            )

            # Comment
            if in_comment:

                if char == "*" and next_char == "/":
                    in_comment = False
                    i += 2
                else:
                    i += 1

                continue

            # Start comment
            if (
                not in_string
                and char == "/"
                and next_char == "*"
            ):
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

            # Another rule boundary before {
            if char == "}":
                break

            # Found opening brace
            if char == "{":
                opening = i
                break

            i += 1

        if opening == -1:
            search_from = target_pos + len(TARGET)
            continue

        # Find matching closing brace.
        closing = find_matching_brace(
            css,
            opening
        )

        if closing == -1:
            search_from = target_pos + len(TARGET)
            continue

        rules.append(
            (
                target_pos,
                opening,
                closing
            )
        )

        # Continue after this rule.
        search_from = closing + 1

    return rules


def disable_transitions_and_animations(block):
    """
    Comment out direct transition and animation declarations.

    Handles:

        transition:all .2s;

        transition:all .2s

        animation:foo .3s ease-in-out;

        animation:foo .3s ease-in-out

    Works with minified CSS.
    """

    result = []
    last = 0

    i = 0
    depth = 0

    in_string = None
    in_comment = False
    escape = False

    changes = 0

    # Properties we want to kill.
    properties = (
        "transition",
        "animation",
    )

    while i < len(block):

        char = block[i]
        next_char = (
            block[i + 1]
            if i + 1 < len(block)
            else ""
        )

        # ---------------------------------------------------------
        # Comment
        # ---------------------------------------------------------

        if in_comment:

            if char == "*" and next_char == "/":
                in_comment = False
                i += 2
            else:
                i += 1

            continue

        # Start comment
        if (
            not in_string
            and char == "/"
            and next_char == "*"
        ):
            in_comment = True
            i += 2
            continue

        # ---------------------------------------------------------
        # String
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # Nested block
        # ---------------------------------------------------------

        if char == "{":
            depth += 1
            i += 1
            continue

        if char == "}":
            depth -= 1
            i += 1
            continue

        # ---------------------------------------------------------
        # Look for transition or animation
        # ---------------------------------------------------------

        if depth == 0:

            found_property = None

            for property_name in properties:

                if not block.startswith(
                    property_name,
                    i
                ):
                    continue

                before = (
                    block[i - 1]
                    if i > 0
                    else ""
                )

                after_pos = (
                    i + len(property_name)
                )

                after = (
                    block[after_pos]
                    if after_pos < len(block)
                    else ""
                )

                # Must be an actual property name.
                #
                # Prevent:
                #
                # transition-property
                # transition-duration
                # animation-name
                # animation-duration
                #
                if (
                    before.isalnum()
                    or before in "_-"
                ):
                    continue

                if after not in " \t\r\n:":
                    continue

                found_property = property_name
                break

            if found_property:

                property_end = (
                    i + len(found_property)
                )

                # Skip whitespace between property
                # name and colon.
                colon = property_end

                while (
                    colon < len(block)
                    and block[colon].isspace()
                ):
                    colon += 1

                # Must have a colon.
                if (
                    colon < len(block)
                    and block[colon] == ":"
                ):

                    # -------------------------------------------------
                    # Find end of declaration.
                    # -------------------------------------------------

                    j = colon + 1

                    value_string = None
                    value_comment = False
                    value_escape = False

                    while j < len(block):

                        c = block[j]
                        n = (
                            block[j + 1]
                            if j + 1 < len(block)
                            else ""
                        )

                        # Comment inside value
                        if value_comment:

                            if c == "*" and n == "/":
                                value_comment = False
                                j += 2
                            else:
                                j += 1

                            continue

                        if (
                            not value_string
                            and c == "/"
                            and n == "*"
                        ):
                            value_comment = True
                            j += 2
                            continue

                        # String inside value
                        if value_string:

                            if value_escape:
                                value_escape = False

                            elif c == "\\":
                                value_escape = True

                            elif c == value_string:
                                value_string = None

                            j += 1
                            continue

                        if c in ("'", '"'):
                            value_string = c
                            j += 1
                            continue

                        # Declaration ends here.
                        if c == ";":
                            break

                        # Rule ends here.
                        if c == "}":
                            break

                        j += 1

                    # Make sure there is a value.
                    value = block[
                        colon + 1:j
                    ]

                    if value.strip():

                        # Include semicolon if it exists.
                        end = j

                        if (
                            j < len(block)
                            and block[j] == ";"
                        ):
                            end = j + 1

                        original = block[
                            i:end
                        ]

                        result.append(
                            block[last:i]
                        )

                        # Comment it out.
                        result.append(
                            "/*"
                            + original
                            + "*/"
                        )

                        i = end
                        last = i

                        changes += 1

                        continue

        i += 1

    result.append(
        block[last:]
    )

    return (
        "".join(result),
        changes
    )


def process_css(css):

    rules = find_rules_containing_target(
        css
    )

    total_changes = 0

    # Work backwards so positions don't shift.
    for target_pos, opening, closing in reversed(rules):

        block = css[
            opening + 1:
            closing
        ]

        modified_block, changes = (
            disable_transitions_and_animations(
                block
            )
        )

        css = (
            css[:opening + 1]
            + modified_block
            + css[closing:]
        )

        total_changes += changes

    return (
        css,
        len(rules),
        total_changes
    )


def main():

    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Select compressed CSS file",
        filetypes=[
            ("CSS files", "*.css"),
            ("All files", "*.*")
        ]
    )

    if not file_path:
        return

    path = Path(file_path)

    try:

        css = path.read_text(
            encoding="utf-8"
        )

        modified_css, rule_count, change_count = (
            process_css(css)
        )

        output_path = path.with_name(
            path.stem
            + "_modified"
            + path.suffix
        )

        output_path.write_text(
            modified_css,
            encoding="utf-8"
        )

        messagebox.showinfo(
            "Complete",
            (
                f"Finished!\n\n"
                f"Rules containing '{TARGET}': "
                f"{rule_count}\n\n"
                f"Transitions/animations disabled: "
                f"{change_count}\n\n"
                f"Output file:\n"
                f"{output_path}"
            )
        )

    except Exception as e:

        messagebox.showerror(
            "Error",
            (
                "Something went wrong:\n\n"
                f"{type(e).__name__}: {e}"
            )
        )


if __name__ == "__main__":
    main()