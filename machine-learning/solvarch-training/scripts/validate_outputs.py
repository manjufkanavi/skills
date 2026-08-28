#!/usr/bin/env python3
"""
Phase 3: Schema & Quality Validation for Solvarch Generated Outputs.
Validates free-text model outputs against AWS Well-Architected framework principles.
"""

import json
import re
import sys
from pathlib import Path

# AWS services we check for presence in responses
AWS_SERVICES = {
    "EC2", "Lambda", "ECS", "EKS", "Fargate", "S3", "RDS", "Aurora", "DynamoDB",
    "Redshift", "Athena", "Glue", "EMR", "CloudFront", "Route 53", "API Gateway",
    "ELB", "VPC", "IAM", "KMS", "CloudWatch", "CloudTrail", "SQS", "SNS",
    "EventBridge", "Step Functions", "Kinesis", "SageMaker", "IoT Core",
    "WAF", "Shield", "GuardDuty", "Config", "X-Ray", "CodePipeline",
    "Transit Gateway", "NAT Gateway", "App Mesh", "ElastiCache", "DocumentDB"
}

# Well-Architected pillars to check for
WELL_ARCHITECTED_PILLARS = {
    "Operational Excellence": ["operational", "monitoring", "observability", "automation", "ops"],
    "Security": ["security", "iam", "encryption", "kms", "waf", "shield", "guardduty", "auth"],
    "Reliability": ["reliability", "fault", "failover", "backup", "recovery", "ha", "high-availability", "disaster"],
    "Performance Efficiency": ["performance", "latency", "throughput", "cache", "cdn", "optimization"],
    "Cost Optimization": ["cost", "savings", "reserved", "spot", "rightsizing", "graceful"],
    "Sustainability": ["sustainability", "carbon", "efficiency", "green", "energy"],
}

# Required structural elements for a good architecture response
REQUIRED_ELEMENTS = [
    "architecture", "component", "service", "data", "network", "security",
    "scal", "deploy", "monitor", "design", "architect"
]


def count_aws_services(text: str) -> list:
    """Find AWS services mentioned in the text."""
    found = []
    text_upper = text.upper()
    for service in AWS_SERVICES:
        if service.upper() in text_upper:
            found.append(service)
    return found


def check_well_architected(text: str) -> dict:
    """Check which Well-Architected pillars are covered."""
    text_lower = text.lower()
    results = {}
    for pillar, keywords in WELL_ARCHITECTED_PILLARS.items():
        matches = [kw for kw in keywords if kw in text_lower]
        results[pillar] = {
            "covered": len(matches) > 0,
            "keywords_found": matches
        }
    return results


def check_structure(text: str) -> dict:
    """Check if the response has proper structure."""
    has_headings = bool(re.search(r'###?\s', text))
    has_bullets = bool(re.search(r'-\s', text))
    has_numbered = bool(re.search(r'\d+\.\s', text))
    has_sections = bool(re.search(r'(?:section|component|step|phase|pillar)\s+\d', text, re.IGNORECASE))
    
    return {
        "has_headings": has_headings,
        "has_bullets": has_bullets,
        "has_numbered": has_numbered,
        "has_sections": has_sections,
        "structural_score": sum([has_headings, has_bullets, has_numbered, has_sections]) / 4
    }


def check_response_length(text: str) -> dict:
    """Check response length quality."""
    word_count = len(text.split())
    char_count = len(text)
    
    if word_count >= 200:
        length_quality = "excellent"
    elif word_count >= 100:
        length_quality = "good"
    elif word_count >= 50:
        length_quality = "adequate"
    else:
        length_quality = "too_short"
    
    return {
        "word_count": word_count,
        "char_count": char_count,
        "quality": length_quality
    }


def validate_response(response: str, prompt: str, idx: int) -> dict:
    """Full validation of a single response."""
    aws_services = count_aws_services(response)
    pillars = check_well_architected(response)
    structure = check_structure(response)
    length = check_response_length(response)
    
    # Calculate overall quality score
    pillar_score = sum(1 for v in pillars.values() if v["covered"]) / len(pillars)
    service_score = len(aws_services) / 15  # Expect at least 15 services
    structure_score = structure["structural_score"]
    
    overall = (pillar_score * 0.35 + service_score * 0.35 + structure_score * 0.3)
    
    return {
        "sample_index": idx + 1,
        "prompt": prompt,
        "response_length": length,
        "aws_services_found": aws_services,
        "service_count": len(aws_services),
        "well_architected_coverage": pillars,
        "pillar_score": round(pillar_score, 3),
        "structure": structure,
        "overall_quality_score": round(overall, 3),
        "quality_rating": "excellent" if overall >= 0.7 else "good" if overall >= 0.5 else "needs_improvement"
    }


def main():
    # Default paths — override via args if needed
    project_root = Path(__file__).parent.parent.parent
    output_path = project_root / "evaluation" / "sample_outputs.jsonl"
    if not output_path.exists():
        print("No sample outputs found. Run run_samples.py first.")
        return
    
    results = []
    with open(output_path) as f:
        for line in f:
            entry = json.loads(line)
            result = validate_response(entry["response"], entry["prompt"], len(results))
            results.append(result)
    
    # Save validation report
    report_path = project_root / "evaluation" / "validation_report.json"
    report_path.parent.mkdir(exist_ok=True)
    
    # Summary
    summary = {
        "total_samples": len(results),
        "avg_quality_score": round(sum(r["overall_quality_score"] for r in results) / len(results), 3),
        "avg_pillar_coverage": round(sum(r["pillar_score"] for r in results) / len(results), 3),
        "avg_service_count": round(sum(r["service_count"] for r in results) / len(results), 1),
        "quality_distribution": {},
        "samples": results
    }
    
    for r in results:
        rating = r["quality_rating"]
        summary["quality_distribution"][rating] = summary["quality_distribution"].get(rating, 0) + 1
    
    with open(report_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print summary
    print("=" * 60)
    print("SOLVARCH VALIDATION REPORT")
    print("=" * 60)
    print(f"Total Samples:     {summary['total_samples']}")
    print(f"Avg Quality Score: {summary['avg_quality_score']}")
    print(f"Avg Pillar Cover:  {summary['avg_pillar_coverage']}")
    print(f"Avg Services:      {summary['avg_service_count']}")
    print(f"\nQuality Distribution:")
    for rating, count in summary["quality_distribution"].items():
        print(f"  {rating}: {count}")
    
    print(f"\nPer-Sample Results:")
    for r in results:
        print(f"\n  Sample {r['sample_index']}: {r['quality_rating']} (score: {r['overall_quality_score']})")
        print(f"    Services: {r['service_count']} ({', '.join(r['aws_services_found'][:5])}...)")
        print(f"    Pillars:  {sum(1 for v in r['well_architected_coverage'].values() if v['covered'])}/6")
    
    print(f"\nFull report saved to: {report_path}")


if __name__ == "__main__":
    main()
