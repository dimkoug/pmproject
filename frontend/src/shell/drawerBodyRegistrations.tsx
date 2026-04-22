// Drawer body registrations for high-value entities.
// Imported from drawerBodies.ts so these run at app boot.
//
// None of these entities currently have a detail endpoint, so each body
// pulls the matching record out of its list query client-side.

import {
  useGetInvoicesQuery,
  useGetOpportunitiesQuery,
  useGetCompaniesQuery,
  useGetLeadsQuery,
  useGetCrmContactsQuery,
  useGetVendorsQuery,
  useGetExpensesQuery,
  useGetAssetsQuery,
  useGetEmployeesQuery,
  useGetLeaveRequestsQuery,
} from "../services/api";
import type { DrawerBody, DrawerContext } from "./DetailDrawer";
import { registerDrawerBody } from "./DetailDrawer";
import { CommentsTab, OverviewGrid } from "./drawerTabs";
import { useFormat } from "../i18n/format";

function fallbackTitle(entity: string, id: string) {
  return `${entity} ${id.slice(0, 8)}…`;
}

// --- Invoice -----------------------------------------------------------------

function InvoiceOverview({ ctx }: { ctx: DrawerContext }) {
  const { data: invoices = [] } = useGetInvoicesQuery(undefined);
  const { formatCurrency, formatDate } = useFormat();
  const inv = invoices.find((i: any) => i.id === ctx.id);
  if (!inv) return <div style={{ color: "var(--gray-500)" }}>Invoice not found in current list.</div>;
  const currency = inv.currency || "USD";
  return (
    <OverviewGrid
      rows={[
        { label: "Number", value: inv.invoice_number },
        { label: "Type", value: inv.invoice_type },
        { label: "Status", value: <span className="badge badge-blue">{inv.status}</span> },
        { label: "Subtotal", value: formatCurrency(inv.subtotal, currency) },
        { label: "Tax rate", value: inv.tax_rate != null ? `${inv.tax_rate}%` : null },
        { label: "Total", value: formatCurrency(inv.total, currency) },
        { label: "Due", value: formatDate(inv.due_date) },
        { label: "Issued", value: formatDate(inv.issue_date) },
      ]}
    />
  );
}

function InvoiceTitle({ ctx }: { ctx: DrawerContext }) {
  const { data: invoices = [] } = useGetInvoicesQuery(undefined);
  const inv = invoices.find((i: any) => i.id === ctx.id);
  return <>{inv?.invoice_number ?? fallbackTitle("Invoice", ctx.id)}</>;
}

const invoiceBody: DrawerBody = {
  title: (ctx) => <InvoiceTitle ctx={ctx} />,
  tabs: {
    overview: (ctx) => <InvoiceOverview ctx={ctx} />,
    comments: (ctx) => <CommentsTab targetType="invoice" targetId={ctx.id} />,
  },
  defaultTab: "overview",
};

// --- Opportunity -------------------------------------------------------------

function OpportunityOverview({ ctx }: { ctx: DrawerContext }) {
  const { data: opps = [] } = useGetOpportunitiesQuery();
  const { formatCurrency, formatDate } = useFormat();
  const o = opps.find((x: any) => x.id === ctx.id);
  if (!o) return <div style={{ color: "var(--gray-500)" }}>Opportunity not found in current list.</div>;
  return (
    <OverviewGrid
      rows={[
        { label: "Title", value: o.title },
        { label: "Stage", value: <span className="badge badge-blue">{o.stage}</span> },
        { label: "Amount", value: formatCurrency(o.amount) },
        { label: "Probability", value: o.probability != null ? `${o.probability}%` : null },
        { label: "Close date", value: formatDate(o.close_date) },
        { label: "Company", value: o.company_id ? `${o.company_id.slice(0, 8)}…` : null },
      ]}
    />
  );
}

function OpportunityTitle({ ctx }: { ctx: DrawerContext }) {
  const { data: opps = [] } = useGetOpportunitiesQuery();
  const o = opps.find((x: any) => x.id === ctx.id);
  return <>{o?.title ?? fallbackTitle("Opportunity", ctx.id)}</>;
}

const opportunityBody: DrawerBody = {
  title: (ctx) => <OpportunityTitle ctx={ctx} />,
  tabs: {
    overview: (ctx) => <OpportunityOverview ctx={ctx} />,
    comments: (ctx) => <CommentsTab targetType="opportunity" targetId={ctx.id} />,
  },
  defaultTab: "overview",
};

// --- Company -----------------------------------------------------------------

function CompanyOverview({ ctx }: { ctx: DrawerContext }) {
  const { data: companies = [] } = useGetCompaniesQuery();
  const { formatCurrency } = useFormat();
  const c = companies.find((x: any) => x.id === ctx.id);
  if (!c) return <div style={{ color: "var(--gray-500)" }}>Company not found in current list.</div>;
  return (
    <OverviewGrid
      rows={[
        { label: "Name", value: c.name },
        { label: "Industry", value: c.industry },
        { label: "Website", value: c.website },
        { label: "Revenue", value: formatCurrency(c.annual_revenue) },
        { label: "Employees", value: c.employee_count },
        { label: "Health", value: c.health_score != null ? `${c.health_score}/100` : null },
      ]}
    />
  );
}

function CompanyTitle({ ctx }: { ctx: DrawerContext }) {
  const { data: companies = [] } = useGetCompaniesQuery();
  const c = companies.find((x: any) => x.id === ctx.id);
  return <>{c?.name ?? fallbackTitle("Company", ctx.id)}</>;
}

const companyBody: DrawerBody = {
  title: (ctx) => <CompanyTitle ctx={ctx} />,
  tabs: {
    overview: (ctx) => <CompanyOverview ctx={ctx} />,
    comments: (ctx) => <CommentsTab targetType="company" targetId={ctx.id} />,
  },
  defaultTab: "overview",
};

// --- Lead --------------------------------------------------------------------

function LeadOverview({ ctx }: { ctx: DrawerContext }) {
  const { data: leads = [] } = useGetLeadsQuery();
  const { formatCurrency } = useFormat();
  const l = leads.find((x: any) => x.id === ctx.id);
  if (!l) return <div style={{ color: "var(--gray-500)" }}>Lead not found in current list.</div>;
  return (
    <OverviewGrid
      rows={[
        { label: "Contact", value: l.contact_name },
        { label: "Company", value: l.company_name },
        { label: "Source", value: <span className="badge badge-gray">{l.source}</span> },
        { label: "Status", value: <span className="badge badge-blue">{l.status}</span> },
        { label: "Score", value: l.score },
        { label: "Estimated value", value: formatCurrency(l.estimated_value) },
        { label: "Email", value: l.email },
      ]}
    />
  );
}

function LeadTitle({ ctx }: { ctx: DrawerContext }) {
  const { data: leads = [] } = useGetLeadsQuery();
  const l = leads.find((x: any) => x.id === ctx.id);
  return <>{l?.contact_name ?? fallbackTitle("Lead", ctx.id)}</>;
}

const leadBody: DrawerBody = {
  title: (ctx) => <LeadTitle ctx={ctx} />,
  tabs: {
    overview: (ctx) => <LeadOverview ctx={ctx} />,
    comments: (ctx) => <CommentsTab targetType="lead" targetId={ctx.id} />,
  },
  defaultTab: "overview",
};

// --- Contact -----------------------------------------------------------------

function ContactOverview({ ctx }: { ctx: DrawerContext }) {
  const { data: contacts = [] } = useGetCrmContactsQuery(undefined);
  const c = contacts.find((x: any) => x.id === ctx.id);
  if (!c) return <div style={{ color: "var(--gray-500)" }}>Contact not found in current list.</div>;
  return (
    <OverviewGrid
      rows={[
        { label: "Name", value: `${c.first_name} ${c.last_name || ""}`.trim() },
        { label: "Email", value: c.email },
        { label: "Phone", value: c.phone },
        { label: "Title", value: c.job_title },
        { label: "Company", value: c.company_id ? `${c.company_id.slice(0, 8)}…` : null },
      ]}
    />
  );
}

function ContactTitle({ ctx }: { ctx: DrawerContext }) {
  const { data: contacts = [] } = useGetCrmContactsQuery(undefined);
  const c = contacts.find((x: any) => x.id === ctx.id);
  if (!c) return <>{fallbackTitle("Contact", ctx.id)}</>;
  return <>{`${c.first_name} ${c.last_name || ""}`.trim() || fallbackTitle("Contact", ctx.id)}</>;
}

const contactBody: DrawerBody = {
  title: (ctx) => <ContactTitle ctx={ctx} />,
  tabs: {
    overview: (ctx) => <ContactOverview ctx={ctx} />,
    comments: (ctx) => <CommentsTab targetType="contact" targetId={ctx.id} />,
  },
  defaultTab: "overview",
};

// --- Vendor ------------------------------------------------------------------

function VendorOverview({ ctx }: { ctx: DrawerContext }) {
  const { data: vendors = [] } = useGetVendorsQuery();
  const v = vendors.find((x: any) => x.id === ctx.id);
  if (!v) return <div style={{ color: "var(--gray-500)" }}>Vendor not found in current list.</div>;
  return (
    <OverviewGrid
      rows={[
        { label: "Name", value: v.name },
        { label: "Contact", value: v.contact_person },
        { label: "Email", value: v.email },
        { label: "Phone", value: v.phone },
        { label: "Tax ID", value: v.tax_id },
        { label: "Address", value: v.address },
      ]}
    />
  );
}

function VendorTitle({ ctx }: { ctx: DrawerContext }) {
  const { data: vendors = [] } = useGetVendorsQuery();
  const v = vendors.find((x: any) => x.id === ctx.id);
  return <>{v?.name ?? fallbackTitle("Vendor", ctx.id)}</>;
}

const vendorBody: DrawerBody = {
  title: (ctx) => <VendorTitle ctx={ctx} />,
  tabs: {
    overview: (ctx) => <VendorOverview ctx={ctx} />,
    comments: (ctx) => <CommentsTab targetType="vendor" targetId={ctx.id} />,
  },
  defaultTab: "overview",
};

// --- Expense -----------------------------------------------------------------

function ExpenseOverview({ ctx }: { ctx: DrawerContext }) {
  const { data: expenses = [] } = useGetExpensesQuery(undefined);
  const { formatCurrency, formatDate } = useFormat();
  const e = expenses.find((x: any) => x.id === ctx.id);
  if (!e) return <div style={{ color: "var(--gray-500)" }}>Expense not found in current list.</div>;
  return (
    <OverviewGrid
      rows={[
        { label: "Description", value: e.description },
        { label: "Category", value: <span className="badge badge-gray">{e.category}</span> },
        { label: "Amount", value: formatCurrency(e.amount, e.currency || "USD") },
        { label: "Date", value: formatDate(e.expense_date) },
        {
          label: "Approved",
          value: e.is_approved ? (
            <span className="badge badge-green">Yes</span>
          ) : (
            <span className="badge badge-yellow">Pending</span>
          ),
        },
        { label: "Vendor", value: e.vendor_id ? `${e.vendor_id.slice(0, 8)}…` : null },
      ]}
    />
  );
}

function ExpenseTitle({ ctx }: { ctx: DrawerContext }) {
  const { data: expenses = [] } = useGetExpensesQuery(undefined);
  const e = expenses.find((x: any) => x.id === ctx.id);
  return <>{e?.description ?? fallbackTitle("Expense", ctx.id)}</>;
}

const expenseBody: DrawerBody = {
  title: (ctx) => <ExpenseTitle ctx={ctx} />,
  tabs: {
    overview: (ctx) => <ExpenseOverview ctx={ctx} />,
    comments: (ctx) => <CommentsTab targetType="expense" targetId={ctx.id} />,
  },
  defaultTab: "overview",
};

// --- Asset -------------------------------------------------------------------

function AssetOverview({ ctx }: { ctx: DrawerContext }) {
  const { data: assets = [] } = useGetAssetsQuery(undefined);
  const { formatCurrency, formatDate } = useFormat();
  const a = assets.find((x: any) => x.id === ctx.id);
  if (!a) return <div style={{ color: "var(--gray-500)" }}>Asset not found in current list.</div>;
  return (
    <OverviewGrid
      rows={[
        { label: "Name", value: a.name },
        { label: "Tag", value: a.asset_tag },
        { label: "Category", value: a.category },
        { label: "Status", value: <span className="badge badge-blue">{a.status}</span> },
        { label: "Current value", value: formatCurrency(a.current_value) },
        { label: "Purchase price", value: formatCurrency(a.purchase_price) },
        { label: "Location", value: a.location },
        { label: "Acquired", value: formatDate(a.acquisition_date) },
      ]}
    />
  );
}

function AssetTitle({ ctx }: { ctx: DrawerContext }) {
  const { data: assets = [] } = useGetAssetsQuery(undefined);
  const a = assets.find((x: any) => x.id === ctx.id);
  return <>{a?.name ?? fallbackTitle("Asset", ctx.id)}</>;
}

const assetBody: DrawerBody = {
  title: (ctx) => <AssetTitle ctx={ctx} />,
  tabs: {
    overview: (ctx) => <AssetOverview ctx={ctx} />,
    comments: (ctx) => <CommentsTab targetType="asset" targetId={ctx.id} />,
  },
  defaultTab: "overview",
};

// --- Employee ----------------------------------------------------------------

function EmployeeOverview({ ctx }: { ctx: DrawerContext }) {
  const { data: employees = [] } = useGetEmployeesQuery();
  const { data: leaves = [] } = useGetLeaveRequestsQuery({ employeeId: ctx.id });
  const { formatDate } = useFormat();
  const e = (employees as any[]).find((x: any) => x.id === ctx.id);
  if (!e) return <div style={{ color: "var(--gray-500)" }}>Employee not found in current list.</div>;
  const pending = (leaves as any[]).filter((l) => l.status === "pending").length;
  const approved = (leaves as any[]).filter((l) => l.status === "approved").length;
  return (
    <OverviewGrid
      rows={[
        { label: "Number", value: <code>{e.employee_number}</code> },
        { label: "Name", value: e.full_name },
        { label: "Email", value: e.email },
        { label: "Phone", value: e.phone },
        { label: "Department", value: e.department },
        { label: "Job title", value: e.job_title },
        { label: "Hired", value: formatDate(e.hire_date) },
        {
          label: "Status",
          value: e.is_active ? (
            <span className="badge badge-green">active</span>
          ) : (
            <span className="badge badge-gray">inactive</span>
          ),
        },
        { label: "Leave (pending / approved)", value: `${pending} / ${approved}` },
      ]}
    />
  );
}

function EmployeeTitle({ ctx }: { ctx: DrawerContext }) {
  const { data: employees = [] } = useGetEmployeesQuery();
  const e = (employees as any[]).find((x: any) => x.id === ctx.id);
  return <>{e?.full_name ?? fallbackTitle("Employee", ctx.id)}</>;
}

const employeeBody: DrawerBody = {
  title: (ctx) => <EmployeeTitle ctx={ctx} />,
  tabs: {
    overview: (ctx) => <EmployeeOverview ctx={ctx} />,
    comments: (ctx) => <CommentsTab targetType="employee" targetId={ctx.id} />,
  },
  defaultTab: "overview",
};

// --- Registrations -----------------------------------------------------------

registerDrawerBody("invoice", invoiceBody);
registerDrawerBody("opportunity", opportunityBody);
registerDrawerBody("company", companyBody);
registerDrawerBody("lead", leadBody);
registerDrawerBody("contact", contactBody);
registerDrawerBody("vendor", vendorBody);
registerDrawerBody("expense", expenseBody);
registerDrawerBody("asset", assetBody);
registerDrawerBody("employee", employeeBody);

export {};
