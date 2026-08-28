# Training Data Schema Validation

Validating and fixing structured JSON training datasets against a schema definition before fine-tuning.

## Problem Pattern

Training data from multiple sources often has structural mismatches with the target training schema:

| Issue | Example | Fix |
|-------|---------|-----|
| **Type mismatch** | `components` is `["EC2", "S3"]` (strings) instead of `[{"service":"EC2","role":"...", "configuration":"..."}]` | Map strings → objects |
| **Nested structure mismatch** | `principles` is `"Auto scaling, monitoring"` (string) instead of `["Auto scaling", "monitoring"]` (list) | Split string → list |
| **Enum mismatch** | `industry` is `"Fintech & Banking"` instead of `"Financial Services"` | Mapping dictionary |
| **ID format mismatch** | `id` is `"aws-arch-1000"` (4 digits) instead of `^aws-arch-[0-9]{3}$` | Update regex or rename |
| **Constraint violations** | `service_combination` has 10 items, schema says max 8 | Truncate or relax constraint |
| **Missing fields** | `references` field absent | Skip or default |

## Workflow

### Step 1: Inspect Schema

```python
import json
with open("schema/training_schema.json") as f:
    schema = json.load(f)
# Note: required_fields, property types, enums, minItems, maxItems
```

### Step 2: Inspect Data

```python
with open("training-data/unified_training.json") as f:
    data = json.load(f)
records = data["data"]

# Quick audit
for field in schema["required_fields"]:
    missing = sum(1 for r in records if field not in r)
    print(f"  {field}: {missing} missing")

# Type checks
arch = records[0]["architecture_design"]
print(f"  components type: {type(arch['components'][0])}")  # str vs dict
print(f"  principles type: {type(arch['well_architected_pillars']['security']['principles'])}")  # str vs list
```

### Step 3: Build Mapping Dictionaries

**Service name normalization:**
```python
SERVICE_ROLES = {
    "EC2": "Compute instances for application hosting",
    "Lambda": "Serverless compute for event-driven processing",
    "S3": "Object storage for data lakes and backups",
    # ... 80+ services
}
```

**Industry name mapping:**
```python
INDUSTRY_MAPPING = {
    "Fintech & Banking": "Financial Services",
    "Healthcare & Life Sciences": "Healthcare",
    "Retail & E-Commerce": "Retail",
    # ... map non-standard → schema enum
}
```

### Step 4: Validate All Records

```python
def validate_record(record, idx):
    issues = []
    # Check required fields
    # Check types (list vs str, dict vs str)
    # Check enums (industry, deployment_model)
    # Check constraints (minItems, maxItems)
    # Check ID format (regex)
    return issues
```

### Step 5: Fix Records

```python
def fix_record(record):
    fixed = dict(record)
    # Fix components: strings → objects
    if isinstance(components[0], str):
        fixed["components"] = [map_to_component(s) for s in components]
    # Fix principles: string → list
    if isinstance(principles, str):
        fixed["principles"] = split_principles(principles)
    # Fix industry: map to enum
    if record["industry"] in INDUSTRY_MAPPING:
        fixed["industry"] = INDUSTRY_MAPPING[record["industry"]]
    # Fix ID format
    if record["id"] == "aws-arch-1000":
        fixed["id"] = "aws-arch-000"
    # Truncate if over max
    if len(fixed["service_combination"]) > 8:
        fixed["service_combination"] = fixed["service_combination"][:8]
    return fixed
```

### Step 6: Re-validate and Report

```python
# Validate all fixed records
remaining = 0
for rec in fixed_records:
    remaining += len(validate_record(rec))

# Output stats
print(f"  Before: {total_issues} issues across {records_with_issues} records")
print(f"  After:  {remaining} issues across {records_remaining} records")
```

## Key Files (Solvarch Project)

- **Schema:** `schema/training_schema.json` — 12.4KB, 15 required fields, enum constraints
- **Input:** `training-data/unified_training.json` — 1000 records, 137 unique services
- **Script:** `scripts/validate_schema.py` — 200+ lines, auto-fixes structural issues
- **Output:** `training-data/validated_training.json` — clean records ready for formatting
- **Report:** `training-data/schema_validation_report.json` — stats and issue breakdown

## Common Pitfalls

- **Never discard records for enum mismatches** — map them instead. 690 records with non-standard industry names = 69% of dataset. Discarding loses too much signal.
- **Truncate, don't drop services** — When `service_combination` exceeds max, keep the first N services (usually most relevant). Don't drop the whole record.
- **ID collisions after fix** — If you rename `aws-arch-1000` → `aws-arch-999`, you may create a duplicate. Use unused slots (e.g., `aws-arch-000`) or update the regex to accept 4 digits.
- **Service count constraint is often artificial** — The training script just does `", ".join(example["service_combination"])`. It doesn't enforce max 8. Consider relaxing the schema constraint instead of truncating.
- **Always re-validate after fixing** — A fix for one issue can expose another. Run validation twice: before and after fixing.
- **Preserve provenance** — Keep the original file alongside the fixed file. The validation report should document every transformation.

## Service Role Mapping Reference

The Solvarch project uses 137 unique AWS services. Key mappings:

| Service Category | Examples |
|-----------------|----------|
| Compute | EC2, Lambda, ECS, EKS, Fargate, Lightsail, Outposts |
| Storage | S3, EBS, EFS, FSx, Storage Gateway, Snow Family |
| Database | RDS, Aurora, DynamoDB, Redshift, DocumentDB, Neptune |
| Networking | VPC, CloudFront, Route 53, ELB, Direct Connect, Transit Gateway |
| Security | IAM, KMS, Cognito, GuardDuty, Macie, WAF, Shield |
| Monitoring | CloudWatch, CloudTrail, Config, X-Ray |
| AI/ML | SageMaker, Bedrock, Comprehend, Rekognition, Lex, Polly |
| Messaging | SQS, SNS, EventBridge, Step Functions, MSK, Kinesis |
| DevOps | CodePipeline, CodeBuild, CodeCommit, CodeDeploy, Cloud9 |
| Management | Systems Manager, Parameter Store, Control Tower, QuickSight |
