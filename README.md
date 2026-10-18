# WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
## Web Platform & Infrastructure Suite

**Official Secretariat Email**: `wealthbridge.coopsociety@gmail.com`  
**Statutory Jurisdiction**: Lagos State Cooperative Societies Law (Cap C15)  
**Registered Secretariat**: 13, Agbaje Iloro Street, Odogunyan, Ikorodu, Lagos State, Nigeria  
**Banking Partner**: Polaris Bank Limited  

---

### Folder Architecture & File Guide

| File | Purpose |
| :--- | :--- |
| **`index.html`** | Vizient-inspired frontend single-page platform (Public Landing & Member Cockpit) |
| **`styles.css`** | Custom styling, color tokens, and responsive layout |
| **`app.js`** | Client controller, dynamic 2× loan calculator, and REST API connector |
| **`config.js`** | Frontend configuration file |
| **`wbmf_api.py`** | FastAPI REST service running on `http://127.0.0.1:8088` with interactive Swagger docs |
| **`wbmf_db.py`** | Python MySQL client engine executing stored procedures and queries |
| **`wbmf_cooperative_schema.sql`** | Core MySQL 8.0 schema creating 18 relational tables |
| **`seed_founding_members.sql`** | Seed script for 8 founding members, executive appointments, and ledgers |
| **`stored_procedures_contributions.sql`** | Tripartite monthly contribution split and member onboarding stored procedures |
| **`.env`** | MySQL credentials (`wbmf` / `Loveth123.`) and project constants |
| **`start_platform.bat`** | One-click Windows launcher (starts FastAPI server and opens web app in browser) |

---

### One-Click Launch

Simply double-click **`start_platform.bat`** (or **`START_WEALTHBRIDGE_SERVER.bat`** in the main project folder).

This will:
1. Start the FastAPI backend server on `http://127.0.0.1:8088`.
2. Connect to your local MySQL database `wbmf`.
3. Automatically launch the web application in your default browser.
4. Provide interactive Swagger API documentation at `http://127.0.0.1:8088/docs`.
