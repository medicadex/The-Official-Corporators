with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

for p in ['dashboard', 'dues', 'targets', 'loans', 'reports', 'profile', 'executive']:
    pos = text.find(f'id="page-{p}"')
    print(f"page-{p}: pos={pos}")
    if pos != -1:
        line_start = text.rfind('\n', 0, pos)
        line_end = text.find('\n', pos)
        print("  line:", repr(text[line_start:line_end].strip()))

# Check children of page-reports and page-executive
p_rep = text.find('id="page-reports"')
if p_rep != -1:
    print("page-reports snippet:", repr(text[p_rep:p_rep+300]))

p_exec = text.find('id="page-executive"')
if p_exec != -1:
    print("page-executive snippet:", repr(text[p_exec:p_exec+300]))
