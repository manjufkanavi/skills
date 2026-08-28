# Apple M4 Max (64GB) Reference

**Class:** `comfyui`  
**Topic:** High-memory Apple Silicon configuration  
**Discussed:** 2026-07-12

---

## System Profile

| Component | Value |
|-----------|-------|
| **GPU** | Apple M4 Max (integrated) |
| **CPU** | Apple M4 Max (ARM64) |
| **Total RAM** | 64 GB unified memory |
| **Free RAM** | 10.46 GB (16.34% free) |
| **Page Size** | 16384 bytes (16KB) |
| **Architecture** | ARM64 |

---

## ComfyUI Performance Expectations

**Overall Verdict:** **Excellent** - all models run comfortably.

| Model | VRAM Required | Performance | Notes |
|-------|---------------|-------------|-------|
| **SD 1.5** | ~4 GB | **Excellent** | Fast, responsive |
| **SDXL** | ~6.5 GB | **Excellent** | ~8KB VRAM, smooth |
| **Flux Dev** | ~12 GB | **Excellent** | Full frame buffer, fast |
| **Flux Video/AnimateDiff** | 12+ GB | **Excellent** | All video workflows supported |

### **Key Insights**

1. **Memory is not a constraint** - 64GB unified memory is more than sufficient for all ComfyUI workflows.
2. **GPU is integrated** - M4 Max handles both graphics and CPU tasks efficiently.
3. **No WSL/AMD/Intel issues** - Native Apple Silicon setup, no compatibility layers needed.
4. **Future-proof** - Can handle all current and near-future model sizes including video generation.

---

## **Installation Command**

```bash
comfy --skip-prompt install --m-series
comfy launch --background
```

---

## **Verification**

```bash
python3 scripts/health_check.py
# Expected: all checks pass (server reachable, checkpoint available, smoke test passes)
```

---

## **Related References**

- [`hardware_check.py`](scripts/hardware_check.py) - Automates hardware assessment
- [`comfyui_setup.sh`](scripts/comfyui_setup.sh) - Full installation script

---

## **Caveats**

- This is a **single known-good configuration**. Actual performance may vary based on workload and other running processes.
- Apple Silicon is **not supported for ComfyUI Desktop** (Windows/macOS only for Intel/NVIDIA/AMD). Use `comfy-cli` on macOS.

---

## **Update History**

- 2026-07-12: Initial reference created based on system memory analysis and ComfyUI compatibility assessment.
