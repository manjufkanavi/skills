#!/usr/bin/env python3
"""Inspect a HuggingFace parquet file's schema and dump a sample row.

Flattens nested struct/list fields for readability. If `pyarrow` is missing, prints the
`uv` command to spin up a throwaway venv and install it (so the script self-heals on a
fresh machine instead of failing).

Usage:
    python3 scripts/inspect_parquet_schema.py <path-or-hf-url> [--rows 3]

Example:
    python3 scripts/inspect_parquet_schema.py \
        https://huggingface.co/datasets/jjovalle99/raft-dataset-aws-wellarchitected/resolve/main/data/train-00000-of-00001.parquet
"""
import argparse
import os
import sys
import tempfile
import urllib.request


def _ensure_pyarrow():
    """Return pyarrow.parquet, or print the install command and exit."""
    try:
        import pyarrow.parquet as pq
        return pq
    except ImportError:
        print("pyarrow not installed. Install it into a throwaway venv with:\n")
        print("    uv venv /tmp/_pq && "
              "/tmp/_pq/bin/pip install pyarrow && "
              "/tmp/_pq/bin/python <this_script> <path>")
        sys.exit(1)


def _download(url, tmp):
    print(f"downloading {url} ...")
    out = os.path.join(tmp, "file.parquet")
    urllib.request.urlretrieve(url, out)
    return out


def _flatten(value, prefix=""):
    """Flatten nested dict/list values into a flat {key: str} for display."""
    if isinstance(value, dict):
        return {f"{prefix}.{k}": v for k, v in value.items()}
    if isinstance(value, list):
        if not value:
            return {prefix: "[]"}
        item = value[0]
        if isinstance(item, dict):
            out = {}
            for k, v in item.items():
                out[f"{prefix}.{k}"] = v
            return out
        return {prefix: [str(x)[:200] for x in value[:3]]}
    return {prefix: str(value)[:300]}


def main():
    ap = argparse.ArgumentParser(description="Inspect an HF parquet schema + sample row.")
    ap.add_argument("path", help="local path or HF parquet URL")
    ap.add_argument("--rows", type=int, default=3, help="rows to flatten/dump")
    args = ap.parse_args()

    pq = _ensure_pyarrow()

    tmp = tempfile.mkdtemp(prefix="parquet_inspect_")
    path = args.path
    if str(path).startswith("http"):
        path = _download(path, tmp)

    table = pq.read_table(path)
    print("\n=== schema ===")
    print(table.schema)
    print(f"\nnum rows: {table.num_rows}\n")

    rows = table.slice(0, args.rows).to_pylist()
    print("=== sample rows (flattened) ===")
    for i, row in enumerate(rows):
        print(f"\n--- row {i} ---")
        flat = {}
        for k, v in row.items():
            flat.update(_flatten(v, k))
        for k, v in flat.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
