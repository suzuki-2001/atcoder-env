#!/usr/bin/env python3
# Extend onlinejudge/service/atcoder.py to accept KiB/MiB memory units.
# Why: AtCoder changed MB → MiB around ABC408 (2025-06); upstream parser
# asserts on the unit and `oj submit` fails. See api-client#172 / oj#939.

from __future__ import annotations

import sys
from pathlib import Path


def main():
    import onlinejudge.service.atcoder as mod
    path = Path(mod.__file__)
    text = path.read_text()

    patches = [
        (
            "regex_units",
            "re.search(r'^(メモリ制限|Memory Limit): ([0-9.]+) (KB|MB)'",
            "re.search(r'^(メモリ制限|Memory Limit): ([0-9.]+) (KB|MB|KiB|MiB)'",
        ),
        (
            "from_html_branches",
            (
                "if memory_limit_unit == 'KB':\n"
                "            memory_limit_byte = int(float(memory_limit_value) * 1000)\n"
                "        elif memory_limit_unit == 'MB':\n"
                "            memory_limit_byte = int(float(memory_limit_value) * 1000 * 1000)\n"
                "        else:\n"
                "            assert False"
            ),
            (
                "if memory_limit_unit == 'KB':\n"
                "            memory_limit_byte = int(float(memory_limit_value) * 1000)\n"
                "        elif memory_limit_unit == 'KiB':\n"
                "            memory_limit_byte = int(float(memory_limit_value) * 1024)\n"
                "        elif memory_limit_unit == 'MB':\n"
                "            memory_limit_byte = int(float(memory_limit_value) * 1000 * 1000)\n"
                "        elif memory_limit_unit == 'MiB':\n"
                "            memory_limit_byte = int(float(memory_limit_value) * 1024 * 1024)\n"
                "        else:\n"
                "            assert False"
            ),
        ),
        (
            "from_table_row_branches",
            (
                "if tds[3].text.endswith(' KB'):\n"
                "            memory_limit_byte = int(float(utils.remove_suffix(tds[3].text, ' KB')) * 1000)\n"
                "        elif tds[3].text.endswith(' MB'):\n"
                "            memory_limit_byte = int(float(utils.remove_suffix(tds[3].text, ' MB')) * 1000 * 1000)"
            ),
            (
                "if tds[3].text.endswith(' KB'):\n"
                "            memory_limit_byte = int(float(utils.remove_suffix(tds[3].text, ' KB')) * 1000)\n"
                "        elif tds[3].text.endswith(' KiB'):\n"
                "            memory_limit_byte = int(float(utils.remove_suffix(tds[3].text, ' KiB')) * 1024)\n"
                "        elif tds[3].text.endswith(' MB'):\n"
                "            memory_limit_byte = int(float(utils.remove_suffix(tds[3].text, ' MB')) * 1000 * 1000)\n"
                "        elif tds[3].text.endswith(' MiB'):\n"
                "            memory_limit_byte = int(float(utils.remove_suffix(tds[3].text, ' MiB')) * 1024 * 1024)"
            ),
        ),
    ]

    failures = []
    for name, before, after in patches:
        if after in text and before not in text:
            print(f"[mib-patch] {name}: already applied")
            continue
        if before not in text:
            failures.append(name)
            print(f"[mib-patch] {name}: PATTERN NOT FOUND", file=sys.stderr)
            continue
        text = text.replace(before, after, 1)
        print(f"[mib-patch] {name}: applied")

    if failures:
        print(
            f"[mib-patch] ERROR: {len(failures)} pattern(s) missing in {path}.\n"
            "Upstream atcoder.py likely changed; update this script.",
            file=sys.stderr,
        )
        return 1

    path.write_text(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
