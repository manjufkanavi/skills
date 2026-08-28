#!/bin/bash
# Resume Platform — Deployment Verification Script
# Run on VM: bash /home/mkanavi/docker/iacgenie/resume-platform/verify-deployment.sh
# Checks: MinIO bucket, PostgreSQL tables, API health, n8n health, Ollama model

set -euo pipefail

VM_USER="mkanavi"
VM_HOST="192.168.0.118"
PASS=0
FAIL=0

pass() { echo "✅ $1"; ((PASS++)); }
fail() { echo "❌ $1"; ((FAIL++)); }

echo "=========================================="
echo "Resume Platform Deployment Verification"
echo "=========================================="
echo ""

# 1. Check resume-api container
echo "--- Container Status ---"
if docker ps --format '{{.Names}}' | grep -q "iacgenie_resume_api"; then
    pass "resume-api container is running"
else
    fail "resume-api container is NOT running"
fi

if docker ps --format '{{.Names}}' | grep -q "iacgenie_n8n"; then
    pass "n8n container is running"
else
    fail "n8n container is NOT running"
fi

# 2. Check API health
echo ""
echo "--- API Health ---"
if curl -sf http://127.0.0.1:3006/health > /dev/null 2>&1; then
    pass "Resume API health check passed"
else
    fail "Resume API health check failed"
fi

# 3. Check n8n health
echo ""
echo "--- n8n Health ---"
if curl -sf http://127.0.0.1:3005/ > /dev/null 2>&1; then
    pass "n8n is responding"
else
    fail "n8n is NOT responding"
fi

# 4. Check MinIO bucket
echo ""
echo "--- MinIO Bucket ---"
if docker exec iacgenie_minio mc ls iacgenie/resume-files > /dev/null 2>&1; then
    pass "MinIO resume-files bucket exists"
else
    fail "MinIO resume-files bucket does NOT exist"
fi

# 5. Check PostgreSQL tables
echo ""
echo "--- PostgreSQL Tables ---"
if docker exec iacgenie_postgres psql -U lightsrp -d lightsrp -c "SELECT 1 FROM information_schema.tables WHERE table_name='users'" 2>/dev/null | grep -q "1"; then
    pass "PostgreSQL 'users' table exists"
else
    fail "PostgreSQL 'users' table does NOT exist"
fi

if docker exec iacgenie_postgres psql -U lightsrp -d lightsrp -c "SELECT 1 FROM information_schema.tables WHERE table_name='resumes'" 2>/dev/null | grep -q "1"; then
    pass "PostgreSQL 'resumes' table exists"
else
    fail "PostgreSQL 'resumes' table does NOT exist"
fi

# 6. Check Ollama model
echo ""
echo "--- Ollama Model ---"
if docker exec ollama ollama list 2>/dev/null | grep -q "qwen2.5:0.5b"; then
    pass "Ollama qwen2.5:0.5b model is pulled"
else
    fail "Ollama qwen2.5:0.5b model is NOT pulled"
fi

# 7. Check Nginx vHost
echo ""
echo "--- Nginx vHost ---"
if curl -sf -o /dev/null -w "%{http_code}" -H "Host: resume.iacgenie.com" http://127.0.0.1:80 2>/dev/null | grep -q "200\|301\|302\|404"; then
    pass "Nginx responds to resume.iacgenie.com"
else
    fail "Nginx does NOT respond to resume.iacgenie.com"
fi

# 8. Check Cloudflare tunnel ingress
echo ""
echo "--- Cloudflare Tunnel ---"
if grep -q "resume.iacgenie.com" /home/mkanavi/docker/iacgenie/cloudflared/config.yml 2>/dev/null; then
    pass "Cloudflare tunnel has resume.iacgenie.com ingress"
else
    fail "Cloudflare tunnel missing resume.iacgenie.com ingress"
fi

# Summary
echo ""
echo "=========================================="
echo "Summary: $PASS passed, $FAIL failed"
echo "=========================================="

if [ $FAIL -gt 0 ]; then
    echo ""
    echo "Run the manual deployment steps to fix failures:"
    echo "  See references/resume-platform-ansible-deployment.md"
    exit 1
fi

echo ""
echo "All checks passed! Resume platform is fully deployed."
exit 0
