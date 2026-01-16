#!/usr/bin/env python3
"""Comprehensive API Test Suite for Alphha DMS"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:7001/api/v1"
RESULTS = {"passed": 0, "failed": 0, "tests": []}

def test(name, condition, details=""):
    """Record test result."""
    status = "✅ PASS" if condition else "❌ FAIL"
    RESULTS["tests"].append({"name": name, "passed": condition, "details": details})
    if condition:
        RESULTS["passed"] += 1
    else:
        RESULTS["failed"] += 1
    print(f"{status}: {name}" + (f" - {details}" if details and not condition else ""))
    return condition

def get_auth_token():
    """Login and get auth token."""
    response = requests.post(f"{BASE_URL}/auth/login/json", json={
        "email": "admin@alphha.local",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def headers(token):
    """Get auth headers."""
    return {"Authorization": f"Bearer {token}"}

print("=" * 60)
print("ALPHHA DMS - COMPREHENSIVE API TEST SUITE")
print("=" * 60)
print()

# ============ 1. HEALTH & MONITORING ============
print("\n--- 1. HEALTH & MONITORING ---")

r = requests.get(f"{BASE_URL}/monitoring/health")
test("Health endpoint accessible", r.status_code == 200)
if r.status_code == 200:
    data = r.json()
    test("Database healthy", data.get("components", {}).get("database") == "healthy")
    test("API healthy", data.get("components", {}).get("api") == "healthy")

r = requests.get(f"{BASE_URL}/auth/sso/status")
test("SSO status endpoint", r.status_code == 200)

# ============ 2. AUTHENTICATION ============
print("\n--- 2. AUTHENTICATION ---")

r = requests.post(f"{BASE_URL}/auth/login/json", json={
    "email": "admin@alphha.local",
    "password": "admin123"
})
test("Admin login", r.status_code == 200)
token = r.json().get("access_token") if r.status_code == 200 else None
test("Access token received", token is not None)

r = requests.post(f"{BASE_URL}/auth/login/json", json={
    "email": "admin@alphha.local",
    "password": "wrongpassword"
})
test("Invalid password rejected", r.status_code == 401)

r = requests.get(f"{BASE_URL}/auth/me", headers=headers(token))
test("Get current user", r.status_code == 200)
if r.status_code == 200:
    user = r.json()
    test("User has email", "email" in user)
    test("User has roles", "roles" in user)

# ============ 3. DOCUMENTS ============
print("\n--- 3. DOCUMENTS ---")

r = requests.get(f"{BASE_URL}/documents", headers=headers(token))
test("List documents", r.status_code == 200)
if r.status_code == 200:
    data = r.json()
    test("Documents response has items", "items" in data)
    test("Documents response has total", "total" in data)
    doc_count = data.get("total", 0)
    test(f"Documents exist ({doc_count})", doc_count > 0)

# Get first document for detail tests
doc_id = None
if r.status_code == 200 and data.get("items"):
    doc_id = data["items"][0]["id"]
    
    r = requests.get(f"{BASE_URL}/documents/{doc_id}", headers=headers(token))
    test("Get document detail", r.status_code == 200)
    if r.status_code == 200:
        doc = r.json()
        test("Document has title", "title" in doc)
        test("Document has lifecycle_status", "lifecycle_status" in doc)
        test("Document has is_owner field", "is_owner" in doc)

# ============ 4. DOCUMENT VERSIONS ============
print("\n--- 4. DOCUMENT VERSIONS ---")

if doc_id:
    r = requests.get(f"{BASE_URL}/documents/{doc_id}/versions", headers=headers(token))
    test("Get document versions", r.status_code == 200)
    if r.status_code == 200:
        versions = r.json()
        test("Versions is list", isinstance(versions, list))
        if versions:
            test("Version has version_number", "version_number" in versions[0])
            test("Version has is_current", "is_current" in versions[0])

# ============ 5. DOCUMENT TYPES ============
print("\n--- 5. DOCUMENT TYPES ---")

r = requests.get(f"{BASE_URL}/documents/types", headers=headers(token))
test("List document types", r.status_code == 200)
if r.status_code == 200:
    types = r.json()
    test("Document types exist", len(types) > 0)

# ============ 6. FOLDERS ============
print("\n--- 6. FOLDERS ---")

r = requests.get(f"{BASE_URL}/documents/folders", headers=headers(token))
test("List folders", r.status_code == 200)

# ============ 7. DEPARTMENTS ============
print("\n--- 7. DEPARTMENTS ---")

r = requests.get(f"{BASE_URL}/documents/departments", headers=headers(token))
test("List departments", r.status_code == 200)

# ============ 8. ENTITIES ============
print("\n--- 8. ENTITIES (Customers/Vendors) ---")

r = requests.get(f"{BASE_URL}/entities/customers", headers=headers(token))
test("List customers", r.status_code == 200)

r = requests.get(f"{BASE_URL}/entities/vendors", headers=headers(token))
test("List vendors", r.status_code == 200)

# ============ 9. SHARING ============
print("\n--- 9. SHARING ---")

if doc_id:
    r = requests.get(f"{BASE_URL}/documents/{doc_id}/permissions", headers=headers(token))
    test("Get document permissions", r.status_code == 200)
    
    r = requests.get(f"{BASE_URL}/documents/{doc_id}/share-links", headers=headers(token))
    test("Get share links", r.status_code == 200)

# ============ 10. COMPLIANCE ============
print("\n--- 10. COMPLIANCE ---")

r = requests.get(f"{BASE_URL}/compliance/retention-policies", headers=headers(token))
test("List retention policies", r.status_code == 200)

r = requests.get(f"{BASE_URL}/compliance/legal-holds", headers=headers(token))
test("List legal holds", r.status_code == 200)

# ============ 11. AUDIT ============
print("\n--- 11. AUDIT ---")

r = requests.get(f"{BASE_URL}/monitoring/dashboard", headers=headers(token))
test("Get audit via monitoring dashboard", r.status_code == 200)
if r.status_code == 200:
    data = r.json()
    test("Dashboard has audit data", "audit" in data)

# ============ 12. PII DETECTION ============
print("\n--- 12. PII DETECTION ---")

r = requests.get(f"{BASE_URL}/pii/patterns", headers=headers(token))
test("List PII patterns", r.status_code == 200)

r = requests.get(f"{BASE_URL}/pii/policies", headers=headers(token))
test("List PII policies", r.status_code == 200)

# ============ 13. SEARCH ============
print("\n--- 13. SEARCH ---")

r = requests.get(f"{BASE_URL}/search/?query=test", headers=headers(token))
test("Search documents", r.status_code == 200)

# ============ 14. TAGS ============
print("\n--- 14. TAGS ---")

r = requests.get(f"{BASE_URL}/tags", headers=headers(token))
test("List tags", r.status_code == 200)

# ============ 15. WORKFLOWS ============
print("\n--- 15. WORKFLOWS ---")

r = requests.get(f"{BASE_URL}/workflows", headers=headers(token))
test("List workflows", r.status_code == 200)

# ============ 16. NOTIFICATIONS ============
print("\n--- 16. NOTIFICATIONS ---")

r = requests.get(f"{BASE_URL}/notifications", headers=headers(token))
test("List notifications", r.status_code == 200)

r = requests.get(f"{BASE_URL}/notifications/unread-count", headers=headers(token))
test("Get unread count", r.status_code == 200)

# ============ 17. ANALYTICS ============
print("\n--- 17. ANALYTICS ---")

r = requests.get(f"{BASE_URL}/analytics/dashboard", headers=headers(token))
test("Analytics dashboard", r.status_code == 200)

# ============ 18. USERS ============
print("\n--- 18. USERS ---")

r = requests.get(f"{BASE_URL}/users", headers=headers(token))
test("List users", r.status_code == 200)
if r.status_code == 200:
    users = r.json()
    test("Users exist", len(users.get("items", users)) > 0 if isinstance(users, dict) else len(users) > 0)

# ============ 19. CONFIG ============
print("\n--- 19. CONFIG ---")

r = requests.get(f"{BASE_URL}/config/options", headers=headers(token))
test("Get config options", r.status_code == 200)

# ============ 20. CONNECTORS ============
print("\n--- 20. EXTERNAL CONNECTORS ---")

r = requests.get(f"{BASE_URL}/connectors/status", headers=headers(token))
test("Connectors status", r.status_code == 200)
if r.status_code == 200:
    connectors = r.json()
    test("Connectors list returned", isinstance(connectors, list))

# ============ 21. MONITORING METRICS ============
print("\n--- 21. MONITORING METRICS ---")

r = requests.get(f"{BASE_URL}/monitoring/health")
test("Health check (no auth)", r.status_code == 200)

r = requests.get(f"{BASE_URL}/monitoring/prometheus")
test("Prometheus metrics", r.status_code == 200)

# ============ 22. ACCESS REQUESTS ============
print("\n--- 22. ACCESS REQUESTS ---")

r = requests.get(f"{BASE_URL}/access-requests/my-requests", headers=headers(token))
test("List my access requests", r.status_code == 200)

r = requests.get(f"{BASE_URL}/access-requests/pending", headers=headers(token))
test("List pending access requests", r.status_code == 200)

# ============ 23. BSI (Bank Statement Intelligence) ============
print("\n--- 23. BSI ---")

r = requests.get(f"{BASE_URL}/bsi/statements", headers=headers(token))
test("List bank statements", r.status_code == 200)

# ============ 24. CHAT/AI ============
print("\n--- 24. AI CHAT ---")

r = requests.get(f"{BASE_URL}/chat/sessions", headers=headers(token))
test("List chat sessions", r.status_code == 200)

# ============ 25. OFFLINE SYNC ============
print("\n--- 25. OFFLINE SYNC ---")

r = requests.get(f"{BASE_URL}/offline/devices", headers=headers(token))
test("List offline devices", r.status_code == 200)

# ============ 26. LICENSE ============
print("\n--- 26. LICENSE ---")

r = requests.get(f"{BASE_URL}/license/status", headers=headers(token))
test("License status", r.status_code == 200)

# ============ SUMMARY ============
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print(f"Total Tests: {RESULTS['passed'] + RESULTS['failed']}")
print(f"✅ Passed: {RESULTS['passed']}")
print(f"❌ Failed: {RESULTS['failed']}")
print(f"Success Rate: {RESULTS['passed'] / (RESULTS['passed'] + RESULTS['failed']) * 100:.1f}%")
print("=" * 60)

# List failed tests
failed = [t for t in RESULTS["tests"] if not t["passed"]]
if failed:
    print("\nFailed Tests:")
    for t in failed:
        print(f"  - {t['name']}: {t.get('details', '')}")

sys.exit(0 if RESULTS["failed"] == 0 else 1)
