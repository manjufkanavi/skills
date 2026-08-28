#!/bin/bash
# convert.sh — Convert multiple document types to markdown
# Usage: ./convert.sh <file1> [file2] ...

set -euo pipefail

# Activate venv
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/../markitdown-env"
source "${VENV_DIR}/bin/activate"

POSTPROCESS="${SCRIPT_DIR}/postprocess_pdf.py"
PROJECT_DIR="${SCRIPT_DIR}/../../project_work"

for file in "$@"; do
    full_path="${PROJECT_DIR}/${file}"
    basename=$(basename "$file")
    name="${basename%.*}"
    ext="${basename##*.}"
    out_file="${PROJECT_DIR}/markdown/${name}.md"
    
    echo "Converting: ${file}"
    
    case "$ext" in
        pdf)
            python3 -m markitdown "$full_path" --output /dev/stdout | python3 "$POSTPROCESS" > "$out_file"
            ;;
        pptx)
            python3 -m markitdown "$full_path" --output "$out_file"
            ;;
        docx)
            python3 -m markitdown "$full_path" --output "$out_file"
            ;;
        *)
            echo "Unsupported format: $ext"
            continue
            ;;
    esac
    
    echo "  → ${out_file}"
done

echo "Done."
