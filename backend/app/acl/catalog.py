"""Permission catalog — the single source of truth for every codename the app
recognises. The seeder (`app.acl.seed`) upserts these at startup so new codes
appear without manual DB work, and removed codes are simply unreferenced.

Codename convention: `<app>.<resource>.<action>`.
Categories match the five apps in the workspace shell.
"""

from typing import NamedTuple


class PermissionSpec(NamedTuple):
    codename: str
    name: str
    description: str
    category: str


CATALOG: list[PermissionSpec] = [
    # ── Projects ────────────────────────────────────────────────────
    PermissionSpec("projects.project.view",       "View projects",       "Read project metadata, tasks, risks, deliverables", "projects"),
    PermissionSpec("projects.project.create",     "Create project",      "Start new projects",                                 "projects"),
    PermissionSpec("projects.project.update",     "Update project",      "Edit project settings, schedule, baselines",         "projects"),
    PermissionSpec("projects.project.delete",     "Delete project",      "Archive or remove projects",                         "projects"),
    PermissionSpec("projects.task.view",          "View tasks",          "List and read tasks in a project",                   "projects"),
    PermissionSpec("projects.task.create",        "Create tasks",        "Add tasks, subtasks, dependencies",                  "projects"),
    PermissionSpec("projects.task.update",        "Update tasks",        "Edit status, estimates, assignments",                "projects"),
    PermissionSpec("projects.task.delete",        "Delete tasks",        "Remove tasks and dependencies",                      "projects"),
    PermissionSpec("projects.risk.manage",        "Manage risks",        "Create and update risk register",                    "projects"),
    PermissionSpec("projects.deliverable.manage", "Manage deliverables", "Create / update deliverables & milestones",          "projects"),
    PermissionSpec("projects.change.manage",      "Manage change reqs",  "Submit and decide change requests",                  "projects"),
    PermissionSpec("projects.reports.view",       "View reports",        "EVM, burndown, Monte Carlo, portfolio",              "projects"),

    # ── Sales (CRM) ─────────────────────────────────────────────────
    PermissionSpec("sales.company.view",          "View companies",      "",                                                   "sales"),
    PermissionSpec("sales.company.manage",        "Manage companies",    "Create / update / delete companies",                 "sales"),
    PermissionSpec("sales.contact.manage",        "Manage contacts",     "Create / update / delete CRM contacts",              "sales"),
    PermissionSpec("sales.lead.view",             "View leads",          "",                                                   "sales"),
    PermissionSpec("sales.lead.create",           "Create leads",        "Add new leads",                                      "sales"),
    PermissionSpec("sales.lead.update_status",    "Update lead status",  "Change lead status / score",                         "sales"),
    PermissionSpec("sales.opportunity.view",      "View opportunities",  "",                                                   "sales"),
    PermissionSpec("sales.opportunity.manage",    "Manage opportunities","Create / update opportunities and stages",           "sales"),
    PermissionSpec("sales.quote.manage",          "Manage quotes",       "Create quotes, convert to invoices",                 "sales"),
    PermissionSpec("sales.contract.manage",       "Manage contracts",    "Create / update / close contracts",                  "sales"),
    PermissionSpec("sales.campaign.manage",       "Manage campaigns",    "Run marketing campaigns",                            "sales"),
    PermissionSpec("sales.commission.manage",     "Manage commissions",  "Configure rules and pay commissions",                "sales"),
    PermissionSpec("sales.territory.manage",      "Manage territories",  "Configure territories and auto-assign",              "sales"),

    # ── Finance (ERP) ───────────────────────────────────────────────
    PermissionSpec("finance.invoice.view",        "View invoices",       "",                                                   "finance"),
    PermissionSpec("finance.invoice.create",      "Create invoices",     "Draft and send invoices",                            "finance"),
    PermissionSpec("finance.invoice.update_status","Update invoice status","Move invoices through their lifecycle",            "finance"),
    PermissionSpec("finance.payment.record",      "Record payments",     "",                                                   "finance"),
    PermissionSpec("finance.expense.view",        "View expenses",       "",                                                   "finance"),
    PermissionSpec("finance.expense.manage",      "Manage expenses",     "Create / approve expenses",                          "finance"),
    PermissionSpec("finance.vendor.manage",       "Manage vendors",      "",                                                   "finance"),
    PermissionSpec("finance.po.manage",           "Manage purchase orders","Create and update POs",                            "finance"),
    PermissionSpec("finance.requisition.manage",  "Manage requisitions", "Submit, approve, convert to POs",                    "finance"),
    PermissionSpec("finance.asset.manage",        "Manage assets",       "",                                                   "finance"),
    PermissionSpec("finance.account.manage",      "Manage chart of accts","Configure accounts",                                "finance"),
    PermissionSpec("finance.journal.post",        "Post journal entries","Create and post journal entries",                    "finance"),
    PermissionSpec("finance.bank.manage",         "Manage bank txns",    "Ingest / match bank transactions",                   "finance"),
    PermissionSpec("finance.inventory.manage",    "Manage inventory",    "Warehouses, products, stock movements",              "finance"),
    PermissionSpec("finance.budget.manage",       "Manage budgets",      "",                                                   "finance"),
    PermissionSpec("finance.reports.view",        "View financial reports","P&L, Balance Sheet, Cash Flow, Tax",               "finance"),

    # ── Documents (DMS) ─────────────────────────────────────────────
    PermissionSpec("documents.folder.view",       "View folders",        "",                                                   "documents"),
    PermissionSpec("documents.folder.manage",     "Manage folders",      "Create / rename / delete folders",                   "documents"),
    PermissionSpec("documents.file.upload",       "Upload files",        "",                                                   "documents"),
    PermissionSpec("documents.file.download",     "Download files",      "",                                                   "documents"),
    PermissionSpec("documents.file.delete",       "Delete files",        "",                                                   "documents"),
    PermissionSpec("documents.signature.manage",  "Manage signatures",   "Request / sign documents",                           "documents"),
    PermissionSpec("documents.workflow.manage",   "Manage workflows",    "Create / advance doc workflows",                     "documents"),
    PermissionSpec("documents.retention.manage",  "Manage retention",    "Configure retention policies",                       "documents"),

    # ── Admin ──────────────────────────────────────────────────────
    PermissionSpec("admin.user.manage",           "Manage users",        "Invite, deactivate, reset",                          "admin"),
    PermissionSpec("admin.group.manage",          "Manage groups",       "Create / edit ACL groups",                           "admin"),
    PermissionSpec("admin.permission.assign",     "Assign permissions",  "Attach permissions to groups and users",             "admin"),
    PermissionSpec("admin.approval.decide",       "Decide approvals",    "Approve / reject in the approvals inbox",            "admin"),
    PermissionSpec("admin.webhook.manage",        "Manage webhooks",     "",                                                   "admin"),
    PermissionSpec("admin.apikey.manage",         "Manage API keys",     "",                                                   "admin"),
    PermissionSpec("admin.audit.view",            "View audit log",      "",                                                   "admin"),
    PermissionSpec("admin.sso.manage",            "Manage SSO",          "",                                                   "admin"),
    PermissionSpec("admin.workspace.manage",      "Manage workspaces",   "",                                                   "admin"),
]


# ── Default groups and their permissions ─────────────────────────────

GroupSpec = tuple[str, str, list[str]]  # (name, description, codenames or prefixes)


def _prefix(*prefixes: str) -> list[str]:
    """Expand category prefixes into codenames."""
    result = []
    for p in prefixes:
        result.extend([c.codename for c in CATALOG if c.codename.startswith(p)])
    return result


DEFAULT_GROUPS: list[GroupSpec] = [
    ("Admins",          "Full access to every module.",                 [c.codename for c in CATALOG]),
    ("Project Managers","Run projects end-to-end plus read financials.", _prefix("projects.") + ["finance.reports.view", "finance.budget.manage", "documents.folder.view", "documents.file.upload", "documents.file.download"]),
    ("Members",         "Day-to-day contributors on projects.",          ["projects.project.view", "projects.task.view", "projects.task.create", "projects.task.update", "projects.risk.manage", "projects.deliverable.manage", "projects.reports.view", "documents.folder.view", "documents.file.upload", "documents.file.download"]),
    ("Viewers",         "Read-only across projects.",                    ["projects.project.view", "projects.task.view", "projects.reports.view", "sales.opportunity.view", "sales.lead.view", "finance.invoice.view", "finance.expense.view", "finance.reports.view", "documents.folder.view", "documents.file.download"]),
    ("Sales",           "Full CRM + read-only finance.",                 _prefix("sales.") + ["finance.invoice.view", "finance.reports.view", "projects.project.view"]),
    ("Finance",         "Full ERP + read-only projects.",                _prefix("finance.") + ["projects.project.view", "projects.reports.view"]),
    ("Operations",      "Warehouse, inventory, assets, POs.",            ["finance.inventory.manage", "finance.asset.manage", "finance.vendor.manage", "finance.po.manage", "finance.requisition.manage", "documents.folder.view", "documents.file.upload", "documents.file.download"]),
]
