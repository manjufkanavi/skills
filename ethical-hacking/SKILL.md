---
name: ethical-hacking
description: Ethical hacking & penetration testing with CLI tooling - reconnaissance, enumeration, vulnerability scanning, and exploitation for authorized assessments. Tool catalog, kill-chain workflow, and agent guidance for AI agents.
---

# Ethical Hacking (Penetration Testing)

Use this skill when the user wants to assess the security posture of a system: map an attack surface, discover services/paths/technologies, run vulnerability scans, and prove/exploit findings. It also teaches **AI agents** how to operate this toolchain deterministically.

## 🎯 The Kill Chain (typical engagement)

`Recon → Enumeration → Fingerprinting → Vulnerability Scanning → Exploitation/Proof → Triage → Reporting`

Most engagements never reach exploitation; the goal is often just to **catalogue risk**.

## 🛠️ Tool Catalog

### Phase 0 — Passive Reconnaissance (no direct contact with target)

| Tool | Purpose | Example |
|------|---------|---------|
| `theHarvester` | Harvest emails, subdomains, hosts from search engines/sources | `theHarvester -d example.com -b google` |
| `amass` | Aggressive DNS/subdomain discovery (passive + active) | `amass enum -active -d example.com` |
| `subfinder` | Subdomain discovery across many sources | `subfinder -d example.com` |
| `assetfinder` | Crawls web pages to harvest subdomains | `assetfinder example.com` |
| `crt.sh` | Subdomains from public TLS certificates | `crtshtool -d example.com` |
| `whois` | Domain registration / registrar info | `whois example.com` |

### Phase 1 — Active Discovery & Fingerprinting

| Tool | Purpose | Example |
|------|---------|---------|
| `nmap` | Hosts, ports, services, OS, scripts (the workhorse) | `nmap -sV -sC -Pn target` |
| `masscan` | Ultra-fast TCP SYN sweep of huge ranges | `masscan -iR 192.168.0.0/16 --rate 10000` |
| `httpx` | Probe URLs: tech, title, status, headers | `httpx -n http://target -title -status-code` |
| `whatweb` | Web technology/version fingerprinting | `whatweb http://target` |
| `wafw00f` | Detect & fingerprint WAFs/CACHES | `wafw00f http://target` |
| `dnsrecon` | DNS zone enumeration + records | `dnsrecon -d example.com` |
| `dnsenum` | DNS brute-force / zone transfer | `dnsenum -d example.com` |
| `paramspider` | Discover URL & endpoint parameters | `paramspider -u http://target/search` |

### Phase 2 — Web Fuzzing / Directory & Parameter Discovery

| Tool | Purpose | Example |
|------|---------|---------|
| `gobuster` | Dirs/files/params/subdomains brute-force | `gobuster dir -u http://t/ -w wordlist.txt -t 20` |
| `ffuf` | Blazing-fast fuzzer, dir/enum/subdomain | `ffuf -u http://t/F -w wordlist.txt -o res.txt` |
| `feroxbuster` | Resilient recursive dir fuzzer (Rust) | `feroxbuster http://target` |
| `wfuzz` | Scriptable fuzzer (old but powerful) | `wfuzz --hc 403 -z wordlist.txt http://t/F` |
| `dirb` | Classic dir/file enumerator (needs server) | `dirb http://target -w wordlist.txt` |
| `dirbuster` | Web-only dir/file finder (historical) | `java -jar dirbuster.jar -u http://target` |
| `skipfish` | Automated security misconfig / WSTG checklist | `skipfish -o report http://target` |
| `webinspect` | Manual interactive pen-test helper | `webinspect -u "https://testphp.vulnsec.com/"` |
| `acunetix` | Automated web vuln scanner (GUI + CLI) | `acunetix scan target.json` |
| `arachni` | Web app testing (Ruby), pentest reports | `arachni http://target` |
| `waz` | Web app scanner (Ruby), WSTG checks | `waz.rb scan --target http://target` |
| `nikto` | Server-side vuln/config/tech scanner | `nikto -h http://target -o report` |
| `nessus` | Enterprise vuln/asset management scanner | server + scanner UI |
| `openvas` | Greenbone vuln scanner (NVT-based) | `openvas -n -t target` |
| `nuclei` | Template-based vuln scanner (fast, huge TTPs DB) | `nuclei -u http://target` |
| `burp` | Manual proxy/repeater/intruder platform | GUI |
| `owasp-zap` | OWASP ZAP free DAST + spider/active scan | `zap-cli scan --url http://target -f html -o rep.html` |
| `hydra` | Network credential brute-force (SSH/FTP/SMB…) | `hydra -L users.txt -P pass.txt ssh://target -t 16` |
| `medusa` | Multi-protocol brute-forcer (SSH/FTP/HTTP/SMB) | `medusa -h target -U users.txt -P pass.txt -M ssh` |
| `sqlmap` | SQLi detection → DB dump/exfil/OS info leak | `sqlmap -u "http://t?id=1" --dbs` |
| `toolshell` | Exploit for CVE-2025-53770 (Linux tooling) | CVE-specific, see references |

### Phase 3 — Code / Config Analysis (SAST)

| Tool | Purpose | Example |
|------|---------|---------|
| `bandit` | Python SAST, finds common vulns (SQLi, XSS…) | `bandit -r project/` |
| `semgrep` | Cross-language SAST, custom/auto rules | `semgrep --config auto -l .` |

### Phase 4 — Exploitation & Post-Exploitation

| Tool | Purpose | Example |
|------|---------|---------|
| `metasploit` (`msfconsole`) | Exploit dev + payload delivery; 10k+ modules | `msfconsole` → `use exploit/multi/http/...` |

## 📦 Tool Installation (isolated venv — never on the machine)

Install everything inside a dedicated, per-user Python venv + env-local bin dir. Do NOT `pip install` to the system Python, and do NOT `apt`/`brew`/`gem` install tools onto the host. Everything runs from `~/.venvs/pentest`.

### Step 1 — pip tools (automated)

```bash
bash "$SKILL_DIR/install.sh"          # creates ~/.venvs/pentest, activates it, pip install -r requirements.txt
source ~/.venvs/pentest/bin/activate
python -m pip list                    # confirm the pip tools installed
```

### Step 2 — non-Python tools (Go / Ruby / system binaries)

Install each of these into the venv's `bin/` dir and prepend it to PATH (keep them off the host machine):

```bash
PENTEST_VENV="$HOME/.venvs/pentest"
BIN="$PENTEST_VENV/bin"
export PATH="$BIN:$PATH"
```

Go binaries — install with `go install`, then symlink into the venv bin (runs from the isolated env):

| Tool | Install command |
|------|-----------------|
| `nuclei` | `go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest` |
| `amass` | `go install github.com/owenrumney/amass@latest` |
| `subfinder` | `go install github.com/projectdiscovery/subfinder/cmd/subfinder@latest` |
| `assetfinder` | `go install github.com/mozar/assetfinder@latest` |
| `masscan` | `go install github.com/robertkrimen/masscan@latest` |
| `ffuf` | `go install github.com/ffuf/ffuf/v2/cmd/ffuf@latest` |
| `feroxbuster` | `go install github.com/epi052/feroxbuster@latest` |
| `gobuster` | `go install github.com/OJ/gobuster@latest` |

Then symlink them into the venv:
```bash
for t in nuclei amass subfinder assetfinder masscan ffuf feroxbuster gobuster; do
  ln -sf "$HOME/go/bin/$t" "$BIN/"
done
```

System binaries — download the release into `$BIN` and `chmod +x`; never install system-wide:

| Tool | Action |
|------|--------|
| `nmap` | `curl -L -o "$BIN/nmap" https://nmap.org/nmap.st && chmod +x "$BIN/nmap"` |
| `owasp-zap` | unzip official release; run `bin/zap.sh` (Java) |
| `sqlmap` | copy official prebuilt binary into `$BIN/` |
| `nikto` | download release `bin/nikto` into `$BIN/` |
| `hydra` | clone `t6/hydra`, `make`, symlink `bin/hydra` → `$BIN/` |
| `dnsrecon` | clone `dnsrecon/dnsrecon`; run `python3 dnsrecon.py` |
| `dirb` | copy release binary into `$BIN/` |
| `dirbuster` | download jar; run `java -jar` (needs a JRE in the venv) |
| `skipfish` | clone `mabilynn/skipfish`, build from source, symlink → `$BIN/` |

Ruby gems: `gem install arachni` (needs bundler); `gem install msfcore-lib` then run `msfconsole setup`.
Special: `crt.sh` needs the Rust toolchain; `acunetix` is commercial (vendor install);
`toolshell` is a CVE-specific exploit (source repo, authorization only).

> Note: Ruby-based tools (metasploit/arachni/waz) may need a Ruby environment — Ruby is typically system-level, so keep gems in a user install (`--user-install`) and invoke from the venv.

Verify the whole stack:
```bash
nmap -V; nuclei -version; subfinder -v; theHarvester -h; medusa --help; bandit --version; semgrep --version
```

### ✅ Tool-install pitfalls (durable)
- PyPI **`nuclei`** is a package-squatter (returns junk v0.1.0). ProjectDiscovery's real tool is awkward to pip-install (uv mis-resolves `projectdiscovery/nuclei-OT`); **install the standalone release binary** instead.
- **`nikto`**'s official raw `bin/nikto` URLs 404 oddly; prefer the release zip + `bin/nikto`, or the v3 Go build (`go install github.com/skeema/nikto/cmd/nikto@latest`).

## 🌐 ASP.NET / IIS Web Apps (the common corporate stack)

Most mid-tier web targets are **ASP.NET MVC / WebForms on IIS**, not a generic box. Fingerprint first (`x-aspnet-version`, `x-aspnetmvc-version`, `server`, `x-powered-by`), then treat this as a first-class class.

- **customErrors mode="Off" (CVE-2166) → info disclosure.** A 404 leaks the **full server stack trace + framework versions + the app's controller namespace** (e.g. `californiaspa.Controllers.AccountController`), including the leaked assembly name. It's HIGH and the seed for the ASP.NET RCE chain. **Trigger correctly: request a non-existent ACTION on a REAL controller** (a URL that parses to a known controller + unknown action → `Controller.HandleUnknownAction(String actionName)` → the leak). A URL that matches no controller at all leaks only framework fragments (`.NET Framework Version`, `System.Web.Mvc`), **not** the namespace. So probe a real action (e.g. a known login/register action) with a quote in the action-name segment.
- **MVC ≠ WebForms for ViewState.** CVE-2016-0799/0798 server-variable injection **only applies to .aspx WebForms pages that carry `__VIEWSTATE`**. A pure-MVC app has no ViewState → injection params are **no-ops**. Check for `__VIEWSTATE`/`__EVENTVALIDATION` in the HTML; if absent, skip server-var injection.
- **Enumerate the controller surface** once customErrors is off: every non-existent `Controller/Action` returns a 404 whose error text names the controller. Probing `ControllerName` (actionless) reveals which controllers exist.
- **The leaked namespace is a filesystem-path clue.** Use it to probe app paths with a **bounded** list: the assembly name → `californiaspa.dll`, `californiaspa/`, `App_Config/Global.asax`, `web.config`, `Controllers/*.cs`. Keep the probe list bounded (don't fire an infinite-typo-open command; it aborts the whole probe). Probe for a writable config / file-write path (e.g. PUT `web.config`) — that write path is the RCE precondition; if there's no file-write route, stop at disclosure.
- **Don't fight for a 500.** Modern MVC re-renders the view on model/validation failure → you get **200 + a re-rendered form**, not a stack trace. Only *uncaught* exceptions surface the trace. Stop throwing payloads at forms; use the 404 leak.
- **returnUrl / CSRF are usually handled.** MVC login `returnUrl` is commonly format-validated and hidden (not reflected) → no open redirect. Login controllers are parameterized → SQLi payloads hit a **validation error**, not a DB. Verify rather than assume.

See `references/aspnet-iis-webapp.md` for the condensed knowledge bank (reproduction recipe, CVE-2166 proof sample, enumeration playbook, remediation).

## ✅ Vulnerability Triage & Reporting

1. Confirm each finding is **real** (reproduce manually), not a false positive.
2. Classify against a framework (e.g., **OWASP Top 10** for web; **CVSS** for severity).
3. Save raw output + screenshots to the engagement directory; keep data labelled.
4. Write a report: finding, impact, proof, affected assets, recommended fix + CVSS.

## 🧠 AI-Agent Guidance

- Keep recon **deterministic and observable**: always capture and save tool output.
- One technique per step.
- Respect rate limits; throttle parallel requests (`-t`/`--parallelism`).

## References

- OWASP Testing Guide & OWASP Top 10 — web app security methodology.
- enaqx/awesome-pentest (GitHub) — curated OSINT/pentest tool collection.
- "An Empirical Comparison of Pen-Testing Tools for Detecting Web App Vulnerabilities" (IEEE Xplore).
- "Multi-Agent Penetration Testing AI for the Web" — AI-assisted pentest research.
- "Web Application Penetration Testing 2026: Beyond OWASP Top 10" — Hive Security.
- "Hottest cybersecurity open-source tools of the month: May 2026" — Help Net Security.
- OWASP Source Analyzer (source code analysis tools) & free OSS AppSec tools.
