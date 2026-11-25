"""Regenerate docs/reference/commands.md from the live command registry.

    .venv/bin/python docs/gen_commands.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from blackbyrd3d.commands.help_cmd import command_reference  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "reference", "commands.md")


def render() -> str:
    lines = [
        "# Command reference",
        "",
        "Every command is typed on the command line (Tab completes,",
        "F1 opens this list inside the app). Aliases in parentheses.",
        "Commands that need a file open a filtered chooser by default. Append",
        "`--headless` to keep the typed path prompt for scripts and automation.",
        "",
    ]
    for section, cmds in command_reference(builtin_only=True).items():
        lines.append(f"## {section}")
        lines.append("")
        lines.append("| Command | Does |")
        lines.append("|---|---|")
        for name, aliases, doc in cmds:
            label = f"`{name}`"
            if aliases:
                label += " (" + ", ".join(f"`{a}`" for a in aliases) + ")"
            lines.append(f"| {label} | {doc.replace('|', chr(92) + '|')} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render())
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
