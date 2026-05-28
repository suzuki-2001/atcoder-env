#!/usr/bin/env bash
set -euo pipefail

if command -v acc >/dev/null 2>&1; then
    ACC_CONFIG_DIR="$(acc config-dir)"
    mkdir -p "$ACC_CONFIG_DIR"

    if [ -d /work/templates ]; then
        for d in /work/templates/*/; do
            name=$(basename "$d")
            mkdir -p "$ACC_CONFIG_DIR/$name"
            cp -rT "$d" "$ACC_CONFIG_DIR/$name"
        done
    fi

    acc config default-template      "${DEFAULT_TEMPLATE:-cpp}"   >/dev/null 2>&1 || true
    acc config default-test-dirname-format "test"                 >/dev/null 2>&1 || true
    acc config default-task-choice   "${DEFAULT_TASK_CHOICE:-all}" >/dev/null 2>&1 || true
fi

exec "$@"
