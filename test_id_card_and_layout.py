import sys
sys.stdout.reconfigure(encoding="utf-8")
import requests
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:8088"

def test_dom_structure():
    print("\n--- 1. Testing DOM Structure & Tag Balancing in index.html ---")
    with open("index.html", "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    ws_main = soup.find(id="workspace-main")
    assert ws_main is not None, "workspace-main not found in index.html!"
    
    children_ids = [c.get("id") for c in ws_main.find_all(recursive=False) if hasattr(c, "get")]
    print(f"Direct children of workspace-main: {children_ids}")
    expected_pages = [
        "page-dashboard", "page-dues", "page-targets", 
        "page-loans", "page-reports", "page-profile", "page-executive"
    ]
    for p in expected_pages:
        assert p in children_ids, f"Expected {p} to be a direct child of workspace-main, got {children_ids}"

    # Verify modal-electronic-id exists
    modal_id = soup.find(id="modal-electronic-id")
    assert modal_id is not None, "modal-electronic-id not found in index.html!"
    print("modal-electronic-id exists: PASS")

    # Verify ID buttons
    btn_dash = soup.find(id="btn-dashboard-view-id")
    assert btn_dash is not None, "btn-dashboard-view-id not found in index.html!"
    print("btn-dashboard-view-id exists: PASS")

    btn_prof = soup.find(id="btn-profile-download-id")
    assert btn_prof is not None, "btn-profile-download-id not found in index.html!"
    print("btn-profile-download-id exists: PASS")
    print("DOM Structure Test: PASSED ✅")

def test_api_id_card():
    print("\n--- 2. Testing API ID Card & PDF Endpoints ---")
    # Login as Founding Member WMC-2026-001
    login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "identifier": "WMC-2026-001",
        "password": "Wealthbridge@2026"
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["token"]
    user_data = login_resp.json()["user"]
    member_id = user_data["id"]
    print(f"Logged in successfully as {user_data['full_name']} (ID: {member_id})")

    # 1. Test GET /api/members/{member_id}/id-card
    id_resp = requests.get(
        f"{BASE_URL}/api/members/{member_id}/id-card",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert id_resp.status_code == 200, f"ID card data failed: {id_resp.text}"
    id_json = id_resp.json()
    assert id_json["status"] == "success"
    assert id_json["eligible"] is True
    data = id_json["data"]
    assert data["member_code"] == "WMC-2026-001"
    assert data["secretariat_contact"] == "wealthbridge.coopsociety@gmail.com"
    print(f"ID card JSON verified: {data['full_name']}, Code: {data['member_code']}, Eligible: {id_json['eligible']}")

    # 2. Test GET /api/members/{member_id}/id-card/pdf via Header
    pdf_resp = requests.get(
        f"{BASE_URL}/api/members/{member_id}/id-card/pdf",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert pdf_resp.status_code == 200, f"ID card PDF failed: {pdf_resp.text}"
    assert pdf_resp.headers["Content-Type"] == "application/pdf"
    pdf_bytes = pdf_resp.content
    assert pdf_bytes.startswith(b"%PDF-"), "Invalid PDF header!"
    assert len(pdf_bytes) > 3000, f"PDF too small: {len(pdf_bytes)} bytes"
    print(f"ID Card PDF (Bearer Header) generated successfully: {len(pdf_bytes)} bytes")

    # 3. Test GET /api/members/{member_id}/id-card/pdf via ?token= Query Parameter
    pdf_token_resp = requests.get(
        f"{BASE_URL}/api/members/{member_id}/id-card/pdf?token={token}"
    )
    assert pdf_token_resp.status_code == 200, f"ID card PDF via token query failed: {pdf_token_resp.text}"
    assert pdf_token_resp.content.startswith(b"%PDF-"), "Invalid PDF header via token query!"
    print(f"ID Card PDF (?token= Query) generated successfully: {len(pdf_token_resp.content)} bytes")

    # Save a copy to verify on disk
    with open("test_output_id_card.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("Saved test_output_id_card.pdf cleanly.")
    print("API ID Card & PDF Test: PASSED ✅")

if __name__ == "__main__":
    test_dom_structure()
    test_api_id_card()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! 🎉")
