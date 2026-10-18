import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = '<!-- Recent Transactions Table Preview -->'
end_marker = '<div id="page-dues"'

p1 = content.find(start_marker)
p2 = content.find(end_marker)

replacement = """<!-- Recent Transactions Table Preview -->
            <div class="glass-panel p-6 rounded-2xl border border-slate-200 space-y-4">
              <div class="flex justify-between items-center pb-3 border-b border-slate-200">
                <div>
                  <h4 class="text-sm font-bold text-wmcNavy-950 uppercase tracking-wider">Transaction Audit Trail</h4>
                  <p class="text-xs text-slate-400">Live Double-Entry Passbook Ledger</p>
                </div>
                <div class="flex items-center gap-3">
                  <button onclick="refreshTransactions()" class="text-xs text-amber-600 font-bold hover:underline">
                    ↻ Refresh Ledger
                  </button>
                  <a href="#/reports" class="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition">
                    Full Passbook &rarr;
                  </a>
                </div>
              </div>

              <div class="overflow-x-auto">
                <table class="w-full text-left text-xs">
                  <thead>
                    <tr class="border-b border-slate-200 text-slate-400 font-semibold uppercase">
                      <th class="py-2.5">Date / Ref</th>
                      <th class="py-2.5">Ledger Category</th>
                      <th class="py-2.5">Narration</th>
                      <th class="py-2.5">Amount</th>
                      <th class="py-2.5">Status</th>
                    </tr>
                  </thead>
                  <tbody id="transactions-table-body" class="divide-y divide-slate-100">
                    <!-- Populated via live API/database query -->
                    <tr>
                      <td colspan="5" class="py-4 text-center text-slate-400">Loading audit trail...</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

          </div> <!-- Closes page-dashboard -->

          <!-- =================================================================
               PAGE 2: DUES & PAYMENTS
               ================================================================= -->
          """

test_content = content[:p1] + replacement + content[p2:]
soup = BeautifulSoup(test_content, 'html.parser')

print("--- Check direct children of workspace-main ---")
ws_main = soup.find(id='workspace-main')
if ws_main:
    for c in ws_main.find_all(recursive=False):
        if hasattr(c, 'get'):
            print(f"  {c.name} id={c.get('id')}")

print("\n--- Check parent of each page ---")
for pid in ['page-dashboard', 'page-dues', 'page-targets', 'page-loans', 'page-reports', 'page-profile', 'page-executive']:
    el = soup.find(id=pid)
    if el:
        print(f"  {pid}: parent={el.parent.name} id={el.parent.get('id')} class={el.parent.get('class')}")
    else:
        print(f"  {pid}: NOT FOUND")
