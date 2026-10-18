"""
Automated Verification Suite: Cooperative Member Statements & Reports
"""
import requests

login_payload = {
    'identifier': 'WMC-2026-001',
    'password': 'Wealthbridge@2026'
}
r = requests.post('http://127.0.0.1:8088/api/auth/login', json=login_payload)
assert r.status_code == 200, f'Login failed: {r.text}'
res = r.json()
token = res['token']
member_id = res['user']['id']
headers = {'Authorization': f'Bearer {token}'}

print('=== 1. Testing Financial Years API ===')
r_yrs = requests.get(f'http://127.0.0.1:8088/api/members/{member_id}/reports/years', headers=headers)
assert r_yrs.status_code == 200
years = r_yrs.json()['data']
print('  + Available Years:', years)
assert 2026 in years

print('\n=== 2. Testing Passbook Ledger (Tripartite) ===')
r_led = requests.get(f'http://127.0.0.1:8088/api/members/{member_id}/reports/ledger?year=2026', headers=headers)
assert r_led.status_code == 200
led_data = r_led.json()['data']
print('  + Cooperator:', led_data['member']['full_name'], f"({led_data['member']['member_code']})")
print('  + Opening Net Equity:', led_data['opening_balances']['total_equity'])
print('  + Inward Credits:', led_data['period_movements']['total_credits'])
print('  + Outward Debits:', led_data['period_movements']['total_debits'])
print('  + Closing Net Equity:', led_data['closing_balances']['total_equity'])
print('  + 2x Borrowing Limit:', led_data['closing_balances']['ordinary_loan_capacity_2x'])
print('  + Total Entries:', len(led_data['entries']))
assert len(led_data['entries']) > 0

print('\n=== 3. Testing Passbook Ledger PDF Generation ===')
r_led_pdf = requests.get(f'http://127.0.0.1:8088/api/members/{member_id}/reports/ledger/pdf?year=2026&token={token}')
assert r_led_pdf.status_code == 200
assert r_led_pdf.headers.get('content-type') == 'application/pdf'
assert len(r_led_pdf.content) > 1000
print(f'  + Passbook PDF generated: {len(r_led_pdf.content)} bytes, Filename: {r_led_pdf.headers.get("Content-Disposition")}')

print('\n=== 4. Testing Inward Remittances (Credits) ===')
r_cred = requests.get(f'http://127.0.0.1:8088/api/members/{member_id}/reports/credits?year=2026', headers=headers)
assert r_cred.status_code == 200
cred_data = r_cred.json()['data']
print('  + Total Remitted:', cred_data['summary']['total_remitted'])
print('  + Remittance Count:', cred_data['summary']['remittance_count'])
r_cred_pdf = requests.get(f'http://127.0.0.1:8088/api/members/{member_id}/reports/credits/pdf?year=2026&token={token}')
assert r_cred_pdf.status_code == 200
print(f'  + Credits PDF generated: {len(r_cred_pdf.content)} bytes')

print('\n=== 5. Testing Outward Disbursements (Debits) ===')
r_deb = requests.get(f'http://127.0.0.1:8088/api/members/{member_id}/reports/debits?year=2026', headers=headers)
assert r_deb.status_code == 200
deb_data = r_deb.json()['data']
print('  + Total Disbursed:', deb_data['summary']['total_disbursed'])
print('  + Disbursement Count:', deb_data['summary']['disbursement_count'])
r_deb_pdf = requests.get(f'http://127.0.0.1:8088/api/members/{member_id}/reports/debits/pdf?year=2026&token={token}')
assert r_deb_pdf.status_code == 200
print(f'  + Debits PDF generated: {len(r_deb_pdf.content)} bytes')

print('\n=== 6. Testing Loan Amortization Statement ===')
r_loans = requests.get(f'http://127.0.0.1:8088/api/members/{member_id}/reports/loans', headers=headers)
assert r_loans.status_code == 200
loans_data = r_loans.json()['data']
print('  + Active Facilities:', loans_data['summary']['total_loans_count'])
print('  + Statutory Policy:', loans_data['summary']['statutory_interest_rate'])
r_loans_pdf = requests.get(f'http://127.0.0.1:8088/api/members/{member_id}/reports/loans/pdf?token={token}')
assert r_loans_pdf.status_code == 200
print(f'  + Loans PDF generated: {len(r_loans_pdf.content)} bytes')

print('\n[ALL TESTS PASSED SUCCESSFULLY]')
