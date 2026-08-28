# Hermes "Provider Authentication Failed" — Debugging Guide

## Symptom
Telegram bot returns: "⚠️ Provider authentication failed. Check the configured credentials; raw provider details are in the gateway logs."

## Gateway log signature
```
response ready: platform=telegram chat=XXX time=N.Ns api_calls=0 response=73 chars
```
`api_calls=0` means **no LLM call was made** — the gateway hit an exception during provider resolution.

## Root causes (ordered by likelihood)

### 1. Config key `inference_url` instead of `base_url` (most common for local providers)
The runtime reads `model.default.base_url` from config.yaml. If the key is `inference_url`, the runtime gets empty `base_url`, and the custom runtime for ollama/vllm/llamacpp can never resolve.

**Check**:
```python
python3 -c "
import sys; sys.path.insert(0, '/home/mkanavi/.hermes/venv/lib/python3.12/site-packages')
from hermes_cli.config import load_config
c = load_config()
print('base_url:', repr(c.get('model', {}).get('default', {}).get('base_url')))
"
# Should print: base_url: 'http://localhost:11434/v1'
# If prints: base_url: '' → fix the key
```

**Fix**:
```yaml
# Change from:
inference_url: http://localhost:11434/v1
# To:
base_url: http://localhost:11434/v1
```
Then restart the gateway (process reads config at startup).

### 2. Provider disabled in config
If `providers.<name>.enabled: false` is set, `resolve_runtime_provider()` raises `ValueError` which propagates as auth failure.

### 3. DNS/network failure
If the gateway couldn't resolve the provider endpoint URL. DNS fixes (pinning to 1.1.1.1) resolve this.

### 4. Stale gateway process
The gateway reads config only at startup. If config was changed but gateway wasn't restarted, the old (broken) config is still active.

**Always restart** after config changes:
```bash
ps aux | grep hermes_cli.main | grep -v grep | awk '{print $2}' | xargs kill
sleep 3
nohup /home/mkanavi/.hermes/venv/bin/python -m hermes_cli.main gateway run > /home/mkanavi/.hermes/logs/gateway_stdout.log 2>&1 &
```

## Verification steps
1. Check config: `cat /home/mkanavi/.hermes/config.yaml | grep base_url`
2. Verify Python can read it (see check above)
3. Restart gateway
4. Send test message and check: `grep "api_calls=" /home/mkanavi/.hermes/logs/gateway.log | tail -3`
5. `api_calls=0` = still broken; `api_calls>0` = fixed

## Error message patterns
| Error text in bot | Likely cause |
|---|---|
| "Provider authentication failed" | Config key wrong, provider disabled, or resolution exception |
| "The model returned no response" | LLM call succeeded but model produced no content |
| "Provider rejected the request" | Content policy or API quota issue |
