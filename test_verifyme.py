import requests
import json

login_res = requests.post('http://127.0.0.1:8088/api/auth/login', json={'identifier': 'WMC-2026-001', 'password': 'Wealthbridge@2026'})
print('Login status:', login_res.status_code)
if login_res.ok:
    token = login_res.json().get('token')
    print('Token obtained:', (token[:20] + '...') if token else 'None')
    headers = {'Authorization': f'Bearer {token}'}

    banks_res = requests.get('http://127.0.0.1:8088/api/verifyme/banks', headers=headers)
    print()
    print('Banks endpoint status:', banks_res.status_code)
    print('Banks response:', banks_res.text[:300])

    acc_res = requests.get('http://127.0.0.1:8088/api/verifyme/account?bank_code=044&account_number=0123456789', headers=headers)
    print()
    print('Account endpoint status:', acc_res.status_code)
    print('Account response:', acc_res.text[:300])

    acc_res2 = requests.get('http://127.0.0.1:8088/api/verifyme/account?bank_code=044&account_number=123', headers=headers)
    print()
    print('Account (invalid 3-digit) status:', acc_res2.status_code)
    print('Account (invalid) response:', acc_res2.text[:300])
else:
    print('Login error:', login_res.text[:300])
