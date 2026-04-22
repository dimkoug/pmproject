export type NavItem = {
  to: string;
  label: string;
  end?: boolean;
};

export type NavGroup = {
  title?: string;
  items: NavItem[];
};

export type AppDef = {
  id: string;
  label: string;
  short: string;
  path: string;
  color: string;
  accent: string;
  description: string;
  groups: NavGroup[];
};

export const APPS: AppDef[] = [
  {
    id: "projects",
    label: "Projects",
    short: "PJ",
    path: "/",
    color: "#4f46e5",
    accent: "#eef2ff",
    description: "Plan, track, and deliver projects",
    groups: [
      { items: [{ to: "/", label: "All Projects", end: true }, { to: "/portfolio", label: "Portfolio" }] },
    ],
  },
  {
    id: "sales",
    label: "Sales",
    short: "SL",
    path: "/sales",
    color: "#0ea5e9",
    accent: "#e0f2fe",
    description: "CRM, leads, and opportunities",
    groups: [
      { title: "Overview", items: [{ to: "/sales", label: "Dashboard", end: true }, { to: "/sales/forecast", label: "Forecast" }] },
      { title: "Customers", items: [
        { to: "/sales/companies", label: "Companies" },
        { to: "/sales/contacts", label: "Contacts" },
      ]},
      { title: "Pipeline", items: [
        { to: "/sales/leads", label: "Leads" },
        { to: "/sales/opportunities", label: "Opportunities" },
        { to: "/sales/quotes", label: "Quotes" },
        { to: "/sales/orders", label: "Sales Orders" },
        { to: "/sales/contracts", label: "Contracts" },
      ]},
      { title: "Engagement", items: [
        { to: "/sales/campaigns", label: "Campaigns" },
        { to: "/sales/drips", label: "Drip Sequences" },
        { to: "/sales/emails", label: "Emails" },
        { to: "/sales/interactions", label: "Interactions" },
        { to: "/sales/follow-ups", label: "Follow-ups" },
      ]},
      { title: "Revenue Ops", items: [
        { to: "/sales/commissions", label: "Commissions" },
        { to: "/sales/territories", label: "Territories" },
        { to: "/sales/health", label: "Account Health" },
      ]},
    ],
  },
  {
    id: "finance",
    label: "Finance",
    short: "FN",
    path: "/finance",
    color: "#059669",
    accent: "#d1fae5",
    description: "ERP, accounting, and operations",
    groups: [
      { title: "Overview", items: [
        { to: "/finance", label: "Dashboard", end: true },
      ]},
      { title: "Receivables", items: [
        { to: "/finance/invoices", label: "Invoices" },
        { to: "/finance/recurring", label: "Recurring" },
        { to: "/finance/credit-notes", label: "Credit Notes" },
        { to: "/finance/returns", label: "Returns (RMA)" },
        { to: "/finance/aging", label: "Aging" },
        { to: "/finance/pricing", label: "Pricing" },
      ]},
      { title: "Payables", items: [
        { to: "/finance/expenses", label: "Expenses" },
        { to: "/finance/vendors", label: "Vendors" },
        { to: "/finance/rfqs", label: "RFQs" },
        { to: "/finance/requisitions", label: "Requisitions" },
        { to: "/finance/purchase-orders", label: "Purchase Orders" },
        { to: "/finance/goods-receipts", label: "Goods Receipts" },
      ]},
      { title: "Ledger", items: [
        { to: "/finance/accounts", label: "Chart of Accounts" },
        { to: "/finance/centers", label: "Cost / Profit Centers" },
        { to: "/finance/journal", label: "Journal" },
        { to: "/finance/bank", label: "Bank" },
        { to: "/finance/reconciliation", label: "Reconciliation" },
        { to: "/finance/trial-balance", label: "Trial Balance" },
      ]},
      { title: "Operations", items: [
        { to: "/finance/inventory", label: "Inventory" },
        { to: "/finance/batches", label: "Batches / Lots" },
        { to: "/finance/serials", label: "Serial Numbers" },
        { to: "/finance/shipments", label: "Shipments" },
        { to: "/finance/assets", label: "Assets" },
        { to: "/finance/depreciation", label: "Depreciation" },
        { to: "/finance/budgets", label: "Budgets" },
      ]},
      { title: "Reports", items: [
        { to: "/finance/pnl", label: "P&L" },
        { to: "/finance/balance-sheet", label: "Balance Sheet" },
        { to: "/finance/cash-flow", label: "Cash Flow" },
        { to: "/finance/tax", label: "Tax" },
      ]},
    ],
  },
  {
    id: "documents",
    label: "Documents",
    short: "DM",
    path: "/documents",
    color: "#7c3aed",
    accent: "#ede9fe",
    description: "Files, workflows, and signatures",
    groups: [
      { title: "Library", items: [
        { to: "/documents", label: "Files", end: true },
        { to: "/documents/qa", label: "Q&A / Search" },
        { to: "/documents/signatures", label: "Signatures" },
        { to: "/documents/templates", label: "Templates" },
        { to: "/documents/workflows", label: "Workflows" },
        { to: "/documents/retention", label: "Retention" },
        { to: "/documents/locks", label: "Checked Out" },
        { to: "/documents/annotations", label: "Annotations" },
        { to: "/documents/scans", label: "Scans" },
      ]},
      { title: "Reports", items: [
        { to: "/documents/reports/usage", label: "Usage" },
        { to: "/documents/reports/pending", label: "Pending Approvals" },
      ]},
    ],
  },
  {
    id: "admin",
    label: "Admin",
    short: "AD",
    path: "/admin",
    color: "#475569",
    accent: "#f1f5f9",
    description: "Workspace settings and audit",
    groups: [
      { title: "Overview", items: [
        { to: "/admin", label: "Settings", end: true },
        { to: "/admin/security", label: "Security" },
        { to: "/admin/activity", label: "Activity Log" },
        { to: "/admin/trash", label: "Trash" },
        { to: "/admin/email-templates", label: "Email templates" },
      ]},
      { title: "Access Control", items: [
        { to: "/admin/acl/groups", label: "Groups" },
        { to: "/admin/acl/permissions", label: "Permissions" },
        { to: "/admin/acl/users", label: "Users" },
        { to: "/admin/acl/inspector", label: "Permission Inspector" },
      ]},
      { title: "Taxonomy", items: [
        { to: "/admin/tags", label: "Tags" },
      ]},
      { title: "Automation", items: [
        { to: "/admin/automation", label: "Rules" },
      ]},
      { title: "HR", items: [
        { to: "/admin/hr", label: "Overview", end: true },
        { to: "/admin/hr/employees", label: "Employees" },
        { to: "/admin/hr/leave", label: "Leave" },
        { to: "/admin/hr/attendance", label: "Attendance" },
        { to: "/admin/hr/timesheets", label: "Timesheets" },
      ]},
    ],
  },
];

export const getAppByPath = (pathname: string): AppDef => {
  if (pathname.startsWith("/sales")) return APPS[1];
  if (pathname.startsWith("/finance")) return APPS[2];
  if (pathname.startsWith("/documents")) return APPS[3];
  if (pathname.startsWith("/admin")) return APPS[4];
  return APPS[0];
};

export const PROJECT_NAV: NavGroup[] = [
  { title: "Overview", items: [
    { to: "", label: "Dashboard", end: true },
    { to: "reports", label: "Reports" },
    { to: "activity", label: "Activity Log" },
  ]},
  { title: "Planning", items: [
    { to: "tasks", label: "Tasks" },
    { to: "gantt", label: "Gantt" },
    { to: "calendar", label: "Calendar" },
    { to: "schedule", label: "CPM / PERT" },
    { to: "sprints", label: "Sprints" },
    { to: "baselines", label: "Baselines" },
  ]},
  { title: "People", items: [
    { to: "team", label: "Team" },
    { to: "workload", label: "Workload" },
    { to: "time-tracking", label: "Time Tracking" },
    { to: "stakeholders", label: "Stakeholders" },
  ]},
  { title: "Delivery", items: [
    { to: "deliverables", label: "Deliverables" },
    { to: "changes", label: "Change Requests" },
    { to: "risks", label: "Risks" },
    { to: "lessons", label: "Lessons Learned" },
  ]},
  { title: "Analytics", items: [
    { to: "evm", label: "EVM" },
    { to: "burndown", label: "Burndown" },
    { to: "monte-carlo", label: "Monte Carlo" },
    { to: "measurements", label: "KPIs" },
  ]},
];
