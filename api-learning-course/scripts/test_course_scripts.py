"""Verify every script in an API-learning course before committing.

Two checks per .py file:
  1. Syntax check via py_compile (catches typos / indent errors fast).
  2. Run each script and confirm exit code 0, with NO api-key env var set so
     auth-guarded scripts fail gracefully (print a hint, exit 0) instead of
     crashing or hitting the network.

Public-endpoint scripts should hit a live endpoint and return sensible data;
auth-guarded ones must skip cleanly without the key.

Usage:  python3 scripts/test_course_scripts.py <repo_root>
"""
import subprocess, sys, os, glob, py_compile


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    py_files = sorted(glob.glob(os.path.join(repo, "**", "*.py"), recursive=True))

    print("=" * 70)
    print("PHASE 1 — syntax check (py_compile)")
    print("=" * 70)
    syntax_ok = True
    for path in py_files:
        rel = os.path.relpath(path, repo)
        try:
            py_compile.compile(path, doraise=True)
            print(f"  OK   {rel}")
        except Exception as exc:
            syntax_ok = False
            print(f"  FAIL {rel}: {exc}")

    print()
    print("=" * 70)
    print("PHASE 2 — runtime check (each script, no API key set)")
    print("=" * 70)

    # Ensure NO api-key env var leaks in, so every guarded script exits early.
    for k in ("RESTFUL_API_KEY", "API_KEY"):
        os.environ.pop(k, None)

    results = []
    for path in py_files:
        rel = os.path.relpath(path, repo)
        try:
            proc = subprocess.run(
                [sys.executable, path],
                capture_output=True, text=True, timeout=30, cwd=repo,
            )
        except subprocess.TimeoutExpired:
            results.append((rel, "TIMEOUT", ""))
            print(f"  TIMEOUT {rel}")
            continue

        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        head = out.replace("\n", " | ")[:200].strip()
        results.append((rel, f"exit={proc.returncode}", head))
        print(f"\n--- {rel} (exit {proc.returncode}) ---")
        for line in out.splitlines()[:6]:
            print(f"  {line}")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    all_ok = syntax_ok and all(code == "exit=0" for _, code, _ in results)
    for rel, code, head in results:
        print(f"  {code:<10} {rel}")
    print()
    print("ALL GREEN" if all_ok else "SEE FAILURES ABOVE")


if __name__ == "__main__":
    main()
