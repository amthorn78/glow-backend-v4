import os
import json
from flask import request, jsonify

# --- Configuration ---
IS_ENABLED = os.environ.get("ENABLE_WRITER_CONTRACT_AUDIT") == "1"
IS_STRICT = os.environ.get("WRITER_AUDIT_STRICT") == "1"
WATCHED_PATHS = [p.strip() for p in os.environ.get("WRITER_AUDIT_PATHS", "").split(",") if p.strip()]

FINDINGS = []
MAX_FINDINGS = 20

# --- Contract Rules ---
OK_BODY = b"{\"status\":\"ok\"}"

def audit_writer_response(response):
    """Audits a response against the writer contract rules."""
    if not IS_ENABLED or request.method not in {"POST", "PUT", "PATCH", "DELETE"} or request.path not in WATCHED_PATHS:
        return response

    if not (200 <= response.status_code < 300):
        return response

    findings = []

    # Rule: 204 must have empty body
    if response.status_code == 204 and response.get_data():
        findings.append("204_with_body")

    # Rule: 200 must have exact body
    if response.status_code == 200 and response.get_data() != OK_BODY:
        findings.append("200_invalid_body")

    # Rule: 201 must have Location header and empty body
    if response.status_code == 201:
        if "Location" not in response.headers:
            findings.append("201_missing_location")
        if response.get_data():
            findings.append("201_with_body")

    # Rule: All 2xx writes must have Cache-Control: no-store
    if "no-store" not in response.headers.get("Cache-Control", ""):
        findings.append("missing_no_store")

    if findings:
        log_violation(request, response, findings)
        if IS_STRICT:
            return jsonify({"error": "writer_contract_violation"}), 500

    return response

def log_violation(request, response, findings):
    """Logs a writer contract violation."""
    log_entry = {
        "path": request.path,
        "method": request.method,
        "status_code": response.status_code,
        "findings": findings,
        "body_size": len(response.get_data()),
        "cache_control": response.headers.get("Cache-Control"),
    }
    # In a real app, this would use app.logger.error()
    print(f"WRITER_AUDIT_FAIL: {log_entry}")
    FINDINGS.insert(0, log_entry)
    if len(FINDINGS) > MAX_FINDINGS:
        FINDINGS.pop()

def create_writer_audit_endpoint(app):
    """Creates the /__audit/writers endpoint."""
    if not IS_ENABLED:
        return

    @app.route("/__audit/writers", methods=["GET"])
    def get_writer_audit_info():
        return jsonify({
            "enabled": IS_ENABLED,
            "strict": IS_STRICT,
            "watched_paths": WATCHED_PATHS,
            "rules": [
                "204 -> empty body",
                "200 -> exactly {\"status\":\"ok\"}",
                "201 -> Location header + empty body",
                "2xx -> Cache-Control: no-store",
            ],
            "recent_findings": FINDINGS,
        })

