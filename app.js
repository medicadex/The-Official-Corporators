/**
 * =============================================================================
 * WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
 * CLIENT INTERACTION & RBAC PLATFORM ENGINE (app.js)
 * Official Contact: wealthbridge.coopsociety@gmail.com
 * Document Reference: SOP-WMC-2026-V1 & WMC-BYELAWS-REV-2026-V1
 * =============================================================================
 */

const API_BASE_URL = window.API_BASE_URL || (window.location.protocol.startsWith('http') ? window.location.origin + "/api" : "http://127.0.0.1:8088/api");

// Keep authentication transport centralized so API authorization is enforced server-side.
const nativeFetch = window.fetch.bind(window);
window.fetch = async (resource, options = {}) => {
  const url = typeof resource === "string" ? resource : (resource && resource.url ? resource.url : "");
  const isApiRequest = typeof url === "string" && url.startsWith(API_BASE_URL);
  const isPublicAuthRequest = typeof url === "string" && (url.endsWith("/auth/login") || url.endsWith("/register"));
  const token = localStorage.getItem("wmc_token");

  let opts = { ...options };
  if (isApiRequest && !isPublicAuthRequest && token) {
    const headers = new Headers(opts.headers || {});
    if (!headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    opts.headers = headers;
  }

  const response = await nativeFetch(resource, opts);

  // If session expired on the backend, inform the application
  if (response.status === 401 && isApiRequest && !isPublicAuthRequest) {
    console.warn("Authentication session expired for API call:", url);
  }

  return response;
};

function formatNaira(val) {
  const num = parseFloat(val) || 0;
  return "₦" + num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
window.formatNaira = formatNaira;

function formatApiErrorMessage(detail, fallback = "An unexpected error occurred.") {
  if (!detail) return fallback;
  let msg = "";
  if (typeof detail === "string") {
    msg = detail;
  } else if (Array.isArray(detail)) {
    msg = detail.map(d => {
      if (typeof d === "string") return d;
      const field = (d.loc && d.loc.length > 0) ? d.loc[d.loc.length - 1] : "";
      const fieldName = field ? field.replace(/_/g, " ").toUpperCase() + ": " : "";
      return `${fieldName}${d.msg || "invalid field"}`;
    }).join("; ");
  } else if (typeof detail === "object") {
    msg = detail.msg || detail.message || JSON.stringify(detail);
  } else {
    msg = String(detail);
  }

  // Detect and translate internal database/network errors into cooperative friendly language
  const technicalKeywords = [
    "pooler.supabase",
    "could not translate host",
    "name or service not known",
    "connection to server",
    "timeout expired",
    "operationalerror",
    "psycopg2",
    "mysql.connector",
    "econnrefused",
    "failed to fetch",
    "database error",
    "authentication service error",
    "internal server error",
    "ssl connection has been closed"
  ];

  const lower = msg.toLowerCase();
  for (const kw of technicalKeywords) {
    if (lower.includes(kw)) {
      return "Cooperative servers are temporarily unreachable. Please check your internet connection and try again in a few moments, or contact the Secretariat (wealthbridge.coopsociety@gmail.com).";
    }
  }

  return msg;
}

// Fallback founder dataset if backend API is cold-starting
const FALLBACK_FOUNDERS = [
  { id: 1, member_code: "WMC-2026-001", full_name: "Qazeem Adebowale", executive_portfolio: "PRESIDENT", status: "ACTIVE", contribution_tier: "STANDARD", admission_date: "2026-09-26", share_units: 6, share_equity_paid: 6000, savings_balance: 8000, welfare_pool: 1000 },
  { id: 2, member_code: "WMC-2026-002", full_name: "Olaleke Olaoye", executive_portfolio: "GENERAL_SECRETARY", status: "ACTIVE", contribution_tier: "STANDARD", admission_date: "2026-09-26", share_units: 5, share_equity_paid: 5000, savings_balance: 0, welfare_pool: 0 },
  { id: 3, member_code: "WMC-2026-003", full_name: "Sulaimon Olajide", executive_portfolio: "LEGAL_COMPLIANCE_LEAD", status: "ACTIVE", contribution_tier: "STANDARD", admission_date: "2026-09-26", share_units: 5, share_equity_paid: 5000, savings_balance: 0, welfare_pool: 0 },
  { id: 4, member_code: "WMC-2026-004", full_name: "Rukayat Yahaya", executive_portfolio: "FINANCIAL_SECRETARY", status: "ACTIVE", contribution_tier: "STANDARD", admission_date: "2026-09-26", share_units: 5, share_equity_paid: 5000, savings_balance: 0, welfare_pool: 0 },
  { id: 5, member_code: "WMC-2026-005", full_name: "Evelyn Omokosi", executive_portfolio: "TREASURER", status: "ACTIVE", contribution_tier: "STANDARD", admission_date: "2026-09-26", share_units: 5, share_equity_paid: 5000, savings_balance: 0, welfare_pool: 0 },
  { id: 6, member_code: "WMC-2026-006", full_name: "Yusuf Adebowale", executive_portfolio: "TECHNOLOGY_SYSTEMS_LEAD", status: "ACTIVE", contribution_tier: "STANDARD", admission_date: "2026-09-26", share_units: 5, share_equity_paid: 5000, savings_balance: 0, welfare_pool: 0 },
  { id: 7, member_code: "WMC-2026-007", full_name: "Hammed Badmus", executive_portfolio: null, status: "ACTIVE", contribution_tier: "STANDARD", admission_date: "2026-09-26", share_units: 5, share_equity_paid: 5000, savings_balance: 0, welfare_pool: 0 },
  { id: 8, member_code: "WMC-2026-008", full_name: "Azeezat Adebowale", executive_portfolio: null, status: "ACTIVE", contribution_tier: "STANDARD", admission_date: "2026-09-26", share_units: 5, share_equity_paid: 5000, savings_balance: 0, welfare_pool: 0 }
];

let currentUser = null;
let cachedMembers = [];
let cachedStatement = null;
let cachedBanks = [];
let banksLoaded = false;

// -----------------------------------------------------------------------------
// INITIALIZATION
// -----------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  updateCalculator();
  setupContributionSplitPreview();
  restoreSavedSession();
  fetchAllMembers();
  window.addEventListener("hashchange", handleRoute);
  handleRoute();
});

// -----------------------------------------------------------------------------
// 1. SESSION MANAGEMENT & AUTHENTICATION STATE
// -----------------------------------------------------------------------------
function restoreSavedSession() {
  const saved = localStorage.getItem("wmc_user");
  if (saved) {
    try {
      currentUser = JSON.parse(saved);
      updateAuthNavUI();
      loadAuthenticatedMember();
      if (currentUser.is_executive) {
        loadExecutiveData();
      }
      if (currentUser.must_change_password) {
        setTimeout(() => {
          openChangePasswordModal(true);
        }, 500);
      }
    } catch (e) {
      console.warn("Failed to parse saved session:", e);
      localStorage.removeItem("wmc_user");
      currentUser = null;
      updateAuthNavUI();
    }
  } else {
    currentUser = null;
    updateAuthNavUI();
  }
}

function updateAuthNavUI() {
  const guestBox = document.getElementById("nav-guest-actions");
  const authBox = document.getElementById("nav-auth-actions");
  const avatar = document.getElementById("nav-user-avatar");
  const userName = document.getElementById("nav-user-name");
  const roleBadge = document.getElementById("nav-user-role-badge");
  const portalToggleLabel = document.getElementById("portal-toggle-label");

  if (!currentUser) {
    if (guestBox) guestBox.classList.remove("hidden");
    if (authBox) authBox.classList.add("hidden");
    if (portalToggleLabel) portalToggleLabel.textContent = "Member Portal";
    return;
  }

  // Logged-in State
  if (guestBox) guestBox.classList.add("hidden");
  if (authBox) authBox.classList.remove("hidden");

  // Initials
  const names = (currentUser.full_name || "Cooperator").split(" ");
  const initials = names.length > 1 ? (names[0][0] + names[1][0]).toUpperCase() : names[0].substring(0, 2).toUpperCase();
  if (avatar) avatar.textContent = initials;

  if (userName) userName.textContent = currentUser.full_name;
  if (roleBadge) {
    if (currentUser.is_admin_only) {
      roleBadge.textContent = "SUPER ADMIN (DEV)";
      roleBadge.className = "inline-block text-[9px] font-black uppercase tracking-wider text-amber-300 bg-slate-900 border border-amber-500/50 px-2 py-0.5 rounded";
    } else if (currentUser.primary_role === "PRESIDENT" || currentUser.primary_role === "SUPER_ADMIN") {
      roleBadge.textContent = currentUser.primary_role.replace(/_/g, " ");
      roleBadge.className = "inline-block text-[9px] font-black uppercase tracking-wider text-amber-800 bg-amber-200 px-1.5 py-0.5 rounded";
    } else if (currentUser.is_executive) {
      roleBadge.textContent = currentUser.primary_role.replace(/_/g, " ");
      roleBadge.className = "inline-block text-[9px] font-black uppercase tracking-wider text-blue-800 bg-blue-100 px-1.5 py-0.5 rounded";
    } else {
      roleBadge.textContent = currentUser.primary_role.replace(/_/g, " ");
      roleBadge.className = "inline-block text-[9px] font-black uppercase tracking-wider text-emerald-800 bg-emerald-100 px-1.5 py-0.5 rounded";
    }
  }

  if (portalToggleLabel) {
    portalToggleLabel.textContent = currentUser.is_admin_only ? "Developer Console" : currentUser.member_code;
  }

  // Update Left Vertical Sidebar & Topbar User Elements
  const sideUserName = document.getElementById("sidebar-user-name");
  const sideAvatarInitials = document.getElementById("sidebar-avatar-initials");
  const sideRoleBadge = document.getElementById("sidebar-user-role-badge");
  const topbarUserAvatar = document.getElementById("topbar-user-avatar");
  const topbarUserName = document.getElementById("topbar-user-name");
  const topbarUserCode = document.getElementById("topbar-user-code");
  const topbarKycText = document.getElementById("topbar-kyc-text");
  const sidebarKycBadge = document.getElementById("sidebar-kyc-badge");
  const sidebarExecSection = document.getElementById("sidebar-exec-section");
  const kycPct = currentUser.kyc_completion_percent || 0;

  if (sideUserName) sideUserName.textContent = currentUser.full_name || "Cooperator";
  if (sideAvatarInitials) sideAvatarInitials.textContent = initials;
  if (topbarUserAvatar) topbarUserAvatar.textContent = initials;
  if (topbarUserName) topbarUserName.textContent = currentUser.full_name || "Cooperator";
  if (topbarUserCode) topbarUserCode.textContent = currentUser.member_code || "WMC-MEMBER";
  if (topbarKycText) topbarKycText.textContent = `KYC: ${kycPct}%`;
  if (sidebarKycBadge) sidebarKycBadge.textContent = `${kycPct}%`;

  if (sideRoleBadge) {
    if (currentUser.is_admin_only) {
      sideRoleBadge.textContent = "SUPER ADMIN (DEV)";
      sideRoleBadge.className = "inline-block text-[9px] font-black uppercase tracking-wider text-amber-300 bg-slate-900 px-1.5 py-0.2 rounded border border-amber-500/40";
    } else {
      sideRoleBadge.textContent = (currentUser.primary_role || "MEMBER").replace(/_/g, " ");
      sideRoleBadge.className = "inline-block text-[9px] font-black uppercase tracking-wider text-amber-300 bg-amber-500/20 px-1.5 py-0.2 rounded";
    }
  }

  if (sidebarExecSection) {
    if (currentUser.is_executive || currentUser.is_admin_only) {
      sidebarExecSection.classList.remove("hidden");
    } else {
      sidebarExecSection.classList.add("hidden");
    }
  }

  // If pure admin, hide personal member links in sidebar
  const memberLinks = ["dashboard", "dues", "targets", "loans"];
  memberLinks.forEach(lnk => {
    const el = document.getElementById(`sidebar-link-${lnk}`);
    if (el) {
      if (currentUser.is_admin_only) el.classList.add("hidden");
      else el.classList.remove("hidden");
    }
  });

  // Topbar Dashboard Electronic ID Button: Active only after Secretariat approval
  const dashIdBtn = document.getElementById("btn-dashboard-view-id");
  const isIdApproved = ["ACTIVE", "SYSTEM_ADMINISTRATOR"].includes(currentUser.membership_status) || currentUser.is_executive;
  if (dashIdBtn) {
    if (isIdApproved) {
      dashIdBtn.classList.remove("opacity-50");
      dashIdBtn.title = "View Official Electronic ID Card";
      dashIdBtn.innerHTML = `<span>🪪</span><span>Digital ID</span>`;
    } else {
      dashIdBtn.classList.add("opacity-50");
      dashIdBtn.title = "ID Card Locked (Awaiting Secretariat Approval)";
      dashIdBtn.innerHTML = `<span>🔒</span><span>Digital ID</span>`;
    }
  }

  // Populate Navbar Dropdown & Topbar Dropdown User Details
  const ddAvatar = document.getElementById("dd-user-avatar");
  const ddName = document.getElementById("dd-user-name");
  const ddCode = document.getElementById("dd-user-code");
  const ddRole = document.getElementById("dd-user-role");
  const ddEmail = document.getElementById("dd-user-email");
  const ddKyc = document.getElementById("dd-user-kyc");
  const ddPortalTitle = document.getElementById("dd-portal-toggle-title");
  const ddPortalDesc = document.getElementById("dd-portal-toggle-desc");

  const topbarDdAvatar = document.getElementById("topbar-dd-user-avatar");
  const topbarDdName = document.getElementById("topbar-dd-user-name");
  const topbarDdCode = document.getElementById("topbar-dd-user-code");
  const topbarDdRole = document.getElementById("topbar-dd-user-role");
  const topbarDdPortalTitle = document.getElementById("topbar-dd-portal-toggle-title");
  const profileSecBadge = document.getElementById("profile-security-badge");

  if (ddAvatar) ddAvatar.textContent = initials;
  if (ddName) ddName.textContent = currentUser.full_name || "Cooperator";
  if (ddCode) ddCode.textContent = currentUser.member_code || "WMC-MEMBER";
  if (ddRole) ddRole.textContent = (currentUser.primary_role || "MEMBER").replace(/_/g, " ");
  if (ddEmail) ddEmail.textContent = currentUser.email || "No email";
  if (ddKyc) ddKyc.textContent = `KYC ${kycPct}%`;
  if (ddPortalTitle) ddPortalTitle.textContent = currentUser.is_executive ? "Executive Desk" : "Member Portal";
  if (ddPortalDesc) ddPortalDesc.textContent = currentUser.is_executive ? "Administrative control center" : "Cooperative accounts & loans";

  if (topbarDdAvatar) topbarDdAvatar.textContent = initials;
  if (topbarDdName) topbarDdName.textContent = currentUser.full_name || "Cooperator";
  if (topbarDdCode) topbarDdCode.textContent = currentUser.member_code || "WMC-MEMBER";
  if (topbarDdRole) topbarDdRole.textContent = (currentUser.primary_role || "MEMBER").replace(/_/g, " ");
  if (topbarDdPortalTitle) topbarDdPortalTitle.textContent = "Public Site";

  if (profileSecBadge) {
    if (currentUser.must_change_password) {
      profileSecBadge.textContent = "⚠️ Default Password (Action Required)";
      profileSecBadge.className = "px-2.5 py-0.5 rounded text-[10px] font-black bg-amber-100 text-amber-800 border border-amber-300";
    } else {
      profileSecBadge.textContent = "🛡️ Password Secured";
      profileSecBadge.className = "px-2.5 py-0.5 rounded text-[10px] font-black bg-emerald-100 text-emerald-800 border border-emerald-200";
    }
  }
}

// -----------------------------------------------------------------------------
// 2. AUTHENTICATION & LOGIN WORKFLOW
// -----------------------------------------------------------------------------
function openLoginModal() {
  const modal = document.getElementById("modal-login");
  if (modal) modal.classList.remove("hidden");
  hideLoginAlert();
}

function closeLoginModal() {
  const modal = document.getElementById("modal-login");
  if (modal) modal.classList.add("hidden");
}

function togglePasswordVisibility(inputId) {
  const input = document.getElementById(inputId);
  if (!input) return;
  input.type = input.type === "password" ? "text" : "password";
}

function showLoginAlert(msg, type = "error") {
  const box = document.getElementById("login-alert");
  if (!box) return;
  box.classList.remove("hidden", "bg-red-50", "text-red-800", "border-red-200", "bg-emerald-50", "text-emerald-800");
  if (type === "error") {
    box.className = "p-3 rounded-xl text-xs mb-4 bg-red-50 text-red-800 border border-red-200 font-semibold";
  } else {
    box.className = "p-3 rounded-xl text-xs mb-4 bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold";
  }
  box.textContent = msg;
}

function hideLoginAlert() {
  const box = document.getElementById("login-alert");
  if (box) box.classList.add("hidden");
}

async function handleLoginSubmit(e) {
  if (e && e.preventDefault) e.preventDefault();

  const idInput = document.getElementById("login-identifier");
  const passInput = document.getElementById("login-password");
  const submitBtn = document.getElementById("btn-login-submit");

  const identifier = idInput ? idInput.value.trim() : "";
  const password = passInput ? passInput.value.trim() : "";

  if (!identifier || !password) {
    showLoginAlert("Please provide both account identifier and password.", "error");
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Verifying Credentials...";
  }

  try {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, password })
    });

    const data = await res.json();

    if (!res.ok) {
      const loginErr = formatApiErrorMessage(data.detail, "Authentication failed. Please verify credentials.");
      showLoginAlert(`⚠️ ${loginErr}`, "error");
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Sign In to Portal →";
      }
      return;
    }

    // Success!
    currentUser = data.user;
    localStorage.setItem("wmc_user", JSON.stringify(currentUser));
    localStorage.setItem("wmc_token", data.token);

    showLoginAlert(`✅ Welcome back, ${currentUser.full_name}! Redirecting to portal...`, "success");

    setTimeout(() => {
      closeLoginModal();
      updateAuthNavUI();
      showMemberPortal();
      loadAuthenticatedMember();
      if (currentUser.is_executive) {
        loadExecutiveData();
      }
      if (data.login_prompts && data.login_prompts.length > 0) {
        renderLoginPrompts(data.login_prompts);
      }
      if (currentUser.must_change_password) {
        setTimeout(() => {
          openChangePasswordModal(true);
        }, 500);
      }
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Sign In to Portal →";
      }
    }, 700);

  } catch (err) {
    console.error("Login fetch error:", err);
    showLoginAlert("⚠️ Cooperative servers are temporarily unreachable. Please check your internet connection and try again in a few moments, or contact the Secretariat (wealthbridge.coopsociety@gmail.com).", "error");
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Sign In to Portal →";
    }
  }
}

function quickLoginAs(memberCode, password = "Wealthbridge@2026") {
  const idInput = document.getElementById("login-identifier");
  const passInput = document.getElementById("login-password");
  if (idInput) idInput.value = memberCode;
  if (passInput) passInput.value = password;
  handleLoginSubmit(new Event("submit"));
}

function handleLogout() {
  localStorage.removeItem("wmc_user");
  localStorage.removeItem("wmc_token");
  currentUser = null;
  updateAuthNavUI();
  showPublicLanding();
  alert("You have been signed out successfully.");
}

// -----------------------------------------------------------------------------
// 3. CLIENT-SIDE ROUTER & WORKSPACE PAGINATION
// -----------------------------------------------------------------------------
const VALID_ROUTES = ["landing", "dashboard", "dues", "targets", "loans", "reports", "profile", "executive"];

function getHashRoute() {
  const hash = window.location.hash || "#/landing";
  const clean = hash.replace(/^#\/?/, "").split("?")[0].trim().toLowerCase();
  return VALID_ROUTES.includes(clean) ? clean : "landing";
}

function navigateTo(route) {
  const clean = String(route).replace(/^#\/?/, "").split("?")[0].trim().toLowerCase();
  window.location.hash = `#/${clean}`;
}
window.navigateTo = navigateTo;

function handleRoute() {
  const route = getHashRoute();

  // Route Guards
  if (route !== "landing") {
    if (!currentUser) {
      window.location.hash = "#/landing";
      openLoginModal();
      return;
    }
    if (currentUser.is_admin_only && ["dashboard", "dues", "targets", "loans"].includes(route)) {
      window.location.hash = "#/executive";
      return;
    }
    if (route === "executive" && (!currentUser.is_executive && !currentUser.is_admin_only)) {
      alert("Access Denied: Executive governance clearance required.");
      window.location.hash = "#/dashboard";
      return;
    }
  }

  // View Switching (Public Landing vs Authenticated App Workspace)
  const publicLanding = document.getElementById("public-landing-view");
  const appWorkspace = document.getElementById("app-workspace-view");
  const publicHeader = document.getElementById("public-header");
  const publicFooter = document.getElementById("public-footer");
  const landingAuthBanner = document.getElementById("landing-authenticated-banner");

  if (route === "landing") {
    if (publicLanding) publicLanding.classList.remove("hidden");
    if (appWorkspace) appWorkspace.classList.add("hidden");
    if (publicHeader) publicHeader.classList.remove("hidden");
    if (publicFooter) publicFooter.classList.remove("hidden");

    if (currentUser && landingAuthBanner) {
      landingAuthBanner.classList.remove("hidden");
      const nameEl = document.getElementById("landing-banner-name");
      if (nameEl) nameEl.textContent = currentUser.full_name;
    } else if (landingAuthBanner) {
      landingAuthBanner.classList.add("hidden");
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }

  // Authenticated Workspace Views
  if (publicLanding) publicLanding.classList.add("hidden");
  if (appWorkspace) appWorkspace.classList.remove("hidden");
  if (publicHeader) publicHeader.classList.add("hidden");
  if (publicFooter) publicFooter.classList.add("hidden");

  // Toggle page views
  const pages = ["dashboard", "dues", "targets", "loans", "reports", "profile", "executive"];
  pages.forEach(p => {
    const el = document.getElementById(`page-${p}`);
    if (el) {
      if (p === route) {
        el.classList.remove("hidden");
      } else {
        el.classList.add("hidden");
      }
    }
  });

  // Update Breadcrumb & Header Title
  updateAppHeaderTitle(route);

  // Update Active Link Styling in Sidebar
  updateSidebarActive(route);

  // Close Mobile Drawer
  toggleMobileSidebar(false);

  // Hydrate Data for Target Page
  if (route === "dashboard") {
    loadAuthenticatedMember();
    loadMemberCurrentPaymentAdvice();
    loadMemberDedicatedAccount(currentUser ? currentUser.id : null);
    loadMemberTargetSavings();
    refreshTransactions();
  } else if (route === "dues") {
    loadMemberCurrentPaymentAdvice();
    loadMemberDedicatedAccount(currentUser ? currentUser.id : null);
  } else if (route === "targets") {
    loadMemberTargetSavings();
  } else if (route === "loans") {
    loadLoansPageData();
  } else if (route === "reports") {
    initMemberReportsCenter();
  } else if (route === "profile") {
    populateProfilePageData();
    loadMemberDividendSection();
  } else if (route === "executive") {
    loadExecutiveData();
    switchExecutiveTab("members");
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}
window.handleRoute = handleRoute;

function updateAppHeaderTitle(route) {
  const breadcrumb = document.getElementById("app-page-breadcrumb");
  const title = document.getElementById("app-page-title");
  
  const map = {
    dashboard: { bc: "Cooperator Workspace", title: "📊 Member Dashboard" },
    dues: { bc: "Billing & Remittances", title: "💳 Dues & Payments" },
    targets: { bc: "Goal Vaults", title: "🎯 Dynamic Target Savings" },
    loans: { bc: "Financing & Solidarity", title: "🤝 0% Interest Loans & Welfare" },
    reports: { bc: "Statutory Books", title: "📑 Financial Reports & Passbook" },
    profile: { bc: "KYC & Identity", title: "👤 My Profile & Verification" },
    executive: { bc: "Board & Secretarial Console", title: "🏛️ Executive Governance Desks" }
  };

  const item = map[route] || { bc: "Workspace", title: "Member Dashboard" };
  if (breadcrumb) breadcrumb.textContent = item.bc;
  if (title) title.innerHTML = item.title;
}

function updateSidebarActive(activeRoute) {
  const routes = ["dashboard", "dues", "targets", "loans", "reports", "profile", "executive"];
  const activeClass = "sidebar-nav-item flex items-center justify-between px-3.5 py-3 rounded-xl transition bg-gradient-to-r from-wmcNavy-900 to-slate-900 text-amber-300 font-bold border-l-4 border-amber-400 shadow-md";
  const inactiveClass = "sidebar-nav-item flex items-center justify-between px-3.5 py-3 rounded-xl transition text-slate-300 hover:text-white hover:bg-white/5 font-medium";

  routes.forEach(r => {
    const link = document.getElementById(`sidebar-link-${r}`);
    if (link) {
      if (r === activeRoute) {
        link.className = activeClass;
      } else {
        link.className = inactiveClass;
      }
    }
  });
}

function toggleMobileSidebar(open) {
  const sidebar = document.getElementById("app-sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (!sidebar) return;

  if (open) {
    sidebar.classList.remove("-translate-x-full");
    sidebar.classList.add("translate-x-0");
    if (backdrop) backdrop.classList.remove("hidden");
  } else {
    sidebar.classList.add("-translate-x-full");
    sidebar.classList.remove("translate-x-0");
    if (backdrop) backdrop.classList.add("hidden");
  }
}
window.toggleMobileSidebar = toggleMobileSidebar;

function togglePortalMode() {
  if (!currentUser) {
    openLoginModal();
    return;
  }
  const route = getHashRoute();
  if (route === "landing") {
    showMemberPortal();
  } else {
    showPublicLanding();
  }
}
window.togglePortalMode = togglePortalMode;

function showMemberPortal() {
  if (currentUser && currentUser.is_admin_only) {
    navigateTo("executive");
  } else {
    navigateTo("dashboard");
  }
}
window.showMemberPortal = showMemberPortal;

function showPublicLanding() {
  navigateTo("landing");
}
window.showPublicLanding = showPublicLanding;

function switchPortalView(viewMode) {
  if (viewMode === "executive") {
    navigateTo("executive");
  } else if (viewMode === "reports") {
    navigateTo("reports");
  } else {
    navigateTo("dashboard");
  }
}
window.switchPortalView = switchPortalView;

function populateProfilePageData() {
  if (!currentUser) return;
  const nameEl = document.getElementById("prof-page-name");
  const codeEl = document.getElementById("prof-page-code");
  const emailEl = document.getElementById("prof-page-email");
  const phoneEl = document.getElementById("prof-page-phone");
  const addrEl = document.getElementById("prof-page-address");
  const tierEl = document.getElementById("prof-page-tier");
  const bankEl = document.getElementById("prof-page-bank");
  const accEl = document.getElementById("prof-page-account");
  const accNameEl = document.getElementById("prof-page-accname");
  const kycEl = document.getElementById("prof-page-kyc");

  if (nameEl) nameEl.textContent = currentUser.full_name || "N/A";
  if (codeEl) codeEl.textContent = currentUser.member_code || "N/A";
  if (emailEl) emailEl.textContent = currentUser.email || "N/A";
  if (phoneEl) phoneEl.textContent = currentUser.phone || "N/A";
  if (addrEl) addrEl.textContent = currentUser.residential_address || "Lagos State, Nigeria";
  if (tierEl) tierEl.textContent = currentUser.contribution_tier || "STANDARD";
  if (bankEl) bankEl.textContent = currentUser.bank_name || "Polaris Bank Limited";
  if (accEl) accEl.textContent = currentUser.bank_account_number || "Pending";
  if (accNameEl) accNameEl.textContent = currentUser.bank_account_name || currentUser.full_name;
  if (kycEl) {
    const kyc = currentUser.kyc_completion_percent || 0;
    kycEl.textContent = `${kyc}% Complete (${currentUser.membership_status || "PENDING"})`;
    kycEl.className = kyc >= 100 ? "font-bold text-emerald-600" : "font-bold text-amber-600";
  }

  // ID Card Showcase Elements on Profile Page: Strictly visible/unlocked only after Secretariat approval
  const idBadge = document.getElementById("prof-id-status-badge");
  const idDownloadBtn = document.getElementById("btn-profile-download-id");
  const idKycNotice = document.getElementById("prof-id-kyc-notice");
  const kycVal = currentUser.kyc_completion_percent || 0;
  const isApproved = ["ACTIVE", "SYSTEM_ADMINISTRATOR"].includes(currentUser.membership_status) || currentUser.is_executive;

  if (idBadge) {
    if (isApproved) {
      idBadge.textContent = "Verified • Lagos State Cap C15";
      idBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30";
    } else {
      idBadge.textContent = "Pending Secretariat Approval • ID Locked";
      idBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-400/30";
    }
  }

  if (idDownloadBtn) {
    if (isApproved) {
      idDownloadBtn.classList.remove("opacity-60", "cursor-not-allowed");
      idDownloadBtn.disabled = false;
      idDownloadBtn.innerHTML = `<span>📥</span><span>Download Vector PDF ID</span>`;
    } else {
      idDownloadBtn.classList.add("opacity-60", "cursor-not-allowed");
      idDownloadBtn.disabled = true;
      idDownloadBtn.innerHTML = `<span>🔒</span><span>Pending Secretariat Approval</span>`;
    }
  }

  if (idKycNotice) {
    if (isApproved) {
      idKycNotice.classList.add("hidden");
    } else {
      idKycNotice.classList.remove("hidden");
      idKycNotice.innerHTML = `
        <div class="flex items-center gap-2 text-xs text-amber-300">
          <span>🔒</span>
          <span><strong>Statutory Rule:</strong> Your Official Electronic Membership ID Card is accessible only <strong>after formal Secretariat approval</strong> and admission into active Society standing. Profile KYC completion is currently at <strong>${kycVal}%</strong>.</span>
        </div>
      `;
    }
  }
}
window.populateProfilePageData = populateProfilePageData;

function loadLoansPageData() {
  if (!currentUser) return;
  const loanLimitEl = document.getElementById("loans-stat-loan-limit");
  const welfareEl = document.getElementById("loans-stat-welfare");
  const statLoanLimit = document.getElementById("stat-loan-limit");
  const statWelfare = document.getElementById("stat-welfare");

  if (loanLimitEl && statLoanLimit) {
    loanLimitEl.textContent = statLoanLimit.textContent;
  }
  if (welfareEl && statWelfare) {
    welfareEl.textContent = statWelfare.textContent;
  }
  loadMemberLoanApplications();
  loadIncomingGuarantorRequests();
}
window.loadLoansPageData = loadLoansPageData;

function switchExecutiveTab(tabKey) {
  const tabs = ["members", "sec", "fin", "targets", "pres", "admin", "loans", "polaris", "rbac", "audit", "exits", "accounting", "dividends"];
  tabs.forEach(t => {
    const desk = document.getElementById(`desk-${t}`);
    const btn = document.getElementById(`tab-btn-${t}`);
    if (desk) {
      if (t === tabKey) {
        desk.classList.remove("hidden");
      } else {
        desk.classList.add("hidden");
      }
    }
    if (btn) {
      if (t === tabKey) {
        btn.className = "px-3.5 py-2 rounded-lg text-xs font-bold bg-wmcNavy-900 text-white shadow-sm flex items-center gap-1.5 transition";
      } else {
        btn.className = "px-3.5 py-2 rounded-lg text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 transition flex items-center gap-1.5";
      }
    }
  });

  if (tabKey === "sec") {
    loadPendingMembers();
    loadPendingContactChanges();
  } else if (tabKey === "members") {
    loadExecMembersRegistry();
  } else if (tabKey === "targets") {
    loadAdminTargetSavings();
  } else if (tabKey === "loans") {
    loadExecutiveLoans();
    loadExecutiveLoanAppeals();
  } else if (tabKey === "polaris") {
    loadPendingManualPayments();
    populateDirectCreditMembers();
    populateDirectDebitMembers();
  } else if (tabKey === "rbac") {
    loadRbacDesk();
  } else if (tabKey === "audit") {
    loadAuditLogs();
  } else if (tabKey === "fin") {
    loadFinancialDeskAdvices();
  } else if (tabKey === "exits") {
    loadPendingExitsDesk();
  } else if (tabKey === "accounting") {
    loadAccountingDesk();
  } else if (tabKey === "dividends") {
    loadDividendsDesk();
  }
}
window.switchExecutiveTab = switchExecutiveTab;

// -----------------------------------------------------------------------------
// 4. DATA HYDRATION: MEMBER PORTFOLIO
// -----------------------------------------------------------------------------
async function loadAuthenticatedMember() {
  if (!currentUser) return;

  if (currentUser.is_admin_only) {
    document.getElementById("portal-member-name").textContent = currentUser.full_name;
    document.getElementById("portal-member-code").textContent = currentUser.member_code;
    document.getElementById("portal-member-tier").textContent = "Platform Superuser";
    document.getElementById("portal-member-date").textContent = "Developer Console";
    const roleBadge = document.getElementById("portal-member-role-badge");
    if (roleBadge) {
      roleBadge.textContent = "SUPER ADMIN (DEV)";
      roleBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-900 text-amber-300 border border-amber-500/40";
    }
    const statusBadge = document.getElementById("portal-member-status-badge");
    if (statusBadge) {
      statusBadge.textContent = "SYSTEM_ADMINISTRATOR";
      statusBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-900 text-amber-300 border border-amber-500/40";
    }
    return;
  }

  // Header Status Bar
  document.getElementById("portal-member-name").textContent = currentUser.full_name;
  document.getElementById("portal-member-code").textContent = currentUser.member_code;
  document.getElementById("portal-member-tier").textContent = `${currentUser.contribution_tier} Tier`;
  document.getElementById("portal-member-date").textContent = currentUser.admission_date || "2026-09-26";

  const roleBadge = document.getElementById("portal-member-role-badge");
  if (roleBadge) {
    roleBadge.textContent = currentUser.primary_role.replace(/_/g, " ");
  }

  const statusBadge = document.getElementById("portal-member-status-badge");
  if (statusBadge) {
    statusBadge.textContent = currentUser.membership_status || "ACTIVE";
    if (currentUser.membership_status === "PENDING_KYC") {
      statusBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800";
    } else {
      statusBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800";
    }
  }

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/statement`);
    if (res.ok) {
      cachedStatement = await res.json();
      renderMemberStatement(cachedStatement);
    }
  } catch (err) {
    console.warn("Could not fetch statement from API, using cached data:", err);
  }

  refreshMemberKYCAndPhoto();
  refreshTransactions();
  loadMemberTargetSavings();
  loadMemberDedicatedAccount(currentUser.id);
  loadMemberCurrentPaymentAdvice(currentUser.id);
}

function renderMemberStatement(stmt) {
  if (!stmt) return;

  const totalSavings = parseFloat(stmt.total_savings_balance_ngn || 0);
  const availSavings = parseFloat(stmt.available_unencumbered_savings_ngn || totalSavings);
  const sharesPaid = parseFloat(stmt.total_share_equity_ngn || 0);
  const shareUnits = parseInt(stmt.share_units || 0);
  const loanCap = parseFloat(stmt.max_ordinary_loan_capacity_ngn || totalSavings * 2);
  const welfarePaid = parseFloat(stmt.total_welfare_pool_contributed_ngn || 0);
  const welfareMonths = parseInt(stmt.welfare_active_months || 0);
  const isQualified = Boolean(stmt.is_benefits_qualified);

  document.getElementById("stat-savings").textContent = "₦" + totalSavings.toLocaleString(undefined, { minimumFractionDigits: 2 });
  document.getElementById("stat-avail-savings").textContent = "₦" + availSavings.toLocaleString(undefined, { minimumFractionDigits: 2 });

  document.getElementById("stat-shares-amount").textContent = "₦" + sharesPaid.toLocaleString(undefined, { minimumFractionDigits: 2 });
  document.getElementById("stat-shares-units").textContent = `${shareUnits} Units`;

  const qualBadge = document.getElementById("stat-share-qual");
  if (qualBadge) {
    qualBadge.textContent = isQualified ? "Qualified" : "Pending (Min 5)";
    qualBadge.className = isQualified 
      ? "text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-800"
      : "text-[10px] px-2 py-0.5 rounded-full font-bold bg-amber-100 text-amber-800";
  }

  document.getElementById("stat-loan-limit").textContent = "₦" + loanCap.toLocaleString(undefined, { minimumFractionDigits: 2 });
  document.getElementById("stat-welfare").textContent = "₦" + welfarePaid.toLocaleString(undefined, { minimumFractionDigits: 2 });
  document.getElementById("stat-welfare-months").textContent = `${welfareMonths} Month${welfareMonths > 1 ? "s" : ""}`;
}

// -----------------------------------------------------------------------------
// 5. DATA HYDRATION: EXECUTIVE GOVERNANCE CONSOLE
// -----------------------------------------------------------------------------
async function loadExecutiveData() {
  if (!currentUser || !currentUser.is_executive) return;

  loadExecutiveMetrics();
  loadPendingMembers();
  loadPendingContactChanges();
  loadExecMembersRegistry();
  loadSystemConfigTable();
}

async function loadExecutiveMetrics() {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/executive-metrics`);
    if (res.ok) {
      const data = await res.json();
      const pools = data.financial_pools || {};
      
      document.getElementById("exec-stat-aum").textContent = "₦" + (pools.total_assets_under_management || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
      document.getElementById("exec-stat-savings").textContent = "₦" + (pools.ordinary_savings_balance || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
      document.getElementById("exec-stat-shares").textContent = "₦" + (pools.paid_up_share_equity || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
      document.getElementById("exec-stat-share-units").textContent = `${pools.total_share_units_held || 0} Units Held`;
      document.getElementById("exec-stat-welfare").textContent = "₦" + (pools.welfare_solidarity_pool || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
      document.getElementById("exec-stat-liquidity").textContent = "₦" + (pools.polaris_bank_custody_estimate || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
    }

    // Also fetch target savings aggregate metrics
    const tgtRes = await fetch(`${API_BASE_URL}/admin/target-savings`);
    if (tgtRes.ok) {
      const tgtData = await tgtRes.json();
      const totals = tgtData.totals || {};
      const elPool = document.getElementById("exec-stat-target-savings");
      const elCount = document.getElementById("exec-stat-target-count");
      const elBadge = document.getElementById("tab-targets-badge");
      if (elPool) elPool.textContent = "₦" + (totals.total_savings_pool || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
      if (elCount) elCount.textContent = `${totals.active_ledgers || 0} Active / ${totals.matured_ledgers || 0} Matured`;
      if (elBadge) elBadge.textContent = totals.total_ledgers || 0;
    }
  } catch (err) {
    console.warn("Could not fetch executive metrics:", err);
  }
}

async function loadPendingMembers() {
  const tbody = document.getElementById("pending-members-tbody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/pending-members`);
    if (!res.ok) throw new Error("Failed to load queue");
    const pending = await res.json();

    const badge = document.getElementById("tab-sec-badge");
    const countBadge = document.getElementById("pending-badge-count");
    const sideExecBadge = document.getElementById("sidebar-exec-badge");
    if (badge) badge.textContent = pending.length;
    if (countBadge) {
      countBadge.textContent = pending.length;
      if (pending.length > 0) countBadge.classList.remove("hidden");
      else countBadge.classList.add("hidden");
    }
    if (sideExecBadge) {
      sideExecBadge.textContent = pending.length;
      if (pending.length > 0) sideExecBadge.classList.remove("hidden");
      else sideExecBadge.classList.add("hidden");
    }

    if (!pending || pending.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-slate-400">✅ No pending KYC applications in queue. All members vetted!</td></tr>`;
      return;
    }

    tbody.innerHTML = pending.map(m => `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100">
        <td class="p-3 font-mono font-bold text-slate-800">${m.member_code}</td>
        <td class="p-3 font-bold text-wmcNavy-950">${m.first_name} ${m.last_name}</td>
        <td class="p-3 text-slate-600">
          <div>${m.email}</div>
          <div class="text-[10px] text-slate-400">${m.phone}</div>
        </td>
        <td class="p-3">
          <span class="px-2 py-0.5 rounded font-bold text-[10px] bg-slate-100 text-slate-700">${m.contribution_tier}</span>
          <div class="mt-1"><span class="px-1.5 py-0.2 rounded-full text-[9px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">${m.kyc_completion_percent || 0}% KYC</span></div>
        </td>
        <td class="p-3 text-slate-500 max-w-xs truncate">${m.residential_address}</td>
        <td class="p-3"><span class="px-2 py-0.5 rounded-full font-bold text-[10px] bg-amber-100 text-amber-800">${m.status || 'PENDING_KYC'}</span></td>
        <td class="p-3 text-right space-x-1">
          <button onclick="openApplicantDossier(${m.id})" class="px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-[10px] transition shadow-sm">
            🔍 Inspect Dossier
          </button>
          <button onclick="approveKYC(${m.id})" class="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[10px] transition shadow-sm">
            ✅ Approve KYC
          </button>
          <button onclick="rejectKYC(${m.id})" class="px-2.5 py-1 rounded-lg bg-slate-200 hover:bg-red-100 hover:text-red-700 text-slate-700 font-bold text-[10px] transition">
            ❌ Reject
          </button>
        </td>
      </tr>
    `).join("");

  } catch (err) {
    console.warn("Pending members queue error:", err);
    tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-slate-400">Could not retrieve queue from backend.</td></tr>`;
  }
}

async function approveKYC(memberId) {
  if (!confirm(`Are you sure you want to approve and activate Member ID #${memberId}?`)) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/approve-member`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        member_id: memberId,
        officer_id: currentUser ? currentUser.id : 2
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert(`Success! ${data.message}`);
      loadPendingMembers();
      loadExecMembersRegistry();
      loadExecutiveMetrics();
    } else {
      alert(`Error: ${data.detail || "Approval failed."}`);
    }
  } catch (err) {
    alert("Connection error occurred while approving member.");
  }
}

async function rejectKYC(memberId) {
  const reason = prompt("Please provide statutory reason for rejecting/suspending this application:");
  if (!reason) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/reject-member`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        member_id: memberId,
        officer_id: currentUser ? currentUser.id : 2,
        reason: reason
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert(data.message);
      loadPendingMembers();
    } else {
      alert(`Error: ${data.detail || "Rejection failed."}`);
    }
  } catch (err) {
    alert("Connection error occurred while rejecting application.");
  }
}

async function loadExecMembersRegistry() {
  const tbodyLegacy = document.getElementById("exec-members-tbody");
  const fineDropdown = document.getElementById("fine-member-id");

  try {
    const res = await fetch(`${API_BASE_URL}/members`);
    if (!res.ok) throw new Error(`Could not fetch members: ${res.status}`);
    const memData = await res.json();
    cachedMembers = Array.isArray(memData) ? memData : (memData.data || memData.members || []);

    // 1. Render Main Member Management Dashboard Table
    renderMembersManagementTable(cachedMembers);

    // 2. Update Quick Metrics Badges in Member Management Desk
    const total = cachedMembers.length;
    const active = cachedMembers.filter(m => m.membership_status === "ACTIVE").length;
    const standard = cachedMembers.filter(m => m.contribution_tier === "STANDARD").length;
    const plus = cachedMembers.filter(m => m.contribution_tier === "PLUS").length;
    const premium = cachedMembers.filter(m => m.contribution_tier === "PREMIUM").length;

    const elTotal = document.getElementById("mgmt-stat-total");
    const elActive = document.getElementById("mgmt-stat-active");
    const elStandard = document.getElementById("mgmt-stat-standard");
    const elPlus = document.getElementById("mgmt-stat-plus");
    const elPremium = document.getElementById("mgmt-stat-premium");
    const elBadge = document.getElementById("tab-members-badge");

    if (elTotal) elTotal.textContent = total;
    if (elActive) elActive.textContent = active;
    if (elStandard) elStandard.textContent = standard;
    if (elPlus) elPlus.textContent = plus;
    if (elPremium) elPremium.textContent = premium;
    if (elBadge) elBadge.textContent = total;

    // 3. Render Legacy Secretariat Table (if present)
    if (tbodyLegacy) {
      tbodyLegacy.innerHTML = cachedMembers.map(m => `
        <tr class="hover:bg-slate-50 transition border-b border-slate-100">
          <td class="p-3 font-mono font-bold text-slate-800">${m.member_code}</td>
          <td class="p-3 font-bold text-wmcNavy-950">${m.full_name}</td>
          <td class="p-3">
            ${m.executive_portfolio 
              ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-200">${m.executive_portfolio.replace(/_/g, " ")}</span>` 
              : `<span class="text-slate-400">Cooperator</span>`}
          </td>
          <td class="p-3 font-semibold text-slate-800">${m.share_units} Units (₦${parseFloat(m.share_equity_paid).toLocaleString()})</td>
          <td class="p-3 font-bold text-blue-700">₦${parseFloat(m.savings_balance).toLocaleString()}</td>
          <td class="p-3">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${m.membership_status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
              ${m.membership_status}
            </span>
          </td>
        </tr>
      `).join("");
    }

    if (fineDropdown) {
      fineDropdown.innerHTML = cachedMembers.map(m => `
        <option value="${m.id}">${m.member_code} - ${m.full_name}</option>
      `).join("");
    }

  } catch (err) {
    console.warn("Exec members error:", err);
  }
}

function renderMembersManagementTable(list) {
  const tbody = document.getElementById("mgmt-members-tbody");
  if (!tbody) return;

  if (!list || list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-slate-400 font-semibold">🔍 No cooperator records found matching your filters.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(m => {
    const kycPct = m.kyc_completion_percent || 20;
    const tierColor = m.contribution_tier === 'PREMIUM' ? 'bg-purple-100 text-purple-900 border-purple-200' : (m.contribution_tier === 'PLUS' ? 'bg-blue-100 text-blue-900 border-blue-200' : 'bg-amber-100 text-amber-900 border-amber-200');
    const statusColor = m.membership_status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800' : (m.membership_status === 'PENDING_KYC' ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800');

    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100 group">
        <!-- 1. Code & Portfolio -->
        <td class="p-3 align-middle">
          <div class="font-mono font-bold text-slate-900 text-xs">${m.member_code}</div>
          ${m.executive_portfolio 
            ? `<span class="inline-block px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-100 text-amber-900 border border-amber-300 mt-1">${m.executive_portfolio.replace(/_/g, " ")}</span>` 
            : `<span class="text-[10px] text-slate-400">Cooperator</span>`}
        </td>

        <!-- 2. Biodata -->
        <td class="p-3 align-middle">
          <div class="font-bold text-wmcNavy-950 text-xs">${m.full_name}</div>
          <div class="text-[10px] text-slate-500 mt-0.5">
            <span>${m.gender || 'MALE'}</span> &bull; <span>${m.marital_status || 'SINGLE'}</span>
            ${m.employer_or_business_name ? ` &bull; <span class="text-slate-600 truncate max-w-[120px] inline-block align-bottom">${m.employer_or_business_name}</span>` : ''}
          </div>
        </td>

        <!-- 3. Contacts -->
        <td class="p-3 align-middle">
          <div class="text-slate-800 font-semibold">${m.email}</div>
          <div class="text-[10px] text-slate-500 font-mono">${m.phone}</div>
        </td>

        <!-- 4. Tier & Status -->
        <td class="p-3 align-middle">
          <span class="inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${tierColor} mb-1">
            ${m.contribution_tier || 'STANDARD'}
          </span>
          <br>
          <span class="inline-block px-2 py-0.5 rounded-full text-[9px] font-extrabold ${statusColor}">
            ${m.membership_status}
          </span>
        </td>

        <!-- 5. Financial Pool -->
        <td class="p-3 align-middle">
          <div class="font-bold text-slate-900">₦${parseFloat(m.savings_balance || 0).toLocaleString()} <span class="text-[9px] font-normal text-slate-400">Savings</span></div>
          <div class="text-[10px] text-slate-600 font-medium">₦${parseFloat(m.share_equity_paid || 0).toLocaleString()} (${m.share_units || 0} Units)</div>
        </td>

        <!-- 6. KYC Meter -->
        <td class="p-3 align-middle">
          <div class="flex items-center justify-between text-[10px] font-bold text-slate-600 mb-1">
            <span>${kycPct}%</span>
            ${m.identification_number ? `<span class="text-[9px] text-emerald-600 font-mono">NIN Verified</span>` : `<span class="text-[9px] text-amber-600">No NIN</span>`}
          </div>
          <div class="w-20 bg-slate-200 h-1.5 rounded-full overflow-hidden">
            <div class="bg-gradient-to-r from-amber-500 to-emerald-500 h-full rounded-full" style="width: ${kycPct}%"></div>
          </div>
        </td>

        <!-- 7. Action Suite -->
        <td class="p-3 text-right align-middle">
          <div class="flex items-center justify-end gap-1.5">
            <button type="button" onclick="openApplicantDossier(${m.id})" title="Inspect Cooperator Registration Dossier" class="px-2.5 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-900 font-bold text-[11px] transition flex items-center gap-1 shadow-sm">
              <span>🔍</span>
              <span class="hidden sm:inline">Dossier</span>
            </button>
            <button type="button" onclick="openAdminEditMemberModal(${m.id})" title="Modify Biodata &amp; Contact Details" class="px-2.5 py-1.5 rounded-lg bg-amber-50 hover:bg-amber-100 border border-amber-200 text-amber-900 font-bold text-[11px] transition flex items-center gap-1 shadow-sm">
              <span>✏️</span>
              <span class="hidden sm:inline">Edit</span>
            </button>
            <button type="button" onclick="openAdminResetPasswordModal(${m.id}, '${m.member_code}', '${(m.full_name || '').replace(/'/g, "\\'")}')" title="Reset Password to Default (Wealthbridge@2026)" class="px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-800 font-bold text-[11px] transition flex items-center gap-1 shadow-sm">
              <span>🔑</span>
              <span class="hidden sm:inline">Reset</span>
            </button>
            <button type="button" onclick="viewMemberStatementFromAdmin(${m.id})" title="View Consolidated Statement" class="px-2 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 text-[11px] transition">
              <span>📄</span>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function filterMembersRegistry() {
  const query = (document.getElementById("mgmt-search-input")?.value || "").toLowerCase().trim();
  const tierFilter = document.getElementById("mgmt-tier-filter")?.value || "";
  const statusFilter = document.getElementById("mgmt-status-filter")?.value || "";

  const filtered = cachedMembers.filter(m => {
    const matchQuery = !query || 
      (m.member_code && m.member_code.toLowerCase().includes(query)) ||
      (m.full_name && m.full_name.toLowerCase().includes(query)) ||
      (m.email && m.email.toLowerCase().includes(query)) ||
      (m.phone && m.phone.toLowerCase().includes(query));

    const matchTier = !tierFilter || m.contribution_tier === tierFilter;
    const matchStatus = !statusFilter || m.membership_status === statusFilter;

    return matchQuery && matchTier && matchStatus;
  });

  renderMembersManagementTable(filtered);
}

// -----------------------------------------------------------------------------
// 5B. ADMIN MEMBER CRUD: ADD, MODIFY BIODATA, RESET PASSWORD
// -----------------------------------------------------------------------------
function openAdminAddMemberModal() {
  const modal = document.getElementById("modal-admin-add-member");
  if (modal) {
    document.getElementById("form-admin-add-member")?.reset();
    modal.classList.remove("hidden");
  }
  loadVerifyMeBanks();
}

function closeAdminAddMemberModal() {
  const modal = document.getElementById("modal-admin-add-member");
  if (modal) modal.classList.add("hidden");
}

async function handleAdminAddMemberSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-admin-add-submit");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Enrolling Member...";
  }

  const payload = {
    first_name: document.getElementById("admin-add-first-name").value.trim(),
    last_name: document.getElementById("admin-add-last-name").value.trim(),
    other_names: document.getElementById("admin-add-other-names").value.trim() || null,
    email: document.getElementById("admin-add-email").value.trim(),
    phone: document.getElementById("admin-add-phone").value.trim(),
    gender: document.getElementById("admin-add-gender").value,
    marital_status: document.getElementById("admin-add-marital-status").value,
    residential_address: document.getElementById("admin-add-address").value.trim(),
    employment_status: document.getElementById("admin-add-emp-status").value,
    employer_or_business_name: document.getElementById("admin-add-employer").value.trim() || null,
    contribution_tier: document.getElementById("admin-add-tier").value,
    status: document.getElementById("admin-add-status").value,
    identification_type: document.getElementById("admin-add-id-type").value,
    identification_number: document.getElementById("admin-add-id-number").value.trim() || null,
    bank_name: document.getElementById("admin-add-bank-name").value.trim() || null,
    bank_account_number: document.getElementById("admin-add-bank-acc-num").value.trim() || null,
    bank_account_name: document.getElementById("admin-add-bank-acc-name").value.trim() || null,
    nok_name: document.getElementById("admin-add-nok-name").value.trim() || null,
    nok_relationship: document.getElementById("admin-add-nok-rel").value.trim() || null,
    nok_phone: document.getElementById("admin-add-nok-phone").value.trim() || null
  };

  try {
    const res = await fetch(`${API_BASE_URL}/admin/members`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      alert(`⚠️ Enrollment Failed: ${data.detail || "Could not create member."}`);
    } else {
      alert(`✅ Success: ${data.message}\n\nMember Code: ${data.member.member_code}\nInitial Default Password: ${data.member.default_password}`);
      closeAdminAddMemberModal();
      loadExecMembersRegistry();
    }
  } catch (err) {
    alert("Connection error occurred while enrolling member.");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Enroll Cooperator →";
    }
  }
}

let activeEditMemberId = null;

async function openAdminEditMemberModal(memberId) {
  activeEditMemberId = memberId;
  const modal = document.getElementById("modal-admin-edit-member");
  if (!modal) return;

  loadVerifyMeBanks();

  try {
    const res = await fetch(`${API_BASE_URL}/admin/members/${memberId}`);
    if (!res.ok) throw new Error("Could not load member details");
    const m = await res.json();

    document.getElementById("admin-edit-member-id").value = m.id;
    document.getElementById("admin-edit-display-name").textContent = `${m.first_name} ${m.last_name}`;
    document.getElementById("admin-edit-display-code").textContent = m.member_code;

    document.getElementById("admin-edit-first-name").value = m.first_name || "";
    document.getElementById("admin-edit-last-name").value = m.last_name || "";
    document.getElementById("admin-edit-other-names").value = m.other_names || "";
    document.getElementById("admin-edit-email").value = m.email || "";
    document.getElementById("admin-edit-phone").value = m.phone || "";
    document.getElementById("admin-edit-gender").value = m.gender || "MALE";
    document.getElementById("admin-edit-marital-status").value = m.marital_status || "SINGLE";
    document.getElementById("admin-edit-address").value = m.residential_address || "";
    document.getElementById("admin-edit-emp-status").value = m.employment_status || "SALARY_EARNER";
    document.getElementById("admin-edit-employer").value = m.employer_or_business_name || "";
    document.getElementById("admin-edit-tier").value = m.contribution_tier || "STANDARD";
    document.getElementById("admin-edit-status").value = m.status || "ACTIVE";
    document.getElementById("admin-edit-id-type").value = m.identification_type || "NIN";
    document.getElementById("admin-edit-id-number").value = m.identification_number || "";
    document.getElementById("admin-edit-bank-name").value = m.bank_name || "";
    await loadVerifyMeBanks();
    const editBankCode = document.getElementById("admin-edit-bank-code");
    if (editBankCode && m.bank_name) {
      const matched = cachedBanks.find(b => b.name.toLowerCase() === m.bank_name.toLowerCase());
      if (matched) editBankCode.value = matched.code;
    }
    document.getElementById("admin-edit-bank-acc-num").value = m.bank_account_number || "";
    document.getElementById("admin-edit-bank-acc-name").value = m.bank_account_name || "";
    document.getElementById("admin-edit-bvn").value = m.bvn || "";
    document.getElementById("admin-edit-nok-name").value = m.nok_name || "";
    document.getElementById("admin-edit-nok-rel").value = m.nok_relationship || "";
    document.getElementById("admin-edit-nok-phone").value = m.nok_phone || "";

    modal.classList.remove("hidden");
  } catch (err) {
    alert("Could not retrieve member details for editing.");
  }
}

function closeAdminEditMemberModal() {
  const modal = document.getElementById("modal-admin-edit-member");
  if (modal) modal.classList.add("hidden");
  activeEditMemberId = null;
}

async function handleAdminEditMemberSubmit(e) {
  e.preventDefault();
  if (!activeEditMemberId) return;

  const btn = document.getElementById("btn-admin-edit-submit");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Saving Modifications...";
  }

  const payload = {
    first_name: document.getElementById("admin-edit-first-name").value.trim(),
    last_name: document.getElementById("admin-edit-last-name").value.trim(),
    other_names: document.getElementById("admin-edit-other-names").value.trim() || null,
    email: document.getElementById("admin-edit-email").value.trim(),
    phone: document.getElementById("admin-edit-phone").value.trim(),
    gender: document.getElementById("admin-edit-gender").value,
    marital_status: document.getElementById("admin-edit-marital-status").value,
    residential_address: document.getElementById("admin-edit-address").value.trim(),
    employment_status: document.getElementById("admin-edit-emp-status").value,
    employer_or_business_name: document.getElementById("admin-edit-employer").value.trim() || null,
    contribution_tier: document.getElementById("admin-edit-tier").value,
    status: document.getElementById("admin-edit-status").value,
    identification_type: document.getElementById("admin-edit-id-type").value,
    identification_number: document.getElementById("admin-edit-id-number").value.trim() || null,
    bank_name: document.getElementById("admin-edit-bank-name").value.trim() || null,
    bank_account_number: document.getElementById("admin-edit-bank-acc-num").value.trim() || null,
    bank_account_name: document.getElementById("admin-edit-bank-acc-name").value.trim() || null,
    bvn: document.getElementById("admin-edit-bvn").value.trim() || null,
    nok_name: document.getElementById("admin-edit-nok-name").value.trim() || null,
    nok_relationship: document.getElementById("admin-edit-nok-rel").value.trim() || null,
    nok_phone: document.getElementById("admin-edit-nok-phone").value.trim() || null
  };

  try {
    const res = await fetch(`${API_BASE_URL}/admin/members/${activeEditMemberId}/biodata`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      alert(`⚠️ Update Failed: ${data.detail || "Could not save modifications."}`);
    } else {
      alert(`✅ Success: ${data.message}`);
      closeAdminEditMemberModal();
      loadExecMembersRegistry();
    }
  } catch (err) {
    alert("Connection error occurred while updating member biodata.");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Save Biodata Modifications →";
    }
  }
}

let activeResetMemberId = null;

function openAdminResetPasswordModal(memberId, memberCode, fullName) {
  activeResetMemberId = memberId;
  const modal = document.getElementById("modal-admin-reset-password");
  if (!modal) return;

  document.getElementById("reset-display-name").textContent = fullName;
  document.getElementById("reset-display-code").textContent = memberCode;
  modal.classList.remove("hidden");
}

function closeAdminResetPasswordModal() {
  const modal = document.getElementById("modal-admin-reset-password");
  if (modal) modal.classList.add("hidden");
  activeResetMemberId = null;
}

async function confirmAdminResetPassword() {
  if (!activeResetMemberId) return;

  const btn = document.getElementById("btn-admin-confirm-reset");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Resetting...";
  }

  try {
    const res = await fetch(`${API_BASE_URL}/admin/members/${activeResetMemberId}/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });

    const data = await res.json();
    if (!res.ok) {
      alert(`⚠️ Password Reset Failed: ${data.detail || "Could not reset password."}`);
    } else {
      alert(`🔑 Success: ${data.message}\n\nDefault Password: ${data.default_password}`);
      closeAdminResetPasswordModal();
    }
  } catch (err) {
    alert("Connection error occurred while resetting password.");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Confirm Reset";
    }
  }
}

function viewMemberStatementFromAdmin(memberId) {
  fetch(`${API_BASE_URL}/members/${memberId}/statement`)
    .then(res => res.json())
    .then(stmt => {
      alert(`📄 Statement for ${stmt.member_code} (${stmt.full_name}):\n\n• Paid-Up Share Equity: ₦${parseFloat(stmt.share_equity_paid).toLocaleString()} (${stmt.units_held} units)\n• Available Liquid Savings: ₦${parseFloat(stmt.available_savings_balance).toLocaleString()}\n• Cumulative Welfare Fund: ₦${parseFloat(stmt.welfare_balance).toLocaleString()}\n• Benefits Qualified: ${stmt.benefits_qualified ? 'YES' : 'NO'}`);
    })
    .catch(err => {
      alert("Could not load statement for this member.");
    });
}

let cachedSystemConfigList = [];

async function loadSystemConfigTable() {
  const tbody = document.getElementById("system-config-tbody");
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-slate-400">Loading system parameters...</td></tr>`;

  try {
    const res = await fetch(`${API_BASE_URL}/config?format=full`);
    if (!res.ok) throw new Error("Could not fetch system configuration");
    const configList = await res.json();
    cachedSystemConfigList = configList;

    if (!Array.isArray(configList) || configList.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-slate-400">No configuration records found in MySQL.</td></tr>`;
      return;
    }

    tbody.innerHTML = configList.map(item => {
      const key = item.config_key;
      const val = item.config_value;
      const desc = item.description || "Statutory system parameter";
      const updated = item.updated_at ? item.updated_at.slice(0, 16) : "System Default";

      // Currency formatting for financial amounts
      let displayVal = val;
      if (["SHARE_UNIT_PRICE", "TARGET_SHARE_CAPITAL", "WELFARE_MONTHLY_LEVY", "REGISTRATION_FEE", "PASSBOOK_FEE", "BANK_DEBIT_STAMP_DUTY_FEE", "BANK_DEBIT_STAMP_DUTY_THRESHOLD", "BANK_DEBIT_TRANSFER_FEE"].includes(key)) {
        displayVal = `<span class="font-bold text-emerald-800">${formatNaira(val)}</span>`;
      } else if (key === "MONTHLY_DUE_DAY") {
        displayVal = `<span class="font-bold text-indigo-900">${val}th of month</span>`;
      } else if (["MIN_SHARE_UNITS", "MAX_SHARE_UNITS"].includes(key)) {
        displayVal = `<span class="font-bold text-amber-800">${val} Units</span>`;
      } else if (["BANK_DEBIT_CAMF_RATE", "BANK_DEBIT_VAT_RATE"].includes(key)) {
        displayVal = `<span class="font-bold text-purple-900">${(parseFloat(val) * 100).toFixed(2)}%</span> <span class="text-[10px] text-slate-400 font-mono">(${val})</span>`;
      } else if (key === "BANK_DEBIT_CHARGES_BEARER") {
        displayVal = `<span class="font-bold px-2 py-0.5 rounded text-[11px] ${val === 'SOCIETY' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'}">${val}</span>`;
      } else if (key === "BANK_CREDIT_CHARGES_ENABLED") {
        displayVal = `<span class="font-bold px-2 py-0.5 rounded text-[11px] ${val === '1' || val === 'true' ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'}">${val === '1' || val === 'true' ? 'ENABLED' : 'DISABLED (0% Charges)'}</span>`;
      } else if (key === "OFFICIAL_EMAIL") {
        displayVal = `<span class="font-bold text-amber-700 underline">${val}</span>`;
      }

      return `
        <tr class="hover:bg-slate-50 transition border-b border-slate-100">
          <td class="p-3">
            <span class="font-mono font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded text-[11px]">${key}</span>
          </td>
          <td class="p-3 font-mono text-slate-800">${displayVal}</td>
          <td class="p-3 text-slate-600 text-[11px] max-w-xs">${desc}</td>
          <td class="p-3 font-mono text-slate-400 text-[10px] whitespace-nowrap">${updated}</td>
          <td class="p-3 text-center">
            <button onclick="openEditConfigModal('${key}')" class="px-3 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-amber-300 font-bold text-[10px] transition shadow-sm active:scale-95">
              ✏️ Edit
            </button>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.warn("Config load error:", err);
    tbody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-rose-500 font-semibold">⚠️ Failed to load parameters: ${err.message}</td></tr>`;
  }
}

function openEditConfigModal(configKey) {
  const item = (cachedSystemConfigList || []).find(c => c.config_key === configKey);
  const modal = document.getElementById("modal-edit-config");
  const keyInput = document.getElementById("edit-config-key");
  const descEl = document.getElementById("edit-config-desc");
  const curValEl = document.getElementById("edit-config-current-val");
  const newValInput = document.getElementById("edit-config-new-value");
  const hintEl = document.getElementById("edit-config-hint");
  const invariantAlert = document.getElementById("edit-config-invariant-alert");

  if (!modal || !keyInput) return;

  const currentVal = item ? item.config_value : "";
  const desc = item ? item.description : "";

  keyInput.value = configKey;
  if (descEl) descEl.textContent = desc || "Statutory cooperative parameter loaded from MySQL.";
  if (curValEl) curValEl.textContent = currentVal;
  if (newValInput) {
    newValInput.value = currentVal;
    newValInput.focus();
  }

  if (configKey === "OFFICIAL_EMAIL") {
    if (invariantAlert) invariantAlert.classList.remove("hidden");
    if (hintEl) hintEl.textContent = "Invariant: Must remain wealthbridge.coopsociety@gmail.com";
  } else {
    if (invariantAlert) invariantAlert.classList.add("hidden");
    if (["SHARE_UNIT_PRICE", "MIN_SHARE_UNITS", "MAX_SHARE_UNITS", "TARGET_SHARE_CAPITAL", "WELFARE_MONTHLY_LEVY", "REGISTRATION_FEE", "PASSBOOK_FEE"].includes(configKey)) {
      if (hintEl) hintEl.textContent = "Numerical value (e.g., 5000, 1000)";
    } else if (configKey === "MONTHLY_DUE_DAY") {
      if (hintEl) hintEl.textContent = "Calendar day between 1 and 31 (e.g., 28)";
    } else {
      if (hintEl) hintEl.textContent = "Enter updated statutory setting";
    }
  }

  modal.classList.remove("hidden");
}

function closeEditConfigModal() {
  const modal = document.getElementById("modal-edit-config");
  if (modal) modal.classList.add("hidden");
}

async function handleSaveSystemConfig(e) {
  e.preventDefault();
  const key = document.getElementById("edit-config-key").value;
  const newVal = document.getElementById("edit-config-new-value").value.trim();
  const saveBtn = document.getElementById("btn-save-config");

  if (!newVal) {
    alert("Configuration value cannot be empty.");
    return;
  }

  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.innerHTML = `<span>↻</span><span>Saving...</span>`;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/admin/config/${encodeURIComponent(key)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config_value: newVal })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to update configuration parameter.");
    }

    closeEditConfigModal();
    alert(`✅ Successfully updated '${key}' to '${newVal}'.`);
    await loadSystemConfigTable();
  } catch (err) {
    console.error("Config update error:", err);
    alert(`⚠️ Update Failed: ${err.message}`);
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.innerHTML = `<span>💾</span><span>Save Configuration</span>`;
    }
  }
}


// -----------------------------------------------------------------------------
// 6. DISCIPLINARY FINES & LOAN ACTIONS
// -----------------------------------------------------------------------------
function openIssueFineModal() {
  const modal = document.getElementById("modal-fine");
  if (modal) modal.classList.remove("hidden");
}

function closeIssueFineModal() {
  const modal = document.getElementById("modal-fine");
  if (modal) modal.classList.add("hidden");
}

async function handleFineSubmit(e) {
  e.preventDefault();
  const memberId = parseInt(document.getElementById("fine-member-id").value);
  const infraction = document.getElementById("fine-infraction").value;
  const amount = parseFloat(document.getElementById("fine-amount").value);
  const reason = document.getElementById("fine-reason").value.trim();

  try {
    const res = await fetch(`${API_BASE_URL}/admin/fines/issue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        member_id: memberId,
        infraction_type: infraction,
        fine_amount: amount,
        reason: reason
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert(`Success! ${data.message}`);
      closeIssueFineModal();
      document.getElementById("fine-form").reset();
    } else {
      alert(`Error: ${data.detail || "Could not record fine."}`);
    }
  } catch (err) {
    alert("Connection error while issuing disciplinary fine.");
  }
}

window.cachedGuarantorCandidates = [];

async function populateGuarantorCandidates() {
  const datalist = document.getElementById("guarantors-datalist");
  if (!datalist) return;

  try {
    const res = await fetch(`${API_BASE_URL}/members/guarantor-candidates`);
    if (!res.ok) throw new Error("Could not fetch candidates");
    const result = await res.json();
    const candidates = Array.isArray(result) ? result : (result.data || []);
    window.cachedGuarantorCandidates = candidates;

    datalist.innerHTML = candidates.map(c => `
      <option value="${c.member_code} - ${c.first_name} ${c.last_name}" data-id="${c.id}" data-code="${c.member_code}" data-name="${c.first_name} ${c.last_name}" data-savings="${c.total_savings}">
        Savings: ₦${parseFloat(c.total_savings).toLocaleString()} | ${c.phone || c.email}
      </option>
    `).join("");
  } catch (err) {
    console.warn("Could not load guarantor candidates:", err);
  }
}
window.populateGuarantorCandidates = populateGuarantorCandidates;

function handleLoanProductChange() {
  const select = document.getElementById("loan-product");
  const hint = document.getElementById("loan-product-hint");
  const marketplaceNotice = document.getElementById("loan-marketplace-notice");
  const tenureSelect = document.getElementById("loan-tenure");
  if (!select) return;

  const val = select.value;

  if (val === "1") {
    // Ordinary loan (*2 of savings)
    if (hint) hint.textContent = "Maximum 2× your current unencumbered savings balance per statutory bye-laws.";
    if (marketplaceNotice) marketplaceNotice.classList.add("hidden");
    if (tenureSelect) {
      tenureSelect.innerHTML = `
        <option value="1">1 Month</option>
        <option value="3">3 Months</option>
        <option value="6" selected>6 Months</option>
        <option value="12">12 Months</option>
        <option value="18">18 Months</option>
        <option value="24">24 Months</option>
      `;
    }
  } else if (val === "2") {
    // Investment Loan
    if (hint) hint.textContent = "Up to 3× savings collateral for capital projects, enterprise development, and high-yield cooperative investments.";
    if (marketplaceNotice) marketplaceNotice.classList.add("hidden");
    if (tenureSelect) {
      tenureSelect.innerHTML = `
        <option value="3">3 Months</option>
        <option value="6">6 Months</option>
        <option value="12" selected>12 Months</option>
        <option value="18">18 Months</option>
        <option value="24">24 Months</option>
        <option value="36">36 Months</option>
      `;
    }
  } else if (val === "3") {
    // Salary Advance Loan
    if (hint) hint.textContent = "Short-term payroll liquidity advance facility (capped at 1x savings/salary, max 3 months).";
    if (marketplaceNotice) marketplaceNotice.classList.add("hidden");
    if (tenureSelect) {
      tenureSelect.innerHTML = `
        <option value="1" selected>1 Month</option>
        <option value="2">2 Months</option>
        <option value="3">3 Months</option>
      `;
    }
  } else if (val === "4") {
    // General Purchase Loan
    if (hint) hint.textContent = "Direct consumer finance facility powered by the CO-CARE Marketplace portal.";
    if (marketplaceNotice) marketplaceNotice.classList.remove("hidden");
    if (tenureSelect) {
      tenureSelect.innerHTML = `
        <option value="1">1 Month</option>
        <option value="3">3 Months</option>
        <option value="6" selected>6 Months</option>
        <option value="12">12 Months</option>
      `;
    }
  }
}
window.handleLoanProductChange = handleLoanProductChange;

function redirectToMarketplacePortal() {
  closeLoanModal();
  if (typeof switchPage === "function") {
    switchPage("marketplace");
  } else {
    window.location.hash = "#/marketplace";
  }
}
window.redirectToMarketplacePortal = redirectToMarketplacePortal;

function addGuarantorRow(defaultId = "", defaultAmount = "") {
  const container = document.getElementById("loan-guarantors-container");
  if (!container) return;

  const rowId = "guar-row-" + Date.now() + "-" + Math.floor(Math.random() * 10000);
  const rowDiv = document.createElement("div");
  rowDiv.id = rowId;
  rowDiv.className = "flex items-center gap-2 p-2 rounded-xl bg-slate-50 border border-slate-200 transition-all";
  rowDiv.innerHTML = `
    <div class="flex-1">
      <input type="text" list="guarantors-datalist" class="guarantor-search-input w-full p-2 text-xs rounded-lg border border-slate-300 bg-white font-medium focus:ring-2 focus:ring-indigo-500" placeholder="Type member name or code (e.g. WMC-2026-002)..." oninput="onGuarantorInputChanged(this)" required>
      <input type="hidden" class="guarantor-member-id-input" value="${defaultId}">
    </div>
    <div class="w-32 sm:w-40">
      <div class="relative">
        <span class="absolute left-2.5 top-2 text-slate-400 font-bold text-xs">₦</span>
        <input type="number" min="1000" step="1000" class="guarantor-amount-input w-full pl-6 pr-2 py-2 text-xs rounded-lg border border-slate-300 bg-white font-mono font-bold focus:ring-2 focus:ring-indigo-500" placeholder="Amount" oninput="updateGuarantorTotals()" required value="${defaultAmount}">
      </div>
    </div>
    <button type="button" onclick="removeGuarantorRow('${rowId}')" class="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 border border-transparent hover:border-rose-200 transition" title="Remove Guarantor">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
    </button>
  `;
  container.appendChild(rowDiv);
  updateGuarantorTotals();
}
window.addGuarantorRow = addGuarantorRow;

function removeGuarantorRow(rowId) {
  const row = document.getElementById(rowId);
  if (row) {
    row.remove();
  }
  const container = document.getElementById("loan-guarantors-container");
  if (container && container.children.length === 0) {
    addGuarantorRow();
  }
  updateGuarantorTotals();
}
window.removeGuarantorRow = removeGuarantorRow;

function onGuarantorInputChanged(inputElem) {
  const val = inputElem.value.trim().toLowerCase();
  const row = inputElem.closest("div.flex");
  const hiddenInput = row ? row.querySelector(".guarantor-member-id-input") : null;
  if (!hiddenInput) return;

  const candidates = window.cachedGuarantorCandidates || [];
  const matched = candidates.find(c => {
    const fullStr = `${c.member_code} - ${c.first_name} ${c.last_name}`.toLowerCase();
    return fullStr === val || c.member_code.toLowerCase() === val || `${c.first_name} ${c.last_name}`.toLowerCase() === val;
  });

  if (matched) {
    hiddenInput.value = matched.id;
    inputElem.classList.remove("border-rose-300");
    inputElem.classList.add("border-emerald-400");
  } else {
    hiddenInput.value = "";
    inputElem.classList.remove("border-emerald-400");
  }
}
window.onGuarantorInputChanged = onGuarantorInputChanged;

function updateGuarantorTotals() {
  const amountInputs = document.querySelectorAll(".guarantor-amount-input");
  let total = 0;
  amountInputs.forEach(inp => {
    const val = parseFloat(inp.value);
    if (!isNaN(val) && val > 0) total += val;
  });
  const badge = document.getElementById("loan-total-guaranteed-badge");
  if (badge) {
    badge.textContent = `₦${total.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
  }
}
window.updateGuarantorTotals = updateGuarantorTotals;

function openLoanModal() {
  const modal = document.getElementById("modal-loan");
  if (modal) {
    modal.classList.remove("hidden");
    populateGuarantorCandidates();
    handleLoanProductChange();

    const container = document.getElementById("loan-guarantors-container");
    if (container && container.children.length === 0) {
      addGuarantorRow();
    }
  }
}
window.openLoanModal = openLoanModal;

function closeLoanModal() {
  const modal = document.getElementById("modal-loan");
  if (modal) modal.classList.add("hidden");
}
window.closeLoanModal = closeLoanModal;

async function handleLoanSubmit(e) {
  e.preventDefault();
  if (!currentUser || !currentUser.id) {
    alert("Please log in as an active cooperator to apply for a loan.");
    return;
  }
  const amount = parseFloat(document.getElementById("loan-request-amount").value);
  const purpose = document.getElementById("loan-purpose").value.trim();
  const tenure = parseInt(document.getElementById("loan-tenure").value || "6");
  const productId = parseInt(document.getElementById("loan-product").value || "1");

  // Collect guarantors
  const guarantorRows = document.querySelectorAll("#loan-guarantors-container > div");
  const guarantors = [];

  for (const row of guarantorRows) {
    const textInput = row.querySelector(".guarantor-search-input");
    const hiddenInput = row.querySelector(".guarantor-member-id-input");
    const amountInput = row.querySelector(".guarantor-amount-input");

    const textVal = textInput ? textInput.value.trim() : "";
    let memberId = hiddenInput ? parseInt(hiddenInput.value) : 0;
    const gAmount = amountInput ? parseFloat(amountInput.value) : 0;

    // Fallback search if hidden input wasn't populated yet
    if (!memberId && textVal) {
      const candidates = window.cachedGuarantorCandidates || [];
      const found = candidates.find(c => 
        textVal.toLowerCase().includes(c.member_code.toLowerCase()) || 
        textVal.toLowerCase().includes(c.first_name.toLowerCase())
      );
      if (found) memberId = found.id;
    }

    if (memberId && gAmount > 0) {
      if (memberId === currentUser.id) {
        alert("You cannot add yourself as your own guarantor. Please select another cooperator.");
        return;
      }
      guarantors.push({
        guarantor_member_id: memberId,
        guaranteed_amount: gAmount
      });
    }
  }

  if (guarantors.length === 0) {
    alert("Please add at least one valid cooperator guarantor with a guaranteed amount.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/loans`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        principal_amount: amount,
        tenure_months: tenure,
        purpose_narration: purpose,
        product_id: productId,
        guarantors: guarantors
      })
    });

    const result = await res.json();
    if (res.ok) {
      const loanData = result.data || result;
      alert(`✅ Loan Application Lodged Successfully!\n\nLoan Reference: ${loanData.loan_reference}\nProduct: ${loanData.product_name || 'Cooperative Facility'}\nAmount: ₦${parseFloat(loanData.principal_amount).toLocaleString()}\nGuarantors: ${guarantors.length} co-signers attached\nStatus: Stage 1 Credit Committee Vetting (0% Progress)`);
      closeLoanModal();
      document.getElementById("loan-form").reset();
      loadMemberLoanApplications();
    } else {
      alert(`Application Error: ${result.detail || "Could not lodge loan application."}`);
    }
  } catch (err) {
    alert("Connection error while submitting loan application.");
  }
}
window.handleLoanSubmit = handleLoanSubmit;

// -----------------------------------------------------------------------------
// 7. REGISTRATION, CONTRIBUTIONS & TRANSACTIONS
// -----------------------------------------------------------------------------
function openRegistrationModal() {
  const modal = document.getElementById("modal-registration");
  if (modal) modal.classList.remove("hidden");
}

function closeRegistrationModal() {
  const modal = document.getElementById("modal-registration");
  if (modal) modal.classList.add("hidden");
}

function openContributionModal() {
  const modal = document.getElementById("modal-contribution");
  if (modal) modal.classList.remove("hidden");
}

function closeContributionModal() {
  const modal = document.getElementById("modal-contribution");
  if (modal) modal.classList.add("hidden");
}

async function handleRegistrationSubmit(e) {
  e.preventDefault();
  const submitBtn = document.querySelector("#registration-form button[type='submit']");
  
  const firstName = document.getElementById("reg-first-name").value.trim();
  const lastName = document.getElementById("reg-last-name").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const phone = document.getElementById("reg-phone").value.trim();
  const employment = document.getElementById("reg-employment").value;
  const tier = document.getElementById("reg-tier").value;
  const address = document.getElementById("reg-address").value.trim();
  const passEl = document.getElementById("reg-password");
  const rawPass = passEl ? passEl.value.trim() : "";
  const password = rawPass || "Wealthbridge@2026";

  if (!firstName || !lastName || !email || !phone || !address) {
    showRegAlert("⚠️ Incomplete Entry: Please fill in all required fields marked with an asterisk (*).", "error");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Validating & Submitting to Database...";
  showRegAlert("Connecting to secure cooperative servers...", "info");

  try {
    const res = await fetch(`${API_BASE_URL}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        first_name: firstName,
        last_name: lastName,
        email: email,
        phone: phone,
        employment_status: employment,
        contribution_tier: tier,
        residential_address: address,
        identification_type: "NIN",
        password: password
      })
    });

    const data = await res.json();

    if (!res.ok) {
      const errMsg = formatApiErrorMessage(data.detail, data.message || "Registration could not be completed.");
      showRegAlert(`⚠️ ${errMsg}`, "error");
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Application & Generate Member ID";
      return;
    }

    const assignedCode = data.member_code || "";
    const memberName = data.full_name || `${firstName} ${lastName}`;
    const initialPwd = data.default_password || password;

    showRegAlert(`✅ ${data.message || 'Registration successful!'} Assigned Member Code: ${assignedCode}. Initial Password: ${initialPwd}`, "success");
    submitBtn.textContent = "Registered Successfully!";

    setTimeout(() => {
      closeRegistrationModal();
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Application & Generate Member ID";
      document.getElementById("registration-form").reset();
      hideRegAlert();
      // Prompt user to sign in
      openLoginModal();
      const idInput = document.getElementById("login-identifier");
      if (idInput && assignedCode) idInput.value = assignedCode;
      const pwdInput = document.getElementById("login-password");
      if (pwdInput && initialPwd) pwdInput.value = initialPwd;
    }, 2500);

  } catch (err) {
    showRegAlert("⚠️ Cooperative servers are temporarily unreachable. Please check your internet connection and try again in a few moments, or contact the Secretariat (wealthbridge.coopsociety@gmail.com).", "error");
    submitBtn.disabled = false;
    submitBtn.textContent = "Submit Application & Generate Member ID";
  }
}

function showRegAlert(msg, type) {
  const alertBox = document.getElementById("reg-status-alert");
  if (!alertBox) return;
  alertBox.classList.remove("hidden", "bg-red-50", "text-red-800", "border-red-200", "bg-emerald-50", "text-emerald-800", "border-emerald-200", "bg-blue-50", "text-blue-800", "border-blue-200");
  if (type === "error") {
    alertBox.className = "p-3.5 rounded-xl text-xs mb-4 bg-red-50 text-red-800 border border-red-200 font-semibold";
  } else if (type === "success") {
    alertBox.className = "p-3.5 rounded-xl text-xs mb-4 bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold";
  } else {
    alertBox.className = "p-3.5 rounded-xl text-xs mb-4 bg-blue-50 text-blue-800 border border-blue-200";
  }
  alertBox.textContent = msg;
}

function hideRegAlert() {
  const alertBox = document.getElementById("reg-status-alert");
  if (alertBox) alertBox.classList.add("hidden");
}

function setupContributionSplitPreview() {
  const amountInput = document.getElementById("contrib-amount");
  if (!amountInput) return;

  amountInput.addEventListener("input", () => {
    const val = parseFloat(amountInput.value) || 0;
    if (val < 10000) {
      document.getElementById("split-preview-text").textContent = "Amount must meet the N10,000 monthly baseline.";
      return;
    }
    const share = Math.round((val * 0.10) / 1000) * 1000;
    const sav = val - 1000 - share;
    document.getElementById("split-preview-text").textContent = 
      `₦${sav.toLocaleString()} → Savings | ₦${share.toLocaleString()} → Shares | ₦1,000 → Welfare`;
  });
}

async function handleContributionSubmit(e) {
  e.preventDefault();
  const amount = parseFloat(document.getElementById("contrib-amount").value);
  const method = document.getElementById("contrib-method").value;
  const ref = document.getElementById("contrib-ref").value.trim();

  const memberId = currentUser ? currentUser.id : 1;

  try {
    const res = await fetch(`${API_BASE_URL}/contributions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        member_id: memberId,
        total_amount: amount,
        payment_method: method,
        channel_reference: ref,
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert("Success! " + data.message);
      closeContributionModal();
      loadAuthenticatedMember();
      refreshTransactions();
      if (currentUser && currentUser.is_executive) {
        loadExecutiveMetrics();
      }
    } else {
      alert(`Error: ${data.detail || "Remittance processing failed."}`);
    }
  } catch (err) {
    alert("Connection error while recording contribution.");
  }
}

async function refreshTransactions() {
  try {
    const res = await fetch(`${API_BASE_URL}/transactions?limit=15`);
    if (res.ok) {
      const txns = await res.json();
      renderTransactionsTable(txns);
    }
  } catch (err) {
    console.warn("Could not load transactions from API:", err);
  }
}

function renderTransactionsTable(txns) {
  const tbody = document.getElementById("transactions-table-body");
  if (!tbody) return;

  if (!txns || txns.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-4 text-center text-slate-400">No transactions recorded yet in ledger.</td></tr>`;
    return;
  }

  tbody.innerHTML = txns.map(t => {
    const catClass = 
      t.ledger_category === 'SAVINGS' ? 'text-blue-600 bg-blue-50 border-blue-200' :
      t.ledger_category === 'SHARE_CAPITAL' ? 'text-amber-700 bg-amber-50 border-amber-200' :
      t.ledger_category === 'WELFARE_FUND' ? 'text-purple-700 bg-purple-50 border-purple-200' :
      'text-slate-700 bg-slate-50 border-slate-200';

    return `
      <tr class="hover:bg-slate-50 transition">
        <td class="py-2.5 font-mono text-[11px] text-slate-500">
          <div>${t.transaction_date ? t.transaction_date.split("T")[0] : '2026-10-14'}</div>
          <div class="text-[10px] text-slate-400">${t.transaction_ref}</div>
        </td>
        <td class="py-2.5">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${catClass}">${t.ledger_category}</span>
        </td>
        <td class="py-2.5 text-slate-700">${t.narration}</td>
        <td class="py-2.5 font-bold text-slate-900">₦${parseFloat(t.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
        <td class="py-2.5">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
            ${t.status || 'VERIFIED'}
          </span>
        </td>
      </tr>
    `;
  }).join("");
}

async function fetchAllMembers() {
  try {
    const res = await fetch(`${API_BASE_URL}/members`);
    if (res.ok) {
      cachedMembers = await res.json();
    }
  } catch (err) {
    console.warn("API members lookup:", err);
  }
}

// -----------------------------------------------------------------------------
// 8. TESTING CONTROLS (Wipe & Re-Seed)
// -----------------------------------------------------------------------------
function confirmResetDatabase() {
  if (confirm("⚠️ WARNING: This will purge all registered members and transactions from the backend database for fresh testing.\n\nProceed?")) {
    alert("To execute a complete purge, run WIPE_DATABASE_TEST_DATA.bat or wipe_test_data.py directly in the folder.");
  }
}

function confirmSeedDatabase() {
  if (confirm("Re-populate the 8 Founding Members (WMC-2026-001 through WMC-2026-008)?")) {
    alert("To re-seed founding members, run SEED_FOUNDING_MEMBERS.bat or seed_founding_members.py directly in the folder.");
  }
}

// -----------------------------------------------------------------------------
// 9. PUBLIC LANDING CALCULATOR
// -----------------------------------------------------------------------------
function updateCalculator() {
  const contribInput = document.getElementById("slider-contrib");
  const monthsInput = document.getElementById("slider-months");

  if (!contribInput || !monthsInput) return;

  const monthly = parseFloat(contribInput.value);
  const months = parseInt(monthsInput.value);

  document.getElementById("slider-contrib-display").textContent = "₦" + monthly.toLocaleString();
  document.getElementById("slider-months-display").textContent = months + " Month" + (months > 1 ? "s" : "");

  const monthlyShare = Math.round((monthly * 0.10) / 1000) * 1000;
  const monthlySavings = monthly - 1000 - monthlyShare;

  const totalSavings = monthlySavings * months;
  const totalSharesAmount = Math.min(200000, monthlyShare * months);
  const totalShareUnits = Math.floor(totalSharesAmount / 1000);
  const totalWelfare = 1000 * months;
  const maxLoan = totalSavings * 2.0;

  document.getElementById("calc-savings").textContent = "₦" + totalSavings.toLocaleString();
  document.getElementById("calc-loan").textContent = "₦" + maxLoan.toLocaleString();
  document.getElementById("calc-shares").textContent = `${totalShareUnits} units (₦${totalSharesAmount.toLocaleString()})`;
  document.getElementById("calc-welfare").textContent = "₦" + totalWelfare.toLocaleString() + " Pool";
}

// =============================================================================
// 10. KYC PROFILE & STATUTORY CONTACT GOVERNANCE WORKFLOW
// =============================================================================

async function refreshMemberKYCAndPhoto() {
  if (!currentUser) return;

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/profile`);
    if (!res.ok) return;
    const profile = await res.json();
    const member = profile.member || {};
    const percent = profile.kyc_completion_percent || 0;

    // Cockpit status bar progress
    const cockpitPercent = document.getElementById("cockpit-kyc-percent");
    const cockpitBar = document.getElementById("cockpit-kyc-bar");
    const cockpitStatus = document.getElementById("cockpit-kyc-status");
    const quickPill = document.getElementById("quick-kyc-pill");

    if (cockpitPercent) cockpitPercent.textContent = `${percent}%`;
    if (cockpitBar) cockpitBar.style.width = `${percent}%`;
    if (cockpitStatus) cockpitStatus.textContent = percent === 100 ? "100% Verified" : `${percent}% Done`;
    if (quickPill) quickPill.textContent = `${percent}%`;

    // Cockpit Avatar Photo Preview
    const avatarImg = document.getElementById("portal-avatar-img");
    const avatarInitials = document.getElementById("portal-avatar-initials");
    if (member.passport_photo) {
      if (avatarImg) {
        avatarImg.src = member.passport_photo;
        avatarImg.classList.remove("hidden");
      }
      if (avatarInitials) avatarInitials.classList.add("hidden");
    } else {
      if (avatarImg) avatarImg.classList.add("hidden");
      if (avatarInitials) avatarInitials.classList.remove("hidden");
    }

    // Pending contact update badge in cockpit
    const pendingBadge = document.getElementById("portal-contact-pending-badge");
    if (pendingBadge) {
      if (member.contact_change_status === "PENDING_APPROVAL") {
        pendingBadge.classList.remove("hidden");
      } else {
        pendingBadge.classList.add("hidden");
      }
    }
  } catch (err) {
    console.warn("Could not refresh member KYC profile:", err);
  }
}

function openProfileModal() {
  if (!currentUser) {
    openLoginModal();
    return;
  }
  const modal = document.getElementById("modal-profile");
  if (modal) modal.classList.remove("hidden");
  hideProfileAlert();
  loadMemberProfile(currentUser.id);
  loadVerifyMeBanks();
}

function closeProfileModal() {
  const modal = document.getElementById("modal-profile");
  if (modal) modal.classList.add("hidden");
}

let modalChangePasswordIsMandatory = false;

function openChangePasswordModal(isMandatory = false) {
  modalChangePasswordIsMandatory = Boolean(isMandatory);

  const modal = document.getElementById("modal-change-password");
  const title = document.getElementById("cp-modal-title");
  const subtitle = document.getElementById("cp-modal-subtitle");
  const closeBtn = document.getElementById("cp-modal-close-btn");
  const cancelBtn = document.getElementById("cp-cancel-btn");
  const mandatoryAlert = document.getElementById("cp-mandatory-alert");
  const alertBox = document.getElementById("cp-alert");
  const form = document.getElementById("change-password-form");

  if (form) form.reset();
  if (alertBox) {
    alertBox.className = "hidden p-3 rounded-xl text-xs mb-4";
    alertBox.textContent = "";
  }

  if (modalChangePasswordIsMandatory) {
    if (title) title.textContent = "Mandatory Password Update";
    if (subtitle) subtitle.textContent = "Please set a secure personal password to continue";
    if (closeBtn) closeBtn.classList.add("hidden");
    if (cancelBtn) cancelBtn.classList.add("hidden");
    if (mandatoryAlert) mandatoryAlert.classList.remove("hidden");
  } else {
    if (title) title.textContent = "Change Access Password";
    if (subtitle) subtitle.textContent = "Update your member portal sign-in credentials";
    if (closeBtn) closeBtn.classList.remove("hidden");
    if (cancelBtn) cancelBtn.classList.remove("hidden");
    if (mandatoryAlert) mandatoryAlert.classList.add("hidden");
  }

  if (modal) modal.classList.remove("hidden");
}

function closeChangePasswordModal() {
  if (modalChangePasswordIsMandatory) {
    alert("Cooperative Security Notice: You must update your default password before accessing other features.");
    return;
  }
  const modal = document.getElementById("modal-change-password");
  if (modal) modal.classList.add("hidden");
}

async function handleChangePasswordSubmit(e) {
  if (e && e.preventDefault) e.preventDefault();

  const oldPass = document.getElementById("cp-old-password")?.value.trim() || "";
  const newPass = document.getElementById("cp-new-password")?.value.trim() || "";
  const confirmPass = document.getElementById("cp-confirm-password")?.value.trim() || "";
  const alertBox = document.getElementById("cp-alert");
  const submitBtn = document.getElementById("btn-change-password-submit");

  function showAlert(msg, type = "error") {
    if (!alertBox) return;
    alertBox.className = `p-3.5 rounded-xl text-xs mb-4 font-medium leading-relaxed ${
      type === "success" ? "bg-emerald-50 text-emerald-900 border border-emerald-300" : "bg-red-50 text-red-900 border border-red-300"
    }`;
    alertBox.textContent = msg;
    alertBox.classList.remove("hidden");
  }

  if (!oldPass || !newPass || !confirmPass) {
    showAlert("Please fill in all password fields.", "error");
    return;
  }

  if (newPass.length < 8) {
    showAlert("New password must be at least 8 characters long.", "error");
    return;
  }

  if (newPass !== confirmPass) {
    showAlert("The new password and confirmation password do not match.", "error");
    return;
  }

  if (oldPass === newPass) {
    showAlert("The new password cannot be the same as your current default password.", "error");
    return;
  }

  const token = localStorage.getItem("wmc_token");
  if (!token) {
    showAlert("Authentication session expired. Please sign in again.", "error");
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = "<span>⏳</span><span>Updating Password...</span>";
  }

  try {
    const res = await fetch(`${API_BASE_URL}/auth/change-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        old_password: oldPass,
        new_password: newPass
      })
    });

    const data = await res.json();

    if (!res.ok) {
      const errDetail = formatApiErrorMessage(data.detail, "Password update failed. Please verify your current password.");
      showAlert(`⚠️ ${errDetail}`, "error");
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = "<span>🔒</span><span>Update Password</span>";
      }
      return;
    }

    // Success!
    showAlert("✅ Password updated successfully! Your account is now secured.", "success");
    modalChangePasswordIsMandatory = false;

    if (currentUser) {
      currentUser.must_change_password = false;
      localStorage.setItem("wmc_user", JSON.stringify(currentUser));
      updateAuthNavUI();
    }

    setTimeout(() => {
      closeChangePasswordModal();
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = "<span>🔒</span><span>Update Password</span>";
      }
    }, 1200);

  } catch (err) {
    console.error("Change password fetch error:", err);
    showAlert(`⚠️ Connection error: Could not reach authentication server.`, "error");
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = "<span>🔒</span><span>Update Password</span>";
    }
  }
}

function toggleUserDropdown(e) {
  if (e) e.stopPropagation();
  const menu = document.getElementById("nav-user-dropdown-menu");
  const chevron = document.getElementById("nav-user-chevron");
  const topbarMenu = document.getElementById("topbar-user-dropdown-menu");
  const topbarChevron = document.getElementById("topbar-user-chevron");

  if (topbarMenu) topbarMenu.classList.add("hidden");
  if (topbarChevron) topbarChevron.classList.remove("rotate-180");

  if (!menu) return;
  const isClosed = menu.classList.contains("hidden");
  if (isClosed) {
    menu.classList.remove("hidden");
    if (chevron) chevron.classList.add("rotate-180");
  } else {
    menu.classList.add("hidden");
    if (chevron) chevron.classList.remove("rotate-180");
  }
}

function toggleTopbarDropdown(e) {
  if (e) e.stopPropagation();
  const menu = document.getElementById("topbar-user-dropdown-menu");
  const chevron = document.getElementById("topbar-user-chevron");
  const navMenu = document.getElementById("nav-user-dropdown-menu");
  const navChevron = document.getElementById("nav-user-chevron");

  if (navMenu) navMenu.classList.add("hidden");
  if (navChevron) navChevron.classList.remove("rotate-180");

  if (!menu) return;
  const isClosed = menu.classList.contains("hidden");
  if (isClosed) {
    menu.classList.remove("hidden");
    if (chevron) chevron.classList.add("rotate-180");
  } else {
    menu.classList.add("hidden");
    if (chevron) chevron.classList.remove("rotate-180");
  }
}

function closeAllUserDropdowns() {
  const navMenu = document.getElementById("nav-user-dropdown-menu");
  const navChevron = document.getElementById("nav-user-chevron");
  const topbarMenu = document.getElementById("topbar-user-dropdown-menu");
  const topbarChevron = document.getElementById("topbar-user-chevron");

  if (navMenu) navMenu.classList.add("hidden");
  if (navChevron) navChevron.classList.remove("rotate-180");
  if (topbarMenu) topbarMenu.classList.add("hidden");
  if (topbarChevron) topbarChevron.classList.remove("rotate-180");
}

window.addEventListener("click", (e) => {
  const navContainer = document.getElementById("nav-user-dropdown-container");
  const topbarContainer = document.getElementById("topbar-user-dropdown-container");
  if (navContainer && !navContainer.contains(e.target) &&
      topbarContainer && !topbarContainer.contains(e.target)) {
    closeAllUserDropdowns();
  }
});

function showProfileAlert(msg, type = "error") {
  const alertBox = document.getElementById("profile-status-alert");
  if (!alertBox) return;
  alertBox.classList.remove("hidden", "bg-red-50", "text-red-800", "border-red-200", "bg-emerald-50", "text-emerald-800", "bg-amber-50", "text-amber-900", "border-amber-200");
  if (type === "error") {
    alertBox.className = "p-3.5 rounded-xl text-xs mb-4 bg-red-50 text-red-800 border border-red-200 font-semibold";
  } else if (type === "warning") {
    alertBox.className = "p-3.5 rounded-xl text-xs mb-4 bg-amber-50 text-amber-900 border border-amber-300 font-semibold";
  } else {
    alertBox.className = "p-3.5 rounded-xl text-xs mb-4 bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold";
  }
  alertBox.innerHTML = msg;
}

function hideProfileAlert() {
  const alertBox = document.getElementById("profile-status-alert");
  if (alertBox) alertBox.classList.add("hidden");
}

async function loadMemberProfile(memberId) {
  try {
    const res = await fetch(`${API_BASE_URL}/members/${memberId}/profile`);
    if (!res.ok) throw new Error("Failed to load profile");
    const data = await res.json();
    const member = data.member || {};
    const nok = data.next_of_kin || {};
    const percent = data.kyc_completion_percent || 0;
    const breakdown = data.kyc_breakdown || {};

    // 1. Score & Progress Bar
    const percentBadge = document.getElementById("kyc-percent-badge");
    const progressFill = document.getElementById("kyc-progress-fill");
    if (percentBadge) percentBadge.textContent = `${percent}% COMPLETE`;
    if (progressFill) progressFill.style.width = `${percent}%`;

    // 2. Pillars Breakdown
    updatePillarUI("pillar-personal", breakdown.personal);
    updatePillarUI("pillar-nin", breakdown.id_verification);
    updatePillarUI("pillar-contact", breakdown.contact);
    updatePillarUI("pillar-photo", breakdown.passport_photo);
    updatePillarUI("pillar-bank", breakdown.banking);
    updatePillarUI("pillar-nok", breakdown.next_of_kin);

    // 3. Populate Form Inputs
    const fullNameInput = document.getElementById("profile-full-name");
    if (fullNameInput) fullNameInput.value = member.full_name || "";

    const dobInput = document.getElementById("profile-dob");
    if (dobInput) dobInput.value = member.date_of_birth ? member.date_of_birth.split("T")[0] : "";

    const genderInput = document.getElementById("profile-gender");
    if (genderInput) genderInput.value = member.gender || "";

    const maritalInput = document.getElementById("profile-marital-status");
    if (maritalInput) maritalInput.value = member.marital_status || "";

    const occInput = document.getElementById("profile-occupation");
    if (occInput) occInput.value = member.occupation || "";

    const ninInput = document.getElementById("profile-nin");
    if (ninInput) ninInput.value = member.national_id_nin || "";

    const bvnInput = document.getElementById("profile-bvn");
    if (bvnInput) bvnInput.value = member.bvn || "";

    const codeInput = document.getElementById("profile-member-code");
    if (codeInput) codeInput.value = member.member_code || "";

    const emailInput = document.getElementById("profile-email");
    if (emailInput) emailInput.value = member.email || "";

    const phoneInput = document.getElementById("profile-phone");
    if (phoneInput) phoneInput.value = member.phone_number || "";

    const addrInput = document.getElementById("profile-address");
    if (addrInput) addrInput.value = member.residential_address || "";

    const bankNameInput = document.getElementById("profile-bank-name");
    if (bankNameInput) bankNameInput.value = member.bank_name || "";

    await loadVerifyMeBanks();
    const bankCodeInput = document.getElementById("profile-bank-code");
    if (bankCodeInput && member.bank_name) {
      const matched = cachedBanks.find(b => b.name.toLowerCase() === member.bank_name.toLowerCase());
      if (matched) bankCodeInput.value = matched.code;
    }

    const bankAccNumInput = document.getElementById("profile-bank-account-num");
    if (bankAccNumInput) bankAccNumInput.value = member.bank_account_number || "";

    const bankAccNameInput = document.getElementById("profile-bank-account-name");
    if (bankAccNameInput) bankAccNameInput.value = member.bank_account_name || "";

    const nokNameInput = document.getElementById("profile-nok-name");
    if (nokNameInput) nokNameInput.value = nok.full_name || "";

    const nokRelInput = document.getElementById("profile-nok-rel");
    if (nokRelInput) nokRelInput.value = nok.relationship || "";

    const nokPhoneInput = document.getElementById("profile-nok-phone");
    if (nokPhoneInput) nokPhoneInput.value = nok.phone_number || "";

    const nokAddrInput = document.getElementById("profile-nok-address");
    if (nokAddrInput) nokAddrInput.value = nok.residential_address || "";

    // 4. Passport Photograph
    const photoPreview = document.getElementById("profile-photo-preview");
    const photoPlaceholder = document.getElementById("profile-photo-placeholder");
    const removeBtn = document.getElementById("btn-remove-photo");
    const hiddenBase64 = document.getElementById("profile-photo-base64");

    if (member.passport_photo) {
      if (photoPreview) {
        photoPreview.src = member.passport_photo;
        photoPreview.classList.remove("hidden");
      }
      if (photoPlaceholder) photoPlaceholder.classList.add("hidden");
      if (removeBtn) removeBtn.classList.remove("hidden");
      if (hiddenBase64) hiddenBase64.value = member.passport_photo;
    } else {
      if (photoPreview) photoPreview.classList.add("hidden");
      if (photoPlaceholder) photoPlaceholder.classList.remove("hidden");
      if (removeBtn) removeBtn.classList.add("hidden");
      if (hiddenBase64) hiddenBase64.value = "";
    }

    // 5. Active Pending Contact Modifications Alert
    const pendingBox = document.getElementById("modal-pending-contact-alert");
    const badgeEmail = document.getElementById("badge-email-pending");
    const badgePhone = document.getElementById("badge-phone-pending");
    const badgeAddr = document.getElementById("badge-address-pending");

    if (member.contact_change_status === "PENDING_APPROVAL") {
      if (pendingBox) pendingBox.classList.remove("hidden");
      const alertEmail = document.getElementById("pending-alert-email");
      const alertPhone = document.getElementById("pending-alert-phone");
      const alertAddr = document.getElementById("pending-alert-address");
      const alertDate = document.getElementById("pending-alert-date");

      if (alertEmail) alertEmail.textContent = member.pending_email || "(No change)";
      if (alertPhone) alertPhone.textContent = member.pending_phone || "(No change)";
      if (alertAddr) alertAddr.textContent = member.pending_address || "(No change)";
      if (alertDate) alertDate.textContent = member.contact_change_requested_at ? member.contact_change_requested_at.replace("T", " ").substring(0, 19) : "Pending";

      if (badgeEmail) {
        if (member.pending_email) badgeEmail.classList.remove("hidden");
        else badgeEmail.classList.add("hidden");
      }
      if (badgePhone) {
        if (member.pending_phone) badgePhone.classList.remove("hidden");
        else badgePhone.classList.add("hidden");
      }
      if (badgeAddr) {
        if (member.pending_address) badgeAddr.classList.remove("hidden");
        else badgeAddr.classList.add("hidden");
      }
    } else {
      if (pendingBox) pendingBox.classList.add("hidden");
      if (badgeEmail) badgeEmail.classList.add("hidden");
      if (badgePhone) badgePhone.classList.add("hidden");
      if (badgeAddr) badgeAddr.classList.add("hidden");
    }

    // Also update Cockpit widgets
    refreshMemberKYCAndPhoto();

  } catch (err) {
    console.error("Error loading member profile:", err);
    showProfileAlert("Could not load profile details from backend database.", "error");
  }
}

function updatePillarUI(pillarElementId, pillarData) {
  const el = document.getElementById(pillarElementId);
  if (!el) return;
  const statusSpan = el.querySelector(".pillar-status");

  if (pillarData && pillarData.status === "COMPLETE") {
    el.className = "p-2 rounded-lg kyc-pillar-complete flex items-center justify-between";
    if (statusSpan) {
      statusSpan.className = "pillar-status font-bold text-emerald-400";
      statusSpan.textContent = "✅ Complete";
    }
  } else {
    el.className = "p-2 rounded-lg kyc-pillar-pending flex items-center justify-between";
    if (statusSpan) {
      statusSpan.className = "pillar-status font-bold text-slate-400";
      statusSpan.textContent = "⚪ Pending";
    }
  }
}

function handlePassportPhotoUpload(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  if (file.size > 3 * 1024 * 1024) {
    alert("Photograph exceeds the 3MB statutory file size limit. Please upload an optimized passport image.");
    event.target.value = "";
    return;
  }

  const reader = new FileReader();
  reader.onload = function(e) {
    const base64Data = e.target.result;
    const hiddenInput = document.getElementById("profile-photo-base64");
    if (hiddenInput) hiddenInput.value = base64Data;

    const preview = document.getElementById("profile-photo-preview");
    const placeholder = document.getElementById("profile-photo-placeholder");
    const removeBtn = document.getElementById("btn-remove-photo");

    if (preview) {
      preview.src = base64Data;
      preview.classList.remove("hidden");
    }
    if (placeholder) placeholder.classList.add("hidden");
    if (removeBtn) removeBtn.classList.remove("hidden");
  };
  reader.readAsDataURL(file);
}

function removePassportPhoto() {
  const hiddenInput = document.getElementById("profile-photo-base64");
  const fileInput = document.getElementById("profile-photo-file");
  if (hiddenInput) hiddenInput.value = "";
  if (fileInput) fileInput.value = "";

  const preview = document.getElementById("profile-photo-preview");
  const placeholder = document.getElementById("profile-photo-placeholder");
  const removeBtn = document.getElementById("btn-remove-photo");

  if (preview) preview.classList.add("hidden");
  if (placeholder) placeholder.classList.remove("hidden");
  if (removeBtn) removeBtn.classList.add("hidden");
}

async function handleProfileSubmit(e) {
  if (e && e.preventDefault) e.preventDefault();
  if (!currentUser) return;

  const btn = document.getElementById("btn-save-profile");
  const origText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span>⏳</span><span>Saving to Database...</span>`;
  hideProfileAlert();

  const payload = {
    gender: document.getElementById("profile-gender").value || null,
    marital_status: document.getElementById("profile-marital-status").value || null,
    date_of_birth: document.getElementById("profile-dob").value || null,
    occupation: document.getElementById("profile-occupation").value || null,
    national_id_nin: document.getElementById("profile-nin").value.trim() || null,
    identification_number: document.getElementById("profile-nin").value.trim() || null,
    bvn: document.getElementById("profile-bvn").value.trim() || null,
    email: document.getElementById("profile-email").value.trim(),
    phone: document.getElementById("profile-phone").value.trim(),
    phone_number: document.getElementById("profile-phone").value.trim(),
    residential_address: document.getElementById("profile-address").value.trim(),
    bank_name: document.getElementById("profile-bank-name").value.trim() || null,
    bank_account_number: document.getElementById("profile-bank-account-num").value.trim() || null,
    bank_account_name: document.getElementById("profile-bank-account-name").value.trim() || null,
    passport_photo: (document.getElementById("profile-photo-base64") && document.getElementById("profile-photo-base64").value) || null,
    next_of_kin_name: document.getElementById("profile-nok-name").value.trim() || null,
    next_of_kin_relationship: document.getElementById("profile-nok-rel").value.trim() || null,
    next_of_kin_phone: document.getElementById("profile-nok-phone").value.trim() || null,
    next_of_kin_address: document.getElementById("profile-nok-address").value.trim() || null
  };

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (!res.ok) {
      showProfileAlert(`⚠️ ${data.detail || "Failed to update profile."}`, "error");
      btn.disabled = false;
      btn.innerHTML = origText;
      return;
    }

    // Success Handling
    let successMsg = `✅ <strong>Profile Saved Successfully!</strong> KYC Completion is now at <strong>${data.kyc_completion_percent}%</strong>.`;
    if (data.contact_changes_pending) {
      successMsg += `<div class="mt-2 text-[11px] p-2 bg-amber-100/60 rounded border border-amber-300 text-amber-950 font-normal">
        <strong>⚖️ Statutory Dual Sign-Off Notice:</strong> Your modifications to <em>${data.pending_fields.join(", ")}</em> have been queued for statutory approval by the President and General Secretary before overwriting live records.
      </div>`;
      showProfileAlert(successMsg, "warning");
    } else {
      showProfileAlert(successMsg, "success");
    }

    // Reload profile modal and cockpit UI
    loadMemberProfile(currentUser.id);

  } catch (err) {
    console.error("Profile submit error:", err);
    showProfileAlert("Network/Server error: Could not reach the backend API server.", "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = origText;
  }
}

// -----------------------------------------------------------------------------
// 10B. VERIFYME NG BANK LOOKUP & NUBAN ACCOUNT NAME RESOLUTION
// -----------------------------------------------------------------------------
const BANK_FORM_MAP = {
  "profile": {
    name: "profile-bank-name",
    code: "profile-bank-code",
    list: "profile-bank-list",
    accNum: "profile-bank-account-num",
    accName: "profile-bank-account-name",
    status: "profile-account-verify-status"
  },
  "admin-add": {
    name: "admin-add-bank-name",
    code: "admin-add-bank-code",
    list: "admin-add-bank-list",
    accNum: "admin-add-bank-acc-num",
    accName: "admin-add-bank-acc-name",
    status: "admin-add-account-verify-status"
  },
  "admin-edit": {
    name: "admin-edit-bank-name",
    code: "admin-edit-bank-code",
    list: "admin-edit-bank-list",
    accNum: "admin-edit-bank-acc-num",
    accName: "admin-edit-bank-acc-name",
    status: "admin-edit-account-verify-status"
  }
};

async function loadVerifyMeBanks(force = false) {
  if (banksLoaded && !force && cachedBanks.length > 0) return cachedBanks;
  try {
    const res = await fetch(`${API_BASE_URL}/verifyme/banks`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      console.warn("Could not load bank list:", err.detail || res.statusText);
      return cachedBanks;
    }
    const data = await res.json();
    cachedBanks = (data.data || []).sort((a, b) => a.name.localeCompare(b.name));
    banksLoaded = true;
    return cachedBanks;
  } catch (err) {
    console.warn("Bank list fetch error:", err);
    return cachedBanks;
  }
}

function getBankFormIds(prefix) {
  return BANK_FORM_MAP[prefix] || null;
}

async function showBankList(prefix) {
  const ids = getBankFormIds(prefix);
  if (!ids) return;
  const listEl = document.getElementById(ids.list);
  if (!listEl) return;

  if (!banksLoaded) {
    await loadVerifyMeBanks();
  }

  const input = document.getElementById(ids.name);
  const query = (input ? input.value : "").toLowerCase().trim();
  renderBankList(prefix, query);
  listEl.classList.remove("hidden");
}

function hideBankList(prefix) {
  const ids = getBankFormIds(prefix);
  if (!ids) return;
  const listEl = document.getElementById(ids.list);
  if (listEl) listEl.classList.add("hidden");
}

function filterBankList(prefix) {
  const ids = getBankFormIds(prefix);
  if (!ids) return;
  const input = document.getElementById(ids.name);
  const listEl = document.getElementById(ids.list);
  if (!input || !listEl) return;

  const query = input.value.toLowerCase().trim();
  renderBankList(prefix, query);
  listEl.classList.remove("hidden");
}

function renderBankList(prefix, query) {
  const ids = getBankFormIds(prefix);
  if (!ids) return;
  const listEl = document.getElementById(ids.list);
  if (!listEl) return;

  let banks = cachedBanks.slice();

  if (query.length >= 1) {
    const q = query;
    banks = banks.filter(b => {
      const name = b.name.toLowerCase();
      return name.startsWith(q) || name.includes(q);
    });
  }

  if (banks.length === 0) {
    listEl.innerHTML = `<div class="p-3 text-xs text-slate-400 text-center">${query ? "No banks match your search." : "Loading banks..."}</div>`;
    return;
  }

  const maxShow = query.length >= 3 ? banks.length : Math.min(banks.length, 50);
  const shown = banks.slice(0, maxShow);

  listEl.innerHTML = shown.map(b => {
    const typeLabel = b.type === "microfinance" ? " (MFB)" : "";
    return `<div class="bank-option px-3 py-2 text-xs hover:bg-amber-50 cursor-pointer border-b border-slate-100"
      onmousedown="selectBank('${prefix}', '${escapeAttr(b.name)}', '${escapeAttr(b.code)}')">
      <span class="font-bold text-slate-800">${escapeHtml(b.name)}</span>
      <span class="text-slate-400 font-mono ml-1">[${b.code}]</span>
      <span class="text-emerald-600 text-[10px] ml-1">${typeLabel}</span>
    </div>`;
  }).join("");

  if (banks.length > maxShow) {
    listEl.innerHTML += `<div class="p-2 text-[10px] text-slate-400 text-center bg-slate-50">...and ${banks.length - maxShow} more. Type 3+ letters to narrow.</div>`;
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function escapeAttr(str) {
  return String(str).replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

function selectBank(prefix, bankName, bankCode) {
  const ids = getBankFormIds(prefix);
  if (!ids) return;
  const nameInput = document.getElementById(ids.name);
  const codeInput = document.getElementById(ids.code);
  if (nameInput) nameInput.value = bankName;
  if (codeInput) codeInput.value = bankCode;
  hideBankList(prefix);
}

async function verifyAccountName(prefix) {
  const ids = getBankFormIds(prefix);
  if (!ids) return;

  const bankNameInput = document.getElementById(ids.name);
  const bankCodeInput = document.getElementById(ids.code);
  const accNumInput = document.getElementById(ids.accNum);
  const accNameInput = document.getElementById(ids.accName);
  const statusEl = document.getElementById(ids.status);

  const bankName = bankNameInput ? bankNameInput.value.trim() : "";
  const bankCode = bankCodeInput ? bankCodeInput.value.trim() : "";
  const accountNumber = accNumInput ? accNumInput.value.trim() : "";

  if (!bankName) {
    setVerifyStatus(statusEl, "Please select a bank from the list first.", "error");
    return;
  }
  if (!bankCode) {
    const matched = cachedBanks.find(b => b.name.toLowerCase() === bankName.toLowerCase());
    if (matched) {
      if (bankCodeInput) bankCodeInput.value = matched.code;
    } else {
      setVerifyStatus(statusEl, "Please select a bank from the dropdown list to get its code.", "error");
      return;
    }
  }
  if (!accountNumber || accountNumber.length !== 10 || !/^\d+$/.test(accountNumber)) {
    setVerifyStatus(statusEl, "Please enter a valid 10-digit NUBAN account number.", "error");
    return;
  }

  const finalCode = (bankCodeInput ? bankCodeInput.value : "") || bankCode;
  setVerifyStatus(statusEl, "⏳ Verifying account name with your bank...", "info");

  try {
    const res = await fetch(`${API_BASE_URL}/verifyme/account?bank_code=${encodeURIComponent(finalCode)}&account_number=${encodeURIComponent(accountNumber)}`);
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      setVerifyStatus(statusEl, `⚠️ ${data.detail || "Account verification failed."}`, "error");
      return;
    }

    const accName = (data.data && data.data.account_name) || "";
    if (accName && accNameInput) {
      accNameInput.value = accName.toUpperCase();
      setVerifyStatus(statusEl, `✅ Account verified: <strong>${escapeHtml(accName.toUpperCase())}</strong>`, "success");
    } else {
      setVerifyStatus(statusEl, "⚠️ No account name returned. Please check the account number.", "error");
    }
  } catch (err) {
    console.error("Account verification error:", err);
    setVerifyStatus(statusEl, "⚠️ Network error: Could not reach the verification service.", "error");
  }
}

function setVerifyStatus(el, msg, type) {
  if (!el) return;
  el.classList.remove("hidden", "text-red-600", "text-emerald-600", "text-slate-500", "text-amber-600");
  if (type === "error") el.className = "text-[11px] text-red-600 font-semibold mt-1";
  else if (type === "success") el.className = "text-[11px] text-emerald-600 font-semibold mt-1";
  else el.className = "text-[11px] text-amber-600 font-semibold mt-1";
  el.innerHTML = msg;
}

// -----------------------------------------------------------------------------
// 11. EXECUTIVE GOVERNANCE: STATUTORY CONTACT REVIEW QUEUE
// -----------------------------------------------------------------------------
async function loadPendingContactChanges() {
  const tbodySec = document.getElementById("pending-contact-tbody");
  const tbodyPres = document.getElementById("pending-contact-pres-tbody");

  try {
    const res = await fetch(`${API_BASE_URL}/admin/pending-contact-changes`);
    if (!res.ok) throw new Error("Failed to load queue");
    const items = await res.json();

    const badgeSec = document.getElementById("tab-sec-contact-badge");
    const badgePres = document.getElementById("tab-pres-contact-badge");
    if (badgeSec) badgeSec.textContent = items.length;
    if (badgePres) badgePres.textContent = items.length;

    const renderContent = (isPres) => {
      if (!items || items.length === 0) {
        return `<tr><td colspan="6" class="p-4 text-center text-slate-400">✅ No pending contact modifications. All cooperator records are verified!</td></tr>`;
      }

      return items.map(item => {
        const fields = [];
        let currVal = [];
        let propVal = [];

        if (item.pending_email) {
          fields.push("Email");
          currVal.push(`<div><strong>Email:</strong> ${item.current_email || 'None'}</div>`);
          propVal.push(`<div><strong>Email:</strong> <span class="diff-new">${item.pending_email}</span></div>`);
        }
        if (item.pending_phone) {
          fields.push("Phone");
          currVal.push(`<div><strong>Phone:</strong> ${item.current_phone || 'None'}</div>`);
          propVal.push(`<div><strong>Phone:</strong> <span class="diff-new">${item.pending_phone}</span></div>`);
        }
        if (item.pending_address) {
          fields.push("Address");
          currVal.push(`<div><strong>Address:</strong> ${item.current_address || 'None'}</div>`);
          propVal.push(`<div><strong>Address:</strong> <span class="diff-new">${item.pending_address}</span></div>`);
        }

        const rawDate = item.contact_change_requested_at || item.requested_at;
        const dateStr = rawDate ? String(rawDate).replace("T", " ").substring(0, 16) : "Recent";
        const roleLabel = isPres ? "Presidential Dual Sign-Off" : "Secretariat Authorization";

        return `
          <tr class="hover:bg-slate-50 transition border-b border-slate-100">
            <td class="p-3">
              <span class="font-mono font-bold text-slate-800 block">${item.member_code}</span>
              <span class="font-bold text-wmcNavy-950">${item.full_name}</span>
            </td>
            <td class="p-3">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">${fields.join(", ")}</span>
            </td>
            <td class="p-3 text-[11px] text-slate-600">${currVal.join("")}</td>
            <td class="p-3 text-[11px]">${propVal.join("")}</td>
            <td class="p-3 text-[11px] text-slate-400 font-mono">${dateStr}</td>
            <td class="p-3 text-right space-x-1">
              <button onclick="approveContactChange(${item.id})" class="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[10px] transition shadow-sm" title="${roleLabel}">
                ✅ Approve &amp; Activate
              </button>
              <button onclick="rejectContactChange(${item.id})" class="px-2.5 py-1.5 rounded-lg bg-slate-200 hover:bg-red-100 hover:text-red-700 text-slate-700 font-bold text-[10px] transition">
                ❌ Reject
              </button>
            </td>
          </tr>
        `;
      }).join("");
    };

    if (tbodySec) tbodySec.innerHTML = renderContent(false);
    if (tbodyPres) tbodyPres.innerHTML = renderContent(true);

  } catch (err) {
    console.warn("Could not load contact changes queue:", err);
    if (tbodySec) tbodySec.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-400">Could not retrieve queue from backend.</td></tr>`;
    if (tbodyPres) tbodyPres.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-400">Could not retrieve queue from backend.</td></tr>`;
  }
}

async function approveContactChange(memberId) {
  if (!confirm(`Are you sure you want to approve and promote these statutory contact modifications to the live cooperator record?`)) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/approve-contact-change`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        member_id: memberId,
        officer_id: currentUser ? currentUser.id : 1
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert(`✅ Success: ${data.message}`);
      loadPendingContactChanges();
      loadExecMembersRegistry();
      if (currentUser && currentUser.id === memberId) {
        loadAuthenticatedMember();
        loadMemberProfile(currentUser.id);
      }
    } else {
      alert(`⚠️ Error: ${data.detail || "Approval failed."}`);
    }
  } catch (err) {
    alert("Connection error occurred while approving contact changes.");
  }
}

async function rejectContactChange(memberId) {
  const reason = prompt("Please provide a reason for rejecting this contact modification request:");
  if (reason === null) return; // User pressed Cancel

  try {
    const res = await fetch(`${API_BASE_URL}/admin/reject-contact-change`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        member_id: memberId,
        officer_id: currentUser ? currentUser.id : 1,
        reason: reason || "Rejected by Secretariat"
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert(`✅ Contact change rejected: ${data.message}`);
      loadPendingContactChanges();
      if (currentUser && currentUser.id === memberId) {
        loadAuthenticatedMember();
        loadMemberProfile(currentUser.id);
      }
    } else {
      alert(`⚠️ Error: ${data.detail || "Rejection failed."}`);
    }
  } catch (err) {
    alert("Connection error occurred while rejecting contact changes.");
  }
}

// =============================================================================
// DYNAMIC TARGET SAVINGS LEDGERS (VOLUNTARY GOAL SAVINGS)
// =============================================================================

const TARGET_CATEGORY_META = {
  BIRTHDAY: { icon: "🎂", label: "Birthday Target", badgeBg: "bg-pink-100 text-pink-800 border-pink-200", barColor: "from-pink-500 to-rose-500", defaultTitle: "Birthday Celebration Target" },
  CHRISTMAS: { icon: "🎄", label: "Christmas Target", badgeBg: "bg-red-100 text-red-800 border-red-200", barColor: "from-red-500 to-emerald-600", defaultTitle: "Christmas & End of Year Celebration Target" },
  ILEYA: { icon: "🐑", label: "Ileya Target", badgeBg: "bg-amber-100 text-amber-800 border-amber-200", barColor: "from-amber-500 to-yellow-600", defaultTitle: "Eid-el-Kabir (Ileya) Celebration Target" },
  BUILDING: { icon: "🏗️", label: "Building Target", badgeBg: "bg-sky-100 text-sky-800 border-sky-200", barColor: "from-sky-500 to-blue-600", defaultTitle: "Property & Building Construction Target" },
  PILGRIMAGE: { icon: "✈️", label: "Pilgrimage Target (Hajj & Jerusalem)", badgeBg: "bg-indigo-100 text-indigo-800 border-indigo-200", barColor: "from-indigo-500 to-purple-600", defaultTitle: "Holy Pilgrimage Target (Hajj & Jerusalem)" },
  EDUCATION: { icon: "🎓", label: "Education Target", badgeBg: "bg-blue-100 text-blue-800 border-blue-200", barColor: "from-blue-600 to-cyan-500", defaultTitle: "Education & Professional Tuition Target" },
  OTHERS: { icon: "🎯", label: "Others", badgeBg: "bg-slate-100 text-slate-800 border-slate-200", barColor: "from-teal-500 to-emerald-600", defaultTitle: "Special Target Savings" }
};

let cachedMemberTargets = [];

function handleTargetTypeChange(type) {
  const meta = TARGET_CATEGORY_META[type];
  const titleInput = document.getElementById("target-title-input");
  if (meta && titleInput && !titleInput.value) {
    const curYear = new Date().getFullYear();
    const nextYear = curYear + 1;
    if (type === "ILEYA" || type === "BIRTHDAY") {
      titleInput.value = `${nextYear} ${meta.defaultTitle}`;
    } else if (type === "CHRISTMAS") {
      titleInput.value = `${curYear} ${meta.defaultTitle}`;
    } else {
      titleInput.value = meta.defaultTitle;
    }
  }
}

function openCreateTargetSavingsModal() {
  const modal = document.getElementById("modal-create-target-savings");
  if (!modal) return;
  const alertEl = document.getElementById("create-target-alert");
  if (alertEl) alertEl.classList.add("hidden");

  // Set minimum maturity date to tomorrow
  const dateInput = document.getElementById("target-maturity-date");
  if (dateInput) {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const minStr = tomorrow.toISOString().split("T")[0];
    dateInput.min = minStr;
    if (!dateInput.value) {
      // Default suggested maturity: 6 months out
      const defDate = new Date();
      defDate.setMonth(defDate.getMonth() + 6);
      dateInput.value = defDate.toISOString().split("T")[0];
    }
  }

  modal.classList.remove("hidden");
}

function closeCreateTargetSavingsModal() {
  const modal = document.getElementById("modal-create-target-savings");
  if (modal) modal.classList.add("hidden");
}

async function handleCreateTargetSavingsSubmit(event) {
  event.preventDefault();
  const alertEl = document.getElementById("create-target-alert");
  const submitBtn = document.getElementById("btn-submit-create-target");

  const targetType = document.getElementById("target-type-select").value;
  const title = document.getElementById("target-title-input").value.trim();
  const targetAmount = parseFloat(document.getElementById("target-amount-input").value || "0");
  const maturityDate = document.getElementById("target-maturity-date").value;
  const initialDeposit = parseFloat(document.getElementById("target-initial-deposit").value || "0");
  const autoSave = parseFloat(document.getElementById("target-auto-save").value || "0");
  const paymentMethod = document.getElementById("target-payment-method").value;

  if (!currentUser) {
    alert("Please sign in to create a Target Savings Ledger.");
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Creating Target Ledger...";
  }

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/target-savings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_type: targetType,
        title: title,
        target_amount: targetAmount,
        maturity_date: maturityDate,
        initial_deposit: initialDeposit,
        auto_save_amount: autoSave,
        payment_method: paymentMethod
      })
    });

    const data = await res.json();
    if (res.ok) {
      if (alertEl) {
        alertEl.className = "p-3.5 rounded-xl text-xs mb-4 bg-emerald-50 text-emerald-900 border border-emerald-200";
        alertEl.textContent = `✅ Success: Target Savings Ledger '${data.title}' created!`;
        alertEl.classList.remove("hidden");
      }
      setTimeout(() => {
        closeCreateTargetSavingsModal();
        loadMemberTargetSavings();
        loadAuthenticatedMember();
      }, 1000);
    } else {
      if (alertEl) {
        alertEl.className = "p-3.5 rounded-xl text-xs mb-4 bg-red-50 text-red-900 border border-red-200";
        alertEl.textContent = `⚠️ Error: ${data.detail || "Failed to create target ledger."}`;
        alertEl.classList.remove("hidden");
      }
    }
  } catch (err) {
    if (alertEl) {
      alertEl.className = "p-3.5 rounded-xl text-xs mb-4 bg-red-50 text-red-900 border border-red-200";
      alertEl.textContent = "⚠️ Network error: Could not reach backend server.";
      alertEl.classList.remove("hidden");
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Create Target Ledger →";
    }
  }
}

async function loadMemberTargetSavings() {
  if (!currentUser || currentUser.is_admin_only) return;
  const container = document.getElementById("target-savings-container");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/target-savings`);
    if (!res.ok) throw new Error("Could not fetch target savings");
    const data = await res.json();

    const summary = data.summary || {};
    cachedMemberTargets = data.targets || [];

    // Update Summary Header Widgets
    const statTotal = document.getElementById("stat-target-total");
    const statGoal = document.getElementById("stat-target-goal");
    const statProgress = document.getElementById("stat-target-progress-overall");
    const statActive = document.getElementById("stat-target-active-count");
    const statMatured = document.getElementById("stat-target-matured-count");

    if (statTotal) statTotal.textContent = "₦" + (summary.total_target_savings || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
    if (statGoal) statGoal.textContent = "₦" + (summary.total_target_goal || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
    if (statProgress) statProgress.textContent = `${summary.overall_completion_rate || 0}% Goal Achieved`;
    if (statActive) statActive.textContent = summary.active_targets_count || 0;
    if (statMatured) statMatured.textContent = summary.matured_targets_count || 0;

    // Mirror to Dashboard Target Quick Card & Sidebar Badge
    const dashTargetTotal = document.getElementById("dash-stat-target-total");
    const dashTargetActive = document.getElementById("dash-stat-target-active");
    const dashTargetMatured = document.getElementById("dash-stat-target-matured");
    const sidebarTargetsBadge = document.getElementById("sidebar-targets-badge");

    if (dashTargetTotal) dashTargetTotal.textContent = "₦" + (summary.total_target_savings || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
    if (dashTargetActive) dashTargetActive.textContent = `${summary.active_targets_count || 0} Active`;
    if (dashTargetMatured) dashTargetMatured.textContent = `${summary.matured_targets_count || 0} Ready`;

    if (sidebarTargetsBadge) {
      const activeCount = summary.active_targets_count || 0;
      sidebarTargetsBadge.textContent = activeCount;
      if (activeCount > 0) sidebarTargetsBadge.classList.remove("hidden");
      else sidebarTargetsBadge.classList.add("hidden");
    }

    if (cachedMemberTargets.length === 0) {
      container.innerHTML = `
        <div class="col-span-full py-12 px-6 text-center bg-slate-50/70 rounded-3xl border-2 border-dashed border-slate-200">
          <div class="text-4xl mb-3">🎯</div>
          <h4 class="text-base font-bold text-slate-800">No Target Savings Ledgers Yet</h4>
          <p class="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-5">
            Voluntary target savings empower you to plan ahead for birthdays, festivals (Christmas, Ileya), real estate building, pilgrimages, and tuition. Funds are strictly segregated and 100% withdrawable at maturity.
          </p>
          <button type="button" onclick="openCreateTargetSavingsModal()" class="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-500 hover:to-teal-600 text-white font-bold text-xs shadow-md transition">
            ➕ Create Your First Target Ledger
          </button>
        </div>
      `;
      return;
    }

    let cardsHtml = "";
    cachedMemberTargets.forEach(tgt => {
      const meta = TARGET_CATEGORY_META[tgt.target_type] || TARGET_CATEGORY_META.OTHERS;
      const progress = tgt.progress_percent || 0;
      const curBal = tgt.current_balance || 0;
      const goalAmt = tgt.target_amount || 0;
      const isMatured = tgt.is_matured;
      const isWithdrawn = tgt.status === "WITHDRAWN";

      let statusBadge = "";
      let actionButtons = "";

      if (isWithdrawn) {
        statusBadge = `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-slate-100 text-slate-600 border border-slate-200">✅ Fully Withdrawn</span>`;
        actionButtons = `<div class="text-center py-2 text-xs font-semibold text-slate-400 bg-slate-50 rounded-xl border border-slate-100">🎉 Financial Goal Completed &amp; Paid Out</div>`;
      } else if (isMatured) {
        statusBadge = `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-amber-400 text-slate-950 border border-amber-500 shadow-sm animate-pulse">🎉 Matured &bull; Unlocked</span>`;
        actionButtons = `
          <div class="grid grid-cols-2 gap-2">
            <button type="button" onclick="openDepositTargetSavingsModal(${tgt.id})" class="py-2.5 px-3 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 font-bold text-xs transition">
              ➕ Top Up
            </button>
            <button type="button" onclick="openWithdrawTargetSavingsModal(${tgt.id})" class="py-2.5 px-3 rounded-xl bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white font-black text-xs shadow-md transition flex items-center justify-center gap-1">
              <span>💰 Withdraw</span>
            </button>
          </div>
        `;
      } else {
        statusBadge = `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-100 text-blue-800 border border-blue-200">⏳ Active &bull; ${tgt.days_remaining} Days Left</span>`;
        actionButtons = `
          <div class="grid grid-cols-2 gap-2">
            <button type="button" onclick="openDepositTargetSavingsModal(${tgt.id})" class="py-2.5 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-sm transition">
              ➕ Top Up
            </button>
            <button type="button" disabled class="py-2.5 px-3 rounded-xl bg-slate-100 text-slate-400 font-bold text-xs cursor-not-allowed border border-slate-200" title="Locked until maturity date (${tgt.maturity_date}) to maintain savings discipline">
              🔒 Lock: ${tgt.maturity_date}
            </button>
          </div>
        `;
      }

      cardsHtml += `
        <div class="glass-panel p-5 rounded-3xl border border-slate-200 shadow-sm flex flex-col justify-between hover:shadow-md transition">
          <div>
            <!-- Header Badges -->
            <div class="flex items-center justify-between gap-2 mb-3">
              <span class="px-2.5 py-1 rounded-xl text-[10px] font-extrabold border ${meta.badgeBg} flex items-center gap-1.5 shadow-xs">
                <span>${meta.icon}</span>
                <span>${tgt.target_type_label}</span>
              </span>
              ${statusBadge}
            </div>

            <!-- Title -->
            <h4 class="font-bold text-base text-wmcNavy-950 mb-1 leading-snug">
              ${tgt.title}
            </h4>

            <!-- Balances -->
            <div class="flex items-baseline justify-between mt-3 mb-1">
              <span class="text-xs text-slate-500">Saved Balance:</span>
              <span class="font-mono text-xl font-black text-emerald-950">₦${curBal.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            </div>

            <!-- Target Goal -->
            <div class="flex items-center justify-between text-[11px] text-slate-500 mb-2">
              <span>Goal: ₦${goalAmt.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
              <span class="font-bold text-blue-700">${progress}% Achieved</span>
            </div>

            <!-- Progress Bar -->
            <div class="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden p-0.5 border border-slate-200 mb-4">
              <div class="bg-gradient-to-r ${meta.barColor} h-full rounded-full transition-all duration-500 shadow-xs" style="width: ${progress}%"></div>
            </div>

            <!-- Timeline & Auto-Save -->
            <div class="grid grid-cols-2 gap-2 text-[10px] p-2.5 bg-slate-50/80 rounded-xl border border-slate-200/80 mb-4">
              <div>
                <span class="text-slate-400 block uppercase font-sans">Created On:</span>
                <span class="font-mono font-semibold text-slate-700">${tgt.start_date}</span>
              </div>
              <div class="text-right">
                <span class="text-slate-400 block uppercase font-sans">Maturity Date:</span>
                <span class="font-mono font-bold text-blue-900">${tgt.maturity_date}</span>
              </div>
            </div>
          </div>

          <!-- Bottom Actions -->
          <div class="pt-2 border-t border-slate-100">
            ${actionButtons}
          </div>
        </div>
      `;
    });

    container.innerHTML = cardsHtml;

  } catch (err) {
    console.error("Error loading target savings:", err);
    container.innerHTML = `
      <div class="col-span-full py-8 text-center text-red-500 text-xs">
        Could not load target savings ledgers from backend database.
      </div>
    `;
  }
}

function openDepositTargetSavingsModal(targetId) {
  const target = cachedMemberTargets.find(t => t.id === targetId);
  if (!target) return;

  const modal = document.getElementById("modal-deposit-target-savings");
  if (!modal) return;

  const alertEl = document.getElementById("deposit-target-alert");
  if (alertEl) alertEl.classList.add("hidden");

  document.getElementById("deposit-target-id").value = target.id;
  document.getElementById("deposit-target-title-display").textContent = target.title;
  document.getElementById("deposit-target-balance-display").textContent = "₦" + (target.current_balance || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
  document.getElementById("deposit-target-goal-display").textContent = "₦" + (target.target_amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
  document.getElementById("deposit-target-date-display").textContent = `${target.maturity_date} (${target.days_remaining} days remaining)`;
  document.getElementById("deposit-target-amount").value = "";
  document.getElementById("deposit-target-narration").value = `Top-up for ${target.title}`;

  modal.classList.remove("hidden");
}

function closeDepositTargetSavingsModal() {
  const modal = document.getElementById("modal-deposit-target-savings");
  if (modal) modal.classList.add("hidden");
}

async function handleDepositTargetSavingsSubmit(event) {
  event.preventDefault();
  const alertEl = document.getElementById("deposit-target-alert");
  const submitBtn = document.getElementById("btn-submit-deposit-target");

  const targetId = document.getElementById("deposit-target-id").value;
  const amount = parseFloat(document.getElementById("deposit-target-amount").value || "0");
  const paymentMethod = document.getElementById("deposit-target-method").value;
  const narration = document.getElementById("deposit-target-narration").value.trim();

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Processing Deposit...";
  }

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/target-savings/${targetId}/deposit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        amount: amount,
        payment_method: paymentMethod,
        narration: narration
      })
    });

    const data = await res.json();
    if (res.ok) {
      if (alertEl) {
        alertEl.className = "p-3.5 rounded-xl text-xs mb-4 bg-emerald-50 text-emerald-900 border border-emerald-200";
        alertEl.textContent = `✅ Success: Deposited ₦${amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}! New balance: ₦${data.new_balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
        alertEl.classList.remove("hidden");
      }
      setTimeout(() => {
        closeDepositTargetSavingsModal();
        loadMemberTargetSavings();
        loadAuthenticatedMember();
      }, 1000);
    } else {
      if (alertEl) {
        alertEl.className = "p-3.5 rounded-xl text-xs mb-4 bg-red-50 text-red-900 border border-red-200";
        alertEl.textContent = `⚠️ Error: ${data.detail || "Deposit failed."}`;
        alertEl.classList.remove("hidden");
      }
    }
  } catch (err) {
    if (alertEl) {
      alertEl.className = "p-3.5 rounded-xl text-xs mb-4 bg-red-50 text-red-900 border border-red-200";
      alertEl.textContent = "⚠️ Network error: Could not process deposit.";
      alertEl.classList.remove("hidden");
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Confirm Deposit";
    }
  }
}

function openWithdrawTargetSavingsModal(targetId) {
  const target = cachedMemberTargets.find(t => t.id === targetId);
  if (!target) return;

  const modal = document.getElementById("modal-withdraw-target-savings");
  if (!modal) return;

  const alertEl = document.getElementById("withdraw-target-alert");
  if (alertEl) alertEl.classList.add("hidden");

  document.getElementById("withdraw-target-id").value = target.id;
  document.getElementById("withdraw-target-title-display").textContent = target.title;
  document.getElementById("withdraw-target-balance-display").textContent = "₦" + (target.current_balance || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
  document.getElementById("withdraw-target-date-display").textContent = `Matured on ${target.maturity_date}`;
  document.getElementById("withdraw-target-amount").value = target.current_balance || 0;
  document.getElementById("withdraw-target-amount").max = target.current_balance || 0;

  // Pre-fill member settlement bank from profile
  const bankNameInput = document.getElementById("withdraw-bank-name");
  const bankAccInput = document.getElementById("withdraw-bank-account");
  const bankHolderInput = document.getElementById("withdraw-bank-name-holder");

  if (bankNameInput) bankNameInput.value = (currentUser && currentUser.bank_name) || "Polaris Bank";
  if (bankAccInput) bankAccInput.value = (currentUser && currentUser.bank_account_number) || "";
  if (bankHolderInput) bankHolderInput.value = (currentUser && currentUser.bank_account_name) || (currentUser && currentUser.full_name) || "";

  modal.classList.remove("hidden");
}

function closeWithdrawTargetSavingsModal() {
  const modal = document.getElementById("modal-withdraw-target-savings");
  if (modal) modal.classList.add("hidden");
}

function setWithdrawAllTargetAmount() {
  const targetId = parseInt(document.getElementById("withdraw-target-id").value || "0");
  const target = cachedMemberTargets.find(t => t.id === targetId);
  if (target) {
    document.getElementById("withdraw-target-amount").value = target.current_balance || 0;
  }
}

async function handleWithdrawTargetSavingsSubmit(event) {
  event.preventDefault();
  const alertEl = document.getElementById("withdraw-target-alert");
  const submitBtn = document.getElementById("btn-submit-withdraw-target");

  const targetId = document.getElementById("withdraw-target-id").value;
  const amount = parseFloat(document.getElementById("withdraw-target-amount").value || "0");
  const bankName = document.getElementById("withdraw-bank-name").value.trim();
  const accountNum = document.getElementById("withdraw-bank-account").value.trim();
  const accountName = document.getElementById("withdraw-bank-name-holder").value.trim();

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Processing Bank Payout...";
  }

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/target-savings/${targetId}/withdraw`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        amount: amount,
        bank_name: bankName,
        account_number: accountNum,
        account_name: accountName
      })
    });

    const data = await res.json();
    if (res.ok) {
      if (alertEl) {
        alertEl.className = "p-3.5 rounded-xl text-xs mb-4 bg-emerald-50 text-emerald-900 border border-emerald-200";
        alertEl.textContent = `✅ Success: ${data.message}`;
        alertEl.classList.remove("hidden");
      }
      setTimeout(() => {
        closeWithdrawTargetSavingsModal();
        loadMemberTargetSavings();
        loadAuthenticatedMember();
      }, 1200);
    } else {
      if (alertEl) {
        alertEl.className = "p-3.5 rounded-xl text-xs mb-4 bg-red-50 text-red-900 border border-red-200";
        alertEl.textContent = `⚠️ Error: ${data.detail || "Withdrawal failed."}`;
        alertEl.classList.remove("hidden");
      }
    }
  } catch (err) {
    if (alertEl) {
      alertEl.className = "p-3.5 rounded-xl text-xs mb-4 bg-red-50 text-red-900 border border-red-200";
      alertEl.textContent = "⚠️ Network error: Could not process withdrawal.";
      alertEl.classList.remove("hidden");
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Process Bank Payout →";
    }
  }
}

async function loadAdminTargetSavings() {
  const catGrid = document.getElementById("admin-target-categories-grid");
  const tbody = document.getElementById("admin-target-ledgers-tbody");
  if (!catGrid && !tbody) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/target-savings`);
    if (!res.ok) throw new Error("Could not fetch admin target savings");
    const data = await res.json();

    const totals = data.totals || {};
    const categories = data.by_category || [];
    const ledgers = data.ledgers || [];

    // Render Category Distribution Cards
    if (catGrid) {
      let catsHtml = "";
      categories.forEach(c => {
        const meta = TARGET_CATEGORY_META[c.target_type] || TARGET_CATEGORY_META.OTHERS;
        catsHtml += `
          <div class="p-3 rounded-2xl bg-slate-50 border border-slate-200 text-center">
            <span class="text-xl block mb-1">${meta.icon}</span>
            <span class="font-bold text-slate-800 text-[11px] block truncate">${c.label}</span>
            <span class="font-mono font-black text-emerald-800 text-xs block mt-1">₦${(c.total_balance || 0).toLocaleString(undefined, { minimumFractionDigits: 0 })}</span>
            <span class="text-[10px] text-slate-400 block">${c.ledger_count} Ledgers</span>
          </div>
        `;
      });
      catGrid.innerHTML = catsHtml || `<div class="col-span-full py-4 text-center text-slate-400">No categories found.</div>`;
    }

    // Render All Society Target Ledgers Table
    if (tbody) {
      if (ledgers.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-400">No target savings ledgers found in society registry.</td></tr>`;
        return;
      }

      let rowsHtml = "";
      ledgers.forEach(l => {
        const meta = TARGET_CATEGORY_META[l.target_type] || TARGET_CATEGORY_META.OTHERS;
        let stBadge = "";
        if (l.status === "MATURED") {
          stBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-amber-400 text-slate-950">Matured</span>`;
        } else if (l.status === "WITHDRAWN") {
          stBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-slate-200 text-slate-700">Withdrawn</span>`;
        } else {
          stBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-800">Active</span>`;
        }

        rowsHtml += `
          <tr class="hover:bg-slate-50 transition text-xs">
            <td class="p-3">
              <span class="font-bold text-wmcNavy-950 block">${l.member_name}</span>
              <span class="font-mono text-[10px] text-amber-700 block">${l.member_code}</span>
            </td>
            <td class="p-3">
              <span class="font-bold text-slate-800 flex items-center gap-1">
                <span>${meta.icon}</span>
                <span>${l.title}</span>
              </span>
              <span class="text-[10px] text-slate-400 block">${l.target_type_label}</span>
            </td>
            <td class="p-3 font-mono font-semibold text-slate-700">
              ₦${(l.target_amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </td>
            <td class="p-3 font-mono font-bold text-emerald-800">
              ₦${(l.current_balance || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </td>
            <td class="p-3">
              <div class="flex items-center gap-1.5">
                <div class="w-16 bg-slate-100 h-2 rounded-full overflow-hidden border border-slate-200">
                  <div class="bg-gradient-to-r ${meta.barColor} h-full rounded-full" style="width: ${l.progress_percent}%"></div>
                </div>
                <span class="font-mono text-[10px] font-bold text-slate-600">${l.progress_percent}%</span>
              </div>
            </td>
            <td class="p-3 font-mono text-[11px] text-blue-900">
              ${l.maturity_date}
              <span class="text-[9px] text-slate-400 block">${l.days_remaining}d left</span>
            </td>
            <td class="p-3">
              ${stBadge}
            </td>
          </tr>
        `;
      });
      tbody.innerHTML = rowsHtml;
    }
  } catch (err) {
    console.error("Error loading admin target savings:", err);
    if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-red-500">Failed to load target savings registry.</td></tr>`;
  }
}

// =============================================================================
// PAYSTACK PAYMENT GATEWAY & DEDICATED VIRTUAL ACCOUNTS (DVA)
// =============================================================================

async function loadMemberDedicatedAccount(memberId) {
  if (!memberId) {
    if (currentUser && currentUser.id) memberId = currentUser.id;
    else return;
  }
  const container = document.getElementById("dva-container");
  if (currentUser && currentUser.is_admin_only) {
    if (container) container.classList.add("hidden");
    return;
  } else {
    if (container) container.classList.remove("hidden");
  }

  const lockedView = document.getElementById("dva-locked-view");
  const unlockedView = document.getElementById("dva-unlocked-view");
  const numEl = document.getElementById("dva-account-number");
  const bankEl = document.getElementById("dva-bank-name");
  const nameEl = document.getElementById("dva-account-name");
  const meterScore = document.getElementById("dva-compulsory-score");
  const meterBar = document.getElementById("dva-compulsory-progress-bar");
  const checklistEl = document.getElementById("dva-compulsory-checklist");

  try {
    const res = await fetch(`${API_BASE_URL}/members/${memberId}/dedicated-account`);
    if (res.ok) {
      const json = await res.json();
      if (json.is_locked) {
        if (unlockedView) unlockedView.classList.add("hidden");
        if (lockedView) lockedView.classList.remove("hidden");
        const pct = json.kyc_completion_percent ?? (currentUser ? currentUser.kyc_completion_percent : 0);
        if (meterScore) meterScore.textContent = `${pct}% Overall`;
        if (meterBar) meterBar.style.width = `${pct}%`;

        // Load detailed compulsory KYC checklist
        try {
          const kycRes = await fetch(`${API_BASE_URL}/members/${memberId}/kyc-compulsory-status`);
          if (kycRes.ok) {
            const kycData = await kycRes.json();
            const chk = kycData.compulsory_fields_status || kycData.checklist || {};
            const fieldLabels = {
              first_name: "Legal First Name",
              last_name: "Legal Surname",
              phone: "Verified Phone Number",
              email: "Official Email Address",
              residential_address: "Residential Address",
              identification_number: "National Identity No. (NIN)"
            };
            if (checklistEl) {
              checklistEl.innerHTML = Object.keys(fieldLabels).map(k => {
                const isDone = Boolean(chk[k]);
                return `
                  <div class="flex items-center justify-between py-0.5">
                    <span class="${isDone ? 'text-slate-300' : 'text-amber-200 font-semibold'}">${fieldLabels[k]}</span>
                    <span class="${isDone ? 'text-emerald-400 font-bold' : 'text-amber-400 font-bold'}">${isDone ? '✅ Complete' : '⚠️ Pending'}</span>
                  </div>
                `;
              }).join("");
            }
          }
        } catch (e) {
          console.warn("Could not load kyc checklist:", e);
        }
      } else {
        if (lockedView) lockedView.classList.add("hidden");
        if (unlockedView) unlockedView.classList.remove("hidden");
        const dva = json.data || {};
        if (numEl) numEl.textContent = dva.account_number || "9926000001";
        if (bankEl) bankEl.textContent = dva.bank_name || "Polaris Bank (Direct DVA)";
        if (nameEl) nameEl.textContent = dva.account_name || `Wealthbridge / ${currentUser ? currentUser.full_name : 'Cooperator'}`;
      }
    } else {
      if (numEl) numEl.textContent = "Unavailable";
    }
  } catch (err) {
    console.warn("Could not load dedicated account:", err);
    if (numEl) numEl.textContent = "9926000001";
  }
}

function copyDvaAccountNumber() {
  const numEl = document.getElementById("dva-account-number");
  if (!numEl) return;
  const acc = numEl.textContent.trim();
  if (!acc || acc === "Loading..." || acc === "Unavailable") return;

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(acc).then(() => {
      const iconEl = document.getElementById("dva-copy-icon");
      const textEl = document.getElementById("dva-copy-text");
      if (iconEl) iconEl.textContent = "✓";
      if (textEl) textEl.textContent = "Copied!";
      setTimeout(() => {
        if (iconEl) iconEl.textContent = "📋";
        if (textEl) textEl.textContent = "Copy";
      }, 2500);
    }).catch(() => {
      prompt("Copy your Dedicated Virtual NUBAN Account Number:", acc);
    });
  } else {
    prompt("Copy your Dedicated Virtual NUBAN Account Number:", acc);
  }
}

function openPaystackOnlinePaymentModal() {
  const modal = document.getElementById("modal-paystack-payment");
  const statusEl = document.getElementById("paystack-pay-status");
  if (statusEl) statusEl.classList.add("hidden");
  if (modal) modal.classList.remove("hidden");
}

function closePaystackOnlinePaymentModal() {
  const modal = document.getElementById("modal-paystack-payment");
  if (modal) modal.classList.add("hidden");
}

async function handlePaystackPaymentSubmit(event) {
  event.preventDefault();
  const btn = document.getElementById("btn-paystack-submit");
  const statusEl = document.getElementById("paystack-pay-status");
  const purpose = document.getElementById("paystack-pay-purpose").value;
  const amount = parseFloat(document.getElementById("paystack-pay-amount").value);

  if (!amount || amount < 1000) {
    if (statusEl) {
      statusEl.className = "p-3 rounded-xl text-xs font-semibold bg-red-50 text-red-800 border border-red-200 block";
      statusEl.textContent = "⚠️ Minimum online payment amount is ₦1,000.";
      statusEl.classList.remove("hidden");
    }
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="animate-spin inline-block mr-2">↻</span> Connecting to Paystack...`;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/paystack/initialize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        amount: amount,
        purpose: purpose,
        callback_url: window.location.href
      })
    });

    const data = await res.json();
    if (res.ok && data.status === "success" && data.data && data.data.authorization_url) {
      if (statusEl) {
        statusEl.className = "p-3 rounded-xl text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 block";
        statusEl.textContent = "✓ Checkout session ready. Redirecting to Paystack secure checkout...";
        statusEl.classList.remove("hidden");
      }
      setTimeout(() => {
        window.location.href = data.data.authorization_url;
      }, 1000);
    } else {
      if (statusEl) {
        statusEl.className = "p-3 rounded-xl text-xs font-semibold bg-red-50 text-red-800 border border-red-200 block";
        statusEl.textContent = `⚠️ Error: ${data.detail || (data.message || "Could not initialize Paystack payment session.")}`;
        statusEl.classList.remove("hidden");
      }
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<span>🔒</span><span>Proceed to Paystack &rarr;</span>`;
      }
    }
  } catch (err) {
    if (statusEl) {
      statusEl.className = "p-3 rounded-xl text-xs font-semibold bg-red-50 text-red-800 border border-red-200 block";
      statusEl.textContent = "⚠️ Network error connecting to payment gateway.";
      statusEl.classList.remove("hidden");
    }
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>🔒</span><span>Proceed to Paystack &rarr;</span>`;
    }
  }
}

// =============================================================================
// 17. OFFICIAL MONTHLY PAYMENT ADVICE & WATERFALL DISTRIBUTION
// =============================================================================
let cachedCurrentAdvice = null;

function formatAdviceBillingPeriod(periodStr) {
  if (!periodStr) return "Current Month";
  const parts = periodStr.split("-");
  if (parts.length < 2) return periodStr;
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  const mIndex = parseInt(parts[1], 10) - 1;
  const monthName = (mIndex >= 0 && mIndex < 12) ? monthNames[mIndex] : parts[1];
  return `${monthName} ${parts[0]}`;
}

function formatNaira(val) {
  const num = parseFloat(val) || 0;
  return "₦" + num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatAdviceNaira(val) {
  return formatNaira(val);
}


async function loadMemberCurrentPaymentAdvice(memberId) {
  const targetId = memberId || (currentUser ? currentUser.id : null);
  if (!targetId) return;

  try {
    const res = await fetch(`${API_BASE_URL}/members/${targetId}/payment-advice/current`);
    if (!res.ok) {
      console.warn("Could not retrieve current payment advice.");
      return;
    }
    const data = await res.json();
    cachedCurrentAdvice = data.data || data;
    renderMemberPaymentAdvice(cachedCurrentAdvice);
  } catch (err) {
    console.error("Error loading monthly payment advice:", err);
  }
}

function renderMemberPaymentAdvice(adv) {
  if (!adv) return;

  // 1. Badges & Header
  const periodEl = document.getElementById("advice-period-badge");
  if (periodEl) {
    periodEl.textContent = `Billing Period: ${formatAdviceBillingPeriod(adv.billing_period)}`;
  }

  const refEl = document.getElementById("advice-ref-code");
  if (refEl) {
    refEl.textContent = adv.advice_reference || "WMC-ADV-CURRENT";
  }

  const statusBadge = document.getElementById("advice-status-badge");
  if (statusBadge) {
    const st = (adv.status || "DUE").toUpperCase();
    if (st === "FULLY_SETTLED" || st === "SETTLED") {
      statusBadge.textContent = "FULFILLED ✓";
      statusBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-200";
    } else if (st === "PARTIALLY_PAID" || st === "PARTIAL") {
      statusBadge.textContent = "PARTIAL";
      statusBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-blue-100 text-blue-800 border border-blue-200";
    } else if (st === "OVERDUE") {
      statusBadge.textContent = "OVERDUE";
      statusBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-100 text-rose-800 border border-rose-200";
    } else {
      statusBadge.textContent = "DUE (BY 28TH)";
      statusBadge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-100 text-amber-800 border border-amber-200";
    }
  }

  // 2. Metric Boxes
  const exp = adv.totals ? adv.totals.total_expected : 0;
  const paid = adv.totals ? adv.totals.total_paid : 0;
  const bal = adv.totals ? adv.totals.outstanding_balance : 0;
  const pct = adv.progress_percent !== undefined ? adv.progress_percent : 0;

  const expEl = document.getElementById("stat-advice-expected");
  if (expEl) expEl.textContent = formatAdviceNaira(exp);

  const paidEl = document.getElementById("stat-advice-paid");
  if (paidEl) paidEl.textContent = formatAdviceNaira(paid);

  const paidSub = document.getElementById("stat-advice-paid-sub");
  if (paidSub) {
    paidSub.textContent = paid > exp ? "Includes surplus credited to savings" : "Settled towards obligations";
  }

  const outEl = document.getElementById("stat-advice-outstanding");
  if (outEl) outEl.textContent = formatAdviceNaira(bal);

  // Mirror values to Dashboard Quick Card
  const dashExp = document.getElementById("dash-stat-advice-expected");
  const dashPaid = document.getElementById("dash-stat-advice-paid");
  const dashOut = document.getElementById("dash-stat-advice-outstanding");
  const sidebarDuesBadge = document.getElementById("sidebar-dues-badge");

  if (dashExp) dashExp.textContent = formatAdviceNaira(exp);
  if (dashPaid) dashPaid.textContent = formatAdviceNaira(paid);
  if (dashOut) dashOut.textContent = formatAdviceNaira(bal);

  if (sidebarDuesBadge) {
    if (bal > 0) {
      sidebarDuesBadge.textContent = "DUE";
      sidebarDuesBadge.classList.remove("hidden");
    } else {
      sidebarDuesBadge.classList.add("hidden");
    }
  }

  // 3. Progress Bar
  const progText = document.getElementById("stat-advice-progress-text");
  if (progText) progText.textContent = `${pct}% Settled`;

  const progBar = document.getElementById("stat-advice-progress-bar");
  if (progBar) progBar.style.width = `${Math.min(100, Math.max(0, pct))}%`;

  // 4. Pay Button
  const payBtn = document.getElementById("btn-pay-advice-outstanding");
  const payBtnText = document.getElementById("btn-pay-advice-text");
  if (payBtn && payBtnText) {
    if (bal <= 0) {
      payBtn.classList.remove("cursor-not-allowed", "opacity-60");
      payBtnText.textContent = "Make Payment (Fulfilled ✓)";
    } else {
      payBtn.classList.remove("opacity-60", "cursor-not-allowed");
      payBtnText.textContent = `Pay Outstanding (${formatAdviceNaira(bal)})`;
    }
  }

  // 5. Itemized Waterfall Table
  const tbody = document.getElementById("advice-breakdown-tbody");
  if (tbody && adv.breakdown) {
    const hasReg = adv.breakdown.registration_fee && (adv.breakdown.registration_fee.expected > 0 || adv.breakdown.registration_fee.paid > 0);
    const items = [
      {
        priority: "P1",
        label: "Disciplinary Fines",
        cat: "Statutory Compliance",
        expected: adv.breakdown.fines ? adv.breakdown.fines.expected : 0,
        paid: adv.breakdown.fines ? adv.breakdown.fines.paid : 0,
        remaining: adv.breakdown.fines ? adv.breakdown.fines.remaining : 0
      }
    ];

    let pIdx = 2;
    if (hasReg) {
      items.push({
        priority: `P${pIdx}`,
        label: "Entrance / Registration Fee",
        cat: "Statutory Onboarding (Article 7)",
        expected: adv.breakdown.registration_fee.expected,
        paid: adv.breakdown.registration_fee.paid,
        remaining: adv.breakdown.registration_fee.remaining
      });
      pIdx++;
    }

    items.push(
      {
        priority: `P${pIdx}`,
        label: "Active Loan Repayment",
        cat: "Credit Facilities (Amortization)",
        expected: adv.breakdown.loan_repayment ? adv.breakdown.loan_repayment.expected : 0,
        paid: adv.breakdown.loan_repayment ? adv.breakdown.loan_repayment.paid : 0,
        remaining: adv.breakdown.loan_repayment ? adv.breakdown.loan_repayment.remaining : 0
      },
      {
        priority: `P${pIdx + 1}`,
        label: "Welfare Solidarity Pool",
        cat: "Mandatory Welfare (Article 13)",
        expected: adv.breakdown.welfare ? adv.breakdown.welfare.expected : 0,
        paid: adv.breakdown.welfare ? adv.breakdown.welfare.paid : 0,
        remaining: adv.breakdown.welfare ? adv.breakdown.welfare.remaining : 0
      },
      {
        priority: `P${pIdx + 2}`,
        label: "Share Capital Equity",
        cat: "Cooperative Equity (Article 12)",
        expected: adv.breakdown.share_capital ? adv.breakdown.share_capital.expected : 0,
        paid: adv.breakdown.share_capital ? adv.breakdown.share_capital.paid : 0,
        remaining: adv.breakdown.share_capital ? adv.breakdown.share_capital.remaining : 0
      },
      {
        priority: `P${pIdx + 3}`,
        label: "Regular Co-op Savings",
        cat: "Liquid Collateral Savings",
        expected: adv.breakdown.regular_savings ? adv.breakdown.regular_savings.expected : 0,
        paid: adv.breakdown.regular_savings ? adv.breakdown.regular_savings.paid : 0,
        remaining: adv.breakdown.regular_savings ? adv.breakdown.regular_savings.remaining : 0
      },
      {
        priority: `P${pIdx + 4}`,
        label: "Target Savings Commitments",
        cat: "Voluntary Project Targets",
        expected: adv.breakdown.target_savings ? adv.breakdown.target_savings.expected : 0,
        paid: adv.breakdown.target_savings ? adv.breakdown.target_savings.paid : 0,
        remaining: adv.breakdown.target_savings ? adv.breakdown.target_savings.remaining : 0
      }
    );

    if (adv.breakdown.arrears && adv.breakdown.arrears.expected > 0) {
      items.push({
        priority: "Arrears",
        label: "Rollover Prior Arrears",
        cat: "Prior Month Overdue Balance",
        expected: adv.breakdown.arrears.expected,
        paid: 0,
        remaining: adv.breakdown.arrears.expected
      });
    }

    let rowsHtml = "";
    items.forEach(it => {
      let badgeHtml = "";
      if (it.expected === 0 && it.paid === 0) {
        badgeHtml = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-500">None</span>`;
      } else if (it.remaining <= 0) {
        badgeHtml = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">Settled ✓</span>`;
      } else if (it.paid > 0) {
        badgeHtml = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">Partially Paid</span>`;
      } else {
        badgeHtml = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">Due</span>`;
      }

      rowsHtml += `
        <tr class="hover:bg-slate-50 transition border-b border-slate-100">
          <td class="p-3 font-semibold text-slate-800 flex items-center gap-2">
            <span class="w-6 h-6 rounded-md bg-slate-100 text-slate-600 font-mono font-bold text-[10px] flex items-center justify-center shrink-0 border border-slate-200">
              ${it.priority}
            </span>
            <span>${it.label}</span>
          </td>
          <td class="p-3 text-slate-500 font-medium">${it.cat}</td>
          <td class="p-3 text-right font-mono font-bold text-slate-800">${formatAdviceNaira(it.expected)}</td>
          <td class="p-3 text-right font-mono font-bold text-emerald-600">${formatAdviceNaira(it.paid)}</td>
          <td class="p-3 text-right font-mono font-bold ${it.remaining > 0 ? 'text-amber-700' : 'text-slate-400'}">${formatAdviceNaira(it.remaining)}</td>
          <td class="p-3 text-center">${badgeHtml}</td>
        </tr>
      `;
    });

    tbody.innerHTML = rowsHtml;
  }
}

async function payAdviceOutstandingBalance() {
  if (!cachedCurrentAdvice && currentUser && !currentUser.is_admin_only) {
    await loadMemberCurrentPaymentAdvice(currentUser.id);
  }

  openPaystackOnlinePaymentModal();
  const purposeSelect = document.getElementById("paystack-pay-purpose");
  if (purposeSelect) {
    purposeSelect.value = "MONTHLY_PAYMENT_ADVICE";
  }

  const bal = (cachedCurrentAdvice && cachedCurrentAdvice.totals) ? cachedCurrentAdvice.totals.outstanding_balance : 0;
  const amountInput = document.getElementById("paystack-pay-amount");
  if (amountInput) {
    amountInput.value = bal > 0 ? Math.max(1000, Math.round(bal)) : 10000;
  }
}

async function openPaymentAdviceSlipModal() {
  if (!cachedCurrentAdvice && currentUser && !currentUser.is_admin_only) {
    await loadMemberCurrentPaymentAdvice(currentUser.id);
  }

  const adv = cachedCurrentAdvice;
  if (!adv) {
    alert("Please wait a moment while your payment advice is compiling from the server.");
    return;
  }

  const memberName = (currentUser && currentUser.full_name) || "Cooperator";
  const memberCode = (currentUser && currentUser.member_code) || "";

  // Set Cooperator & Advice details
  const elName = document.getElementById("slip-member-name");
  if (elName) elName.textContent = memberName;

  const elCode = document.getElementById("slip-member-code");
  if (elCode) elCode.textContent = memberCode;

  const elRef = document.getElementById("slip-advice-ref");
  if (elRef) elRef.textContent = adv.advice_reference;

  const elTier = document.getElementById("slip-tier-badge");
  if (elTier) elTier.textContent = `${adv.tier || "STANDARD"} TIER`;

  const elPeriod = document.getElementById("slip-period");
  if (elPeriod) elPeriod.textContent = formatAdviceBillingPeriod(adv.billing_period);

  const elIssue = document.getElementById("slip-issue-date");
  if (elIssue) elIssue.textContent = `Issued: ${adv.issue_date}`;

  const elDue = document.getElementById("slip-due-date");
  if (elDue) elDue.textContent = adv.due_date;

  // Build Breakdown Table
  const slipTbody = document.getElementById("slip-table-body");
  if (slipTbody && adv.breakdown) {
    const slipItems = [
      { name: "Disciplinary Fines", key: "fines" },
      { name: "Entrance / Registration Fee (Article 7)", key: "registration_fee" },
      { name: "Active Loan Repayment", key: "loan_repayment" },
      { name: "Welfare Solidarity Pool (Art. 13)", key: "welfare" },
      { name: "Share Capital Subscription (Art. 12)", key: "share_capital" },
      { name: "Regular Monthly Savings (Liquid Collateral)", key: "regular_savings" },
      { name: "Voluntary Target Savings Allocations", key: "target_savings" }
    ];

    let rows = "";
    slipItems.forEach(item => {
      const b = adv.breakdown[item.key];
      if (b && (b.expected > 0 || b.paid > 0)) {
        rows += `
          <tr class="border-b border-slate-100">
            <td class="p-3 font-semibold text-slate-800 font-sans">${item.name}</td>
            <td class="p-3 text-right font-bold">${formatAdviceNaira(b.expected)}</td>
            <td class="p-3 text-right font-bold text-emerald-600">${formatAdviceNaira(b.paid)}</td>
            <td class="p-3 text-right font-bold ${b.remaining > 0 ? 'text-amber-700' : 'text-slate-400'}">${formatAdviceNaira(b.remaining)}</td>
          </tr>
        `;
      }
    });

    if (adv.breakdown.arrears && adv.breakdown.arrears.expected > 0) {
      rows += `
        <tr class="border-b border-slate-100">
          <td class="p-3 font-semibold text-rose-700 font-sans">Rollover Prior Arrears</td>
          <td class="p-3 text-right font-bold">${formatAdviceNaira(adv.breakdown.arrears.expected)}</td>
          <td class="p-3 text-right font-bold text-emerald-600">₦0.00</td>
          <td class="p-3 text-right font-bold text-rose-700">${formatAdviceNaira(adv.breakdown.arrears.expected)}</td>
        </tr>
      `;
    }

    if (!rows) {
      rows = `
        <tr>
          <td colspan="4" class="p-4 text-center text-slate-400 italic">No active billing obligations recorded for this cycle.</td>
        </tr>
      `;
    }
    slipTbody.innerHTML = rows;
  }

  // Totals
  const totalExp = adv.totals ? adv.totals.total_expected : 0;
  const totalPaid = adv.totals ? adv.totals.total_paid : 0;
  const totalBal = adv.totals ? adv.totals.outstanding_balance : 0;

  const elTotExp = document.getElementById("slip-total-expected");
  if (elTotExp) elTotExp.textContent = formatAdviceNaira(totalExp);

  const elTotPaid = document.getElementById("slip-total-paid");
  if (elTotPaid) elTotPaid.textContent = formatAdviceNaira(totalPaid);

  const elTotBal = document.getElementById("slip-total-outstanding");
  if (elTotBal) elTotBal.textContent = formatAdviceNaira(totalBal);

  // Bank & Dedicated Account
  const dvaAcc = (typeof cachedDedicatedAccount !== "undefined" && cachedDedicatedAccount && cachedDedicatedAccount.account_number)
    ? cachedDedicatedAccount.account_number
    : ((currentUser && currentUser.paystack_dva_account_number) || "Generating...");
  const dvaBank = (typeof cachedDedicatedAccount !== "undefined" && cachedDedicatedAccount && cachedDedicatedAccount.bank_name)
    ? cachedDedicatedAccount.bank_name
    : "Wema Bank (Paystack DVA)";

  const elDvaAcc = document.getElementById("slip-dva-account");
  if (elDvaAcc) elDvaAcc.textContent = dvaAcc;

  const elDvaBank = document.getElementById("slip-dva-bank");
  if (elDvaBank) elDvaBank.textContent = dvaBank;

  const elGenDate = document.getElementById("slip-gen-date");
  if (elGenDate) elGenDate.textContent = new Date().toISOString().split("T")[0];

  // Open modal
  const modal = document.getElementById("modal-payment-advice-slip");
  if (modal) modal.classList.remove("hidden");
}

function closePaymentAdviceSlipModal() {
  const modal = document.getElementById("modal-payment-advice-slip");
  if (modal) modal.classList.add("hidden");
}

function printAdviceSlip() {
  window.print();
}

async function downloadCurrentAdvicePDF(targetMemberId) {
  const memberId = targetMemberId || (currentUser ? currentUser.id : null);
  if (!memberId) {
    alert("Please sign in as a cooperator to download your payment advice PDF.");
    return;
  }
  const token = localStorage.getItem("wmc_token") || (currentUser ? currentUser.token : "");

  const btn = document.getElementById("btn-download-pdf-slip");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>↻</span><span>Generating PDF...</span>`;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/members/${memberId}/payment-advice/current/pdf`);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      alert(`⚠️ Could not generate PDF: ${errData.detail || "Server error"}`);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<span>📥</span><span>PDF File</span>`;
      }
      return;
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = url;
    const refCode = (cachedCurrentAdvice && cachedCurrentAdvice.advice_reference) || `WMC-ADV-${memberId}`;
    a.download = `Wealthbridge_Payment_Advice_${refCode}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>📥</span><span>PDF File</span>`;
    }
  } catch (err) {
    console.error("Error downloading advice PDF:", err);
    // Fallback: direct window open with token query parameter
    const refCode = (cachedCurrentAdvice && cachedCurrentAdvice.advice_reference) || `WMC-ADV-${memberId}`;
    window.open(`${API_BASE_URL}/members/${memberId}/payment-advice/current/pdf?token=${encodeURIComponent(token)}`, "_blank");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>📥</span><span>PDF File</span>`;
    }
  }
}

// =============================================================================
// COOPERATIVE STATEMENTS & REPORTS CENTER LOGIC (CAP C15 COMPLIANT)
// =============================================================================

let cachedReportYears = [];
let currentReportData = null;

async function initMemberReportsCenter() {
  const memberId = currentUser ? currentUser.id : null;
  if (!memberId) return;

  const nameEl = document.getElementById("statement-member-name");
  const codeEl = document.getElementById("statement-member-code");
  const tierEl = document.getElementById("statement-member-tier");
  const dvaEl = document.getElementById("statement-member-dva");
  const statusEl = document.getElementById("statement-member-status");
  const admEl = document.getElementById("statement-member-admission");

  if (nameEl && currentUser.full_name) nameEl.textContent = currentUser.full_name;
  if (codeEl && currentUser.member_code) codeEl.textContent = currentUser.member_code;
  if (tierEl && currentUser.contribution_tier) tierEl.textContent = `${currentUser.contribution_tier} (${formatNaira(currentUser.monthly_obligation || 10000)}/mo)`;
  if (dvaEl && cachedDvaInfo && cachedDvaInfo.account_number) {
    dvaEl.textContent = `${cachedDvaInfo.account_number} (${cachedDvaInfo.bank_name || 'Paystack / Wema'})`;
  }
  if (statusEl && currentUser.membership_status) statusEl.textContent = `${currentUser.membership_status} • BENEFITS QUALIFIED`;
  if (admEl && currentUser.admission_date) admEl.textContent = currentUser.admission_date;

  try {
    const res = await fetch(`${API_BASE_URL}/members/${memberId}/reports/years`);
    if (res.ok) {
      const data = await res.json();
      cachedReportYears = data.data || [new Date().getFullYear()];
      populateReportYearsDropdown(cachedReportYears);
    }
  } catch (err) {
    console.error("Error fetching report years:", err);
    populateReportYearsDropdown([new Date().getFullYear()]);
  }

  await generateCurrentReport();
}

function populateReportYearsDropdown(years) {
  const sel = document.getElementById("report-select-year");
  if (!sel) return;
  const currentSelected = sel.value;
  sel.innerHTML = "";

  years.forEach(yr => {
    const opt = document.createElement("option");
    opt.value = yr;
    opt.textContent = `${yr} (Financial Year)`;
    sel.appendChild(opt);
  });

  const allOpt = document.createElement("option");
  allOpt.value = "ALL";
  allOpt.textContent = "All Time (Cumulative)";
  sel.appendChild(allOpt);

  if (currentSelected && years.includes(parseInt(currentSelected))) {
    sel.value = currentSelected;
  } else if (years.length > 0) {
    sel.value = years[0];
  }
}

function handleReportTypeChange() {
  const typeSel = document.getElementById("report-select-type");
  const yrContainer = document.getElementById("report-year-container");
  if (!typeSel) return;

  const val = typeSel.value;
  if (yrContainer) {
    if (val === "LOANS_STATEMENT" || val === "PAYMENT_ADVICE") {
      yrContainer.style.opacity = "0.5";
      yrContainer.style.pointerEvents = "none";
    } else {
      yrContainer.style.opacity = "1";
      yrContainer.style.pointerEvents = "auto";
    }
  }
  generateCurrentReport();
}

async function generateCurrentReport() {
  const memberId = currentUser ? currentUser.id : null;
  if (!memberId) return;

  const typeSel = document.getElementById("report-select-type");
  const yearSel = document.getElementById("report-select-year");
  const reportType = typeSel ? typeSel.value : "PASSBOOK_LEDGER";
  const yearVal = yearSel ? yearSel.value : "2026";
  const yearParam = (yearVal === "ALL" || !yearVal) ? "" : `?year=${yearVal}`;

  const bannerEl = document.getElementById("statement-banner");
  const periodLbl = document.getElementById("statement-period-label");
  const genAtLbl = document.getElementById("statement-generated-at");
  const kpiGrid = document.getElementById("statement-kpi-grid");
  const thead = document.getElementById("statement-table-head");
  const tbody = document.getElementById("statement-table-body");
  const tfoot = document.getElementById("statement-table-foot");

  if (genAtLbl) genAtLbl.textContent = new Date().toLocaleString();
  if (tbody) {
    tbody.innerHTML = `<tr><td colspan="6" class="p-8 text-center text-slate-400">Loading ${reportType.replace(/_/g, " ").toLowerCase()} statement...</td></tr>`;
  }

  try {
    if (reportType === "PASSBOOK_LEDGER") {
      const res = await fetch(`${API_BASE_URL}/members/${memberId}/reports/ledger${yearParam}`);
      if (!res.ok) throw new Error("Failed to load passbook ledger data.");
      const json = await res.json();
      currentReportData = json.data;
      renderPassbookLedgerView(currentReportData, bannerEl, periodLbl, kpiGrid, thead, tbody, tfoot);
    } else if (reportType === "ALL_CREDITS") {
      const res = await fetch(`${API_BASE_URL}/members/${memberId}/reports/credits${yearParam}`);
      if (!res.ok) throw new Error("Failed to load credits statement data.");
      const json = await res.json();
      currentReportData = json.data;
      renderAllCreditsView(currentReportData, bannerEl, periodLbl, kpiGrid, thead, tbody, tfoot);
    } else if (reportType === "ALL_DEBITS") {
      const res = await fetch(`${API_BASE_URL}/members/${memberId}/reports/debits${yearParam}`);
      if (!res.ok) throw new Error("Failed to load debits statement data.");
      const json = await res.json();
      currentReportData = json.data;
      renderAllDebitsView(currentReportData, bannerEl, periodLbl, kpiGrid, thead, tbody, tfoot);
    } else if (reportType === "PAYMENT_ADVICE") {
      const res = await fetch(`${API_BASE_URL}/members/${memberId}/payment-advices`);
      if (!res.ok) throw new Error("Failed to load payment advices history.");
      const json = await res.json();
      currentReportData = json.data;
      renderPaymentAdviceHistoryView(currentReportData, bannerEl, periodLbl, kpiGrid, thead, tbody, tfoot);
    } else if (reportType === "LOANS_STATEMENT") {
      const res = await fetch(`${API_BASE_URL}/members/${memberId}/reports/loans`);
      if (!res.ok) throw new Error("Failed to load loan facilities data.");
      const json = await res.json();
      currentReportData = json.data;
      renderLoansStatementView(currentReportData, bannerEl, periodLbl, kpiGrid, thead, tbody, tfoot);
    }
  } catch (err) {
    console.error("Error generating report:", err);
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="6" class="p-8 text-center text-rose-500 font-semibold">⚠️ Failed to load statement: ${err.message}</td></tr>`;
    }
  }
}

function renderPassbookLedgerView(data, bannerEl, periodLbl, kpiGrid, thead, tbody, tfoot) {
  if (bannerEl) bannerEl.textContent = `STATUTORY ANNUAL PASSBOOK LEDGER STATEMENT • ${data.period_label.toUpperCase()}`;
  if (periodLbl) periodLbl.textContent = data.period_label;

  const op = data.opening_balances || {};
  const cl = data.closing_balances || {};
  const mov = data.period_movements || {};

  if (kpiGrid) {
    kpiGrid.className = "grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs";
    kpiGrid.innerHTML = `
      <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
        <span class="text-[10px] uppercase font-bold text-slate-500 block">Opening Net Equity</span>
        <h4 class="text-base font-black text-slate-800 mt-1">${formatNaira(op.total_equity || 0)}</h4>
        <span class="text-[10px] text-slate-400 block mt-0.5">Savings: ${formatNaira(op.regular_savings || 0)}</span>
      </div>
      <div class="bg-emerald-50/70 p-3 rounded-xl border border-emerald-200">
        <span class="text-[10px] uppercase font-bold text-emerald-800 block">Total Inward Credits</span>
        <h4 class="text-base font-black text-emerald-700 mt-1">${formatNaira(mov.total_credits || 0)}</h4>
        <span class="text-[10px] text-emerald-600 block mt-0.5">Savings: ${formatNaira(mov.credits_savings || 0)}</span>
      </div>
      <div class="bg-rose-50/70 p-3 rounded-xl border border-rose-200">
        <span class="text-[10px] uppercase font-bold text-rose-800 block">Total Outward Debits</span>
        <h4 class="text-base font-black text-rose-700 mt-1">${formatNaira(mov.total_debits || 0)}</h4>
        <span class="text-[10px] text-rose-600 block mt-0.5">Payouts: ${formatNaira(mov.debits_savings || 0)}</span>
      </div>
      <div class="bg-indigo-50/70 p-3 rounded-xl border border-indigo-200">
        <span class="text-[10px] uppercase font-bold text-indigo-900 block">Closing Net Equity</span>
        <h4 class="text-base font-black text-indigo-950 mt-1">${formatNaira(cl.total_equity || 0)}</h4>
        <span class="text-[10px] text-indigo-700 block mt-0.5">Shares: ${formatNaira(cl.share_capital || 0)} (${cl.share_units || 0} Units)</span>
      </div>
      <div class="bg-teal-50/70 p-3 rounded-xl border border-teal-200">
        <span class="text-[10px] uppercase font-bold text-teal-800 block">2× Borrowing Limit</span>
        <h4 class="text-base font-black text-teal-700 mt-1">${formatNaira(cl.ordinary_loan_capacity_2x || 0)}</h4>
        <span class="text-[10px] text-teal-600 block mt-0.5">0.0% Compounding Interest</span>
      </div>
    `;
  }

  if (thead) {
    thead.innerHTML = `
      <tr>
        <th class="p-3">Date / Ref</th>
        <th class="p-3">Ledger Category</th>
        <th class="p-3">Narration &amp; Channel</th>
        <th class="p-3 text-right">Inward (CR)</th>
        <th class="p-3 text-right">Outward (DR)</th>
        <th class="p-3 text-right">Running Net Equity</th>
      </tr>
    `;
  }

  const entries = data.entries || [];
  if (tbody) {
    if (entries.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-400">No transactions recorded during this financial calendar period.</td></tr>`;
    } else {
      tbody.innerHTML = entries.map(e => {
        const isCredit = e.transaction_type === "CREDIT";
        const crStr = isCredit ? `<span class="font-bold text-emerald-700">+${formatNaira(e.amount)}</span>` : `<span class="text-slate-300">-</span>`;
        const drStr = !isCredit ? `<span class="font-bold text-rose-700">-${formatNaira(e.amount)}</span>` : `<span class="text-slate-300">-</span>`;
        const dtStr = (e.transaction_date || "").slice(0, 16);
        const catStr = (e.ledger_category || "").replace(/_/g, " ");

        return `
          <tr class="hover:bg-slate-50 transition">
            <td class="p-3">
              <div class="font-mono font-bold text-slate-800 text-[11px]">${dtStr}</div>
              <div class="font-mono text-[10px] text-slate-400">${e.transaction_ref}</div>
            </td>
            <td class="p-3">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-700">
                ${catStr}
              </span>
            </td>
            <td class="p-3 text-slate-600 text-[11px]">
              <div>${e.narration || e.channel_reference || '-'}</div>
              <div class="text-[10px] text-slate-400">${(e.payment_method || '').replace(/_/g, ' ')}</div>
            </td>
            <td class="p-3 text-right">${crStr}</td>
            <td class="p-3 text-right">${drStr}</td>
            <td class="p-3 text-right font-mono font-bold text-slate-900">${formatNaira(e.running_total || 0)}</td>
          </tr>
        `;
      }).join("");
    }
  }

  if (tfoot) {
    tfoot.innerHTML = `
      <tr>
        <td colspan="3" class="p-3">
          <span>PERIOD CLOSING RECONCILIATION (${entries.length} Transactions)</span>
          <span class="text-amber-300 ml-2 font-normal">Net Movement: ${formatNaira(mov.net_movement || 0)}</span>
        </td>
        <td class="p-3 text-right text-emerald-300">${formatNaira(mov.total_credits || 0)}</td>
        <td class="p-3 text-right text-rose-300">${formatNaira(mov.total_debits || 0)}</td>
        <td class="p-3 text-right text-amber-300 font-mono">${formatNaira(cl.total_equity || 0)}</td>
      </tr>
    `;
  }
}

function renderAllCreditsView(data, bannerEl, periodLbl, kpiGrid, thead, tbody, tfoot) {
  if (bannerEl) bannerEl.textContent = `INWARD REMITTANCES & CREDITS AUDIT • ${data.period_label.toUpperCase()}`;
  if (periodLbl) periodLbl.textContent = data.period_label;

  const summ = data.summary || {};
  const catBd = summ.category_breakdown || {};

  if (kpiGrid) {
    kpiGrid.className = "grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs";
    kpiGrid.innerHTML = `
      <div class="bg-emerald-50/70 p-3 rounded-xl border border-emerald-200">
        <span class="text-[10px] uppercase font-bold text-emerald-800 block">Total Remitted</span>
        <h4 class="text-base font-black text-emerald-700 mt-1">${formatNaira(summ.total_remitted || 0)}</h4>
        <span class="text-[10px] text-emerald-600 block mt-0.5">100% Inward Settlement</span>
      </div>
      <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
        <span class="text-[10px] uppercase font-bold text-slate-500 block">Inward Entries</span>
        <h4 class="text-base font-black text-slate-800 mt-1">${summ.remittance_count || 0}</h4>
        <span class="text-[10px] text-slate-400 block mt-0.5">Deposits &amp; Transfers</span>
      </div>
      <div class="bg-blue-50/70 p-3 rounded-xl border border-blue-200">
        <span class="text-[10px] uppercase font-bold text-blue-800 block">Regular Savings</span>
        <h4 class="text-base font-black text-blue-700 mt-1">${formatNaira(catBd.SAVINGS || 0)}</h4>
        <span class="text-[10px] text-blue-600 block mt-0.5">Liquid Cash Collateral</span>
      </div>
      <div class="bg-amber-50/70 p-3 rounded-xl border border-amber-200">
        <span class="text-[10px] uppercase font-bold text-amber-800 block">Share Capital Equity</span>
        <h4 class="text-base font-black text-amber-700 mt-1">${formatNaira(catBd.SHARE_CAPITAL || 0)}</h4>
        <span class="text-[10px] text-amber-600 block mt-0.5">Permanent Co-op Equity</span>
      </div>
      <div class="bg-purple-50/70 p-3 rounded-xl border border-purple-200">
        <span class="text-[10px] uppercase font-bold text-purple-800 block">Welfare Solidarity</span>
        <h4 class="text-base font-black text-purple-700 mt-1">${formatNaira(catBd.WELFARE_FUND || 0)}</h4>
        <span class="text-[10px] text-purple-600 block mt-0.5">Mutual Aid Scheme Pool</span>
      </div>
    `;
  }

  if (thead) {
    thead.innerHTML = `
      <tr>
        <th class="p-3">Date / Ref</th>
        <th class="p-3">Ledger Category</th>
        <th class="p-3">Payment Channel</th>
        <th class="p-3">Narration / Session ID</th>
        <th class="p-3 text-right">Amount Remitted</th>
        <th class="p-3 text-center">Status</th>
      </tr>
    `;
  }

  const entries = data.entries || [];
  if (tbody) {
    if (entries.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-400">No inward remittances recorded in this financial period.</td></tr>`;
    } else {
      tbody.innerHTML = entries.map(e => `
        <tr class="hover:bg-slate-50 transition">
          <td class="p-3">
            <div class="font-mono font-bold text-slate-800 text-[11px]">${(e.transaction_date || '').slice(0, 16)}</div>
            <div class="font-mono text-[10px] text-slate-400">${e.transaction_ref}</div>
          </td>
          <td class="p-3">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-800 border border-emerald-100">
              ${(e.ledger_category || '').replace(/_/g, ' ')}
            </span>
          </td>
          <td class="p-3 font-semibold text-slate-700 text-[11px]">
            ${(e.payment_method || '').replace(/_/g, ' ')}
          </td>
          <td class="p-3 text-slate-600 text-[11px]">
            <div>${e.narration || '-'}</div>
            <div class="font-mono text-[10px] text-slate-400">${e.channel_reference || ''}</div>
          </td>
          <td class="p-3 text-right font-mono font-bold text-emerald-700">+${formatNaira(e.amount)}</td>
          <td class="p-3 text-center">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
              ✓ ${e.status || 'VERIFIED'}
            </span>
          </td>
        </tr>
      `).join("");
    }
  }

  if (tfoot) {
    tfoot.innerHTML = `
      <tr>
        <td colspan="4" class="p-3">TOTAL INWARD REMITTANCES (${entries.length} Deposits)</td>
        <td class="p-3 text-right text-emerald-300 font-mono">${formatNaira(summ.total_remitted || 0)}</td>
        <td class="p-3 text-center text-emerald-400 font-mono text-[11px]">100% AUDITED</td>
      </tr>
    `;
  }
}

function renderAllDebitsView(data, bannerEl, periodLbl, kpiGrid, thead, tbody, tfoot) {
  if (bannerEl) bannerEl.textContent = `OUTWARD DISBURSEMENTS & CLAIMS AUDIT • ${data.period_label.toUpperCase()}`;
  if (periodLbl) periodLbl.textContent = data.period_label;

  const summ = data.summary || {};
  const catBd = summ.category_breakdown || {};

  if (kpiGrid) {
    kpiGrid.className = "grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs";
    kpiGrid.innerHTML = `
      <div class="bg-rose-50/70 p-3 rounded-xl border border-rose-200">
        <span class="text-[10px] uppercase font-bold text-rose-800 block">Total Disbursed</span>
        <h4 class="text-base font-black text-rose-700 mt-1">${formatNaira(summ.total_disbursed || 0)}</h4>
        <span class="text-[10px] text-rose-600 block mt-0.5">Approved Outflows</span>
      </div>
      <div class="bg-slate-50 p-3 rounded-xl border border-slate-200">
        <span class="text-[10px] uppercase font-bold text-slate-500 block">Disbursement Count</span>
        <h4 class="text-base font-black text-slate-800 mt-1">${summ.disbursement_count || 0}</h4>
        <span class="text-[10px] text-slate-400 block mt-0.5">Payout Vouchers</span>
      </div>
      <div class="bg-blue-50/70 p-3 rounded-xl border border-blue-200">
        <span class="text-[10px] uppercase font-bold text-blue-800 block">Savings / Target Withdrawals</span>
        <h4 class="text-base font-black text-blue-700 mt-1">${formatNaira(catBd.SAVINGS || 0)}</h4>
        <span class="text-[10px] text-blue-600 block mt-0.5">Member Principal Payouts</span>
      </div>
      <div class="bg-teal-50/70 p-3 rounded-xl border border-teal-200">
        <span class="text-[10px] uppercase font-bold text-teal-800 block">Loan Disbursements</span>
        <h4 class="text-base font-black text-teal-700 mt-1">${formatNaira(catBd.LOAN_DISBURSEMENT || 0)}</h4>
        <span class="text-[10px] text-teal-600 block mt-0.5">Direct NUBAN Credits</span>
      </div>
    `;
  }

  if (thead) {
    thead.innerHTML = `
      <tr>
        <th class="p-3">Date / Ref</th>
        <th class="p-3">Disbursement Category</th>
        <th class="p-3">Purpose / Narration</th>
        <th class="p-3">Beneficiary / Channel</th>
        <th class="p-3 text-right">Amount Disbursed</th>
        <th class="p-3 text-center">Status</th>
      </tr>
    `;
  }

  const entries = data.entries || [];
  if (tbody) {
    if (entries.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-400">No outward debits or claims recorded during this period.</td></tr>`;
    } else {
      tbody.innerHTML = entries.map(e => `
        <tr class="hover:bg-slate-50 transition">
          <td class="p-3">
            <div class="font-mono font-bold text-slate-800 text-[11px]">${(e.transaction_date || '').slice(0, 16)}</div>
            <div class="font-mono text-[10px] text-slate-400">${e.transaction_ref}</div>
          </td>
          <td class="p-3">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-rose-50 text-rose-800 border border-rose-100">
              ${(e.ledger_category || '').replace(/_/g, ' ')}
            </span>
          </td>
          <td class="p-3 text-slate-700 text-[11px]">
            ${e.narration || 'Disbursement Outflow'}
          </td>
          <td class="p-3 text-slate-600 text-[11px]">
            <div>${e.channel_reference || e.payment_method || '-'}</div>
          </td>
          <td class="p-3 text-right font-mono font-bold text-rose-700">-${formatNaira(e.amount)}</td>
          <td class="p-3 text-center">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-800">
              ✓ ${e.status || 'VERIFIED'}
            </span>
          </td>
        </tr>
      `).join("");
    }
  }

  if (tfoot) {
    tfoot.innerHTML = `
      <tr>
        <td colspan="4" class="p-3">TOTAL OUTWARD DISBURSEMENTS (${entries.length} Payouts)</td>
        <td class="p-3 text-right text-rose-300 font-mono">${formatNaira(summ.total_disbursed || 0)}</td>
        <td class="p-3 text-center text-slate-300 font-mono text-[11px]">SETTLED</td>
      </tr>
    `;
  }
}

function renderPaymentAdviceHistoryView(advices, bannerEl, periodLbl, kpiGrid, thead, tbody, tfoot) {
  if (bannerEl) bannerEl.textContent = `MONTHLY PAYMENT ADVICES & REMITTANCES HISTORY`;
  if (periodLbl) periodLbl.textContent = "All Monthly Assessments";

  let totalAdv = 0;
  let totalPaid = 0;
  let totalOut = 0;
  (advices || []).forEach(a => {
    totalAdv += parseFloat(a.total_expected_amount || 0);
    totalPaid += parseFloat(a.total_amount_paid || 0);
    totalOut += parseFloat(a.outstanding_balance || 0);
  });

  if (kpiGrid) {
    kpiGrid.className = "grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs";
    kpiGrid.innerHTML = `
      <div class="bg-indigo-50/70 p-4 rounded-xl border border-indigo-200">
        <span class="text-[10px] uppercase font-bold text-indigo-900 block">Total Advised Assessments</span>
        <h4 class="text-xl font-black text-indigo-950 mt-1">${formatNaira(totalAdv)}</h4>
        <span class="text-[10px] text-indigo-700 block mt-0.5">Across all billing cycles</span>
      </div>
      <div class="bg-emerald-50/70 p-4 rounded-xl border border-emerald-200">
        <span class="text-[10px] uppercase font-bold text-emerald-800 block">Total Paid So Far</span>
        <h4 class="text-xl font-black text-emerald-700 mt-1">${formatNaira(totalPaid)}</h4>
        <span class="text-[10px] text-emerald-600 block mt-0.5">Settled via waterfall allocations</span>
      </div>
      <div class="bg-amber-50/70 p-4 rounded-xl border border-amber-200">
        <span class="text-[10px] uppercase font-bold text-amber-800 block">Current Outstanding Balance</span>
        <h4 class="text-xl font-black text-amber-700 mt-1">${formatNaira(totalOut)}</h4>
        <span class="text-[10px] text-amber-600 block mt-0.5">Cumulative remaining dues</span>
      </div>
    `;
  }

  if (thead) {
    thead.innerHTML = `
      <tr>
        <th class="p-3">Billing Period</th>
        <th class="p-3">Advice Reference</th>
        <th class="p-3 text-right">Advised (Expected)</th>
        <th class="p-3 text-right">Paid So Far</th>
        <th class="p-3 text-right">Remaining Due</th>
        <th class="p-3 text-center">Status</th>
        <th class="p-3 text-center">Slip / PDF</th>
      </tr>
    `;
  }

  if (tbody) {
    if (!advices || advices.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-400">No payment advice billing history found.</td></tr>`;
    } else {
      tbody.innerHTML = advices.map(a => {
        const isSettled = a.status === "PAID";
        const statusBadge = isSettled
          ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">SETTLED</span>`
          : (parseFloat(a.total_amount_paid || 0) > 0
              ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800">PARTIAL</span>`
              : `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">DUE</span>`);

        return `
          <tr class="hover:bg-slate-50 transition">
            <td class="p-3 font-bold text-slate-900">${a.billing_period}</td>
            <td class="p-3 font-mono text-slate-600 text-[11px]">${a.advice_reference}</td>
            <td class="p-3 text-right font-mono font-semibold text-slate-800">${formatNaira(a.total_expected_amount)}</td>
            <td class="p-3 text-right font-mono text-emerald-700">${formatNaira(a.total_amount_paid)}</td>
            <td class="p-3 text-right font-mono font-bold text-amber-700">${formatNaira(a.outstanding_balance)}</td>
            <td class="p-3 text-center">${statusBadge}</td>
            <td class="p-3 text-center">
              <button onclick="downloadAdvicePdfForPeriod('${a.billing_period}')" class="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold text-[10px] transition">
                📥 PDF Slip
              </button>
            </td>
          </tr>
        `;
      }).join("");
    }
  }

  if (tfoot) {
    tfoot.innerHTML = `
      <tr>
        <td colspan="2" class="p-3">TOTAL ASSESSMENTS (${advices ? advices.length : 0} Periods)</td>
        <td class="p-3 text-right text-slate-200 font-mono">${formatNaira(totalAdv)}</td>
        <td class="p-3 text-right text-emerald-300 font-mono">${formatNaira(totalPaid)}</td>
        <td class="p-3 text-right text-amber-300 font-mono">${formatNaira(totalOut)}</td>
        <td colspan="2" class="p-3 text-center text-slate-400 text-[10px]">WATERFALL AUDITED</td>
      </tr>
    `;
  }
}

function renderLoansStatementView(data, bannerEl, periodLbl, kpiGrid, thead, tbody, tfoot) {
  if (bannerEl) bannerEl.textContent = `LOAN FACILITIES & AMORTIZATION STATEMENT • 0.0% STATUTORY INTEREST`;
  if (periodLbl) periodLbl.textContent = "Active & Historical Loan Facilities";

  const summ = data.summary || {};
  const mem = data.member || {};
  const loans = data.loans || [];

  if (kpiGrid) {
    kpiGrid.className = "grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs";
    kpiGrid.innerHTML = `
      <div class="bg-indigo-50/70 p-3 rounded-xl border border-indigo-200">
        <span class="text-[10px] uppercase font-bold text-indigo-900 block">Total Borrowed</span>
        <h4 class="text-base font-black text-indigo-950 mt-1">${formatNaira(summ.total_principal_borrowed || 0)}</h4>
        <span class="text-[10px] text-indigo-700 block mt-0.5">Principal Disbursed</span>
      </div>
      <div class="bg-emerald-50/70 p-3 rounded-xl border border-emerald-200">
        <span class="text-[10px] uppercase font-bold text-emerald-800 block">Total Repaid</span>
        <h4 class="text-base font-black text-emerald-700 mt-1">${formatNaira(summ.total_repaid || 0)}</h4>
        <span class="text-[10px] text-emerald-600 block mt-0.5">Principal + 5% Fee</span>
      </div>
      <div class="bg-amber-50/70 p-3 rounded-xl border border-amber-200">
        <span class="text-[10px] uppercase font-bold text-amber-800 block">Outstanding Balance</span>
        <h4 class="text-base font-black text-amber-700 mt-1">${formatNaira(summ.total_outstanding_balance || 0)}</h4>
        <span class="text-[10px] text-amber-600 block mt-0.5">Scheduled Installments</span>
      </div>
      <div class="bg-blue-50/70 p-3 rounded-xl border border-blue-200">
        <span class="text-[10px] uppercase font-bold text-blue-800 block">Available Savings</span>
        <h4 class="text-base font-black text-blue-700 mt-1">${formatNaira(mem.current_savings || 0)}</h4>
        <span class="text-[10px] text-blue-600 block mt-0.5">Cash Collateral Pool</span>
      </div>
      <div class="bg-teal-50/70 p-3 rounded-xl border border-teal-200">
        <span class="text-[10px] uppercase font-bold text-teal-800 block">2× Borrowing Capacity</span>
        <h4 class="text-base font-black text-teal-700 mt-1">${formatNaira(mem.borrowing_capacity_2x || 0)}</h4>
        <span class="text-[10px] text-teal-600 block mt-0.5">0.0% Compounding Int.</span>
      </div>
    `;
  }

  if (thead) {
    thead.innerHTML = `
      <tr>
        <th class="p-3">Loan Ref / Product</th>
        <th class="p-3 text-right">Principal</th>
        <th class="p-3 text-right">Admin Fee (5%)</th>
        <th class="p-3 text-right">Total Payable</th>
        <th class="p-3 text-right">Total Paid</th>
        <th class="p-3 text-right">Outstanding</th>
        <th class="p-3 text-center">Status</th>
      </tr>
    `;
  }

  if (tbody) {
    if (loans.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-slate-400">No active or historical loan facilities found for this cooperator.</td></tr>`;
    } else {
      tbody.innerHTML = loans.map(l => `
        <tr class="hover:bg-slate-50 transition">
          <td class="p-3">
            <div class="font-mono font-bold text-slate-900">${l.loan_reference}</div>
            <div class="text-[11px] text-slate-500">${l.product_name} (${l.tenure_months} Months)</div>
          </td>
          <td class="p-3 text-right font-mono font-semibold text-slate-800">${formatNaira(l.principal_amount)}</td>
          <td class="p-3 text-right font-mono text-slate-600">${formatNaira(l.admin_cost_fee)}</td>
          <td class="p-3 text-right font-mono font-semibold text-slate-800">${formatNaira(l.total_payable)}</td>
          <td class="p-3 text-right font-mono text-emerald-700 font-bold">${formatNaira(l.total_paid)}</td>
          <td class="p-3 text-right font-mono font-bold text-amber-700">${formatNaira(l.outstanding_balance)}</td>
          <td class="p-3 text-center">
            <span class="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-slate-100 text-slate-800">
              ${l.status}
            </span>
          </td>
        </tr>
      `).join("");
    }
  }

  if (tfoot) {
    tfoot.innerHTML = `
      <tr>
        <td class="p-3">TOTAL FACILITIES (${loans.length})</td>
        <td class="p-3 text-right text-slate-200 font-mono">${formatNaira(summ.total_principal_borrowed || 0)}</td>
        <td class="p-3 text-right text-slate-300 font-mono">${formatNaira((summ.total_principal_borrowed || 0) * 0.05)}</td>
        <td class="p-3 text-right text-slate-200 font-mono">${formatNaira((summ.total_principal_borrowed || 0) * 1.05)}</td>
        <td class="p-3 text-right text-emerald-300 font-mono">${formatNaira(summ.total_repaid || 0)}</td>
        <td class="p-3 text-right text-amber-300 font-mono">${formatNaira(summ.total_outstanding_balance || 0)}</td>
        <td class="p-3 text-center text-slate-300 text-[10px]">CAP C15 COMPLIANT</td>
      </tr>
    `;
  }
}

async function downloadCurrentReportPDF() {
  const memberId = currentUser ? currentUser.id : null;
  const token = localStorage.getItem("wbmf_session_token");
  if (!memberId || !token) {
    alert("Please sign in to download your official statement.");
    return;
  }

  const typeSel = document.getElementById("report-select-type");
  const yearSel = document.getElementById("report-select-year");
  const reportType = typeSel ? typeSel.value : "PASSBOOK_LEDGER";
  const yearVal = yearSel ? yearSel.value : "2026";
  const yearParam = (yearVal === "ALL" || !yearVal) ? "" : `&year=${yearVal}`;

  const btn = document.getElementById("btn-download-report-pdf");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>↻</span><span>Generating PDF...</span>`;
  }

  let endpoint = "";
  let defFilename = "";

  if (reportType === "PASSBOOK_LEDGER") {
    endpoint = `${API_BASE_URL}/members/${memberId}/reports/ledger/pdf?token=${encodeURIComponent(token)}${yearParam}`;
    defFilename = `Wealthbridge_Passbook_Ledger_${yearVal}.pdf`;
  } else if (reportType === "ALL_CREDITS") {
    endpoint = `${API_BASE_URL}/members/${memberId}/reports/credits/pdf?token=${encodeURIComponent(token)}${yearParam}`;
    defFilename = `Wealthbridge_Credits_Audit_${yearVal}.pdf`;
  } else if (reportType === "ALL_DEBITS") {
    endpoint = `${API_BASE_URL}/members/${memberId}/reports/debits/pdf?token=${encodeURIComponent(token)}${yearParam}`;
    defFilename = `Wealthbridge_Debits_Audit_${yearVal}.pdf`;
  } else if (reportType === "PAYMENT_ADVICE") {
    endpoint = `${API_BASE_URL}/members/${memberId}/payment-advice/current/pdf?token=${encodeURIComponent(token)}`;
    defFilename = `Wealthbridge_Payment_Advice.pdf`;
  } else if (reportType === "LOANS_STATEMENT") {
    endpoint = `${API_BASE_URL}/members/${memberId}/reports/loans/pdf?token=${encodeURIComponent(token)}`;
    defFilename = `Wealthbridge_Loans_Statement.pdf`;
  }

  try {
    const res = await fetch(endpoint);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(`⚠️ Could not generate PDF: ${err.detail || "Server error"}`);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<span>📥</span><span>Download PDF</span>`;
      }
      return;
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = url;
    a.download = defFilename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>📥</span><span>Download PDF</span>`;
    }
  } catch (err) {
    console.error("Error downloading report PDF:", err);
    window.open(endpoint, "_blank");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>📥</span><span>Download PDF</span>`;
    }
  }
}

async function downloadAdvicePdfForPeriod(billingPeriod) {
  const memberId = currentUser ? currentUser.id : null;
  const token = localStorage.getItem("wbmf_session_token");
  if (!memberId || !token) return;

  const url = `${API_BASE_URL}/members/${memberId}/payment-advice/current/pdf?period=${encodeURIComponent(billingPeriod)}&token=${encodeURIComponent(token)}`;
  window.open(url, "_blank");
}

function printCurrentReportStatement() {
  window.print();
}
window.printCurrentReportStatement = printCurrentReportStatement;


// =============================================================================
// ELECTRONIC MEMBERSHIP ID CARD (FRONT & BACK VIEWS + VECTOR PDF GENERATION)
// =============================================================================
async function openElectronicIdModal() {
  if (!currentUser) {
    openLoginModal();
    return;
  }

  const isApproved = ["ACTIVE", "SYSTEM_ADMINISTRATOR"].includes(currentUser.membership_status) || currentUser.is_executive;
  if (!isApproved) {
    alert("Official Electronic Membership ID Card is accessible only after formal Secretariat approval and admission into active Society standing.\n\nOnce your cooperator admission has been formally approved by the Secretariat, your digital card and downloadable vector PDF will be accessible here.");
    return;
  }

  const modal = document.getElementById("modal-electronic-id");
  if (!modal) return;

  // Hydrate Front of Card Elements
  const nameEl = document.getElementById("modal-id-name");
  const codeEl = document.getElementById("modal-id-code");
  const tierEl = document.getElementById("modal-id-tier");
  const dateEl = document.getElementById("modal-id-date");
  const ninEl = document.getElementById("modal-id-nin");
  const photoInitials = document.getElementById("modal-id-photo-initials");
  const photoImg = document.getElementById("modal-id-photo-img");

  if (nameEl) nameEl.textContent = currentUser.full_name || "Cooperator";
  if (codeEl) codeEl.textContent = currentUser.member_code || "WMC-2026-001";
  if (tierEl) tierEl.textContent = currentUser.contribution_tier || "STANDARD";
  if (dateEl) {
    const rawDate = currentUser.date_of_admission || currentUser.created_at || "2026-09-26";
    dateEl.textContent = String(rawDate).split("T")[0];
  }
  if (ninEl) {
    const ninStr = String(currentUser.nin || "");
    ninEl.textContent = ninStr.length >= 4 ? `******${ninStr.slice(-4)}` : "******0000";
  }

  // Passport photo handling
  if (currentUser.passport_photo && photoImg && photoInitials) {
    photoImg.src = currentUser.passport_photo;
    photoImg.classList.remove("hidden");
    photoInitials.classList.add("hidden");
  } else if (photoImg && photoInitials) {
    photoImg.classList.add("hidden");
    photoInitials.classList.remove("hidden");
    const parts = (currentUser.full_name || "QA").trim().split(" ");
    photoInitials.textContent = parts.length > 1 ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase() : parts[0].substring(0, 2).toUpperCase();
  }

  // Button handling for approved cooperators
  const downloadBtn = document.getElementById("btn-modal-download-pdf-id");
  if (downloadBtn) {
    downloadBtn.disabled = false;
    downloadBtn.classList.remove("opacity-50", "cursor-not-allowed");
    downloadBtn.innerHTML = `<span>📥</span><span>Download Vector PDF</span>`;
  }

  // Hydrate Back of Card Dual Signatures (Dynamic President & General Secretary)
  try {
    const sigRes = await fetch(`${API_BASE_URL}/governance/signatories`);
    if (sigRes.ok) {
      const sigData = await sigRes.json();
      const sigs = sigData.data || sigData;
      const secSigEl = document.getElementById("idcard-sec-signature");
      const secTitleEl = document.getElementById("idcard-sec-title");
      const presSigEl = document.getElementById("idcard-pres-signature");
      const presTitleEl = document.getElementById("idcard-pres-title");

      if (secSigEl && sigs.general_secretary) {
        secSigEl.textContent = sigs.general_secretary.name;
      }
      if (secTitleEl && sigs.general_secretary) {
        secTitleEl.textContent = sigs.general_secretary.title;
      }
      if (presSigEl && sigs.president) {
        presSigEl.textContent = sigs.president.name;
      }
      if (presTitleEl && sigs.president) {
        presTitleEl.textContent = sigs.president.title;
      }
    }
  } catch (sigErr) {
    console.warn("Could not load dynamic signatories for ID Card:", sigErr);
  }

  modal.classList.remove("hidden");
}
window.openElectronicIdModal = openElectronicIdModal;

function closeElectronicIdModal() {
  const modal = document.getElementById("modal-electronic-id");
  if (modal) modal.classList.add("hidden");
}
window.closeElectronicIdModal = closeElectronicIdModal;

async function downloadMemberIdCardPDF() {
  if (!currentUser) {
    openLoginModal();
    return;
  }

  const isApproved = ["ACTIVE", "SYSTEM_ADMINISTRATOR"].includes(currentUser.membership_status) || currentUser.is_executive;
  if (!isApproved) {
    alert("Statutory Notice: Your Electronic Membership ID Card is currently locked pending formal Secretariat approval. Once approved into active Society standing, your official card can be downloaded.");
    return;
  }

  const token = localStorage.getItem("wbmf_session_token") || sessionToken || "";
  const memberId = currentUser.id;
  const endpoint = `${API_BASE_URL}/members/${memberId}/id-card/pdf?token=${encodeURIComponent(token)}`;

  const btnModal = document.getElementById("btn-modal-download-pdf-id");
  const btnProf = document.getElementById("btn-profile-download-id");
  const updateBtns = (txt) => {
    if (btnModal) btnModal.innerHTML = txt;
    if (btnProf) btnProf.innerHTML = txt;
  };

  try {
    updateBtns(`<span>⏳</span><span>Generating Card...</span>`);
    const resp = await fetch(endpoint, {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });

    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      throw new Error(errData.detail || `Server returned ${resp.status}`);
    }

    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = url;
    a.download = `Wealthbridge_ID_Card_${currentUser.member_code || memberId}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    updateBtns(`<span>📥</span><span>Download Vector PDF</span>`);
  } catch (err) {
    console.error("Error generating ID card PDF:", err);
    window.open(endpoint, "_blank");
    updateBtns(`<span>📥</span><span>Download Vector PDF</span>`);
  }
}
window.downloadMemberIdCardPDF = downloadMemberIdCardPDF;

function printMemberIdCard() {
  window.print();
}
window.printMemberIdCard = printMemberIdCard;

// =============================================================================
// COMPREHENSIVE COOPERATIVE GOVERNANCE SUITE ENGINE
// =============================================================================

// -----------------------------------------------------------------------------
// 1. APPLICANT DOSSIER INSPECTION DRAWER (SECRETARIAT & ADMIN)
// -----------------------------------------------------------------------------
let currentInspectingMemberId = null;

async function openApplicantDossier(memberId) {
  currentInspectingMemberId = memberId;
  const modal = document.getElementById("modal-applicant-dossier");
  if (!modal) return;

  const loader = document.getElementById("dossier-loading-indicator");
  const content = document.getElementById("dossier-content");
  if (loader) loader.classList.remove("hidden");
  if (content) content.classList.add("hidden");
  modal.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE_URL}/admin/pending-members/${memberId}/dossier`);
    if (!res.ok) throw new Error("Failed to load applicant dossier");
    const d = await res.json();
    const payload = d.data || d;
    const m = payload.member || {};
    const nok = payload.next_of_kin || {};
    const docs = payload.documents || {};
    const kyc = payload.compulsory_kyc || payload.kyc || {};

    // Header Quick Identity
    const fullName = `${m.first_name || ''} ${m.last_name || ''}`.trim() || 'Cooperator Applicant';
    const nameEl = document.getElementById("dossier-full-name") || document.getElementById("dossier-name");
    const codeEl = document.getElementById("dossier-member-code") || document.getElementById("dossier-code");
    const tierEl = document.getElementById("dossier-tier");
    const statusBadge = document.getElementById("dossier-status-badge") || document.getElementById("dossier-kyc-badge");
    const admDate = document.getElementById("dossier-admission-date") || document.getElementById("dossier-reg-date");
    const compBadge = document.getElementById("dossier-compulsory-badge");
    const memIdInput = document.getElementById("dossier-member-id");
    const photoInitials = document.getElementById("dossier-photo-initials");

    if (nameEl) nameEl.textContent = fullName;
    if (codeEl) codeEl.textContent = m.member_code || `WMC-PENDING-${m.id}`;
    if (tierEl) tierEl.textContent = `${m.contribution_tier || "STANDARD"} TIER`;
    if (statusBadge) {
      statusBadge.textContent = m.membership_status || "PENDING_KYC";
      statusBadge.className = `px-2.5 py-0.5 rounded-full text-[10px] font-bold ${m.membership_status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`;
    }
    if (admDate) admDate.textContent = `Lodged: ${(m.admission_date || m.created_at || '').substring(0, 10) || 'Recent'}`;
    if (memIdInput) memIdInput.value = m.id;
    if (photoInitials) photoInitials.textContent = `${m.first_name ? m.first_name[0] : ''}${m.last_name ? m.last_name[0] : ''}`.toUpperCase() || '--';

    const overallKycPct = m.kyc_completion_percent ?? payload.kyc_completion_percent ?? kyc.kyc_completion_percent ?? 0;
    const compPct = kyc.compulsory_score_percent ?? (kyc.is_compulsory_complete ? 100 : 0);
    const compDone = kyc.completed_count ?? (kyc.is_compulsory_complete ? 6 : 0);
    if (compBadge) {
      compBadge.innerHTML = `
        <span class="block text-white font-extrabold text-xs">${overallKycPct}% Total KYC Profile</span>
        <span class="text-[10px] ${compDone === 6 ? 'text-emerald-300' : 'text-amber-300'} font-semibold">(${compDone}/6 Compulsory DVA Fields Validated)</span>
      `;
    }

    // Biodata & Contacts
    const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val || "Not provided"; };
    setTxt("dossier-gender", m.gender);
    setTxt("dossier-marital", m.marital_status);
    setTxt("dossier-phone", m.phone);
    setTxt("dossier-email", m.email);
    setTxt("dossier-address", m.residential_address);
    setTxt("dossier-employment", m.employment_status ? `${m.employment_status.replace(/_/g, " ")}${m.employer_or_business_name ? ` (${m.employer_or_business_name})` : ''}` : "Not provided");

    // Identification & Bank
    setTxt("dossier-id-type", m.identification_type || "National Identity (NIN)");
    setTxt("dossier-id-num", m.identification_number || "No NIN provided");
    setTxt("dossier-bank-name", m.bank_name || "Commercial Bank not set");
    setTxt("dossier-bank-num", m.bank_account_number || "Not provided");
    setTxt("dossier-bank-holder", m.bank_account_name || "Not provided");

    // Next of Kin
    setTxt("dossier-nok-name", nok.next_of_kin_name || m.next_of_kin_name || "Not assigned");
    setTxt("dossier-nok-rel", nok.relationship || nok.next_of_kin_relationship || m.next_of_kin_relationship || "Not specified");
    setTxt("dossier-nok-phone", nok.phone || nok.next_of_kin_phone || m.next_of_kin_phone || "Not provided");
    setTxt("dossier-nok-alloc", nok.benefit_percentage ? `${nok.benefit_percentage}%` : "100%");
    setTxt("dossier-nok-address", nok.address || nok.next_of_kin_address || m.next_of_kin_address || "Not provided");

    // Compulsory KYC 6-field Assessment Grid
    const compGrid = document.getElementById("dossier-compulsory-grid");
    if (compGrid) {
      const fieldLabels = {
        first_name: "Legal First Name",
        last_name: "Legal Surname",
        phone: "Phone Number",
        email: "Official Email Address",
        residential_address: "Residential Address",
        identification_number: "National Identity (NIN)"
      };
      const chk = kyc.compulsory_fields_status || {};
      compGrid.innerHTML = Object.keys(fieldLabels).map(k => {
        const isDone = Boolean(chk[k]);
        return `
          <div class="p-2.5 rounded-xl border ${isDone ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-amber-50 border-amber-200 text-amber-900'} flex items-center justify-between">
            <span class="font-medium text-[11px]">${fieldLabels[k]}</span>
            <span class="font-bold text-[10px]">${isDone ? '✅ Complete' : '⚠️ Missing'}</span>
          </div>
        `;
      }).join("");
    }

    // Uploaded Documents Cards
    const docsContainer = document.getElementById("dossier-docs-container");
    if (docsContainer) {
      const docTypes = [
        { key: "id_document", label: "National ID / Voter Card / Passport", icon: "🪪" },
        { key: "passport_photo", label: "Applicant Passport Photograph", icon: "👤" },
        { key: "proof_of_address", label: "Utility Bill / Proof of Address", icon: "🏠" },
        { key: "signature_specimen", label: "Authorized Signature Specimen", icon: "✍️" }
      ];

      docsContainer.innerHTML = docTypes.map(dt => {
        const doc = docs[dt.key];
        const hasDoc = Boolean(doc && doc.file_url);
        return `
          <div class="p-3.5 rounded-xl border ${hasDoc ? 'border-emerald-200 bg-emerald-50/40' : 'border-slate-200 bg-white'} flex flex-col justify-between">
            <div class="space-y-1 mb-2">
              <div class="flex items-center gap-1.5">
                <span class="text-base">${dt.icon}</span>
                <h6 class="font-bold text-slate-800 text-[11px] leading-tight">${dt.label}</h6>
              </div>
              <p class="text-[9px] text-slate-500">${hasDoc ? `Uploaded: ${doc.file_name || 'Document'}` : 'No document file submitted'}</p>
            </div>
            <div class="pt-2 border-t ${hasDoc ? 'border-emerald-100' : 'border-slate-100'} flex items-center justify-between">
              ${hasDoc ? `
                <a href="${doc.file_url}" target="_blank" class="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[9px] transition inline-flex items-center gap-1">
                  <span>👁️</span><span>Inspect</span>
                </a>
                <span class="text-[9px] text-emerald-700 font-mono font-bold">Verified</span>
              ` : `
                <span class="text-[9px] font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded">Pending</span>
              `}
            </div>
          </div>
        `;
      }).join("");
    }

    if (loader) loader.classList.add("hidden");
    if (content) content.classList.remove("hidden");

  } catch (err) {
    console.error("Error opening dossier:", err);
    if (loader) loader.innerHTML = `<span class="text-rose-600 font-bold">⚠️ Failed to load applicant dossier: ${err.message}</span>`;
  }
}
window.openApplicantDossier = openApplicantDossier;

function closeApplicantDossier() {
  const modal = document.getElementById("modal-applicant-dossier");
  if (modal) modal.classList.add("hidden");
  currentInspectingMemberId = null;
}
window.closeApplicantDossier = closeApplicantDossier;
window.closeApplicantDossierModal = closeApplicantDossier;

async function approveApplicantDossier() {
  if (!currentInspectingMemberId) return;
  if (!confirm(`Are you sure you want to approve cooperator membership for ID #${currentInspectingMemberId}?`)) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/approve-member`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        member_id: currentInspectingMemberId,
        officer_id: currentUser ? currentUser.id : 2
      })
    });
    const data = await res.json();
    if (res.ok) {
      alert("✅ Membership Approved! Welcome package and dedicated NUBAN unlocked.");
      closeApplicantDossier();
      loadPendingMembers();
      loadExecMembersRegistry();
      loadExecutiveMetrics();
    } else {
      alert("Error: " + (data.detail || "Approval failed"));
    }
  } catch (err) {
    alert("Connection error occurred while approving applicant.");
  }
}
window.approveApplicantDossier = approveApplicantDossier;

async function rejectApplicantDossier() {
  if (!currentInspectingMemberId) return;
  const reason = prompt("Enter statutory reason for declining this membership application:");
  if (!reason) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/reject-member`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        member_id: currentInspectingMemberId,
        officer_id: currentUser ? currentUser.id : 2,
        reason: reason
      })
    });
    const data = await res.json();
    if (res.ok) {
      alert("Application recorded as Declined.");
      closeApplicantDossier();
      loadPendingMembers();
    } else {
      alert("Error: " + (data.detail || "Rejection failed"));
    }
  } catch (err) {
    alert("Connection error occurred while rejecting application.");
  }
}
window.rejectApplicantDossier = rejectApplicantDossier;


// -----------------------------------------------------------------------------
// 2. MEMBER LOAN APPLICATIONS & PROGRESS TRACKER
// -----------------------------------------------------------------------------
async function loadMemberLoanApplications() {
  if (!currentUser || !currentUser.id) return;
  const container = document.getElementById("member-loans-list");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/loans`);
    if (!res.ok) throw new Error("Could not fetch loans");
    const result = await res.json();
    const loans = Array.isArray(result) ? result : (result.data || []);

    if (!loans || loans.length === 0) {
      container.innerHTML = `
        <div class="p-8 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-3">
          <span class="text-3xl">🤝</span>
          <h4 class="font-bold text-slate-700 text-sm">No Active or Past Loan Applications</h4>
          <p class="text-xs text-slate-500 max-w-md mx-auto">
            You currently have no loan applications on file. Qualified cooperators can apply for statutory credit facilities governed by Cooperative Bye-Laws.
          </p>
          <button onclick="openLoanModal()" class="px-4 py-2 rounded-xl btn-primary font-bold text-xs shadow-md">
            Apply for Loan Facility
          </button>
        </div>
      `;
      return;
    }

    container.innerHTML = loans.map(l => {
      const pct = l.approval_level_percent || 0;
      const isDeclined = l.status === "DECLINED";
      const isAppealed = l.status === "APPEALED" || l.has_pending_appeal;
      const isApproved = l.status === "ACTIVE";
      const tenure = l.tenure_months || l.repayment_months || 6;
      const monthly = l.monthly_installment || l.monthly_repayment_ngn || 0;
      const prodName = l.product_name || "Ordinary loan (*2 of savings)";

      const guarantorsHtml = (l.guarantors && l.guarantors.length > 0)
        ? `<div class="text-[11px] text-slate-500 flex flex-wrap items-center gap-1.5 pt-1">
             <span class="font-bold text-slate-700">Guarantor(s):</span>
             ${l.guarantors.map(g => `<span class="bg-indigo-50/70 text-indigo-900 px-2 py-0.5 rounded-md border border-indigo-200 font-mono text-[10px]">👤 ${g.first_name} ${g.last_name} (₦${parseFloat(g.guaranteed_amount).toLocaleString()})</span>`).join("")}
           </div>`
        : "";

      return `
        <div class="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <div>
              <div class="flex items-center gap-2">
                <span class="font-mono font-bold text-xs text-indigo-900 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200">
                  ${l.loan_reference}
                </span>
                <span class="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">${prodName}</span>
                <span class="text-xs text-slate-400 font-mono">Applied: ${(l.application_date || '').substring(0, 10)}</span>
              </div>
              <h4 class="text-base font-black text-wmcNavy-950 mt-1">
                ₦${parseFloat(l.principal_amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                <span class="text-xs font-normal text-slate-500">over ${tenure} Months (₦${parseFloat(monthly).toLocaleString(undefined, { minimumFractionDigits: 2 })}/mo)</span>
              </h4>
              ${guarantorsHtml}
            </div>

            <div>
              ${isApproved ? `
                <span class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  ✅ 100% Disbursed &amp; Active
                </span>
              ` : isDeclined ? `
                <span class="px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200">
                  ❌ Application Declined
                </span>
              ` : isAppealed ? `
                <span class="px-3 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800 border border-blue-200">
                  ⚖️ Under Appeal Review (${pct}%)
                </span>
              ` : `
                <span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
                  ⏳ ${pct}% Approved &bull; In Vetting
                </span>
              `}
            </div>
          </div>

          <!-- 4-Stage Approval Progress Meter -->
          <div class="space-y-2">
            <div class="flex justify-between items-center text-xs">
              <span class="font-bold text-slate-700">Approval Level Progress</span>
              <span class="font-mono font-extrabold ${pct === 100 ? 'text-emerald-600' : 'text-indigo-600'}">${pct}% / 100%</span>
            </div>
            <div class="w-full bg-slate-100 rounded-full h-3 overflow-hidden border border-slate-200">
              <div class="h-3 rounded-full transition-all duration-700 ${isDeclined ? 'bg-rose-500' : 'bg-gradient-to-r from-amber-500 via-indigo-600 to-emerald-500'}" style="width: ${pct}%"></div>
            </div>
            
            <div class="grid grid-cols-4 gap-2 text-[10px] pt-1">
              <div class="text-center ${pct >= 0 ? 'text-slate-700 font-bold' : 'text-slate-400'}">
                <span>0% Submitted</span>
              </div>
              <div class="text-center ${pct >= 33 ? 'text-indigo-600 font-bold' : 'text-slate-400'}">
                <span>33% Committee</span>
              </div>
              <div class="text-center ${pct >= 66 ? 'text-indigo-600 font-bold' : 'text-slate-400'}">
                <span>66% FinSec</span>
              </div>
              <div class="text-center ${pct >= 100 ? 'text-emerald-600 font-bold' : 'text-slate-400'}">
                <span>100% Disbursed</span>
              </div>
            </div>
          </div>

          <!-- Purpose -->
          <div class="text-xs text-slate-600">
            <strong>Purpose:</strong> ${l.purpose_narration || "General Micro-Credit"}
          </div>

          <!-- If Declined: Reason & Contest Button -->
          ${isDeclined ? `
            <div class="p-4 rounded-xl bg-rose-50 border border-rose-200 space-y-3">
              <div class="text-xs text-rose-900">
                <strong>Statutory Reason for Decline:</strong>
                <p class="mt-0.5 text-rose-800">${l.decline_reason || 'Credit risk criteria unfulfilled per SOP.'}</p>
              </div>
              <div class="flex items-center gap-2 pt-1">
                <button type="button" onclick="openLoanAppealModal(${l.id}, '${l.loan_reference}', '${(l.decline_reason || '').replace(/'/g, "\\'")}')" class="px-4 py-2 rounded-xl bg-gradient-to-r from-rose-600 to-indigo-600 hover:from-rose-500 hover:to-indigo-500 text-white font-bold text-xs shadow-md transition flex items-center gap-1.5 active:scale-95">
                  <span>⚖️</span>
                  <span>Contest Decision / File Statutory Appeal</span>
                </button>
              </div>
            </div>
          ` : ''}

        </div>
      `;
    }).join("");

  } catch (err) {
    console.warn("Could not load loans:", err);
    container.innerHTML = `<div class="p-4 text-center text-xs text-rose-500">Failed to load loan applications.</div>`;
  }
}
window.loadMemberLoanApplications = loadMemberLoanApplications;


// -----------------------------------------------------------------------------
// 3. CONTESTED LOAN APPEAL MODAL
// -----------------------------------------------------------------------------
function openLoanAppealModal(loanId, loanRef, declineReason) {
  const modal = document.getElementById("modal-loan-appeal");
  if (!modal) return;

  const idInput = document.getElementById("appeal-loan-id");
  const refDisplay = document.getElementById("appeal-loan-ref");
  const reasonDisplay = document.getElementById("appeal-decline-reason-display");

  if (idInput) idInput.value = loanId;
  if (refDisplay) refDisplay.textContent = loanRef;
  if (reasonDisplay) reasonDisplay.textContent = declineReason || "Stipulated credit criteria not met.";

  const groundsInput = document.getElementById("appeal-contest-grounds");
  if (groundsInput) groundsInput.value = "";
  const fileInput = document.getElementById("appeal-document-file");
  if (fileInput) fileInput.value = "";

  modal.classList.remove("hidden");
}
window.openLoanAppealModal = openLoanAppealModal;

function closeLoanAppealModal() {
  const modal = document.getElementById("modal-loan-appeal");
  if (modal) modal.classList.add("hidden");
}
window.closeLoanAppealModal = closeLoanAppealModal;

async function handleLoanAppealSubmit(e) {
  e.preventDefault();
  if (!currentUser) return;

  const loanId = document.getElementById("appeal-loan-id").value;
  const grounds = document.getElementById("appeal-contest-grounds").value.trim();
  const fileInput = document.getElementById("appeal-document-file");

  if (!grounds) {
    alert("Please provide the statutory grounds for contesting this decision.");
    return;
  }

  let documentUrl = "";

  // 1. Upload supporting evidence file if provided
  if (fileInput && fileInput.files && fileInput.files[0]) {
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", "LOAN_APPEAL_EVIDENCE");
    formData.append("member_id", currentUser.id);

    try {
      const upRes = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData
      });
      if (!upRes.ok) throw new Error("File upload failed");
      const upData = await upRes.json();
      documentUrl = upData.file_url;
    } catch (err) {
      alert("Could not upload evidence document: " + err.message);
      return;
    }
  }

  // 2. Submit appeal
  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/loans/${loanId}/appeal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contest_grounds: grounds,
        supporting_document_url: documentUrl
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert("✅ Appeal submitted successfully! Your case has been routed to the reviewing committee desk for reconsideration.");
      closeLoanAppealModal();
      loadMemberLoanApplications();
    } else {
      alert("Appeal Submission Error: " + (data.detail || "Could not submit appeal"));
    }
  } catch (err) {
    alert("Connection error while submitting appeal.");
  }
}
window.handleLoanAppealSubmit = handleLoanAppealSubmit;


// -----------------------------------------------------------------------------
// 4. EXECUTIVE LOAN PIPELINE & APPEALS DESK (DESK-LOANS)
// -----------------------------------------------------------------------------
async function loadExecutiveLoans() {
  const tbody = document.getElementById("pending-loans-tbody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/loans/pending-review`);
    if (!res.ok) throw new Error("Failed to fetch pending loans");
    const result = await res.json();
    const loans = Array.isArray(result) ? result : (result.data || []);

    const countBadge = document.getElementById("exec-pending-loans-count");
    const tabBadge = document.getElementById("tab-loans-badge");
    if (countBadge) countBadge.textContent = `${loans.length} Applications`;
    if (tabBadge) tabBadge.textContent = loans.length;

    if (!loans || loans.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-400">✅ All loan applications reviewed! No pending pipeline requests.</td></tr>`;
      return;
    }

    tbody.innerHTML = loans.map(l => {
      const pct = l.approval_level_percent || 0;
      const stage = l.current_approval_stage || "CREDIT_COMMITTEE";
      const principal = parseFloat(l.principal_amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
      const monthly = parseFloat(l.monthly_installment || l.monthly_repayment_ngn || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
      const tenure = l.tenure_months || l.repayment_months || 6;
      const prodName = l.product_name || "Ordinary loan (*2 of savings)";

      const guarantorsHtml = (l.guarantors && l.guarantors.length > 0)
        ? l.guarantors.map(g => `
            <div class="relative group inline-block m-0.5">
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-100 hover:bg-indigo-100 text-slate-800 border border-slate-200 cursor-pointer transition shadow-xs">
                <span class="text-indigo-600">👤</span>
                <span>${g.first_name} ${g.last_name}</span>
                <span class="font-mono text-[10px] text-indigo-700 bg-white px-1.5 py-0.5 rounded border border-slate-200">₦${parseFloat(g.guaranteed_amount || 0).toLocaleString()}</span>
              </span>
              <!-- Tooltip Hover: Shows Total Savings of the Guarantor -->
              <div class="hidden group-hover:block absolute z-50 bottom-full left-0 mb-2 w-72 p-3.5 bg-slate-950 text-white rounded-2xl shadow-2xl border border-slate-700 text-xs pointer-events-none transform transition duration-150">
                <div class="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
                  <div>
                    <div class="font-bold text-amber-300 text-xs">${g.first_name} ${g.last_name}</div>
                    <span class="text-[10px] font-mono text-slate-400">${g.member_code}</span>
                  </div>
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${g.is_adequate ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'}">
                    ${g.is_adequate ? 'Adequate' : 'Deficit'}
                  </span>
                </div>
                <div class="space-y-1.5 text-[11px]">
                  <div class="flex justify-between items-center bg-slate-900 p-2 rounded-lg border border-slate-800">
                    <span class="text-slate-400">Total Savings:</span>
                    <span class="font-bold font-mono text-emerald-400 text-sm">₦${parseFloat(g.total_savings || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                  </div>
                  <div class="flex justify-between items-center px-1">
                    <span class="text-slate-400">Available Savings:</span>
                    <span class="font-mono text-slate-200">₦${parseFloat(g.available_savings || g.total_savings || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                  </div>
                  <div class="flex justify-between items-center px-1">
                    <span class="text-slate-400">Guaranteed Amount:</span>
                    <span class="font-bold font-mono text-indigo-300">₦${parseFloat(g.guaranteed_amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                  </div>
                  <div class="pt-1.5 border-t border-slate-800 text-[10px] flex items-center justify-between">
                    <span class="text-slate-400">Collateral Coverage:</span>
                    <span class="font-bold ${g.is_adequate ? 'text-emerald-400' : 'text-rose-400'}">
                      ${g.is_adequate ? '✅ 100%+ Savings Covered' : '⚠️ Deficit: Less than guaranteed'}
                    </span>
                  </div>
                </div>
                <!-- Arrow Pointer -->
                <div class="w-2.5 h-2.5 bg-slate-950 rotate-45 absolute -bottom-1 left-5 border-r border-b border-slate-700"></div>
              </div>
            </div>
          `).join("")
        : `<span class="text-slate-400 italic text-[11px]">No guarantors</span>`;

      return `
        <tr class="hover:bg-slate-50 transition border-b border-slate-100">
          <td class="p-3 font-mono font-bold text-indigo-900">
            <div>${l.loan_reference}</div>
            <span class="text-[10px] text-slate-400 font-normal">${(l.application_date || '').substring(0, 10)}</span>
          </td>
          <td class="p-3 font-bold text-slate-900">
            <div>${l.first_name} ${l.last_name}</div>
            <span class="text-[10px] font-mono text-slate-400">${l.member_code}</span>
          </td>
          <td class="p-3">
            <div class="font-bold text-slate-900">₦${principal}</div>
            <div class="text-[10px] text-emerald-700 font-bold">${prodName}</div>
            <div class="text-[10px] text-slate-500">${tenure} Mos (₦${monthly}/mo)</div>
          </td>
          <td class="p-3 max-w-xs">
            ${guarantorsHtml}
          </td>
          <td class="p-3">
            <div class="flex items-center gap-1.5">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${pct >= 66 ? 'bg-indigo-100 text-indigo-800' : 'bg-amber-100 text-amber-800'}">
                ${stage} (${pct}%)
              </span>
            </div>
          </td>
          <td class="p-3 text-right space-x-1 whitespace-nowrap">
            ${stage === "CREDIT_COMMITTEE" ? `
              <button onclick="reviewLoanStage(${l.id}, 'APPROVE', false)" class="px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-[10px] transition shadow-sm">
                Pass Stage 1 (33%)
              </button>
            ` : stage === "FINANCIAL_SECRETARY" ? `
              <button onclick="reviewLoanStage(${l.id}, 'APPROVE', false)" class="px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-[10px] transition shadow-sm">
                Pass Stage 2 (66%)
              </button>
            ` : `
              <button onclick="reviewLoanStage(${l.id}, 'APPROVE', false)" class="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[10px] transition shadow-sm">
                Disburse (100%)
              </button>
            `}

            <!-- Presidential Superior Override (100% Direct Disbursement) -->
            <button onclick="reviewLoanStage(${l.id}, 'APPROVE', true)" class="px-2 py-1 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-black text-[10px] transition shadow-sm" title="Presidential / Super Admin Superior Override to 100% direct disbursement">
              👑 Override 100%
            </button>

            <button onclick="reviewLoanStage(${l.id}, 'DECLINE', false)" class="px-2 py-1 rounded-lg bg-slate-200 hover:bg-rose-100 hover:text-rose-700 text-slate-700 font-bold text-[10px] transition">
              Decline
            </button>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.warn("Could not load executive loans:", err);
    tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-rose-500">Error loading loans pipeline.</td></tr>`;
  }
}
window.loadExecutiveLoans = loadExecutiveLoans;

async function reviewLoanStage(loanId, action, override) {
  let comment = "";
  if (action === "DECLINE") {
    comment = prompt("Enter mandatory statutory reason for declining this loan application:");
    if (!comment) return;
  } else {
    comment = prompt(override 
      ? "Enter Presidential Superior Override justification (Immediate 100% Disbursement):" 
      : "Enter committee vetting comments (optional):") || (override ? "Presidential Superior Override" : "Approved per Bye-Laws");
  }

  try {
    const res = await fetch(`${API_BASE_URL}/admin/loans/${loanId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: action,
        comments: comment,
        is_president_override: Boolean(override),
        presidential_override: Boolean(override)
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert(`✅ Action Executed!\n${data.message}`);
      loadExecutiveLoans();
      loadExecutiveMetrics();
    } else {
      alert("Error: " + (data.detail || "Review failed"));
    }
  } catch (err) {
    alert("Connection error while reviewing loan stage.");
  }
}
window.reviewLoanStage = reviewLoanStage;

async function loadExecutiveLoanAppeals() {
  const tbody = document.getElementById("loan-appeals-tbody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/loan-appeals`);
    if (!res.ok) throw new Error("Could not load appeals");
    const appeals = await res.json();

    if (!appeals || appeals.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-400">No contested loan decisions or appeals on record.</td></tr>`;
      return;
    }

    tbody.innerHTML = appeals.map(a => `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100">
        <td class="p-3 font-mono font-bold text-slate-800">${a.appeal_reference}</td>
        <td class="p-3 font-bold text-slate-900">
          <div>${a.first_name} ${a.last_name}</div>
          <span class="text-[10px] font-mono text-indigo-700">${a.loan_reference}</span>
        </td>
        <td class="p-3 text-slate-600 max-w-xs">
          <div class="text-rose-700 font-semibold text-[11px]">${a.original_decline_reason || 'N/A'}</div>
          <div class="text-[10px] text-slate-400">By: ${a.declined_by_role || 'Executive'}</div>
        </td>
        <td class="p-3 text-slate-700 max-w-xs">
          <p class="text-xs">${a.contest_grounds}</p>
          ${a.supporting_document_url ? `
            <div class="mt-1">
              <a href="${a.supporting_document_url}" target="_blank" class="text-[10px] font-bold text-indigo-600 hover:underline flex items-center gap-1">
                <span>📎</span><span>Open Attached Proof</span>
              </a>
            </div>
          ` : ''}
        </td>
        <td class="p-3">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${a.status === 'PENDING' ? 'bg-amber-100 text-amber-800' : a.status === 'OVERTURNED_APPROVED' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'}">
            ${a.status}
          </span>
        </td>
        <td class="p-3 text-right space-x-1">
          ${a.status === 'PENDING' ? `
            <button onclick="resolveLoanAppeal(${a.id}, 'OVERTURNED_APPROVED')" class="px-2 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[10px] transition shadow-sm">
              Overturn &amp; Disburse
            </button>
            <button onclick="resolveLoanAppeal(${a.id}, 'UPHELD_DECLINED')" class="px-2 py-1 rounded-lg bg-slate-200 hover:bg-rose-100 hover:text-rose-700 text-slate-700 font-bold text-[10px] transition">
              Uphold Decline
            </button>
          ` : `
            <span class="text-[10px] text-slate-400 font-mono">Resolved</span>
          `}
        </td>
      </tr>
    `).join("");

  } catch (err) {
    console.warn("Could not load appeals:", err);
    tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-rose-500">Error loading appeals queue.</td></tr>`;
  }
}
window.loadExecutiveLoanAppeals = loadExecutiveLoanAppeals;

async function resolveLoanAppeal(appealId, resolution) {
  const notes = prompt(`Enter official resolution findings (${resolution}):`);
  if (!notes) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/loan-appeals/${appealId}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resolution: resolution,
        resolution_notes: notes,
        officer_id: currentUser ? currentUser.id : 1
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert("✅ Appeal resolution recorded!");
      loadExecutiveLoanAppeals();
      loadExecutiveLoans();
    } else {
      alert("Error: " + (data.detail || "Could not resolve appeal"));
    }
  } catch (err) {
    alert("Connection error occurred while resolving appeal.");
  }
}
window.resolveLoanAppeal = resolveLoanAppeal;


// -----------------------------------------------------------------------------
// 5. POLARIS BANK MANUAL TRANSFER LOGGING & TREASURY RECONCILIATION
// -----------------------------------------------------------------------------
function openLogManualBankPaymentModal() {
  const modal = document.getElementById("modal-log-bank-payment");
  if (!modal) return;
  const memberCodeInput = document.getElementById("manual-pay-member-code");
  const dateInput = document.getElementById("manual-pay-date");

  if (memberCodeInput && currentUser) memberCodeInput.value = currentUser.member_code || "";
  if (dateInput) dateInput.value = new Date().toISOString().substring(0, 10);

  modal.classList.remove("hidden");
}
window.openLogManualBankPaymentModal = openLogManualBankPaymentModal;

function closeLogManualBankPaymentModal() {
  const modal = document.getElementById("modal-log-bank-payment");
  if (modal) modal.classList.add("hidden");
}
window.closeLogManualBankPaymentModal = closeLogManualBankPaymentModal;

async function handleManualBankPaymentSubmit(e) {
  e.preventDefault();
  if (!currentUser || !currentUser.id) return;

  const amount = parseFloat(document.getElementById("manual-pay-amount").value);
  const bankRef = document.getElementById("manual-pay-bank-ref").value.trim();
  const paymentDate = document.getElementById("manual-pay-date").value;
  const tellerNarration = document.getElementById("manual-pay-narration").value.trim();
  const fileInput = document.getElementById("manual-pay-receipt-file");

  let receiptUrl = "";

  if (fileInput && fileInput.files && fileInput.files[0]) {
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", "POLARIS_TELLER_RECEIPT");
    formData.append("member_id", currentUser.id);

    try {
      const upRes = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData
      });
      if (!upRes.ok) throw new Error("Receipt upload failed");
      const upData = await upRes.json();
      receiptUrl = upData.file_url;
    } catch (err) {
      alert("Could not upload teller receipt: " + err.message);
      return;
    }
  }

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/manual-payments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        amount: amount,
        bank_reference: bankRef,
        payment_date: paymentDate,
        teller_narration: tellerNarration,
        receipt_document_url: receiptUrl
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert(`✅ Transfer Logged Successfully!\nReference: ${data.payment_reference}\nTreasury Officers (FinSec, Treasurer) have received notification for auto-waterfall verification.`);
      closeLogManualBankPaymentModal();
      document.getElementById("form-log-manual-payment").reset();
    } else {
      alert("Error logging payment: " + (data.detail || "Failed"));
    }
  } catch (err) {
    alert("Connection error while logging transfer.");
  }
}
window.handleManualBankPaymentSubmit = handleManualBankPaymentSubmit;

async function loadPendingManualPayments() {
  const tbody = document.getElementById("pending-manual-payments-tbody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/manual-payments/pending`);
    if (!res.ok) throw new Error("Could not load pending manual payments");
    const payments = await res.json();

    const countBadge = document.getElementById("exec-pending-payments-count");
    const tabBadge = document.getElementById("tab-polaris-badge");
    if (countBadge) countBadge.textContent = `${payments.length} Pending Transfers`;
    if (tabBadge) tabBadge.textContent = payments.length;

    if (!payments || payments.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-400">✅ All Polaris manual bank transfers reconciled! No pending items.</td></tr>`;
      return;
    }

    tbody.innerHTML = payments.map(p => {
      const amount = parseFloat(p.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 });
      return `
        <tr class="hover:bg-slate-50 transition border-b border-slate-100">
          <td class="p-3 font-mono font-bold text-amber-900">${p.payment_reference}</td>
          <td class="p-3 font-bold text-slate-900">
            <div>${p.first_name} ${p.last_name}</div>
            <span class="text-[10px] font-mono text-slate-400">${p.member_code}</span>
          </td>
          <td class="p-3">
            <div class="font-bold text-emerald-700">₦${amount}</div>
            <div class="text-[10px] text-slate-500">${(p.payment_date || '').substring(0, 10)}</div>
          </td>
          <td class="p-3 font-mono text-slate-700">${p.bank_reference || 'N/A'}</td>
          <td class="p-3">
            ${p.receipt_document_url ? `
              <a href="${p.receipt_document_url}" target="_blank" class="px-2.5 py-1 rounded bg-indigo-50 border border-indigo-200 text-indigo-700 hover:underline text-[10px] font-bold inline-flex items-center gap-1">
                <span>🧾</span><span>View Receipt</span>
              </a>
            ` : '<span class="text-slate-400 text-[10px]">No file</span>'}
          </td>
          <td class="p-3 text-right space-x-1">
            <button onclick="verifyManualBankPayment(${p.id})" class="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[10px] transition shadow-sm">
              ✅ Verify &amp; Waterfall
            </button>
            <button onclick="rejectManualBankPayment(${p.id})" class="px-2 py-1 rounded-lg bg-slate-200 hover:bg-rose-100 hover:text-rose-700 text-slate-700 font-bold text-[10px] transition">
              Reject
            </button>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.warn("Could not load manual payments:", err);
    tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-rose-500">Error loading pending payments queue.</td></tr>`;
  }
}
window.loadPendingManualPayments = loadPendingManualPayments;

async function verifyManualBankPayment(paymentId) {
  if (!confirm("Confirm Polaris bank deposit verification? This will automatically distribute funds via the statutory waterfall (Ordinary Savings, Shares, Welfare).")) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/manual-payments/${paymentId}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        officer_id: currentUser ? currentUser.id : 1,
        officer_notes: "Polaris Bank branch deposit verified by Treasury"
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert("✅ Transfer Verified & Distributed successfully!");
      loadPendingManualPayments();
      loadExecutiveMetrics();
    } else {
      alert("Verification Error: " + (data.detail || "Failed"));
    }
  } catch (err) {
    alert("Connection error while verifying bank transfer.");
  }
}
window.verifyManualBankPayment = verifyManualBankPayment;

async function rejectManualBankPayment(paymentId) {
  const reason = prompt("Enter statutory reason for rejecting this deposit receipt:");
  if (!reason) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/manual-payments/${paymentId}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        officer_id: currentUser ? currentUser.id : 1,
        rejection_reason: reason
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert("Transfer rejected.");
      loadPendingManualPayments();
    } else {
      alert("Rejection Error: " + (data.detail || "Failed"));
    }
  } catch (err) {
    alert("Connection error while rejecting deposit.");
  }
}
window.rejectManualBankPayment = rejectManualBankPayment;

async function populateDirectCreditMembers() {
  const select = document.getElementById("direct-credit-member-id");
  if (!select) return;

  try {
    const res = await fetch(`${API_BASE_URL}/members`);
    if (res.ok) {
      const members = await res.json();
      select.innerHTML = '<option value="">Select Cooperator...</option>' + 
        members.map(m => `<option value="${m.id}">${m.first_name} ${m.last_name} (${m.member_code})</option>`).join("");
    }
  } catch (e) {
    console.warn("Could not populate members for direct credit:", e);
  }
}
window.populateDirectCreditMembers = populateDirectCreditMembers;

async function handleDirectCreditSubmit(e) {
  e.preventDefault();
  const memberId = parseInt(document.getElementById("direct-credit-member-id").value);
  const destAccount = document.getElementById("direct-credit-dest-account").value;
  const amount = parseFloat(document.getElementById("direct-credit-amount").value);
  const bankRef = document.getElementById("direct-credit-bank-ref").value.trim();
  const narration = document.getElementById("direct-credit-narration").value.trim();

  if (!confirm(`Confirm posting direct credit of ₦${amount.toLocaleString()} to ${destAccount}?`)) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/manual-payments/direct-credit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        member_id: memberId,
        destination_account: destAccount,
        amount: amount,
        bank_reference: bankRef,
        narration: narration,
        officer_id: currentUser ? currentUser.id : 1
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert("✅ Direct account credit posted and journal entries created!");
      document.getElementById("form-direct-credit").reset();
      loadExecutiveMetrics();
    } else {
      alert("Credit Error: " + (data.detail || "Failed"));
    }
  } catch (err) {
    alert("Connection error while posting direct credit.");
  }
}
window.handleDirectCreditSubmit = handleDirectCreditSubmit;

// -----------------------------------------------------------------------------
// DIRECT EXECUTIVE DEBIT & OUTWARD BANK PAYOUT DESK (DYNAMIC BANK CHARGES)
// -----------------------------------------------------------------------------
async function populateDirectDebitMembers() {
  const select = document.getElementById("direct-debit-member-id");
  if (!select) return;

  try {
    const res = await fetch(`${API_BASE_URL}/members`);
    if (res.ok) {
      const data = await res.json();
      const members = Array.isArray(data) ? data : (data.data || []);
      select.innerHTML = '<option value="">Select Cooperator...</option>' + 
        members.map(m => `<option value="${m.id}">${m.first_name} ${m.last_name} (${m.member_code})</option>`).join("");
    }
  } catch (e) {
    console.warn("Could not populate members for direct debit:", e);
  }
}
window.populateDirectDebitMembers = populateDirectDebitMembers;

async function updateDirectDebitMemberBalance() {
  const select = document.getElementById("direct-debit-member-id");
  const balSpan = document.getElementById("direct-debit-member-bal");
  if (!select || !balSpan) return;
  const mId = select.value;
  if (!mId) {
    balSpan.textContent = "";
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/members/${mId}/profile`);
    if (res.ok) {
      const data = await res.json();
      const profile = data.data || data;
      const savBal = profile.savings_balance || profile.savings || 0;
      balSpan.textContent = `Ordinary Savings Balance: ₦${parseFloat(savBal).toLocaleString('en-NG', {minimumFractionDigits: 2})}`;
    }
  } catch (e) {
    balSpan.textContent = "";
  }
}
window.updateDirectDebitMemberBalance = updateDirectDebitMemberBalance;

let debitPreviewTimer = null;
async function calculateDebitChargesPreview() {
  clearTimeout(debitPreviewTimer);
  debitPreviewTimer = setTimeout(async () => {
    const amtInput = document.getElementById("direct-debit-amount");
    const previewBox = document.getElementById("direct-debit-charges-preview");
    if (!amtInput || !previewBox) return;

    const amt = parseFloat(amtInput.value);
    if (!amt || amt <= 0) {
      previewBox.classList.add("hidden");
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/accounting/bank-debit-charges?amount=${amt}`);
      if (res.ok) {
        const body = await res.json();
        const c = body.data || body;
        previewBox.classList.remove("hidden");
        document.getElementById("preview-charges-bearer").textContent = `BEARER: ${c.charges_bearer}`;
        document.getElementById("preview-gross-amt").textContent = `₦${c.gross_amount.toLocaleString('en-NG', {minimumFractionDigits: 2})}`;
        document.getElementById("preview-camf-amt").textContent = `₦${c.camf_amount.toLocaleString('en-NG', {minimumFractionDigits: 2})}`;
        document.getElementById("preview-stamp-amt").textContent = `₦${c.stamp_duty_amount.toLocaleString('en-NG', {minimumFractionDigits: 2})}`;
        document.getElementById("preview-vat-amt").textContent = `₦${c.vat_amount.toLocaleString('en-NG', {minimumFractionDigits: 2})}`;
        document.getElementById("preview-total-charges").textContent = `₦${c.total_bank_charges.toLocaleString('en-NG', {minimumFractionDigits: 2})}`;
        document.getElementById("preview-total-outflow").textContent = `₦${c.total_debit_from_polaris.toLocaleString('en-NG', {minimumFractionDigits: 2})}`;
      }
    } catch (e) {
      console.warn("Error calculating bank debit charges preview:", e);
    }
  }, 250);
}
window.calculateDebitChargesPreview = calculateDebitChargesPreview;

async function handleDirectDebitSubmit(e) {
  e.preventDefault();
  const memberId = parseInt(document.getElementById("direct-debit-member-id").value);
  const category = document.getElementById("direct-debit-category").value;
  const amount = parseFloat(document.getElementById("direct-debit-amount").value);
  const bankName = (document.getElementById("direct-debit-bank-name")?.value || "").trim();
  const accountNumber = (document.getElementById("direct-debit-account-number")?.value || "").trim();
  const narration = document.getElementById("direct-debit-narration").value.trim();

  if (!memberId || !amount || amount <= 0 || !narration) {
    alert("Please fill in all mandatory fields with valid values.");
    return;
  }

  if (!confirm(`Confirm disbursing direct debit payout of ₦${amount.toLocaleString()} from ${category}? Polaris Bank debit charges will be automatically posted.`)) return;

  const btn = document.getElementById("btn-submit-direct-debit");
  if (btn) btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/manual-payments/direct-debit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        member_id: memberId,
        amount: amount,
        debit_category: category,
        narration: narration,
        bank_name: bankName || null,
        account_number: accountNumber || null
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert(`✅ Direct debit payout posted successfully! Net Payout: ₦${data.net_payout.toLocaleString('en-NG', {minimumFractionDigits: 2})} (Bank Charges: ₦${data.bank_charges.total_bank_charges.toLocaleString('en-NG', {minimumFractionDigits: 2})})`);
      document.getElementById("form-direct-debit").reset();
      document.getElementById("direct-debit-charges-preview").classList.add("hidden");
      document.getElementById("direct-debit-member-bal").textContent = "";
      if (typeof loadExecutiveMetrics === "function") loadExecutiveMetrics();
    } else {
      alert("Debit Error: " + (data.detail || "Failed to post payout"));
    }
  } catch (err) {
    alert("Connection error while posting direct debit payout.");
  } finally {
    if (btn) btn.disabled = false;
  }
}
window.handleDirectDebitSubmit = handleDirectDebitSubmit;


// -----------------------------------------------------------------------------
// 6. PAYMENT ADVICE MODIFICATION DESK
// -----------------------------------------------------------------------------
async function loadFinancialDeskAdvices() {
  const tbody = document.getElementById("exec-advices-tbody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE_URL}/members`);
    if (!res.ok) throw new Error("Could not load members");
    const members = await res.json();

    tbody.innerHTML = members.slice(0, 15).map(m => {
      const tierMap = { STANDARD: 25000, PLUS: 50000, PREMIUM: 100000 };
      const total = tierMap[m.contribution_tier] || 25000;
      const welfare = 1000;
      const shares = Math.round(total * 0.1);
      const savings = total - shares - welfare;

      return `
        <tr class="hover:bg-slate-50 transition border-b border-slate-100">
          <td class="p-3 font-mono text-indigo-900 font-bold">ADV-${m.id}-2026-10</td>
          <td class="p-3 font-bold text-slate-900">
            <div>${m.first_name} ${m.last_name}</div>
            <span class="text-[10px] font-mono text-slate-400">${m.member_code} &bull; ${m.contribution_tier}</span>
          </td>
          <td class="p-3 font-mono font-bold text-slate-800">₦${savings.toLocaleString()}</td>
          <td class="p-3 font-mono font-bold text-slate-800">₦${shares.toLocaleString()}</td>
          <td class="p-3 font-mono font-bold text-slate-800">₦${welfare.toLocaleString()}</td>
          <td class="p-3 font-mono font-bold text-emerald-700">₦${total.toLocaleString()}</td>
          <td class="p-3"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">UNPAID</span></td>
          <td class="p-3 text-right">
            <button onclick="openModifyAdviceModal(${m.id}, '${m.first_name} ${m.last_name}', ${savings}, ${shares}, ${welfare})" class="px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-[10px] transition shadow-sm">
              ✏️ Modify
            </button>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.warn("Could not load advices:", err);
    tbody.innerHTML = `<tr><td colspan="8" class="p-4 text-center text-rose-500">Error loading payment advices.</td></tr>`;
  }
}
window.loadFinancialDeskAdvices = loadFinancialDeskAdvices;

function openModifyAdviceModal(adviceId, memberName, currSavings, currShares, currWelfare, currLoan, currReg) {
  const modal = document.getElementById("modal-modify-advice");
  if (!modal) return;

  const idInput = document.getElementById("modify-advice-id");
  const memberDisplay = document.getElementById("modify-advice-member-name");
  const savingsInput = document.getElementById("mod-advice-savings") || document.getElementById("modify-advice-savings");
  const sharesInput = document.getElementById("mod-advice-shares") || document.getElementById("modify-advice-shares");
  const welfareInput = document.getElementById("mod-advice-welfare") || document.getElementById("modify-advice-welfare");
  const loanInput = document.getElementById("mod-advice-loan");
  const targetsInput = document.getElementById("mod-advice-targets");
  const finesInput = document.getElementById("mod-advice-fines");
  const regInput = document.getElementById("mod-advice-registration");

  if (idInput) idInput.value = adviceId || 1;
  if (memberDisplay) memberDisplay.textContent = memberName || "Cooperator";
  if (savingsInput) savingsInput.value = currSavings !== undefined ? currSavings : 21500;
  if (sharesInput) sharesInput.value = currShares !== undefined ? currShares : 2500;
  if (welfareInput) welfareInput.value = currWelfare !== undefined ? currWelfare : 1000;
  if (loanInput) loanInput.value = currLoan !== undefined ? currLoan : 0;
  if (targetsInput) targetsInput.value = 0;
  if (finesInput) finesInput.value = 0;
  if (regInput) regInput.value = currReg !== undefined ? currReg : 0;

  modal.classList.remove("hidden");
}
window.openModifyAdviceModal = openModifyAdviceModal;

function closeModifyAdviceModal() {
  const modal = document.getElementById("modal-modify-advice");
  if (modal) modal.classList.add("hidden");
}
window.closeModifyAdviceModal = closeModifyAdviceModal;

async function handleModifyAdviceSubmit(e) {
  e.preventDefault();
  const token = localStorage.getItem("token") || (currentUser && currentUser.token);
  const adviceId = document.getElementById("modify-advice-id").value;
  const savings = parseFloat((document.getElementById("mod-advice-savings") || document.getElementById("modify-advice-savings") || {}).value || 0);
  const shares = parseFloat((document.getElementById("mod-advice-shares") || document.getElementById("modify-advice-shares") || {}).value || 0);
  const welfare = parseFloat((document.getElementById("mod-advice-welfare") || document.getElementById("modify-advice-welfare") || {}).value || 0);
  const loan = parseFloat((document.getElementById("mod-advice-loan") || {}).value || 0);
  const targets = parseFloat((document.getElementById("mod-advice-targets") || {}).value || 0);
  const fines = parseFloat((document.getElementById("mod-advice-fines") || {}).value || 0);
  const regFee = parseFloat((document.getElementById("mod-advice-registration") || {}).value || 0);

  const scopeRadio = document.querySelector('input[name="advice-scope"]:checked');
  const scope = scopeRadio ? scopeRadio.value : ((document.getElementById("modify-advice-scope") || {}).value || "THIS_MONTH_ONLY");
  const justification = ((document.getElementById("mod-advice-justification") || document.getElementById("modify-advice-justification") || {}).value || "").trim();

  try {
    const res = await fetch(`${API_BASE_URL}/admin/payment-advices/${adviceId}/modify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "Authorization": `Bearer ${token}` } : {})
      },
      body: JSON.stringify({
        scope: scope,
        statutory_justification: justification,
        amount_regular_savings: savings,
        amount_share_capital: shares,
        amount_welfare: welfare,
        amount_loan_repayment: loan,
        amount_target_savings: targets,
        amount_fines: fines,
        amount_registration_fee: regFee
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert("✅ Payment advice modified successfully and logged in forensic audit trail.");
      closeModifyAdviceModal();
      loadFinancialDeskAdvices();
    } else {
      alert("Modification Error: " + (data.detail || "Failed"));
    }
  } catch (err) {
    alert("Connection error while modifying payment advice.");
  }
}
window.handleModifyAdviceSubmit = handleModifyAdviceSubmit;


// -----------------------------------------------------------------------------
// 7. DYNAMIC RBAC & OPERATIONAL ROLE ALLOCATION (DESK-RBAC)
// -----------------------------------------------------------------------------
let cachedSystemRoles = [];
let cachedSystemPermissions = [];

async function loadRbacDesk() {
  const rolesContainer = document.getElementById("rbac-roles-grid");
  const roleSelect = document.getElementById("rbac-assign-role-id");
  const memberSelect = document.getElementById("rbac-assign-member-id");

  try {
    // 1. Fetch Roles
    const rolesRes = await fetch(`${API_BASE_URL}/admin/roles`);
    if (rolesRes.ok) {
      const rolesJson = await rolesRes.json();
      cachedSystemRoles = Array.isArray(rolesJson) ? rolesJson : (rolesJson.data || []);

      if (rolesContainer) {
        if (cachedSystemRoles.length === 0) {
          rolesContainer.innerHTML = `
            <div class="p-6 rounded-2xl bg-slate-50 border border-slate-200 text-center text-xs text-slate-400 col-span-3">
              No operational roles configured.
            </div>
          `;
        } else {
          rolesContainer.innerHTML = cachedSystemRoles.map(r => `
            <div class="glass-panel p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3.5 hover:shadow-md transition">
              <div class="flex justify-between items-start gap-2">
                <div>
                  <span class="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${r.is_system_role ? 'bg-indigo-100 text-indigo-900 border border-indigo-200' : 'bg-purple-100 text-purple-900 border border-purple-200'}">
                    ${r.is_system_role ? 'Statutory System' : 'Custom Operational'}
                  </span>
                  <h4 class="font-bold text-sm text-wmcNavy-950 mt-1.5">${r.role_name}</h4>
                  <span class="font-mono text-[10px] text-slate-400 block">${r.role_code}</span>
                </div>
                <span class="px-2 py-1 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 whitespace-nowrap">
                  ${r.permission_count || (r.permissions ? r.permissions.length : 0)} Perms
                </span>
              </div>
              <p class="text-xs text-slate-500 leading-relaxed min-h-[32px]">${r.description || 'Statutory cooperative role.'}</p>
              
              <div class="pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs">
                ${!r.is_system_role ? `
                  <div class="flex items-center gap-2 w-full justify-between">
                    <button type="button" onclick="openEditRoleModal(${r.id})" class="px-3 py-1.5 rounded-lg bg-purple-50 hover:bg-purple-100 text-purple-700 font-bold transition flex items-center gap-1 active:scale-95 shadow-xs">
                      <span>✏️</span><span>Modify</span>
                    </button>
                    <button type="button" onclick="handleDeleteRole(${r.id}, '${r.role_name.replace(/'/g, "\\'")}')" class="px-3 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-600 font-bold transition flex items-center gap-1 active:scale-95 shadow-xs">
                      <span>🗑️</span><span>Delete</span>
                    </button>
                  </div>
                ` : `
                  <span class="text-[10px] text-slate-400 font-medium flex items-center gap-1">
                    <span>🔒</span><span>Statutory Protected System Role</span>
                  </span>
                `}
              </div>
            </div>
          `).join("");
        }
      }

      if (roleSelect) {
        roleSelect.innerHTML = '<option value="">Select a role to assign...</option>' + 
          cachedSystemRoles.map(r => `<option value="${r.id}">${r.role_name} (${r.role_code})</option>`).join("");
      }
    } else {
      if (rolesRes.status === 401) {
        if (rolesContainer) {
          rolesContainer.innerHTML = `
            <div class="p-6 rounded-2xl bg-amber-50 border border-amber-200 text-center text-xs text-amber-800 col-span-3">
              ⚠️ Your session has expired. Please <a href="javascript:void(0)" onclick="openLoginModal()" class="font-bold underline text-amber-950 hover:text-amber-800">Sign In Again</a> to load operational roles.
            </div>
          `;
        }
        if (roleSelect) roleSelect.innerHTML = '<option value="">Session expired - please sign in</option>';
      } else if (rolesRes.status === 403) {
        if (rolesContainer) {
          rolesContainer.innerHTML = `
            <div class="p-6 rounded-2xl bg-rose-50 border border-rose-200 text-center text-xs text-rose-700 col-span-3">
              ⚠️ Executive clearance required to view operational roles.
            </div>
          `;
        }
      } else {
        if (rolesContainer) {
          rolesContainer.innerHTML = `
            <div class="p-6 rounded-2xl bg-rose-50 border border-rose-200 text-center text-xs text-rose-700 col-span-3">
              Failed to load roles (Server error ${rolesRes.status}).
            </div>
          `;
        }
      }
    }

    // 2. Fetch Members for assignment dropdown
    if (memberSelect) {
      const memRes = await fetch(`${API_BASE_URL}/members`);
      if (memRes.ok) {
        const memData = await memRes.json();
        const members = Array.isArray(memData) ? memData : (memData.data || memData.members || []);
        memberSelect.innerHTML = '<option value="">Choose a member...</option>' +
          members.map(m => {
            const name = m.full_name || `${m.first_name || ''} ${m.last_name || ''}`.trim() || 'Cooperator';
            return `<option value="${m.id}">${name} (${m.member_code})</option>`;
          }).join("");
      } else {
        if (memRes.status === 401) {
          memberSelect.innerHTML = '<option value="">Session expired - please sign in</option>';
        } else {
          memberSelect.innerHTML = '<option value="">Failed to load cooperator list</option>';
        }
      }
    }

  } catch (err) {
    console.warn("Could not load RBAC desk:", err);
    if (rolesContainer) rolesContainer.innerHTML = `<div class="p-4 text-center text-rose-500 col-span-3">Failed to load roles: ${err.message || 'Network error'}</div>`;
  }
}
window.loadRbacDesk = loadRbacDesk;

async function openCreateRoleModal(roleToEdit = null) {
  const modal = document.getElementById("modal-create-role");
  if (!modal) return;

  const permsContainer = document.getElementById("role-permissions-checklist") || document.getElementById("modal-create-role-permissions-list");
  const editIdInput = document.getElementById("edit-role-id");
  const codeInput = document.getElementById("new-role-code") || document.getElementById("create-role-code");
  const nameInput = document.getElementById("new-role-name") || document.getElementById("create-role-name");
  const descInput = document.getElementById("new-role-desc") || document.getElementById("create-role-desc");
  const titleEl = document.getElementById("modal-role-title");
  const subtitleEl = document.getElementById("modal-role-subtitle");
  const submitTextEl = document.getElementById("btn-save-custom-role-text");

  let activePermKeys = [];
  if (roleToEdit) {
    if (editIdInput) editIdInput.value = roleToEdit.id;
    if (titleEl) titleEl.textContent = `Modify Operational Role: ${roleToEdit.role_name}`;
    if (subtitleEl) subtitleEl.textContent = `Update access rights and assigned permissions for ${roleToEdit.role_code}.`;
    if (codeInput) {
      codeInput.value = roleToEdit.role_code;
      codeInput.disabled = true;
    }
    if (nameInput) nameInput.value = roleToEdit.role_name;
    if (descInput) descInput.value = roleToEdit.description || "";
    if (submitTextEl) submitTextEl.textContent = "Save Changes & Update Permissions";

    if (roleToEdit.permissions && Array.isArray(roleToEdit.permissions)) {
      activePermKeys = roleToEdit.permissions.map(p => typeof p === "string" ? p : (p.perm_key || p.permission_code));
    }
  } else {
    if (editIdInput) editIdInput.value = "";
    if (titleEl) titleEl.textContent = "Create Custom Operational Role";
    if (subtitleEl) subtitleEl.textContent = "Define a new access role and select granular permissions across cooperative modules.";
    if (codeInput) {
      codeInput.value = "";
      codeInput.disabled = false;
    }
    if (nameInput) nameInput.value = "";
    if (descInput) descInput.value = "";
    if (submitTextEl) submitTextEl.textContent = "Create Role & Bind Permissions";
  }

  if (permsContainer) {
    try {
      permsContainer.innerHTML = '<span class="text-slate-400 p-2">Loading permissions matrix...</span>';
      const res = await fetch(`${API_BASE_URL}/admin/permissions`);
      if (res.ok) {
        const permsData = await res.json();
        cachedSystemPermissions = Array.isArray(permsData) ? permsData : (permsData.data || []);
        
        permsContainer.innerHTML = cachedSystemPermissions.map(p => {
          const permKey = p.perm_key || p.permission_code;
          const permName = p.perm_name || p.permission_name || permKey;
          const moduleName = p.module || p.module_name || "GENERAL";
          const desc = p.description || "";
          const isChecked = activePermKeys.includes(permKey);

          return `
            <label class="flex items-start gap-2.5 p-2.5 rounded-xl border border-slate-200 bg-white hover:bg-purple-50/50 hover:border-purple-300 cursor-pointer transition select-none shadow-xs">
              <input type="checkbox" name="role_perms" value="${permKey}" class="mt-0.5 rounded border-slate-300 text-purple-600 focus:ring-purple-500" ${isChecked ? "checked" : ""} />
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between gap-1">
                  <span class="font-bold text-xs text-slate-800 truncate">${permName}</span>
                  <span class="text-[9px] font-black uppercase px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 tracking-wider">${moduleName}</span>
                </div>
                <span class="text-[10px] text-slate-400 font-mono block mt-0.5">${permKey}</span>
                ${desc ? `<p class="text-[10px] text-slate-500 mt-1 leading-snug line-clamp-2">${desc}</p>` : ''}
              </div>
            </label>
          `;
        }).join("");
      } else {
        permsContainer.innerHTML = '<span class="text-rose-500 p-2">Failed to load permissions matrix.</span>';
      }
    } catch (e) {
      console.warn("Could not load permissions list:", e);
      permsContainer.innerHTML = '<span class="text-rose-500 p-2">Connection error loading permissions.</span>';
    }
  }

  modal.classList.remove("hidden");
}
window.openCreateRoleModal = openCreateRoleModal;

function openEditRoleModal(roleId) {
  const role = cachedSystemRoles.find(r => r.id === roleId);
  if (!role) {
    alert("Role not found in current cache.");
    return;
  }
  openCreateRoleModal(role);
}
window.openEditRoleModal = openEditRoleModal;

function toggleAllRolePerms(checkAll) {
  const checkboxes = document.querySelectorAll('input[name="role_perms"]');
  checkboxes.forEach(cb => cb.checked = checkAll);
}
window.toggleAllRolePerms = toggleAllRolePerms;

async function handleDeleteRole(roleId, roleName) {
  if (!confirm(`⚠️ Are you sure you want to permanently delete the custom operational role '${roleName}'?\n\nAny cooperator currently assigned this role will immediately forfeit its specialized access capabilities.`)) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/admin/roles/${roleId}`, {
      method: "DELETE"
    });
    const data = await res.json();
    if (res.ok) {
      alert(`✅ Custom role '${roleName}' deleted successfully.`);
      loadRbacDesk();
    } else {
      alert(`Error deleting role: ${data.detail || "Action failed."}`);
    }
  } catch (err) {
    alert("Connection error while deleting custom role.");
  }
}
window.handleDeleteRole = handleDeleteRole;

function closeCreateRoleModal() {
  const modal = document.getElementById("modal-create-role");
  if (modal) modal.classList.add("hidden");
  const form = document.getElementById("form-create-role");
  if (form) form.reset();
  const editIdInput = document.getElementById("edit-role-id");
  if (editIdInput) editIdInput.value = "";
  const codeInput = document.getElementById("new-role-code") || document.getElementById("create-role-code");
  if (codeInput) codeInput.disabled = false;
}
window.closeCreateRoleModal = closeCreateRoleModal;

async function handleCreateRoleSubmit(e) {
  e.preventDefault();
  const editIdInput = document.getElementById("edit-role-id");
  const editRoleId = editIdInput && editIdInput.value ? parseInt(editIdInput.value) : null;

  const codeInput = document.getElementById("new-role-code") || document.getElementById("create-role-code");
  const nameInput = document.getElementById("new-role-name") || document.getElementById("create-role-name");
  const descInput = document.getElementById("new-role-desc") || document.getElementById("create-role-desc");

  const code = codeInput ? codeInput.value.trim().toUpperCase() : "";
  const name = nameInput ? nameInput.value.trim() : "";
  const desc = descInput ? descInput.value.trim() : "";

  const checkedCheckboxes = document.querySelectorAll('input[name="role_perms"]:checked');
  const perms = Array.from(checkedCheckboxes).map(c => c.value);

  if (!editRoleId && !code) {
    alert("Role Code is required.");
    return;
  }
  if (!name) {
    alert("Role Name is required.");
    return;
  }
  if (perms.length === 0) {
    alert("Please select at least one permission for this operational role.");
    return;
  }

  try {
    let res;
    if (editRoleId) {
      res = await fetch(`${API_BASE_URL}/admin/roles/${editRoleId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role_name: name,
          description: desc,
          permission_keys: perms,
          permission_codes: perms
        })
      });
    } else {
      res = await fetch(`${API_BASE_URL}/admin/roles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role_code: code,
          role_name: name,
          description: desc,
          permission_keys: perms,
          permission_codes: perms
        })
      });
    }

    const data = await res.json();
    if (res.ok) {
      const actionMsg = editRoleId ? "updated" : "created";
      alert(`✅ Operational Role '${name}' ${actionMsg} successfully with ${perms.length} permissions!`);
      closeCreateRoleModal();
      loadRbacDesk();
    } else {
      alert("Role Save Error: " + (data.detail || "Failed"));
    }
  } catch (err) {
    alert("Connection error while saving custom role.");
  }
}
window.handleCreateRoleSubmit = handleCreateRoleSubmit;

async function loadMemberRoleBadges(memberId) {
  const container = document.getElementById("rbac-member-roles-list");
  if (!container || !memberId) return;

  try {
    const res = await fetch(`${API_BASE_URL}/members/${memberId}/roles`);
    if (res.ok) {
      const rolesData = await res.json();
      const roles = Array.isArray(rolesData) ? rolesData : (rolesData.data || []);
      if (!roles || roles.length === 0) {
        container.innerHTML = `<span class="text-slate-400 italic">No specialized operational roles assigned (Standard Cooperator).</span>`;
        return;
      }

      container.innerHTML = roles.map(r => `
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-purple-100 text-purple-900 border border-purple-200">
          <span>🛡️ ${r.role_name}</span>
          <button type="button" onclick="revokeRoleFromMember(${memberId}, ${r.id})" class="text-rose-600 hover:text-rose-800 font-bold ml-1" title="Revoke role">✕</button>
        </span>
      `).join("");
    }
  } catch (e) {
    console.warn("Could not load member roles:", e);
  }
}
window.loadMemberRoleBadges = loadMemberRoleBadges;

async function handleAssignRoleClick() {
  const memberId = document.getElementById("rbac-assign-member-id").value;
  const roleId = document.getElementById("rbac-assign-role-id").value;
  const notes = document.getElementById("rbac-assign-notes").value.trim();

  if (!memberId || !roleId) {
    alert("Please select both a cooperator and a role to allocate.");
    return;
  }

  try {
    const assignerId = currentUser && currentUser.id ? currentUser.id : 1;
    const token = localStorage.getItem("wmc_token");
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE_URL}/admin/members/${memberId}/roles`, {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        role_id: parseInt(roleId),
        appointment_notes: notes,
        assigned_by_id: assignerId
      })
    });

    const data = await res.json();
    if (res.ok) {
      alert("✅ Role allocated successfully!");
      document.getElementById("rbac-assign-notes").value = "";
      loadMemberRoleBadges(memberId);
    } else {
      const err = formatApiErrorMessage(data.detail, "Role allocation failed.");
      alert(`⚠️ ${err}`);
    }
  } catch (err) {
    alert("⚠️ Connection error while assigning role.");
  }
}
window.handleAssignRoleClick = handleAssignRoleClick;

async function revokeRoleFromMember(memberId, roleId) {
  if (!confirm("Are you sure you want to revoke this operational role from the cooperator?")) return;

  try {
    const token = localStorage.getItem("wmc_token");
    const headers = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE_URL}/admin/members/${memberId}/roles/${roleId}`, {
      method: "DELETE",
      headers: headers
    });

    if (res.ok) {
      alert("✅ Role revoked successfully.");
      loadMemberRoleBadges(memberId);
    } else {
      const data = await res.json();
      const err = formatApiErrorMessage(data.detail, "Role revocation failed.");
      alert(`⚠️ ${err}`);
    }
  } catch (err) {
    alert("⚠️ Connection error while revoking role.");
  }
}
window.revokeRoleFromMember = revokeRoleFromMember;


// -----------------------------------------------------------------------------
// 8. TAMPER-EVIDENT FORENSIC AUDIT TRAIL (DESK-AUDIT)
// -----------------------------------------------------------------------------
let cachedAuditLogs = [];

async function loadAuditLogs() {
  const tbody = document.getElementById("audit-logs-tbody");
  if (!tbody) return;

  const actionFilter = document.getElementById("audit-filter-action") ? document.getElementById("audit-filter-action").value : "";
  const resourceFilter = document.getElementById("audit-filter-resource") ? document.getElementById("audit-filter-resource").value : "";

  let url = `${API_BASE_URL}/admin/audit-logs?limit=50`;
  if (actionFilter) url += `&action=${encodeURIComponent(actionFilter)}`;
  if (resourceFilter) url += `&resource_type=${encodeURIComponent(resourceFilter)}`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Could not fetch audit logs");
    const resp = await res.json();
    cachedAuditLogs = resp.data?.logs || resp.logs || resp.data || [];

    const countDisplay = document.getElementById("audit-log-count");
    if (countDisplay) countDisplay.textContent = `${resp.data?.total || cachedAuditLogs.length} Events Tracked`;

    if (!cachedAuditLogs || cachedAuditLogs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-400 font-sans">No forensic audit records match your filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = cachedAuditLogs.map(l => `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100">
        <td class="p-3 text-slate-500 whitespace-nowrap">${(l.created_at || '').substring(0, 19).replace('T', ' ')}</td>
        <td class="p-3 font-sans font-bold text-slate-800">
          <div>${l.actor_name || 'System Operator'}</div>
          <span class="text-[10px] text-slate-400 font-mono">${l.actor_code || `USER-${l.user_id || l.actor_id}`}</span>
        </td>
        <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">${l.actor_role || 'SYSTEM'}</span></td>
        <td class="p-3 font-bold text-indigo-900">${l.action}</td>
        <td class="p-3 text-slate-600">${l.resource_type} #${l.resource_id || ''}</td>
        <td class="p-3">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
            ${l.status || 'RECORDED'}
          </span>
        </td>
        <td class="p-3 text-right">
          <button onclick="openAuditDiffModal(${l.id})" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-900 text-white font-sans font-bold text-[10px] transition shadow-sm inline-flex items-center gap-1">
            <span>🔍</span><span>View Diff</span>
          </button>
        </td>
      </tr>
    `).join("");

  } catch (err) {
    console.warn("Could not load audit logs:", err);
    tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-rose-500 font-sans">Failed to load audit trail.</td></tr>`;
  }
}
window.loadAuditLogs = loadAuditLogs;

function openAuditDiffModal(logId) {
  const modal = document.getElementById("modal-view-audit-diff");
  if (!modal) return;

  const log = cachedAuditLogs.find(l => l.id === logId);
  if (!log) return;

  const metaEl = document.getElementById("modal-diff-meta");
  const beforeEl = document.getElementById("modal-diff-before");
  const afterEl = document.getElementById("modal-diff-after");

  if (metaEl) {
    metaEl.innerHTML = `
      <div><strong>Action:</strong> <span class="font-mono text-indigo-700">${log.action}</span></div>
      <div><strong>Resource:</strong> <span class="font-mono">${log.resource_type} #${log.resource_id || ''}</span></div>
      <div><strong>Actor:</strong> ${log.actor_name || 'System'} (${log.actor_role || 'ADMIN'})</div>
      <div><strong>Timestamp:</strong> ${(log.created_at || '').substring(0, 19).replace('T', ' ')}</div>
      <div><strong>Summary:</strong> <span class="text-slate-600">${log.summary || 'N/A'}</span></div>
    `;
  }

  const formatJson = (val) => {
    if (!val) return "null";
    try {
      if (typeof val === "string") val = JSON.parse(val);
      return JSON.stringify(val, null, 2);
    } catch (e) {
      return String(val);
    }
  };

  if (beforeEl) beforeEl.textContent = formatJson(log.details_before || log.before_state_json);
  if (afterEl) afterEl.textContent = formatJson(log.details_after || log.after_state_json);

  modal.classList.remove("hidden");
}
window.openAuditDiffModal = openAuditDiffModal;

function closeAuditDiffModal() {
  const modal = document.getElementById("modal-view-audit-diff");
  if (modal) modal.classList.add("hidden");
}
window.closeAuditDiffModal = closeAuditDiffModal;

function exportAuditLogsCsv() {
  window.open(`${API_BASE_URL}/admin/audit-logs/export`, "_blank");
}
window.exportAuditLogsCsv = exportAuditLogsCsv;


// =============================================================================
// MEMBER OPERATIONS EXTENSIONS: GUARANTOR CONSENT, EXITS & BULK CSV
// =============================================================================

let cachedGuarantorRequests = [];
let activeConsentRequestId = null;
let cachedPendingExits = [];
let activeApproveExitId = null;

// --- 1. GUARANTOR IN-PORTAL DIGITAL CONSENT ---
async function loadIncomingGuarantorRequests() {
  if (!currentUser) return;
  const container = document.getElementById("incoming-guarantor-requests-list");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/guarantor-requests`);
    if (!res.ok) throw new Error("Failed to load guarantor requests.");
    const json = await res.json();
    cachedGuarantorRequests = json.data || [];

    if (cachedGuarantorRequests.length === 0) {
      container.innerHTML = `
        <div class="p-6 rounded-2xl bg-slate-50 border border-slate-200 text-center text-xs text-slate-400">
          You currently have no incoming peer loan guarantee requests or active guarantee liabilities.
        </div>
      `;
      return;
    }

    container.innerHTML = cachedGuarantorRequests.map(req => {
      const isPending = req.consent_status === "PENDING_CONSENT" || req.status === "PENDING_CONSENT";
      const statusBadge = isPending
        ? `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase bg-amber-100 text-amber-800 border border-amber-300">Action Required</span>`
        : (req.consent_status === "ACCEPTED" || req.status === "ACCEPTED"
            ? `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800 border border-emerald-300">Collateral Lien Active</span>`
            : `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-slate-100 text-slate-600">${req.consent_status || req.status}</span>`);

      return `
        <div class="p-5 rounded-2xl border ${isPending ? 'border-amber-300 bg-amber-50/30' : 'border-slate-200 bg-white'} shadow-sm space-y-3">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-200/80">
            <div class="flex items-center gap-2">
              <span class="font-bold text-sm text-wmcNavy-950">${req.borrower_name} (${req.borrower_code})</span>
              ${statusBadge}
            </div>
            <span class="font-mono text-xs text-slate-500 font-bold">${req.loan_reference}</span>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div>
              <span class="text-[10px] text-slate-500 block uppercase">Product</span>
              <strong class="text-slate-800">${req.product_name || 'Ordinary Loan'}</strong>
            </div>
            <div>
              <span class="text-[10px] text-slate-500 block uppercase">Total Facility</span>
              <strong class="text-slate-800">${formatNaira(req.principal_amount)}</strong>
            </div>
            <div>
              <span class="text-[10px] text-amber-700 block uppercase">Requested Guarantee</span>
              <strong class="text-amber-800">${formatNaira(req.guaranteed_amount)}</strong>
            </div>
            <div>
              <span class="text-[10px] text-slate-500 block uppercase">Borrower Savings</span>
              <strong class="text-slate-700">${formatNaira(req.borrower_savings_balance)}</strong>
            </div>
          </div>

          ${isPending ? `
            <div class="pt-2 flex items-center justify-end gap-2 border-t border-slate-200/60">
              <button type="button" onclick="openGuarantorConsentModal(${req.guarantor_request_id || req.id})" class="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-black text-xs shadow transition flex items-center gap-1.5 active:scale-95">
                <span>✍️</span>
                <span>Review &amp; Sign Digital Consent</span>
              </button>
            </div>
          ` : `
            <div class="text-[11px] text-slate-500 flex items-center justify-between pt-1">
              <span>Lien Encumbered: <strong class="text-slate-700 font-mono">${formatNaira(req.lien_encumbered_amount || req.guaranteed_amount)}</strong></span>
              <span>Loan Stage: <strong class="text-indigo-800">${req.current_approval_stage}</strong></span>
            </div>
          `}
        </div>
      `;
    }).join("");

  } catch (err) {
    container.innerHTML = `<div class="p-4 rounded-xl bg-rose-50 text-rose-700 text-xs">${err.message}</div>`;
  }
}
window.loadIncomingGuarantorRequests = loadIncomingGuarantorRequests;

function openGuarantorConsentModal(requestId) {
  const req = cachedGuarantorRequests.find(r => (r.guarantor_request_id || r.id) === requestId);
  if (!req) return;
  activeConsentRequestId = requestId;

  const detailsEl = document.getElementById("guar-consent-details");
  if (detailsEl) {
    detailsEl.innerHTML = `
      <div class="flex justify-between border-b pb-1.5">
        <span class="text-slate-500">Applicant:</span>
        <strong class="text-slate-900">${req.borrower_name} (${req.borrower_code})</strong>
      </div>
      <div class="flex justify-between border-b pb-1.5">
        <span class="text-slate-500">Loan Facility:</span>
        <span class="font-mono">${req.loan_reference} (${req.product_name})</span>
      </div>
      <div class="flex justify-between border-b pb-1.5">
        <span class="text-slate-500">Total Loan Amount:</span>
        <strong class="text-slate-900">${formatNaira(req.principal_amount)}</strong>
      </div>
      <div class="flex justify-between border-b pb-1.5">
        <span class="text-amber-800 font-bold">Guaranteed Collateral Pledge:</span>
        <strong class="text-amber-900 text-sm">${formatNaira(req.guaranteed_amount)}</strong>
      </div>
      <div class="flex justify-between">
        <span class="text-slate-500">Applicant Savings Equity:</span>
        <span class="text-slate-700">${formatNaira(req.borrower_savings_balance)}</span>
      </div>
    `;
  }

  const commentInput = document.getElementById("guar-consent-comment");
  if (commentInput) commentInput.value = "";

  const modal = document.getElementById("modal-guarantor-consent");
  if (modal) modal.classList.remove("hidden");
}
window.openGuarantorConsentModal = openGuarantorConsentModal;

function closeGuarantorConsentModal() {
  const modal = document.getElementById("modal-guarantor-consent");
  if (modal) modal.classList.add("hidden");
  activeConsentRequestId = null;
}
window.closeGuarantorConsentModal = closeGuarantorConsentModal;

async function submitGuarantorDecision(decision) {
  if (!activeConsentRequestId || !currentUser) return;
  const comment = document.getElementById("guar-consent-comment")?.value?.trim() || "";

  if (decision === "DECLINE" && !confirm("Are you sure you want to decline guaranteeing this loan application?")) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/guarantor-requests/${activeConsentRequestId}/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, comments: comment })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to submit decision.");

    alert(data.message || `Decision recorded: ${decision}`);
    closeGuarantorConsentModal();
    loadIncomingGuarantorRequests();
    if (typeof loadMemberSavingsSummary === "function") loadMemberSavingsSummary();
  } catch (err) {
    alert("Error: " + err.message);
  }
}
window.submitGuarantorDecision = submitGuarantorDecision;


// --- 2. COOPERATOR EXIT, WITHDRAWAL & SETTLEMENT DESK ---
async function loadPendingExitsDesk() {
  const tbody = document.getElementById("exec-exits-tbody");
  const badge = document.getElementById("tab-exits-badge");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/exits/pending`);
    if (!res.ok) throw new Error("Failed to load pending exits.");
    const json = await res.json();
    cachedPendingExits = json.data || [];

    if (badge) badge.textContent = cachedPendingExits.length;

    if (cachedPendingExits.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="p-6 text-center text-slate-400">
            No pending cooperator exit requests or withdrawal settlements at this time.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = cachedPendingExits.map(ex => {
      const isCleared = (ex.outstanding_loans_at_exit === 0 && ex.active_guarantor_commitments_count === 0);
      const clearanceBadge = isCleared
        ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">Clear (0 Loans, 0 Guars)</span>`
        : `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800">Blocked: ${formatNaira(ex.outstanding_loans_at_exit)} Loans / ${ex.active_guarantor_commitments_count} Active Guars</span>`;

      return `
        <tr class="hover:bg-slate-50 transition border-b border-slate-100">
          <td class="p-3">
            <strong class="text-slate-900 block">${ex.first_name} ${ex.last_name}</strong>
            <span class="font-mono text-slate-500 text-[11px]">${ex.member_code} (Exit #${ex.id})</span>
          </td>
          <td class="p-3">
            <span class="font-bold text-slate-800 block">${ex.exit_type}</span>
            <span class="text-[11px] text-slate-500">Notice: ${ex.notice_date} &bull; Expiry: ${ex.statutory_notice_expiry_date || 'N/A'}</span>
          </td>
          <td class="p-3 text-slate-700">
            <div>Savings: <strong>${formatNaira(ex.total_savings_at_exit + ex.total_target_savings_at_exit)}</strong></div>
            <div>Shares: <strong>${formatNaira(ex.total_shares_at_exit)}</strong></div>
          </td>
          <td class="p-3">
            ${clearanceBadge}
          </td>
          <td class="p-3">
            <strong class="text-emerald-700 text-sm font-mono block">${formatNaira(ex.net_refund_amount)}</strong>
            <span class="text-[10px] text-slate-400">Exit Fee: -${formatNaira(ex.exit_processing_fee)}</span>
          </td>
          <td class="p-3 text-right">
            <button type="button" onclick="openApproveExitModal(${ex.id})" class="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs shadow-sm transition active:scale-95">
              Approve Settlement
            </button>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-rose-600">${err.message}</td></tr>`;
  }
}
window.loadPendingExitsDesk = loadPendingExitsDesk;

function openApproveExitModal(exitId) {
  const exitRec = cachedPendingExits.find(e => e.id === exitId);
  if (!exitRec) return;
  activeApproveExitId = exitId;

  const summaryEl = document.getElementById("approve-exit-summary");
  if (summaryEl) {
    summaryEl.innerHTML = `
      <div class="flex justify-between border-b pb-1.5">
        <span class="text-slate-500">Exiting Member:</span>
        <strong class="text-slate-900">${exitRec.first_name} ${exitRec.last_name} (${exitRec.member_code})</strong>
      </div>
      <div class="flex justify-between border-b pb-1.5">
        <span class="text-slate-500">Exit Classification:</span>
        <span class="font-bold text-slate-800">${exitRec.exit_type}</span>
      </div>
      <div class="flex justify-between border-b pb-1.5">
        <span class="text-slate-500">Ordinary &amp; Target Savings:</span>
        <span>${formatNaira(exitRec.total_savings_at_exit + exitRec.total_target_savings_at_exit)}</span>
      </div>
      <div class="flex justify-between border-b pb-1.5">
        <span class="text-slate-500">Paid-Up Share Equity:</span>
        <span>${formatNaira(exitRec.total_shares_at_exit)}</span>
      </div>
      <div class="flex justify-between border-b pb-1.5">
        <span class="text-slate-500">Exit Administrative Fee:</span>
        <span class="text-rose-600 font-mono">-${formatNaira(exitRec.exit_processing_fee)}</span>
      </div>
      <div class="flex justify-between pt-1">
        <span class="text-emerald-800 font-bold text-sm">Net Refund Payable:</span>
        <strong class="text-emerald-900 font-mono text-base">${formatNaira(exitRec.net_refund_amount)}</strong>
      </div>
      <div class="pt-2 text-[11px] text-slate-500">
        Designated Bank: <strong>${exitRec.bank_name || 'Polaris Bank'}</strong> &bull; Acc: <strong>${exitRec.bank_account_number || 'N/A'}</strong> (${exitRec.bank_account_name || ''})
      </div>
    `;
  }

  const refInput = document.getElementById("approve-exit-payout-ref");
  if (refInput) {
    refInput.value = `POLARIS-EXIT-${Date.now().toString().slice(-6)}`;
  }

  const modal = document.getElementById("modal-approve-exit-settlement");
  if (modal) modal.classList.remove("hidden");
}
window.openApproveExitModal = openApproveExitModal;

function closeApproveExitModal() {
  const modal = document.getElementById("modal-approve-exit-settlement");
  if (modal) modal.classList.add("hidden");
  activeApproveExitId = null;
}
window.closeApproveExitModal = closeApproveExitModal;

async function confirmApproveExitSettlement() {
  if (!activeApproveExitId) return;
  const refCode = document.getElementById("approve-exit-payout-ref")?.value?.trim() || "";

  if (!confirm("Confirming this settlement will zero out the cooperator's accounts and transition status to EXITED. Proceed?")) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/admin/exits/${activeApproveExitId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refund_payment_ref: refCode })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to approve exit settlement.");

    alert(data.message || "Exit settlement successfully approved and finalized.");
    closeApproveExitModal();
    loadPendingExitsDesk();
  } catch (err) {
    alert("Error: " + err.message);
  }
}
window.confirmApproveExitSettlement = confirmApproveExitSettlement;

function openMemberExitModal() {
  if (!currentUser) return;
  recalculateExitEstimates();
  const modal = document.getElementById("modal-member-exit-request");
  if (modal) modal.classList.remove("hidden");
}
window.openMemberExitModal = openMemberExitModal;

function closeMemberExitModal() {
  const modal = document.getElementById("modal-member-exit-request");
  if (modal) modal.classList.add("hidden");
}
window.closeMemberExitModal = closeMemberExitModal;

function recalculateExitEstimates() {
  const exitType = document.getElementById("member-exit-type")?.value || "VOLUNTARY_WITHDRAWAL";
  const nokFields = document.getElementById("member-exit-nok-fields");
  if (nokFields) {
    if (exitType === "DEATH_ESTATE_SETTLEMENT") {
      nokFields.classList.remove("hidden");
    } else {
      nokFields.classList.add("hidden");
    }
  }

  const container = document.getElementById("member-exit-estimates");
  if (!container || !currentUser) return;

  const savings = parseFloat(currentUser.savings_balance || 0);
  const shares = parseFloat(currentUser.share_equity_paid || 0);
  const exitFee = exitType === "DEATH_ESTATE_SETTLEMENT" ? 0 : 5000;
  const bereavement = exitType === "DEATH_ESTATE_SETTLEMENT" ? 100000 : 0;
  const net = (savings + shares + bereavement) - exitFee;

  container.innerHTML = `
    <div class="flex justify-between border-b pb-1 text-slate-600">
      <span>Regular Savings Balance:</span>
      <strong>${formatNaira(savings)}</strong>
    </div>
    <div class="flex justify-between border-b pb-1 text-slate-600">
      <span>Paid-Up Share Equity:</span>
      <strong>${formatNaira(shares)}</strong>
    </div>
    ${bereavement > 0 ? `
      <div class="flex justify-between border-b pb-1 text-purple-700">
        <span>Bereavement Welfare Grant:</span>
        <strong>+${formatNaira(bereavement)}</strong>
      </div>
    ` : ''}
    <div class="flex justify-between border-b pb-1 text-rose-600">
      <span>Administrative Exit Fee:</span>
      <span>-${formatNaira(exitFee)}</span>
    </div>
    <div class="flex justify-between pt-1">
      <span class="font-bold text-slate-900 text-sm">Estimated Net Refund:</span>
      <strong class="font-mono text-emerald-700 text-sm">${formatNaira(net)}</strong>
    </div>
    <div class="text-[10px] text-slate-400 pt-1">
      *Welfare contributions are non-refundable mutual aid (Article 23.4). All active debt and peer guarantees must be cleared.
    </div>
  `;
}
window.recalculateExitEstimates = recalculateExitEstimates;

async function submitExitRequestForm() {
  if (!currentUser) return;
  const exitType = document.getElementById("member-exit-type")?.value || "VOLUNTARY_WITHDRAWAL";
  const reason = document.getElementById("member-exit-reason")?.value?.trim() || "";

  if (!reason) {
    alert("Please provide a reason for the membership withdrawal or exit notice.");
    return;
  }

  let nok = null;
  if (exitType === "DEATH_ESTATE_SETTLEMENT") {
    nok = {
      name: document.getElementById("member-exit-nok-name")?.value?.trim(),
      phone: document.getElementById("member-exit-nok-phone")?.value?.trim(),
      relationship: document.getElementById("member-exit-nok-rel")?.value?.trim()
    };
  }

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/exit-request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        exit_type: exitType,
        reason: reason,
        nok_claimant: nok
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to submit exit notice.");

    alert(data.message || "Exit request lodged successfully. The Secretariat has received your file.");
    closeMemberExitModal();
  } catch (err) {
    alert("Error: " + err.message);
  }
}
window.submitExitRequestForm = submitExitRequestForm;


// --- 3. BULK COOPERATOR CSV IMPORT & DIRECTORY EXPORT ---
async function downloadMembersDirectoryCsv() {
  const token = localStorage.getItem("wmc_token") || (currentUser ? currentUser.token : "");
  if (!token) {
    alert("Authentication required. Please sign in as General Secretary or President.");
    return;
  }
  try {
    const res = await fetch(`${API_BASE_URL}/admin/members/export-csv`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Access denied. Only General Secretary or President can export directory.");
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Wealthbridge_Cooperators_Directory_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    alert(e.message);
  }
}
window.downloadMembersDirectoryCsv = downloadMembersDirectoryCsv;

async function downloadMemberImportTemplate() {
  const token = localStorage.getItem("wmc_token") || (currentUser ? currentUser.token : "");
  if (!token) {
    alert("Authentication required. Please sign in as General Secretary or President.");
    return;
  }
  try {
    const res = await fetch(`${API_BASE_URL}/admin/members/template-csv`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Access denied. Only General Secretary or President can download template.");
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "Wealthbridge_Member_Import_Template.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    alert(e.message);
  }
}
window.downloadMemberImportTemplate = downloadMemberImportTemplate;

async function handleBulkMemberCsvUpload(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  if (!confirm(`Upload and import cooperators from '${file.name}'?`)) {
    event.target.value = "";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE_URL}/admin/members/bulk-import`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Bulk import failed.");

    alert(`Bulk Import Complete:\n• Successfully Imported: ${data.imported_count}\n• Skipped / Duplicate: ${data.skipped_count}`);
    event.target.value = "";
    if (typeof loadExecMembersRegistry === "function") loadExecMembersRegistry();
  } catch (err) {
    alert("Bulk Import Error: " + err.message);
    event.target.value = "";
  }
}
window.handleBulkMemberCsvUpload = handleBulkMemberCsvUpload;

// =============================================================================
// MODULE 4: DOUBLE-ENTRY GENERAL LEDGER & FINANCIAL CONTROL DESK
// =============================================================================

let cachedCoaAccounts = [];

function switchAccountingSubTab(subTabKey) {
  const subtabs = ["coa", "tb", "ie", "bs", "cf", "je"];
  subtabs.forEach(st => {
    const el = document.getElementById(`subview-${st}`);
    const btn = document.getElementById(`btn-subtab-${st}`);
    if (el) {
      if (st === subTabKey) el.classList.remove("hidden");
      else el.classList.add("hidden");
    }
    if (btn) {
      if (st === subTabKey) {
        btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold bg-wmcNavy-900 text-white transition flex items-center gap-1.5";
      } else {
        btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-100 text-slate-600 hover:bg-slate-200 transition flex items-center gap-1.5";
      }
    }
  });

  if (subTabKey === "coa") loadChartOfAccounts();
  else if (subTabKey === "tb") loadTrialBalance();
  else if (subTabKey === "ie") loadIncomeExpenditure();
  else if (subTabKey === "bs") loadBalanceSheet();
  else if (subTabKey === "cf") loadCashFlowStatement();
  else if (subTabKey === "je") loadJournalEntriesDesk();
}
window.switchAccountingSubTab = switchAccountingSubTab;

async function loadAccountingDesk() {
  const todayStr = new Date().toISOString().split("T")[0];
  const yearStartStr = `${new Date().getFullYear()}-01-01`;

  const tbDate = document.getElementById("tb-date-input");
  if (tbDate && !tbDate.value) tbDate.value = todayStr;

  const bsDate = document.getElementById("bs-date-input");
  if (bsDate && !bsDate.value) bsDate.value = todayStr;

  const ieFrom = document.getElementById("ie-date-from");
  if (ieFrom && !ieFrom.value) ieFrom.value = yearStartStr;

  const ieTo = document.getElementById("ie-date-to");
  if (ieTo && !ieTo.value) ieTo.value = todayStr;

  loadChartOfAccounts();
  checkPendingManualJournalsBadge();
}
window.loadAccountingDesk = loadAccountingDesk;

async function loadChartOfAccounts() {
  const tbody = document.getElementById("coa-tbody");
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-400">Loading statutory Chart of Accounts...</td></tr>`;

  try {
    const res = await fetch(`${API_BASE_URL}/accounting/chart-of-accounts`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load Chart of Accounts.");

    cachedCoaAccounts = data.data || [];
    renderCoaRows(cachedCoaAccounts);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-rose-500 font-semibold">Error: ${err.message}</td></tr>`;
  }
}
window.loadChartOfAccounts = loadChartOfAccounts;

function renderCoaRows(accounts) {
  const tbody = document.getElementById("coa-tbody");
  if (!tbody) return;

  if (!accounts || accounts.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-400">No matching accounts found.</td></tr>`;
    return;
  }

  const typeBadges = {
    ASSET: "bg-blue-100 text-blue-800 border-blue-200",
    LIABILITY: "bg-purple-100 text-purple-800 border-purple-200",
    EQUITY: "bg-emerald-100 text-emerald-800 border-emerald-200",
    INCOME: "bg-amber-100 text-amber-900 border-amber-200",
    EXPENSE: "bg-rose-100 text-rose-800 border-rose-200"
  };

  tbody.innerHTML = accounts.map(a => `
    <tr class="hover:bg-slate-50 transition">
      <td class="p-3 font-mono font-bold text-slate-900">${a.account_code}</td>
      <td class="p-3">
        <span class="font-bold text-slate-900 block">${a.account_name}</span>
        <span class="text-[11px] text-slate-400 block">${a.description || ""}</span>
      </td>
      <td class="p-3">
        <span class="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase border ${typeBadges[a.account_type] || 'bg-slate-100 text-slate-700'}">${a.account_type}</span>
      </td>
      <td class="p-3 text-right font-mono text-slate-600">${formatNaira(a.total_debit)}</td>
      <td class="p-3 text-right font-mono text-slate-600">${formatNaira(a.total_credit)}</td>
      <td class="p-3 text-right font-mono font-bold ${a.net_balance >= 0 ? 'text-slate-900' : 'text-rose-600'}">
        ${formatNaira(a.net_balance)}
      </td>
    </tr>
  `).join("");
}

function filterCoaTable() {
  const q = (document.getElementById("coa-search-input")?.value || "").toLowerCase().trim();
  const t = (document.getElementById("coa-type-filter")?.value || "").toUpperCase().trim();

  const filtered = cachedCoaAccounts.filter(a => {
    const matchQ = !q || a.account_code.toLowerCase().includes(q) || a.account_name.toLowerCase().includes(q) || (a.description || "").toLowerCase().includes(q);
    const matchT = !t || a.account_type === t;
    return matchQ && matchT;
  });

  renderCoaRows(filtered);
}
window.filterCoaTable = filterCoaTable;

async function loadTrialBalance() {
  const tbody = document.getElementById("tb-tbody");
  const asOf = document.getElementById("tb-date-input")?.value;
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-slate-400">Computing Trial Balance equilibrium...</td></tr>`;

  try {
    const url = asOf ? `${API_BASE_URL}/accounting/trial-balance?as_of_date=${asOf}` : `${API_BASE_URL}/accounting/trial-balance`;
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load Trial Balance.");

    const tb = data.data;
    document.getElementById("tb-grand-dr").textContent = formatNaira(tb.grand_total_debit);
    document.getElementById("tb-grand-cr").textContent = formatNaira(tb.grand_total_credit);

    const badge = document.getElementById("tb-balanced-badge");
    if (badge) {
      if (tb.is_balanced) {
        badge.className = "px-3 py-1 rounded-full text-xs font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1.5";
        badge.innerHTML = `<span>✓</span><span>General Ledger In Equilibrium (Debits == Credits)</span>`;
      } else {
        badge.className = "px-3 py-1 rounded-full text-xs font-extrabold bg-rose-100 text-rose-800 border border-rose-300 flex items-center gap-1.5";
        badge.innerHTML = `<span>⚠️</span><span>Unbalanced Ledger Variance: ${formatNaira(tb.variance)}</span>`;
      }
    }

    if (!tb.accounts || tb.accounts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-slate-400">No active posted accounts.</td></tr>`;
      return;
    }

    tbody.innerHTML = tb.accounts.map(a => `
      <tr class="hover:bg-slate-50 transition">
        <td class="p-3 font-mono font-bold text-slate-900">${a.account_code}</td>
        <td class="p-3 font-bold text-slate-900">${a.account_name}</td>
        <td class="p-3 text-[11px] font-bold text-slate-500">${a.account_type}</td>
        <td class="p-3 text-right font-mono font-bold text-slate-800">${a.trial_debit > 0 ? formatNaira(a.trial_debit) : "-"}</td>
        <td class="p-3 text-right font-mono font-bold text-slate-800">${a.trial_credit > 0 ? formatNaira(a.trial_credit) : "-"}</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-rose-500 font-semibold">Error: ${err.message}</td></tr>`;
  }
}
window.loadTrialBalance = loadTrialBalance;

async function loadIncomeExpenditure() {
  const dFrom = document.getElementById("ie-date-from")?.value;
  const dTo = document.getElementById("ie-date-to")?.value;

  try {
    let url = `${API_BASE_URL}/accounting/income-expenditure`;
    const params = [];
    if (dFrom) params.push(`date_from=${dFrom}`);
    if (dTo) params.push(`date_to=${dTo}`);
    if (params.length) url += `?${params.join("&")}`;

    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load Income Statement.");

    const ie = data.data;
    document.getElementById("ie-stat-income").textContent = formatNaira(ie.total_income);
    document.getElementById("ie-stat-expense").textContent = formatNaira(ie.total_expenditure);
    document.getElementById("ie-stat-surplus").textContent = formatNaira(ie.net_surplus);
    document.getElementById("ie-stat-reserve-note").textContent = `50% Statutory Reserve: ${formatNaira(ie.statutory_reserve_50pct)}`;

    const incList = document.getElementById("ie-income-list");
    if (incList) {
      if (!ie.income_items || ie.income_items.length === 0) {
        incList.innerHTML = `<span class="text-slate-400 italic">No revenue recorded in this period.</span>`;
      } else {
        incList.innerHTML = ie.income_items.map(item => `
          <div class="flex justify-between items-center py-1.5 border-b border-slate-100 last:border-0">
            <div>
              <span class="font-bold text-slate-800 block">${item.account_name}</span>
              <span class="text-[10px] text-slate-400 font-mono">${item.account_code}</span>
            </div>
            <span class="font-mono font-bold text-emerald-700">${formatNaira(item.amount)}</span>
          </div>
        `).join("");
      }
    }

    const expList = document.getElementById("ie-expense-list");
    if (expList) {
      if (!ie.expense_items || ie.expense_items.length === 0) {
        expList.innerHTML = `<span class="text-slate-400 italic">No expenses recorded in this period.</span>`;
      } else {
        expList.innerHTML = ie.expense_items.map(item => `
          <div class="flex justify-between items-center py-1.5 border-b border-slate-100 last:border-0">
            <div>
              <span class="font-bold text-slate-800 block">${item.account_name}</span>
              <span class="text-[10px] text-slate-400 font-mono">${item.account_code}</span>
            </div>
            <span class="font-mono font-bold text-rose-700">${formatNaira(item.amount)}</span>
          </div>
        `).join("");
      }
    }
  } catch (err) {
    alert("Error loading Income Statement: " + err.message);
  }
}
window.loadIncomeExpenditure = loadIncomeExpenditure;

async function loadBalanceSheet() {
  const asOf = document.getElementById("bs-date-input")?.value;
  try {
    const url = asOf ? `${API_BASE_URL}/accounting/balance-sheet?as_of_date=${asOf}` : `${API_BASE_URL}/accounting/balance-sheet`;
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load Balance Sheet.");

    const bs = data.data;
    document.getElementById("bs-total-assets").textContent = formatNaira(bs.total_assets);
    document.getElementById("bs-total-liab").textContent = formatNaira(bs.total_liabilities);
    document.getElementById("bs-total-equity").textContent = formatNaira(bs.total_equity);
    document.getElementById("bs-total-liab-eq").textContent = formatNaira(bs.total_liabilities_and_equity);

    const bBadge = document.getElementById("bs-balanced-badge");
    if (bBadge) {
      if (bs.is_balanced) {
        bBadge.className = "px-3 py-1 rounded-full text-xs font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300";
        bBadge.textContent = "Assets = Liabilities + Equity (Balanced)";
      } else {
        bBadge.className = "px-3 py-1 rounded-full text-xs font-extrabold bg-rose-100 text-rose-800 border border-rose-300";
        bBadge.textContent = `⚠️ Unbalanced Equation (Diff: ${formatNaira(bs.difference)})`;
      }
    }

    const aList = document.getElementById("bs-assets-list");
    if (aList) {
      aList.innerHTML = bs.assets.map(a => `
        <div class="flex justify-between items-center py-1 border-b border-slate-100 last:border-0">
          <div>
            <span class="font-bold text-slate-800 block">${a.account_name}</span>
            <span class="text-[10px] text-slate-400 font-mono">${a.account_code}</span>
          </div>
          <span class="font-mono font-bold text-slate-900">${formatNaira(a.balance)}</span>
        </div>
      `).join("");
    }

    const lList = document.getElementById("bs-liab-list");
    if (lList) {
      lList.innerHTML = bs.liabilities.map(l => `
        <div class="flex justify-between items-center py-1 border-b border-slate-100 last:border-0">
          <div>
            <span class="font-bold text-slate-800 block">${l.account_name}</span>
            <span class="text-[10px] text-slate-400 font-mono">${l.account_code}</span>
          </div>
          <span class="font-mono font-bold text-slate-900">${formatNaira(l.balance)}</span>
        </div>
      `).join("");
    }

    const eqList = document.getElementById("bs-equity-list");
    if (eqList) {
      eqList.innerHTML = bs.equity.map(e => `
        <div class="flex justify-between items-center py-1 border-b border-slate-100 last:border-0">
          <div>
            <span class="font-bold text-slate-800 block">${e.account_name}</span>
            <span class="text-[10px] text-slate-400 font-mono">${e.account_code}</span>
          </div>
          <span class="font-mono font-bold text-slate-900">${formatNaira(e.balance)}</span>
        </div>
      `).join("");
    }
  } catch (err) {
    alert("Error loading Balance Sheet: " + err.message);
  }
}
window.loadBalanceSheet = loadBalanceSheet;

async function loadCashFlowStatement() {
  const dFrom = document.getElementById("ie-date-from")?.value;
  const dTo = document.getElementById("ie-date-to")?.value;

  try {
    let url = `${API_BASE_URL}/accounting/cash-flow`;
    const params = [];
    if (dFrom) params.push(`date_from=${dFrom}`);
    if (dTo) params.push(`date_to=${dTo}`);
    if (params.length) url += `?${params.join("&")}`;

    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load Cash Flow Statement.");

    const cf = data.data;
    document.getElementById("cf-closing-cash").textContent = formatNaira(cf.closing_cash_balance);
    document.getElementById("cf-stat-op").textContent = formatNaira(cf.operating_net);
    document.getElementById("cf-stat-inv").textContent = formatNaira(cf.investing_net);
    document.getElementById("cf-stat-fin").textContent = formatNaira(cf.financing_net);

    const cont = document.getElementById("cf-activities-container");
    if (cont) {
      const allActs = [
        ...(cf.operating_activities || []),
        ...(cf.investing_activities || []),
        ...(cf.financing_activities || [])
      ];
      if (allActs.length === 0) {
        cont.innerHTML = `<span class="text-slate-400 italic">No cash flow movements recorded in period.</span>`;
      } else {
        cont.innerHTML = allActs.map(a => `
          <div class="flex justify-between items-center py-2 border-b border-slate-100">
            <div>
              <span class="font-bold text-slate-800 block">${a.activity}</span>
              <span class="text-[10px] text-slate-400">Cash In: ${formatNaira(a.cash_in)} &bull; Cash Out: ${formatNaira(a.cash_out)}</span>
            </div>
            <span class="font-mono font-bold ${a.net >= 0 ? 'text-emerald-700' : 'text-rose-700'}">
              ${a.net >= 0 ? '+' : ''}${formatNaira(a.net)}
            </span>
          </div>
        `).join("");
      }
    }
  } catch (err) {
    alert("Error loading Cash Flow Statement: " + err.message);
  }
}
window.loadCashFlowStatement = loadCashFlowStatement;

// --- MAKER-CHECKER MANUAL JOURNALS ---
function openManualJournalModal() {
  const modal = document.getElementById("modal-manual-journal");
  if (!modal) return;

  const dateInput = document.getElementById("mj-entry-date");
  if (dateInput) dateInput.value = new Date().toISOString().split("T")[0];

  const tbody = document.getElementById("mj-lines-tbody");
  if (tbody) {
    tbody.innerHTML = "";
    addManualJournalRow();
    addManualJournalRow();
  }
  recalculateManualJournalBalance();
  modal.classList.remove("hidden");
}
window.openManualJournalModal = openManualJournalModal;

function closeManualJournalModal() {
  const modal = document.getElementById("modal-manual-journal");
  if (modal) modal.classList.add("hidden");
}
window.closeManualJournalModal = closeManualJournalModal;

function addManualJournalRow() {
  const tbody = document.getElementById("mj-lines-tbody");
  if (!tbody) return;

  const tr = document.createElement("tr");
  tr.className = "hover:bg-slate-50 transition";

  const optionsHtml = (cachedCoaAccounts.length > 0 ? cachedCoaAccounts : [
    { account_code: "1010", account_name: "Polaris Bank Current Escrow Account" },
    { account_code: "2010", account_name: "Member Regular Savings Deposits" },
    { account_code: "3010", account_name: "Member Paid-Up Share Capital" },
    { account_code: "4060", account_name: "Sundry & Incidental Income" },
    { account_code: "5050", account_name: "Technology Infrastructure & SMS Alerting" }
  ]).map(a => `<option value="${a.account_code}">${a.account_code} - ${a.account_name}</option>`).join("");

  tr.innerHTML = `
    <td class="p-2">
      <select class="mj-acc-code w-full p-1.5 border border-slate-300 rounded-lg text-xs bg-white">
        ${optionsHtml}
      </select>
    </td>
    <td class="p-2">
      <select class="mj-line-type w-full p-1.5 border border-slate-300 rounded-lg text-xs bg-white font-bold" onchange="recalculateManualJournalBalance()">
        <option value="DEBIT">DEBIT</option>
        <option value="CREDIT">CREDIT</option>
      </select>
    </td>
    <td class="p-2">
      <input type="number" min="0.01" step="0.01" placeholder="0.00" class="mj-amount w-full p-1.5 border border-slate-300 rounded-lg text-xs font-mono" oninput="recalculateManualJournalBalance()">
    </td>
    <td class="p-2">
      <input type="text" placeholder="Line memo" class="mj-memo w-full p-1.5 border border-slate-300 rounded-lg text-xs">
    </td>
    <td class="p-2 text-center">
      <button type="button" onclick="removeManualJournalRow(this)" class="text-rose-500 hover:text-rose-700 font-bold text-sm">✕</button>
    </td>
  `;
  tbody.appendChild(tr);
  recalculateManualJournalBalance();
}
window.addManualJournalRow = addManualJournalRow;

function removeManualJournalRow(btn) {
  const tr = btn.closest("tr");
  if (tr) tr.remove();
  recalculateManualJournalBalance();
}
window.removeManualJournalRow = removeManualJournalRow;

function recalculateManualJournalBalance() {
  const rows = document.querySelectorAll("#mj-lines-tbody tr");
  let totalDr = 0;
  let totalCr = 0;

  rows.forEach(r => {
    const type = r.querySelector(".mj-line-type")?.value || "DEBIT";
    const amt = parseFloat(r.querySelector(".mj-amount")?.value) || 0;
    if (type === "DEBIT") totalDr += amt;
    else totalCr += amt;
  });

  const drEl = document.getElementById("mj-live-dr");
  if (drEl) drEl.textContent = formatNaira(totalDr);

  const crEl = document.getElementById("mj-live-cr");
  if (crEl) crEl.textContent = formatNaira(totalCr);

  const diff = Math.abs(totalDr - totalCr);
  const statusEl = document.getElementById("mj-live-balance-status");
  const submitBtn = document.getElementById("btn-submit-manual-journal");

  if (statusEl) {
    if (diff < 0.01 && totalDr > 0) {
      statusEl.className = "px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800";
      statusEl.textContent = "✓ Balanced (NGN 0.00 Difference)";
      if (submitBtn) submitBtn.disabled = false;
    } else {
      statusEl.className = "px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800";
      statusEl.textContent = `⚠️ Difference: ${formatNaira(diff)}`;
      if (submitBtn) submitBtn.disabled = true;
    }
  }
}
window.recalculateManualJournalBalance = recalculateManualJournalBalance;

async function submitManualJournalForm(e) {
  if (e) e.preventDefault();

  const entryDate = document.getElementById("mj-entry-date")?.value;
  const narration = document.getElementById("mj-narration")?.value?.trim();
  const docUrl = document.getElementById("mj-doc-url")?.value?.trim() || null;

  const rows = document.querySelectorAll("#mj-lines-tbody tr");
  const lines = [];

  rows.forEach(r => {
    const code = r.querySelector(".mj-acc-code")?.value;
    const type = r.querySelector(".mj-line-type")?.value;
    const amt = parseFloat(r.querySelector(".mj-amount")?.value) || 0;
    const memo = r.querySelector(".mj-memo")?.value?.trim() || null;
    if (amt > 0) {
      lines.push({ account_code: code, line_type: type, amount: amt, memo: memo });
    }
  });

  if (lines.length < 2) {
    alert("Please provide at least 2 valid debit/credit line items.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/accounting/journal-entries`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        entry_date: entryDate,
        narration: narration,
        supporting_doc_url: docUrl,
        lines: lines
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to submit journal entry.");

    alert(`Manual Journal Draft #${data.entry_number} submitted successfully!\nAwaiting Checker (President / Auditor) approval.`);
    closeManualJournalModal();
    loadJournalEntriesDesk();
  } catch (err) {
    alert("Submission Error: " + err.message);
  }
}
window.submitManualJournalForm = submitManualJournalForm;

async function loadJournalEntriesDesk() {
  loadPendingManualJournals();
  loadJournalEntries();
}
window.loadJournalEntriesDesk = loadJournalEntriesDesk;

async function checkPendingManualJournalsBadge() {
  try {
    const res = await fetch(`${API_BASE_URL}/accounting/journal-entries?status=DRAFT`);
    const data = await res.json();
    const count = (data.data || []).length;
    const badge = document.getElementById("badge-pending-je");
    if (badge) {
      if (count > 0) {
        badge.textContent = count;
        badge.classList.remove("hidden");
      } else {
        badge.classList.add("hidden");
      }
    }
  } catch (e) {
    // quiet catch
  }
}

async function loadPendingManualJournals() {
  const tbody = document.getElementById("je-pending-tbody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE_URL}/accounting/journal-entries?status=DRAFT`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load pending journals.");

    const entries = data.data || [];
    checkPendingManualJournalsBadge();

    if (entries.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-400">No pending manual journal entries awaiting checker sign-off.</td></tr>`;
      return;
    }

    tbody.innerHTML = entries.map(e => `
      <tr class="hover:bg-amber-50/50 transition">
        <td class="p-3 font-mono font-bold text-slate-900">${e.entry_number}</td>
        <td class="p-3 text-slate-600">${e.entry_date}</td>
        <td class="p-3">
          <span class="font-bold text-slate-900 block">${e.narration}</span>
          <span class="text-[10px] text-slate-400">Drafted by: ${e.creator_name || 'Finance Officer'}</span>
        </td>
        <td class="p-3 text-right font-mono font-bold text-blue-700">${formatNaira(e.total_debit)}</td>
        <td class="p-3 text-right font-mono font-bold text-purple-700">${formatNaira(e.total_credit)}</td>
        <td class="p-3 text-center font-bold text-slate-500">${(e.lines || []).length}</td>
        <td class="p-3 text-right">
          <div class="flex items-center justify-end gap-1.5">
            <button type="button" onclick="reviewManualJournalEntry(${e.id}, 'APPROVE')" class="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[11px] shadow-sm">
              Approve
            </button>
            <button type="button" onclick="reviewManualJournalEntry(${e.id}, 'REJECT')" class="px-2.5 py-1 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-bold text-[11px] shadow-sm">
              Reject
            </button>
          </div>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-rose-500">Error: ${err.message}</td></tr>`;
  }
}

async function loadJournalEntries() {
  const tbody = document.getElementById("je-history-tbody");
  const stFilter = document.getElementById("je-history-status")?.value || "";
  if (!tbody) return;

  try {
    const url = stFilter ? `${API_BASE_URL}/accounting/journal-entries?status=${stFilter}` : `${API_BASE_URL}/accounting/journal-entries`;
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load journal stream.");

    const entries = data.data || [];
    if (entries.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-400">No journal entries recorded.</td></tr>`;
      return;
    }

    tbody.innerHTML = entries.map(e => `
      <tr class="hover:bg-slate-50 transition">
        <td class="p-3 font-mono font-bold text-slate-900">${e.entry_number}</td>
        <td class="p-3 text-slate-600">${e.entry_date}</td>
        <td class="p-3">
          <span class="px-1.5 py-0.5 rounded text-[10px] font-extrabold uppercase bg-slate-100 text-slate-700 block w-max">${e.source_module.replace(/_/g, ' ')}</span>
          <span class="text-[10px] text-slate-400 font-mono">${e.source_reference || '-'}</span>
        </td>
        <td class="p-3 text-slate-800 font-medium max-w-xs truncate">${e.narration}</td>
        <td class="p-3 text-right font-mono text-slate-700 font-bold">${formatNaira(e.total_debit)}</td>
        <td class="p-3 text-right font-mono text-slate-700 font-bold">${formatNaira(e.total_credit)}</td>
        <td class="p-3">
          <span class="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${e.status === 'POSTED' ? 'bg-emerald-100 text-emerald-800' : e.status === 'DRAFT' ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800'}">
            ${e.status}
          </span>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-rose-500">Error: ${err.message}</td></tr>`;
  }
}
window.loadJournalEntries = loadJournalEntries;

async function reviewManualJournalEntry(entryId, action) {
  let reason = null;
  if (action === "REJECT") {
    reason = prompt("Please provide a factual rejection reason for the audit log:");
    if (!reason) return;
  } else {
    if (!confirm(`Are you sure you want to approve and post Journal Entry #${entryId} to the General Ledger?`)) return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/accounting/journal-entries/${entryId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: action, rejection_reason: reason })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Review action failed.");

    alert(data.message || `Journal entry ${action === 'APPROVE' ? 'posted' : 'rejected'} successfully.`);
    loadJournalEntriesDesk();
  } catch (err) {
    alert("Review Error: " + err.message);
  }
}
window.reviewManualJournalEntry = reviewManualJournalEntry;

async function syncGeneralLedger() {
  if (!confirm("Reconcile and sync any unposted historical transactions into the double-entry General Ledger?")) return;
  try {
    const res = await fetch(`${API_BASE_URL}/accounting/sync-transactions`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Sync failed.");

    alert(`Reconciliation Complete: Synced ${data.synced_transactions_count || 0} transaction(s) to General Ledger.`);
    loadAccountingDesk();
  } catch (err) {
    alert("Reconciliation Error: " + err.message);
  }
}
window.syncGeneralLedger = syncGeneralLedger;


// =============================================================================
// MODULE 5: ANNUAL SURPLUS & DIVIDEND DISTRIBUTION ENGINE
// =============================================================================

let currentDividendSimulation = null;

async function loadDividendsDesk() {
  try {
    const res = await fetch(`${API_BASE_URL}/accounting/income-expenditure`);
    const data = await res.json();
    if (res.ok && data.data) {
      const surplusInput = document.getElementById("div-param-surplus");
      if (surplusInput && !surplusInput.value && data.data.net_surplus > 0) {
        surplusInput.placeholder = `Live GL Net Surplus: ₦${data.data.net_surplus.toLocaleString()}`;
      }
    }
  } catch (e) {
    // quiet catch
  }
  loadDividendPeriods();
}
window.loadDividendsDesk = loadDividendsDesk;

async function triggerDividendSimulation() {
  const fyStart = document.getElementById("div-param-fy-start")?.value;
  const fyEnd = document.getElementById("div-param-fy-end")?.value;
  const periodName = document.getElementById("div-param-name")?.value || "Annual Surplus Distribution";
  const surplusVal = document.getElementById("div-param-surplus")?.value;
  const reservePct = parseFloat(document.getElementById("div-param-reserve-pct")?.value) || 50.00;
  const wShare = parseFloat(document.getElementById("div-param-weight-share")?.value) || 60.00;
  const wSavings = parseFloat(document.getElementById("div-param-weight-savings")?.value) || 40.00;
  const wPatronage = parseFloat(document.getElementById("div-param-weight-patronage")?.value) || 0.00;
  const minShares = parseInt(document.getElementById("div-param-min-shares")?.value) || 5;
  const minMonths = parseInt(document.getElementById("div-param-min-months")?.value) || 0;
  const disqArrears = document.getElementById("div-param-disqualify-arrears")?.checked ?? true;

  const payload = {
    period_name: periodName,
    financial_year_start: fyStart,
    financial_year_end: fyEnd,
    net_surplus: surplusVal ? parseFloat(surplusVal) : null,
    statutory_reserve_pct: reservePct,
    weight_share_pct: wShare,
    weight_savings_pct: wSavings,
    weight_patronage_pct: wPatronage,
    min_shares: minShares,
    min_months: minMonths,
    disqualify_arrears: disqArrears
  };

  try {
    const res = await fetch(`${API_BASE_URL}/dividends/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Simulation calculation failed.");

    currentDividendSimulation = data.data;
    renderDividendSimulation(currentDividendSimulation);
  } catch (err) {
    alert("Simulation Error: " + err.message);
  }
}
window.triggerDividendSimulation = triggerDividendSimulation;

function renderDividendSimulation(sim) {
  const card = document.getElementById("div-sim-results-card");
  if (!card) return;

  card.classList.remove("hidden");
  document.getElementById("div-sim-title").textContent = sim.period_name;
  document.getElementById("div-stat-surplus").textContent = formatNaira(sim.net_surplus_amount);
  document.getElementById("div-stat-reserve").textContent = formatNaira(sim.statutory_reserve_amount);
  document.getElementById("div-stat-pool").textContent = formatNaira(sim.distributable_pool_amount);
  document.getElementById("div-stat-qualified").textContent = sim.summary.total_qualified_members;
  document.getElementById("div-stat-disqualified").textContent = sim.summary.total_disqualified_members;
  document.getElementById("div-stat-allocated").textContent = formatNaira(sim.summary.total_allocated_pool);

  renderDividendAllocationsTable(sim.allocations || []);
}

function renderDividendAllocationsTable(allocations) {
  const tbody = document.getElementById("div-allocations-tbody");
  if (!tbody) return;

  if (!allocations || allocations.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="p-6 text-center text-slate-400">No member allocations generated.</td></tr>`;
    return;
  }

  tbody.innerHTML = allocations.map(a => `
    <tr class="hover:bg-slate-50 transition">
      <td class="p-3">
        <span class="font-bold text-slate-900 block">${a.full_name}</span>
        <span class="text-[10px] text-slate-400 font-mono">${a.member_code}</span>
      </td>
      <td class="p-3 text-right font-mono font-bold text-slate-800">${a.shares_held}</td>
      <td class="p-3 text-right font-mono text-slate-700">${formatNaira(a.savings_balance)}</td>
      <td class="p-3">
        <span class="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${a.is_qualified ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}">
          ${a.is_qualified ? 'QUALIFIED' : 'DISQUALIFIED'}
        </span>
        ${!a.is_qualified ? `<span class="text-[10px] text-rose-500 block mt-0.5">${a.disqualification_reason || ''}</span>` : ''}
      </td>
      <td class="p-3 text-right font-mono text-slate-700">${formatNaira(a.dividend_from_shares)}</td>
      <td class="p-3 text-right font-mono text-slate-700">${formatNaira(a.dividend_from_savings)}</td>
      <td class="p-3 text-right font-mono font-bold text-emerald-700">${formatNaira(a.total_dividend_payable)}</td>
      <td class="p-3 text-slate-600 text-[11px] font-semibold">
        ${a.payout_preference === 'SAVINGS_CREDIT' ? '🏦 Savings Credit' : '💳 Bank Transfer'}
      </td>
    </tr>
  `).join("");
}

function filterDividendTable() {
  if (!currentDividendSimulation) return;
  const q = (document.getElementById("div-table-search")?.value || "").toLowerCase().trim();
  const f = document.getElementById("div-table-filter")?.value;

  const filtered = (currentDividendSimulation.allocations || []).filter(a => {
    const matchQ = !q || a.member_code.toLowerCase().includes(q) || a.full_name.toLowerCase().includes(q);
    const matchF = !f || (f === "QUALIFIED" && a.is_qualified) || (f === "DISQUALIFIED" && !a.is_qualified);
    return matchQ && matchF;
  });

  renderDividendAllocationsTable(filtered);
}
window.filterDividendTable = filterDividendTable;

async function saveDividendSimulationDraft() {
  if (!currentDividendSimulation) {
    alert("Please run a simulation calculation first.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/dividends/save-simulation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ simulation_data: currentDividendSimulation })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to save dividend period.");

    alert(data.message || `Saved dividend distribution run as Period #${data.period_id} (AUDIT_REVIEW).`);
    loadDividendPeriods();
  } catch (err) {
    alert("Save Error: " + err.message);
  }
}
window.saveDividendSimulationDraft = saveDividendSimulationDraft;

async function approveAndPostLiveSimulation() {
  if (!currentDividendSimulation) {
    alert("Please run a simulation calculation first.");
    return;
  }

  if (!confirm(`PRESIDENTIAL SIGN-OFF INITIATION:\n\nAre you sure you want to approve and execute this distribution?\n• Total Net Surplus: ${formatNaira(currentDividendSimulation.net_surplus_amount)}\n• 50% Statutory Reserve: ${formatNaira(currentDividendSimulation.statutory_reserve_amount)}\n• Total Allocated to Cooperators: ${formatNaira(currentDividendSimulation.summary.total_allocated_pool)}\n\nCooperator savings will be automatically credited and balanced General Ledger entries posted.`)) {
    return;
  }

  try {
    const saveRes = await fetch(`${API_BASE_URL}/dividends/save-simulation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ simulation_data: currentDividendSimulation })
    });
    const saveData = await saveRes.json();
    if (!saveRes.ok) throw new Error(saveData.detail || "Failed to persist dividend simulation.");

    const periodId = saveData.period_id;

    const postRes = await fetch(`${API_BASE_URL}/dividends/periods/${periodId}/approve`, {
      method: "POST"
    });
    const postData = await postRes.json();
    if (!postRes.ok) throw new Error(postData.detail || "Presidential sign-off execution failed.");

    alert(`🎉 Presidential Sign-Off Successful!\n\n${postData.message}\n• Total Savings Credited: ${formatNaira(postData.total_savings_credited)}\n• Bank Disbursements Marked: ${formatNaira(postData.total_bank_disbursed)}\n• Statutory Reserve Retained: ${formatNaira(postData.statutory_reserve_retained)}`);
    loadDividendPeriods();
    loadAccountingDesk();
  } catch (err) {
    alert("Execution Error: " + err.message);
  }
}
window.approveAndPostLiveSimulation = approveAndPostLiveSimulation;

async function loadDividendPeriods() {
  const tbody = document.getElementById("div-periods-tbody");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE_URL}/dividends/periods`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load dividend periods.");

    const periods = data.data || [];
    if (periods.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="p-6 text-center text-slate-400">No annual dividend distribution periods created yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = periods.map(p => `
      <tr class="hover:bg-slate-50 transition">
        <td class="p-3">
          <span class="font-bold text-slate-900 block">${p.period_name}</span>
          <span class="text-[10px] text-slate-400 font-mono">Period #${p.id}</span>
        </td>
        <td class="p-3 text-slate-600 font-mono text-[11px]">${p.financial_year_start} to ${p.financial_year_end}</td>
        <td class="p-3 text-right font-mono font-bold text-slate-900">${formatNaira(p.net_surplus_amount)}</td>
        <td class="p-3 text-right font-mono text-amber-700">${formatNaira(p.statutory_reserve_amount)}</td>
        <td class="p-3 text-right font-mono text-emerald-700 font-bold">${formatNaira(p.distributable_pool_amount)}</td>
        <td class="p-3 text-center">
          <span class="font-bold text-emerald-700">${p.total_qualified_members}</span> / <span class="text-slate-400">${p.total_qualified_members + p.total_disqualified_members}</span>
        </td>
        <td class="p-3">
          <span class="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${p.status === 'APPROVED_POSTED' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
            ${p.status}
          </span>
        </td>
        <td class="p-3 text-right">
          <div class="flex items-center justify-end gap-1.5">
            <button type="button" onclick="viewDividendPeriodDetails(${p.id})" class="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-[11px]">
              View Audit File
            </button>
            ${p.status === 'AUDIT_REVIEW' ? `
              <button type="button" onclick="approveExistingDividendPeriod(${p.id})" class="px-2.5 py-1 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-[11px] shadow-sm">
                Sign &amp; Post
              </button>
            ` : ''}
          </div>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="p-6 text-center text-rose-500">Error: ${err.message}</td></tr>`;
  }
}
window.loadDividendPeriods = loadDividendPeriods;

async function viewDividendPeriodDetails(periodId) {
  try {
    const res = await fetch(`${API_BASE_URL}/dividends/periods/${periodId}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load period details.");

    const p = data.data;
    document.getElementById("modal-div-title").textContent = p.period_name;
    document.getElementById("modal-div-subtitle").textContent = `Financial Year: ${p.financial_year_start} to ${p.financial_year_end}`;
    document.getElementById("modal-div-surplus").textContent = formatNaira(p.net_surplus_amount);
    document.getElementById("modal-div-reserve").textContent = formatNaira(p.statutory_reserve_amount);
    document.getElementById("modal-div-pool").textContent = formatNaira(p.distributable_pool_amount);
    document.getElementById("modal-div-status").textContent = p.status;

    const tbody = document.getElementById("modal-div-allocations-tbody");
    if (tbody) {
      tbody.innerHTML = (p.allocations || []).map(a => `
        <tr class="hover:bg-slate-50 transition">
          <td class="p-2.5">
            <span class="font-bold text-slate-900 block">${a.full_name}</span>
            <span class="text-[10px] text-slate-400 font-mono">${a.member_code}</span>
          </td>
          <td class="p-2.5 text-right font-mono">${a.shares_held}</td>
          <td class="p-2.5 text-right font-mono">${formatNaira(a.savings_balance)}</td>
          <td class="p-2.5">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${a.is_qualified ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}">
              ${a.is_qualified ? 'QUALIFIED' : 'DISQUALIFIED'}
            </span>
          </td>
          <td class="p-2.5 text-right font-mono">${formatNaira(a.dividend_from_shares)}</td>
          <td class="p-2.5 text-right font-mono">${formatNaira(a.dividend_from_savings)}</td>
          <td class="p-2.5 text-right font-mono font-bold text-emerald-700">${formatNaira(a.total_dividend_payable)}</td>
          <td class="p-2.5 text-[10px] font-bold text-slate-600">${a.payout_status}</td>
        </tr>
      `).join("");
    }

    const modal = document.getElementById("modal-dividend-period-details");
    if (modal) modal.classList.remove("hidden");
  } catch (err) {
    alert("Audit File Error: " + err.message);
  }
}
window.viewDividendPeriodDetails = viewDividendPeriodDetails;

function closeDividendPeriodModal() {
  const modal = document.getElementById("modal-dividend-period-details");
  if (modal) modal.classList.add("hidden");
}
window.closeDividendPeriodModal = closeDividendPeriodModal;

async function approveExistingDividendPeriod(periodId) {
  if (!confirm(`Are you sure you want to approve & post Dividend Period #${periodId}?\nThis will credit member regular savings accounts and write double-entry General Ledger postings.`)) return;

  try {
    const res = await fetch(`${API_BASE_URL}/dividends/periods/${periodId}/approve`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Approval failed.");

    alert(data.message || "Dividend period approved and posted successfully.");
    loadDividendPeriods();
    loadAccountingDesk();
  } catch (err) {
    alert("Sign-Off Error: " + err.message);
  }
}
window.approveExistingDividendPeriod = approveExistingDividendPeriod;


// --- MEMBER PROFILE: DIVIDEND PREFERENCE & STATEMENT ---
async function loadMemberDividendSection() {
  if (!currentUser || !currentUser.id) return;

  try {
    const resPref = await fetch(`${API_BASE_URL}/members/${currentUser.id}/dividend-preference`);
    const dataPref = await resPref.json();
    if (resPref.ok && dataPref.data) {
      const pref = dataPref.data.dividend_payout_preference || "SAVINGS_CREDIT";
      const radSavings = document.getElementById("pref-savings-credit");
      const radBank = document.getElementById("pref-bank-transfer");
      if (pref === "BANK_TRANSFER" && radBank) radBank.checked = true;
      else if (radSavings) radSavings.checked = true;
    }

    const tbody = document.getElementById("member-dividend-history-tbody");
    if (!tbody) return;

    const resHist = await fetch(`${API_BASE_URL}/members/${currentUser.id}/dividend-history`);
    const dataHist = await resHist.json();
    const records = dataHist.data || [];

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-400">No annual dividend statements recorded for your membership yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = records.map(r => `
      <tr class="hover:bg-slate-50 transition">
        <td class="p-2.5 font-bold text-slate-900">${r.period_name}</td>
        <td class="p-2.5 text-slate-600 font-mono">${formatNaira(r.dividend_from_shares)}</td>
        <td class="p-2.5 text-slate-600 font-mono">${formatNaira(r.dividend_from_savings)}</td>
        <td class="p-2.5 text-emerald-700 font-mono font-bold">${formatNaira(r.total_dividend_payable)}</td>
        <td class="p-2.5">
          <span class="font-bold text-slate-700 block">${r.payout_preference === 'SAVINGS_CREDIT' ? '🏦 Savings Credit' : '💳 Bank Transfer'}</span>
          <span class="text-[10px] text-slate-400 font-mono">${r.payout_reference || '-'}</span>
        </td>
        <td class="p-2.5">
          <span class="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${r.payout_status === 'CREDITED_TO_SAVINGS' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'}">
            ${r.payout_status.replace(/_/g, ' ')}
          </span>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.warn("Could not load member dividend section:", err);
  }
}
window.loadMemberDividendSection = loadMemberDividendSection;

async function saveMemberDividendPreference() {
  if (!currentUser || !currentUser.id) return;

  const radBank = document.getElementById("pref-bank-transfer");
  const selectedPref = radBank && radBank.checked ? "BANK_TRANSFER" : "SAVINGS_CREDIT";

  try {
    const res = await fetch(`${API_BASE_URL}/members/${currentUser.id}/dividend-preference`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payout_preference: selectedPref })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to update preference.");

    alert(`✅ Annual Dividend Preference Saved!\nSelected Payout Mode: ${selectedPref === 'SAVINGS_CREDIT' ? 'Auto-Credit to Regular Savings' : 'Direct Electronic Bank Transfer'}`);
  } catch (err) {
    alert("Preference Error: " + err.message);
  }
}
window.saveMemberDividendPreference = saveMemberDividendPreference;

// =========================================================================
// STATUTORY NOTICES & LOGIN PROMPTS ENGINE
// =========================================================================

function renderLoginPrompts(prompts) {
  if (!prompts || prompts.length === 0) return;

  const container = document.getElementById("login-prompts-container");
  const modal = document.getElementById("modal-login-prompts");
  if (!container || !modal) return;

  container.innerHTML = prompts.map(p => {
    let borderClass = "border-amber-300 bg-amber-50 text-amber-950";
    let badgeClass = "bg-amber-600 text-white";
    let icon = "⚠️";

    if (p.severity === "CRITICAL") {
      borderClass = "border-orange-300 bg-orange-50 text-orange-950";
      badgeClass = "bg-orange-600 text-white";
      icon = "🚨";
    } else if (p.severity === "DANGER") {
      borderClass = "border-red-300 bg-red-50 text-red-950";
      badgeClass = "bg-red-600 text-white";
      icon = "⛔";
    } else if (p.severity === "INFO") {
      borderClass = "border-blue-300 bg-blue-50 text-blue-950";
      badgeClass = "bg-blue-600 text-white";
      icon = "ℹ️";
    }

    let actionBtn = "";
    if (p.type === "LOAN_FORECLOSURE_ACTION_REQUIRED" && p.loan_id) {
      actionBtn = `
        <button type="button" onclick="openForeclosureModal(${p.loan_id}, '${p.title}', '${p.borrower_name}', ${p.outstanding_balance}, 0, 0); closeLoginPromptsModal();" class="mt-2.5 px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-bold text-xs shadow transition">
          ⚖️ Open Foreclosure Offset Desk
        </button>
      `;
    } else if (p.action_url) {
      actionBtn = `
        <a href="${p.action_url}" onclick="closeLoginPromptsModal()" class="inline-block mt-2.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow transition">
          ${p.action_label || 'View Details'} →
        </a>
      `;
    }

    return `
      <div class="p-4 rounded-2xl border ${borderClass} space-y-1.5 text-xs shadow-sm">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1.5 font-bold">
            <span>${icon}</span>
            <span>${p.title}</span>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${badgeClass}">${p.severity}</span>
        </div>
        <p class="leading-relaxed text-slate-700">${p.message}</p>
        ${actionBtn}
      </div>
    `;
  }).join("");

  modal.classList.remove("hidden");
}
window.renderLoginPrompts = renderLoginPrompts;

function closeLoginPromptsModal() {
  const modal = document.getElementById("modal-login-prompts");
  if (modal) modal.classList.add("hidden");
}
window.closeLoginPromptsModal = closeLoginPromptsModal;

function openForeclosureModal(loanId, loanRef, borrowerName, outBal, borrowerSav, guarSav) {
  const idEl = document.getElementById("fcl-loan-id");
  if (!idEl) return;
  idEl.value = loanId;
  document.getElementById("fcl-loan-ref").textContent = loanRef || `Loan #${loanId}`;
  document.getElementById("fcl-borrower-name").textContent = borrowerName || "Borrower";
  document.getElementById("fcl-out-bal").textContent = "₦" + (parseFloat(outBal) || 0).toLocaleString(undefined, {minimumFractionDigits: 2});
  document.getElementById("fcl-borrower-sav").textContent = "₦" + (parseFloat(borrowerSav) || 0).toLocaleString(undefined, {minimumFractionDigits: 2});
  document.getElementById("fcl-guar-sav").textContent = "₦" + (parseFloat(guarSav) || 0).toLocaleString(undefined, {minimumFractionDigits: 2});
  
  document.getElementById("fcl-offset-borrower").value = Math.min(parseFloat(outBal) || 0, parseFloat(borrowerSav) || 0);
  document.getElementById("fcl-offset-guarantor").value = 0;
  recalcForeclosureTotal();

  const modal = document.getElementById("modal-foreclosure-offset");
  if (modal) modal.classList.remove("hidden");
}
window.openForeclosureModal = openForeclosureModal;

function closeForeclosureModal() {
  const modal = document.getElementById("modal-foreclosure-offset");
  if (modal) modal.classList.add("hidden");
}
window.closeForeclosureModal = closeForeclosureModal;

function recalcForeclosureTotal() {
  const bAmt = parseFloat(document.getElementById("fcl-offset-borrower").value) || 0;
  const gAmt = parseFloat(document.getElementById("fcl-offset-guarantor").value) || 0;
  const tot = bAmt + gAmt;
  document.getElementById("fcl-total-offset").textContent = "₦" + tot.toLocaleString(undefined, {minimumFractionDigits: 2});
}
window.recalcForeclosureTotal = recalcForeclosureTotal;

async function submitForeclosureOffset() {
  const loanId = document.getElementById("fcl-loan-id").value;
  const offsetBorrower = parseFloat(document.getElementById("fcl-offset-borrower").value) || 0;
  const offsetGuarantor = parseFloat(document.getElementById("fcl-offset-guarantor").value) || 0;
  const notes = document.getElementById("fcl-notes").value.trim();

  if ((offsetBorrower + offsetGuarantor) <= 0) {
    alert("Please enter a valid offset amount greater than ₦0.00.");
    return;
  }

  if (!confirm(`Are you sure you want to execute statutory foreclosure offset of ₦${(offsetBorrower + offsetGuarantor).toLocaleString()} against this loan? This action debits savings accounts and permanently updates the General Ledger.`)) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/admin/loans/${loanId}/foreclosure-offset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        offset_borrower_amount: offsetBorrower,
        offset_guarantor_amount: offsetGuarantor,
        officer_notes: notes
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Foreclosure offset failed.");

    alert(`✅ ${data.message}`);
    closeForeclosureModal();
    if (typeof loadExecutiveLoans === "function") loadExecutiveLoans();
    if (typeof loadExecutiveData === "function") loadExecutiveData();
  } catch (err) {
    alert("Foreclosure Error: " + err.message);
  }
}
window.submitForeclosureOffset = submitForeclosureOffset;



