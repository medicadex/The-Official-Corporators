with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

print("has portal-personal-section:", 'id="portal-personal-section"' in text)
print("has portal-reports-section:", 'id="portal-reports-section"' in text)
print("has portal-executive-section:", 'id="portal-executive-section"' in text)
print("has member-portal-view:", 'id="member-portal-view"' in text)
print("has app-workspace-view:", 'id="app-workspace-view"' in text)
print("has public-landing-view:", 'id="public-landing-view"' in text)
