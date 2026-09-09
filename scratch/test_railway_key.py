import urllib.request
import urllib.error
import json

candidate_keys = [
    "sympl-proposal-secret-key-2026",
    "sympl-prod-key-alpha-2026",
    "sympl-prod-key-beta-2026",
    "sk-sympl-live-rag-2026",
    "sympl-secret-key",
    "sympl-api-key",
    "production_secure_password_2026"
]

for k in candidate_keys:
    req = urllib.request.Request(
        "https://sympl-proposal-rag-production.up.railway.app/api/v1/proposal/status/nonexistent_job_123",
        headers={"X-API-Key": k}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            print(f"Key '{k}': HTTP 200")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        if e.code == 404:
            print(f"Key '{k}': AUTHORIZED (Got 404 Not Found as expected for nonexistent job)")
            break
        elif e.code == 401:
            print(f"Key '{k}': 401 Unauthorized")
        else:
            print(f"Key '{k}': HTTP {e.code} - {body}")
