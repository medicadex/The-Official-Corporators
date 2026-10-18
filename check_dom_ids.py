import re

with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

with open("app.js", "r", encoding="utf-8") as f:
    js = f.read()

print(f"HTML len: {len(html)}, JS len: {len(js)}")

# Find all document.getElementById calls in app.js
get_ids = re.findall(r'document\.getElementById\(["\']([^"\']+)["\']\)', js)
unique_get_ids = set(get_ids)
print(f"Total unique getElementById lookups in app.js: {len(unique_get_ids)}")

missing_in_html = []
for gid in unique_get_ids:
    if f'id="{gid}"' not in html and f"id='{gid}'" not in html:
        missing_in_html.append(gid)

print(f"Missing in HTML ({len(missing_in_html)}):")
for m in sorted(missing_in_html):
    print(" -", m)
