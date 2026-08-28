#!/usr/bin/env python3
"""
Corpus Validation Script — phd-research-scholar skill

Validates a markdown corpus: detects noise, classifies by pillar/service,
produces category_index.json, manifest.json, and deletion script.

Usage: python3 corpus_validate.py <corpus_dir> <output_dir>
"""

import os, sys, json
from collections import defaultdict, Counter
from datetime import datetime

PILLAR_KEYWORDS = {
    "operational_excellence": ["operational", "operational excellence", "workload review framework", "lens", "devops", "operating"],
    "security": ["security", "iam", "shield", "guardduty", "kms", "secrets manager", "cloudhsm", "waf", "firewall manager", "macie", "trusted advisor"],
    "reliability": ["reliability", "resilien", "disaster", "backup", "drs", "rto", "rpo"],
    "performance_efficiency": ["performance", "comput", "network", "latency", "nitro", "scaling", "elastic"],
    "cost_optimization": ["cost", "pricing", "savings", "rightsizing", "graviton", "spot", "reserved", "budget", "cost explorer"],
    "sustainability": ["sustainability", "carbon", "energy", "environmental", "green"],
}

SERVICE_KEYWORDS = [
    "EC2", "S3", "Lambda", "RDS", "EKS", "ECS", "VPC", "IAM", "CloudWatch",
    "SNS", "SQS", "Step Functions", "API Gateway", "CloudFormation", "CodeBuild",
    "CodePipeline", "SSM", "Organizations", "Control Tower", "Config", "Backup",
    "Cost Explorer", "Budgets", "Glue", "Athena", "Redshift", "SageMaker",
    "DynamoDB", "App Runner", "ElastiCache", "DocumentDB", "Aurora",
    "GuardDuty", "Inspector", "KMS", "Secrets Manager", "Shield", "WAF",
    "X-Ray", "CodeArtifact", "Compute Optimizer", "CloudTrail", "Transfer Family",
    "DataSync", "DevOps Guru", "Elastic Beanstalk", "Lightsail",
]

NOISE_CLI = ["cli 2.", "cli 1.", "aws cli"]
NOISE_SDK = ["aws sdk for java", "aws sdk for python"]

def is_noise(content, title, size):
    cl = content.lower()
    if any(p in cl for p in NOISE_CLI): return True
    if any(p in cl for p in NOISE_SDK): return True
    if len(content) < 200: return True
    if title.lower().startswith("# none") and len(content) < 1000: return True
    if "welcome -" in cl and len(content) < 5000: return True
    if "aws glossary" in cl[:500]: return True
    return False

def classify_pillar(cl):
    scores = {p: sum(1 for kw in kws if kw in cl) for p, kws in PILLAR_KEYWORDS.items()}
    return max(scores, key=scores.get) if max(scores.values()) > 0 else "uncategorized"

def classify_services(cl):
    return [s for s in SERVICE_KEYWORDS if s.lower() in cl]

def validate(corpus_dir, output_dir):
    pillar_files = defaultdict(list)
    service_files = defaultdict(list)
    kept = set()
    deleted = 0

    all_files = [f for f in os.listdir(corpus_dir) if os.path.isfile(os.path.join(corpus_dir, f))]
    for fn in sorted(all_files):
        fp = os.path.join(corpus_dir, fn)
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            title = content.split("\n")[0].strip().lstrip("#").strip()
        except:
            continue
        if is_noise(content, title, len(content)):
            deleted += 1; continue
        pillar = classify_pillar(content.lower())
        services = classify_services(content.lower())
        kept.add(fn)
        pillar_files[pillar].append({"file": fn, "title": title})
        for svc in services:
            service_files[svc].append({"file": fn, "title": title})

    pillar_meta = {
        "operational_excellence": {"pillar": "operational_excellence", "description": "Operational Excellence Pillar"},
        "security": {"pillar": "security", "description": "Security Pillar"},
        "reliability": {"pillar": "reliability", "description": "Reliability Pillar"},
        "performance_efficiency": {"pillar": "performance_efficiency", "description": "Performance Efficiency Pillar"},
        "cost_optimization": {"pillar": "cost_optimization", "description": "Cost Optimization Pillar"},
        "sustainability": {"pillar": "sustainability", "description": "Sustainability Pillar"},
        "uncategorized": {"pillar": "uncategorized", "description": "Uncategorized — needs manual review"},
    }

    index = {}
    for pn, meta in pillar_meta.items():
        meta["files"] = [f["file"] for f in pillar_files.get(pn, [])]
        index[pn] = meta
    for sn, sl in service_files.items():
        index[sn] = {"pillar": "cross-pillar", "description": f"Docs for {sn}", "files": [f["file"] for f in sl]}

    ci = os.path.join(output_dir, "category_index.json")
    with open(ci, "w") as f: json.dump(index, f, indent=2)

    mf = os.path.join(output_dir, "manifest.json")
    with open(mf, "w") as f:
        json.dump({"title": "Corpus Manifest", "generated": datetime.now().strftime("%Y-%m-%d"),
            "total_original": len(all_files), "valid_files": len(kept), "deleted_noise": deleted,
            "pillar_summary": {p: len(pillar_files.get(p, [])) for p in pillar_meta},
            "service_counts": {s: len(v) for s, v in service_files.items()},
            "categories": {n: {"count": len(d.get("files", [])), "pillar": d.get("pillar", "?")} for n, d in index.items()}}, f, indent=2)

    df = sorted(set(all_files) - kept)
    ds = os.path.join(output_dir, "delete_noise.sh")
    with open(ds, "w") as f:
        f.write("#!/bin/bash\n# Delete corpus noise\n# Files: " + str(len(df)) + "\n")
        for fn in df: f.write(f'rm "{fn}"\n')
    os.chmod(ds, 0o755)

    vs = os.path.join(output_dir, "verify_corpus.sh")
    with open(vs, "w") as f:
        f.write(f'#!/bin/bash\nls "{corpus_dir}" | wc -l\necho "Expected: {len(kept)}"\n')
    os.chmod(vs, 0o755)

    print(f"=== VALIDATION COMPLETE ===")
    print(f"Total: {len(all_files)} | Kept: {len(kept)} | Deleted: {deleted}")
    for p in pillar_meta:
        print(f"  {p}: {len(index[p].get('files', []))}")
    print(f"\nOutputs: {ci}, {mf}, {ds}, {vs}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <corpus_dir> <output_dir>"); sys.exit(1)
    os.makedirs(sys.argv[2], exist_ok=True)
    validate(sys.argv[1], sys.argv[2])
