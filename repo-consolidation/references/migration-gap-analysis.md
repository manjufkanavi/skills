# Post-Migration Gap Analysis

Systematic methodology for verifying that a code migration preserved all files with their content intact. Detects files that were **rewritten** (skeleton replacement) vs. **preserved** (intact copy).

## Quick Assessment (5-minute sweep)

```python
from pathlib import Path
import os

def quick_sweep(old_root, new_root, max_depth=2):
    """Top-level structure comparison. Returns list of (old_rel, new_rel, status)."""
    old_tree = {}
    new_tree = {}
    
    for root, dirs, files in os.walk(old_root):
        rel = Path(root).relative_to(old_root)
        old_tree[str(rel)] = set(f for f in files)
    
    for root, dirs, files in os.walk(new_root):
        rel = Path(root).relative_to(new_root)
        new_tree[str(rel)] = set(f for f in files)
    
    # Compare
    issues = []
    for old_dir, old_files in old_tree.items():
        new_files = new_tree.get(old_dir, set())
        missing = old_files - new_files
        extra = new_files - old_files
        if missing:
            issues.append(f"  MISSING in new dir {old_dir}: {missing}")
        if extra:
            issues.append(f"  EXTRA in new dir {old_dir}: {extra}")
    
    return issues
```

## Critical File Check

After the sweep, check these categories specifically:

### 1. Entry Points
| File | Why it matters |
|------|---------------|
| `App.tsx` (or equivalent) | App shell — usually the first thing that gets "simplified" |
| `index.tsx` / `main.ts` | Entry point — import path must resolve |
| `index.html` | Script src must point to the right entry |
| `vite.config.ts` | Build configuration |
| `package.json` | Dependencies |
| `tsconfig.json` | Path aliases |

### 2. Constants & Config
Constants are the #1 silent bug source. They get "simplified" during migration:

- `constants.ts` or `constants/models.ts` — Model definitions, often stripped down
- `constants/providers.ts` — Provider configurations
- `constants.tsx` — Icons and constants, often replaced with minimal version
- Environment configs (`.env.example`, `vite.config.ts` define blocks)

**Red flag:** Any constants file that's < 50% of its original size.

### 3. Page Components
- All page files in `components/pages/` or `src/app/`
- Auth-related pages (SignIn, SignUp, ForgotPassword)
- Dashboard/main application pages

### 4. Services & Stores
- API client services
- Auth stores (useAuthStore, useAppStore)
- WebSocket services

### 5. Docker / Build Config
- `Dockerfile` — Source copy paths, build args
- `nginx.conf` — proxy_pass targets
- `docker-compose*.yml` — Service references

## Size-Based Heuristics

| Size Ratio | Likely State | Action |
|------------|-------------|--------|
| 95–100% | IDENTICAL or near-identical | ✅ Safe |
| 80–94% | Minor edits | ⚠️ Quick diff check |
| 50–79% | Significant changes | 🔍 Manual review needed |
| < 50% | LIKELY REPLACED | 🚨 Flag for restoration |
| 0% | MISSING | 🚨 Must restore |

## Import Path Resolution Check

```python
from pathlib import Path

def check_imports(old_app_path, new_root):
    """Verify every import in old App.tsx resolves in new structure."""
    with open(old_app_path) as f:
        lines = f.readlines()
    
    imports = []
    for line in lines:
        if line.strip().startswith('import'):
            # Extract path from: import X from './path/to/file'
            if "from '" in line:
                path = line.split("from '")[1].split("'")[0]
                imports.append(path)
            elif 'from "' in line:
                path = line.split('from "')[1].split('"')[0]
                imports.append(path)
    
    results = []
    for imp in imports:
        parts = imp.lstrip('./').split('/')
        resolved = new_root / ('/'.join(parts))
        # Try adding .tsx extension
        if not resolved.exists():
            resolved = resolved.with_suffix('.tsx')
        exists = resolved.exists()
        results.append({
            'import': imp,
            'resolved': str(resolved.relative_to(new_root)),
            'exists': exists,
        })
    
    return results

# Usage
results = check_imports(
    '/path/to/old/repo/App.tsx',
    Path('/path/to/new/repo')
)

for r in results:
    print(f"  {'✅' if r['exists'] else '❌'} {r['import']:40s} -> {r['resolved']}")
```

## Detecting Skeleton Replacement

When a file was REPLACED with a skeleton, you'll see:

1. **File exists but is dramatically smaller** — e.g., App.tsx: 20KB → 3KB
2. **Routes simplified** — Full routing (40+ routes) replaced with ~10 generic routes
3. **Components inlined** — Real page components exist as separate files but aren't imported
4. **Auth logic simplified** — ProtectedRoute wrappers replaced with localStorage checks
5. **Missing state management** — Store integrations, LocationSyncer removed

**Evidence pattern:**
```
Old: 454 lines, 40+ routes, 30+ component imports
New: 89 lines, 10 routes, 2 component imports
Ratio: 82% similar (different content, same concept)
Verdict: REPLACED — restore original
```

## Gap Report Format

Use this template when documenting findings:

```markdown
## Migration Gap Report — [Date]

### Root Cause
[Skeleton replacement vs. file preservation — what went wrong]

### Critical Replacements (HIGH impact)
| File | Old Size | New Size | Impact |
|------|----------|----------|--------|
| [filename] | [size] | [size] | [what was lost] |

### Path Mismatches (MEDIUM impact)
| Import | Old Resolved | New Resolved | Fix |
|--------|-------------|-------------|-----|
| [import] | [old path] | [new path] | [fix] |

### Stripped Content (MEDIUM impact)
| File | What was stripped |
|------|-----------------|
| [file] | [constants, icons, configs, etc.] |

### Intact Files (OK)
- [file] — [size match, status]
- [file] — IDENTICAL
```