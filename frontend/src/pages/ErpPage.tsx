import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  useGetErpDashboardQuery, useGetInvoicesQuery, useCreateInvoiceMutation,
  useGetExpensesQuery, useCreateExpenseMutation, useGetVendorsQuery, useCreateVendorMutation,
  useGetPurchaseOrdersQuery, useCreatePurchaseOrderMutation, useGetAssetsQuery, useCreateAssetMutation,
  useGetAccountsQuery, useCreateAccountMutation, useUpdateInvoiceStatusMutation,
  useGetBudgetsQuery, useCreateBudgetMutation, useGetBudgetVarianceQuery,
  useGetInvoiceAgingQuery, useCreatePaymentMutation,
  useGetRecurringInvoicesQuery, useCreateRecurringInvoiceMutation, useRunRecurringInvoicesMutation,
  useGetTaxReportQuery, useGetTrialBalanceQuery,
  useGetJournalQuery, useCreateJournalMutation, usePostJournalMutation,
  useGetBankTransactionsQuery, useCreateBankTransactionMutation, useAutoMatchBankMutation,
  useGetWarehousesQuery, useCreateWarehouseMutation, useGetProductsQuery, useCreateProductMutation,
  useGetStockQuery, useCreateMovementMutation, useGetReorderReportQuery,
  useGetDepreciationQuery, useCreateDepreciationMutation, useRunDepreciationMutation,
  useGetCreditNotesQuery, useCreateCreditNoteMutation,
  useGetPnlQuery, useGetBalanceSheetQuery, useGetCashFlowQuery,
  useGetRequisitionsQuery, useCreateRequisitionMutation, useUpdateRequisitionStatusMutation, useConvertRequisitionMutation,
} from "../services/api";

const TABS = ["dashboard", "invoices", "expenses", "vendors", "purchase-orders", "assets", "accounts",
  "budgets", "aging", "recurring", "tax", "trial-balance", "journal", "bank",
  "inventory", "depreciation", "credit-notes", "pnl", "balance-sheet", "cash-flow", "requisitions"] as const;

export default function ErpPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [tab, setTab] = useState<typeof TABS[number]>("dashboard");
  const { data: dash } = useGetErpDashboardQuery(projectId);
  const { data: invoices = [], refetch: rInv } = useGetInvoicesQuery(projectId);
  const { data: expenses = [], refetch: rExp } = useGetExpensesQuery(projectId);
  const { data: vendors = [], refetch: rVen } = useGetVendorsQuery();
  const { data: pos = [], refetch: rPo } = useGetPurchaseOrdersQuery(projectId);
  const { data: assets = [], refetch: rAss } = useGetAssetsQuery(projectId);
  const { data: accounts = [], refetch: rAcc } = useGetAccountsQuery();
  const [createInvoice] = useCreateInvoiceMutation();
  const [createExpense] = useCreateExpenseMutation();
  const [createVendor] = useCreateVendorMutation();
  const [createPO] = useCreatePurchaseOrderMutation();
  const [createAsset] = useCreateAssetMutation();
  const [createAccount] = useCreateAccountMutation();
  const [updateInvStatus] = useUpdateInvoiceStatusMutation();
  const { data: budgets = [], refetch: rBud } = useGetBudgetsQuery(projectId, { skip: tab !== "budgets" });
  const [createBudget] = useCreateBudgetMutation();
  const [selectedBudget, setSelectedBudget] = useState<string | null>(null);
  const { data: variance } = useGetBudgetVarianceQuery(selectedBudget!, { skip: !selectedBudget });
  const { data: aging } = useGetInvoiceAgingQuery(projectId, { skip: tab !== "aging" });
  const [createPayment] = useCreatePaymentMutation();
  const { data: recurring = [], refetch: rRec } = useGetRecurringInvoicesQuery(undefined, { skip: tab !== "recurring" });
  const [createRecurring] = useCreateRecurringInvoiceMutation();
  const [runRecurring] = useRunRecurringInvoicesMutation();
  const { data: tax } = useGetTaxReportQuery({}, { skip: tab !== "tax" });
  const { data: trialBal } = useGetTrialBalanceQuery(undefined, { skip: tab !== "trial-balance" });
  const { data: journal = [], refetch: rJour } = useGetJournalQuery(undefined, { skip: tab !== "journal" });
  const [createJournal] = useCreateJournalMutation();
  const [postJournal] = usePostJournalMutation();
  const { data: bank = [], refetch: rBank } = useGetBankTransactionsQuery(undefined, { skip: tab !== "bank" });
  const [createBank] = useCreateBankTransactionMutation();
  const [autoMatchBank] = useAutoMatchBankMutation();
  const { data: warehouses = [], refetch: rWh } = useGetWarehousesQuery(undefined, { skip: tab !== "inventory" });
  const [createWarehouse] = useCreateWarehouseMutation();
  const { data: products = [], refetch: rProd } = useGetProductsQuery(undefined, { skip: tab !== "inventory" });
  const [createProduct] = useCreateProductMutation();
  const { data: stock = [], refetch: rStock } = useGetStockQuery(undefined, { skip: tab !== "inventory" });
  const [createMovement] = useCreateMovementMutation();
  const { data: reorder = [] } = useGetReorderReportQuery(undefined, { skip: tab !== "inventory" });
  const { data: dep = [], refetch: rDep } = useGetDepreciationQuery(undefined, { skip: tab !== "depreciation" });
  const [createDep] = useCreateDepreciationMutation();
  const [runDep] = useRunDepreciationMutation();
  const { data: creditNotes = [], refetch: rCN } = useGetCreditNotesQuery(undefined, { skip: tab !== "credit-notes" });
  const [createCN] = useCreateCreditNoteMutation();
  const { data: pnl } = useGetPnlQuery({}, { skip: tab !== "pnl" });
  const { data: bs } = useGetBalanceSheetQuery(undefined, { skip: tab !== "balance-sheet" });
  const { data: cashFlow } = useGetCashFlowQuery(undefined, { skip: tab !== "cash-flow" });
  const { data: reqs = [], refetch: rReqs } = useGetRequisitionsQuery(undefined, { skip: tab !== "requisitions" });
  const [createReq] = useCreateRequisitionMutation();
  const [updateReqStatus] = useUpdateRequisitionStatusMutation();
  const [convertReq] = useConvertRequisitionMutation();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<any>({});

  const openForm = (defaults: any = {}) => { setForm(defaults); setShowForm(true); };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (tab === "invoices") { await createInvoice({ ...form, project_id: projectId }); rInv(); }
    else if (tab === "expenses") { await createExpense({ ...form, project_id: projectId }); rExp(); }
    else if (tab === "vendors") { await createVendor(form); rVen(); }
    else if (tab === "purchase-orders") { await createPO({ ...form, project_id: projectId }); rPo(); }
    else if (tab === "assets") { await createAsset({ ...form, project_id: projectId }); rAss(); }
    else if (tab === "accounts") { await createAccount(form); rAcc(); }
    setShowForm(false);
  };

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "0.3rem" }}>ERP System</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>Financial management, procurement, and asset tracking</p>
      </div>

      <div style={{ display: "flex", gap: "0.35rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        {TABS.map(t => <button key={t} className={`btn btn-sm ${tab === t ? "btn-primary" : ""}`} onClick={() => setTab(t)}>{t.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</button>)}
      </div>

      {tab === "dashboard" && dash && (
        <div className="stats-grid">
          <div className="stat-card"><div className="label">Revenue</div><div className="value" style={{ color: "var(--success)" }}>${dash.revenue?.toLocaleString()}</div></div>
          <div className="stat-card"><div className="label">Expenses</div><div className="value">${dash.expenses?.total?.toLocaleString()}</div></div>
          <div className="stat-card"><div className="label">Profit</div><div className="value" style={{ color: dash.profit >= 0 ? "var(--success)" : "var(--danger)" }}>${dash.profit?.toLocaleString()}</div></div>
          <div className="stat-card"><div className="label">Invoices</div><div className="value">{dash.invoices?.count}</div></div>
          <div className="stat-card"><div className="label">Purchase Orders</div><div className="value">{dash.purchase_orders?.count}</div></div>
          <div className="stat-card"><div className="label">Assets Value</div><div className="value">${dash.assets?.total_value?.toLocaleString()}</div></div>
        </div>
      )}

      {["invoices","expenses","vendors","purchase-orders","assets","accounts"].includes(tab) && (
        <div className="card-header" style={{ marginBottom: "1rem" }}>
          <span />
          <button className="btn btn-primary btn-sm" onClick={() => openForm(tab === "invoices" ? { invoice_number: `INV-${Date.now().toString().slice(-6)}`, subtotal: 0, tax_rate: 0 } : tab === "expenses" ? { description: "", amount: 0, category: "other" } : tab === "vendors" ? { name: "" } : tab === "purchase-orders" ? { po_number: `PO-${Date.now().toString().slice(-6)}`, vendor_id: vendors[0]?.id || "", total_amount: 0 } : tab === "assets" ? { name: "" } : { code: "", name: "", account_type: "asset" })}>+ Add</button>
        </div>
      )}

      {tab === "invoices" && (
        <div className="card"><table><thead><tr><th>Number</th><th>Type</th><th>Status</th><th>Total</th><th>Due</th><th>Actions</th></tr></thead><tbody>
          {invoices.map((i: any) => <tr key={i.id}><td style={{ fontWeight: 500 }}>{i.invoice_number}</td><td><span className="badge badge-blue">{i.invoice_type}</span></td><td>
            <select value={i.status} onChange={e => { updateInvStatus({ id: i.id, status: e.target.value }); rInv(); }} style={{ fontSize: "0.8rem", padding: "0.2rem" }}>
              {["draft","sent","paid","overdue","cancelled"].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </td><td style={{ fontWeight: 600 }}>${i.total?.toLocaleString()}</td><td>{i.due_date || "-"}</td><td>-</td></tr>)}
        </tbody></table></div>
      )}
      {tab === "expenses" && (
        <div className="card"><table><thead><tr><th>Description</th><th>Category</th><th>Amount</th><th>Date</th><th>Approved</th></tr></thead><tbody>
          {expenses.map((e: any) => <tr key={e.id}><td>{e.description}</td><td><span className="badge badge-gray">{e.category}</span></td><td style={{ fontWeight: 600 }}>${e.amount?.toLocaleString()}</td><td>{e.expense_date || "-"}</td><td>{e.is_approved ? <span className="badge badge-green">Yes</span> : <span className="badge badge-yellow">Pending</span>}</td></tr>)}
        </tbody></table></div>
      )}
      {tab === "vendors" && (
        <div className="card"><table><thead><tr><th>Name</th><th>Contact</th><th>Email</th><th>Phone</th></tr></thead><tbody>
          {vendors.map((v: any) => <tr key={v.id}><td style={{ fontWeight: 500 }}>{v.name}</td><td>{v.contact_person || "-"}</td><td>{v.email || "-"}</td><td>{v.phone || "-"}</td></tr>)}
        </tbody></table></div>
      )}
      {tab === "purchase-orders" && (
        <div className="card"><table><thead><tr><th>PO Number</th><th>Status</th><th>Amount</th><th>Description</th></tr></thead><tbody>
          {pos.map((p: any) => <tr key={p.id}><td style={{ fontWeight: 500 }}>{p.po_number}</td><td><span className="badge badge-blue">{p.status}</span></td><td>${p.total_amount?.toLocaleString()}</td><td>{p.description || "-"}</td></tr>)}
        </tbody></table></div>
      )}
      {tab === "assets" && (
        <div className="card"><table><thead><tr><th>Name</th><th>Tag</th><th>Category</th><th>Status</th><th>Value</th><th>Location</th></tr></thead><tbody>
          {assets.map((a: any) => <tr key={a.id}><td style={{ fontWeight: 500 }}>{a.name}</td><td>{a.asset_tag || "-"}</td><td>{a.category || "-"}</td><td><span className="badge badge-blue">{a.status}</span></td><td>${a.current_value?.toLocaleString() || "-"}</td><td>{a.location || "-"}</td></tr>)}
        </tbody></table></div>
      )}
      {tab === "accounts" && (
        <div className="card"><table><thead><tr><th>Code</th><th>Name</th><th>Type</th><th>Balance</th></tr></thead><tbody>
          {accounts.map((a: any) => <tr key={a.id}><td style={{ fontWeight: 600 }}>{a.code}</td><td>{a.name}</td><td><span className="badge badge-blue">{a.account_type}</span></td><td>${a.balance?.toLocaleString()}</td></tr>)}
        </tbody></table></div>
      )}

      {tab === "budgets" && (
        <>
          <div className="card">
            <div className="card-header"><h3>Budgets</h3>
              <button className="btn btn-sm btn-primary" onClick={async () => {
                const name = prompt("Budget name:"); if (!name) return;
                const label = prompt("Line item label:"); const planned = parseFloat(prompt("Planned amount:") || "0");
                await createBudget({ project_id: projectId, name, lines: label ? [{ label, planned_amount: planned }] : [] });
                rBud();
              }}>+ New Budget</button>
            </div>
            <table><thead><tr><th>Name</th><th>Total</th><th>Period</th><th>Actions</th></tr></thead><tbody>
              {budgets.map((b: any) => <tr key={b.id}>
                <td style={{ fontWeight: 500 }}>{b.name}</td>
                <td>${b.total_amount?.toLocaleString()}</td>
                <td style={{ fontSize: "0.82rem" }}>{b.period_start || "-"} → {b.period_end || "-"}</td>
                <td><button className="btn btn-sm" onClick={() => setSelectedBudget(selectedBudget === b.id ? null : b.id)}>{selectedBudget === b.id ? "Hide" : "Variance"}</button></td>
              </tr>)}
            </tbody></table>
          </div>
          {variance && (
            <div className="card" style={{ marginTop: "1rem" }}>
              <div className="card-header"><h3>Variance</h3>
                <div>Planned: <b>${variance.total_planned?.toLocaleString()}</b> / Actual: <b>${variance.total_actual?.toLocaleString()}</b> / Variance: <b style={{ color: variance.total_variance >= 0 ? "var(--success)" : "var(--danger)" }}>${variance.total_variance?.toLocaleString()}</b></div>
              </div>
              <table><thead><tr><th>Line</th><th>Category</th><th>Planned</th><th>Actual</th><th>Variance</th><th>% Used</th></tr></thead><tbody>
                {variance.lines?.map((l: any) => <tr key={l.line_id}>
                  <td>{l.label}</td><td>{l.category || "-"}</td>
                  <td>${l.planned?.toLocaleString()}</td><td>${l.actual?.toLocaleString()}</td>
                  <td style={{ color: l.variance >= 0 ? "var(--success)" : "var(--danger)", fontWeight: 600 }}>${l.variance?.toLocaleString()}</td>
                  <td>{l.pct_used}%</td>
                </tr>)}
              </tbody></table>
            </div>
          )}
        </>
      )}

      {tab === "aging" && aging && (
        <>
          <div className="stats-grid" style={{ marginBottom: "1rem" }}>
            {Object.entries(aging.buckets || {}).map(([k, v]: any) => <div key={k} className="stat-card"><div className="label">{k.replace(/_/g, "-")} days</div><div className="value">${v?.toLocaleString()}</div></div>)}
          </div>
          <div className="card">
            <div className="card-header"><h3>Outstanding Invoices</h3></div>
            <table><thead><tr><th>Invoice</th><th>Bucket</th><th>Due</th><th>Outstanding</th><th>Actions</th></tr></thead><tbody>
              {aging.invoices?.map((i: any) => <tr key={i.id}>
                <td style={{ fontWeight: 500 }}>{i.invoice_number}</td>
                <td><span className="badge badge-blue">{i.bucket}</span></td>
                <td>{i.due_date || "-"}</td>
                <td style={{ fontWeight: 600 }}>${i.outstanding?.toLocaleString()}</td>
                <td><button className="btn btn-sm" onClick={async () => {
                  const amt = parseFloat(prompt(`Payment amount (owed: $${i.outstanding}):`) || "0");
                  if (!amt) return;
                  await createPayment({ invoice_id: i.id, amount: amt });
                  rInv();
                }}>Record Payment</button></td>
              </tr>)}
            </tbody></table>
          </div>
        </>
      )}

      {tab === "recurring" && (
        <div className="card">
          <div className="card-header"><h3>Recurring Invoices</h3>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-sm" onClick={async () => { const r: any = await runRecurring(); alert(`Generated ${r.data?.count || 0}`); rRec(); rInv(); }}>Run Due</button>
              <button className="btn btn-sm btn-primary" onClick={async () => {
                const name = prompt("Template name:"); if (!name) return;
                const amt = parseFloat(prompt("Amount:") || "0");
                const freq = prompt("Frequency (weekly/monthly/quarterly/yearly):", "monthly") || "monthly";
                await createRecurring({ template_name: name, amount: amt, frequency: freq });
                rRec();
              }}>+ New</button>
            </div>
          </div>
          <table><thead><tr><th>Template</th><th>Amount</th><th>Frequency</th><th>Next Run</th><th>Active</th></tr></thead><tbody>
            {recurring.map((r: any) => <tr key={r.id}>
              <td style={{ fontWeight: 500 }}>{r.template_name}</td>
              <td>${r.amount?.toLocaleString()}</td>
              <td><span className="badge badge-blue">{r.frequency}</span></td>
              <td>{r.next_run || "-"}</td>
              <td>{r.is_active ? <span className="badge badge-green">Yes</span> : <span className="badge badge-gray">No</span>}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "tax" && tax && (
        <>
          <div className="stats-grid" style={{ marginBottom: "1rem" }}>
            <div className="stat-card"><div className="label">Collected</div><div className="value">${tax.collected?.toLocaleString()}</div></div>
            <div className="stat-card"><div className="label">Paid</div><div className="value">${tax.paid?.toLocaleString()}</div></div>
            <div className="stat-card"><div className="label">Net Owed</div><div className="value" style={{ color: tax.net_owed > 0 ? "var(--danger)" : "var(--success)" }}>${tax.net_owed?.toLocaleString()}</div></div>
          </div>
          <div className="card"><h3 style={{ marginBottom: "0.75rem" }}>By Rate</h3>
            <table><thead><tr><th>Rate</th><th>Taxable Amount</th><th>Tax</th></tr></thead><tbody>
              {tax.by_rate?.map((r: any) => <tr key={r.rate}>
                <td>{r.rate}%</td><td>${r.taxable?.toLocaleString()}</td><td style={{ fontWeight: 600 }}>${r.tax?.toLocaleString()}</td>
              </tr>)}
            </tbody></table>
          </div>
        </>
      )}

      {tab === "trial-balance" && trialBal && (
        <div className="card">
          <div className="card-header"><h3>Trial Balance</h3>
            <span>Debit: <b>${trialBal.total_debit?.toLocaleString()}</b> / Credit: <b>${trialBal.total_credit?.toLocaleString()}</b> {trialBal.balanced ? <span className="badge badge-green">Balanced</span> : <span className="badge badge-red">Out of balance</span>}</span>
          </div>
          <table><thead><tr><th>Code</th><th>Name</th><th>Type</th><th>Debit</th><th>Credit</th></tr></thead><tbody>
            {trialBal.rows?.map((r: any) => <tr key={r.code}>
              <td style={{ fontWeight: 600 }}>{r.code}</td><td>{r.name}</td>
              <td><span className="badge badge-gray">{r.account_type}</span></td>
              <td>{r.debit ? `$${r.debit.toLocaleString()}` : ""}</td>
              <td>{r.credit ? `$${r.credit.toLocaleString()}` : ""}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "journal" && (
        <div className="card">
          <div className="card-header"><h3>Journal Entries</h3>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              if (accounts.length < 2) { alert("Need at least 2 accounts"); return; }
              const num = prompt("Entry #:") || `J-${Date.now().toString().slice(-6)}`;
              const amt = parseFloat(prompt("Amount:") || "0"); if (!amt) return;
              const debit = accounts[0]; const credit = accounts[1];
              await createJournal({ entry_number: num, memo: "Manual", lines: [
                { account_id: debit.id, debit: amt, credit: 0 },
                { account_id: credit.id, debit: 0, credit: amt },
              ]});
              rJour();
            }}>+ New Entry</button>
          </div>
          <table><thead><tr><th>Entry #</th><th>Date</th><th>Memo</th><th>Posted</th><th>Actions</th></tr></thead><tbody>
            {journal.map((j: any) => <tr key={j.id}>
              <td style={{ fontWeight: 500 }}>{j.entry_number}</td>
              <td>{j.entry_date || "-"}</td>
              <td style={{ fontSize: "0.82rem" }}>{j.memo || "-"}</td>
              <td>{j.is_posted ? <span className="badge badge-green">Yes</span> : <span className="badge badge-yellow">No</span>}</td>
              <td>{!j.is_posted && <button className="btn btn-sm" onClick={async () => { await postJournal(j.id); rJour(); }}>Post</button>}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "bank" && (
        <div className="card">
          <div className="card-header"><h3>Bank Transactions</h3>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-sm" onClick={async () => { const r: any = await autoMatchBank(); alert(`Matched ${r.data?.matched || 0}`); rBank(); }}>Auto Match</button>
              <button className="btn btn-sm btn-primary" onClick={async () => {
                const d = prompt("Description:"); if (!d) return;
                const amt = parseFloat(prompt("Amount (negative for debit):") || "0");
                await createBank({ description: d, amount: amt });
                rBank();
              }}>+ New</button>
            </div>
          </div>
          <table><thead><tr><th>Date</th><th>Description</th><th>Amount</th><th>Reconciled</th><th>Matched Invoice</th></tr></thead><tbody>
            {bank.map((t: any) => <tr key={t.id}>
              <td>{t.txn_date || "-"}</td>
              <td>{t.description}</td>
              <td style={{ fontWeight: 600, color: t.amount >= 0 ? "var(--success)" : "var(--danger)" }}>${t.amount?.toLocaleString()}</td>
              <td>{t.is_reconciled ? <span className="badge badge-green">Yes</span> : <span className="badge badge-gray">No</span>}</td>
              <td style={{ fontSize: "0.75rem" }}>{t.matched_invoice_id ? `${t.matched_invoice_id.slice(0, 8)}…` : "-"}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "inventory" && (
        <>
          <div className="card">
            <div className="card-header"><h3>Warehouses</h3>
              <button className="btn btn-sm btn-primary" onClick={async () => {
                const code = prompt("Code:"); if (!code) return;
                const name = prompt("Name:") || code;
                await createWarehouse({ code, name }); rWh();
              }}>+ Warehouse</button>
            </div>
            <table><thead><tr><th>Code</th><th>Name</th><th>Active</th></tr></thead><tbody>
              {warehouses.map((w: any) => <tr key={w.id}><td style={{ fontWeight: 600 }}>{w.code}</td><td>{w.name}</td><td>{w.is_active ? "Yes" : "No"}</td></tr>)}
            </tbody></table>
          </div>
          <div className="card" style={{ marginTop: "1rem" }}>
            <div className="card-header"><h3>Products</h3>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button className="btn btn-sm btn-primary" onClick={async () => {
                  const sku = prompt("SKU:"); if (!sku) return;
                  const name = prompt("Name:") || sku;
                  const cost = parseFloat(prompt("Unit cost:") || "0");
                  const reorder = parseInt(prompt("Reorder point:") || "0");
                  await createProduct({ sku, name, unit_cost: cost, reorder_point: reorder });
                  rProd();
                }}>+ Product</button>
                <button className="btn btn-sm" onClick={async () => {
                  if (!products.length || !warehouses.length) { alert("Need product + warehouse"); return; }
                  const type = prompt("Type (receipt/issue/adjust):", "receipt") || "receipt";
                  const qty = parseFloat(prompt("Quantity:") || "0"); if (!qty) return;
                  await createMovement({ product_id: products[0].id, warehouse_id: warehouses[0].id, movement_type: type, quantity: qty });
                  rStock();
                }}>+ Movement</button>
              </div>
            </div>
            <table><thead><tr><th>SKU</th><th>Name</th><th>Cost</th><th>Price</th><th>Reorder @</th></tr></thead><tbody>
              {products.map((p: any) => <tr key={p.id}><td style={{ fontWeight: 600 }}>{p.sku}</td><td>{p.name}</td><td>${p.unit_cost}</td><td>${p.unit_price}</td><td>{p.reorder_point}</td></tr>)}
            </tbody></table>
          </div>
          <div className="card" style={{ marginTop: "1rem" }}>
            <h3 style={{ marginBottom: "0.5rem" }}>Stock Levels</h3>
            <table><thead><tr><th>SKU</th><th>Name</th><th>Warehouse</th><th>Qty</th><th>Reorder?</th></tr></thead><tbody>
              {stock.map((s: any, i: number) => <tr key={i}>
                <td style={{ fontWeight: 600 }}>{s.sku}</td><td>{s.name}</td><td>{s.warehouse}</td>
                <td>{s.quantity}</td>
                <td>{s.below_reorder ? <span className="badge badge-red">Low</span> : <span className="badge badge-green">OK</span>}</td>
              </tr>)}
            </tbody></table>
          </div>
          {reorder.length > 0 && (
            <div className="card" style={{ marginTop: "1rem", borderLeft: "3px solid var(--danger)" }}>
              <h3 style={{ marginBottom: "0.5rem" }}>Reorder needed ({reorder.length})</h3>
              {reorder.map((r: any, i: number) => <div key={i} style={{ fontSize: "0.85rem" }}>{r.sku} @ {r.warehouse}: {r.quantity}</div>)}
            </div>
          )}
        </>
      )}

      {tab === "depreciation" && (
        <div className="card">
          <div className="card-header"><h3>Depreciation Schedules</h3>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-sm" onClick={async () => { const r: any = await runDep(); alert(`Posted ${r.data?.schedules_posted || 0} / $${r.data?.total_depreciation || 0}`); rDep(); }}>Run Now</button>
              <button className="btn btn-sm btn-primary" onClick={async () => {
                if (!assets.length) { alert("No assets"); return; }
                const asset_id = prompt("Asset ID (copy from Assets tab):") || assets[0].id;
                const months = parseInt(prompt("Useful life (months):") || "60");
                const salvage = parseFloat(prompt("Salvage value:") || "0");
                const start = prompt("Start date (YYYY-MM-DD):", new Date().toISOString().slice(0, 10)) || "";
                await createDep({ asset_id, useful_life_months: months, salvage_value: salvage, start_date: start });
                rDep();
              }}>+ Schedule</button>
            </div>
          </div>
          <table><thead><tr><th>Asset</th><th>Method</th><th>Life (mo)</th><th>Salvage</th><th>Accumulated</th><th>Last Run</th></tr></thead><tbody>
            {dep.map((d: any) => <tr key={d.id}>
              <td style={{ fontSize: "0.75rem" }}>{d.asset_id.slice(0, 8)}…</td>
              <td><span className="badge badge-blue">{d.method}</span></td>
              <td>{d.useful_life_months}</td>
              <td>${d.salvage_value}</td>
              <td style={{ fontWeight: 600 }}>${d.accumulated?.toLocaleString()}</td>
              <td style={{ fontSize: "0.82rem" }}>{d.last_run || "—"}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "credit-notes" && (
        <div className="card">
          <div className="card-header"><h3>Credit Notes</h3>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const invId = prompt("Invoice ID:"); if (!invId) return;
              const num = prompt("CN number:") || `CN-${Date.now().toString().slice(-6)}`;
              const amt = parseFloat(prompt("Amount:") || "0");
              const reason = prompt("Reason:") || "";
              await createCN({ invoice_id: invId, cn_number: num, amount: amt, reason });
              rCN();
            }}>+ New</button>
          </div>
          <table><thead><tr><th>CN Number</th><th>Invoice</th><th>Amount</th><th>Reason</th><th>Date</th></tr></thead><tbody>
            {creditNotes.map((c: any) => <tr key={c.id}>
              <td style={{ fontWeight: 500 }}>{c.cn_number}</td>
              <td style={{ fontSize: "0.75rem" }}>{c.invoice_id.slice(0, 8)}…</td>
              <td>${c.amount?.toLocaleString()}</td>
              <td style={{ fontSize: "0.82rem" }}>{c.reason || "-"}</td>
              <td>{c.issued_date}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "pnl" && pnl && (
        <>
          <div className="stats-grid" style={{ marginBottom: "1rem" }}>
            <div className="stat-card"><div className="label">Revenue</div><div className="value" style={{ color: "var(--success)" }}>${pnl.revenue?.toLocaleString()}</div></div>
            <div className="stat-card"><div className="label">Expenses</div><div className="value">${pnl.expenses?.toLocaleString()}</div></div>
            <div className="stat-card"><div className="label">Net Income</div><div className="value" style={{ color: pnl.net_income >= 0 ? "var(--success)" : "var(--danger)" }}>${pnl.net_income?.toLocaleString()}</div></div>
          </div>
          <div className="card"><h3 style={{ marginBottom: "0.75rem" }}>Accounts</h3>
            <table><thead><tr><th>Code</th><th>Name</th><th>Type</th><th>Balance</th></tr></thead><tbody>
              {pnl.accounts?.map((a: any) => <tr key={a.code}><td style={{ fontWeight: 600 }}>{a.code}</td><td>{a.name}</td><td><span className="badge badge-blue">{a.type}</span></td><td>${a.balance?.toLocaleString()}</td></tr>)}
            </tbody></table>
          </div>
        </>
      )}

      {tab === "balance-sheet" && bs && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <div className="card"><h3>Assets</h3>
            <table><tbody>{bs.assets?.map((a: any) => <tr key={a.code}><td style={{ fontFamily: "monospace" }}>{a.code}</td><td>{a.name}</td><td style={{ textAlign: "right" }}>${a.balance?.toLocaleString()}</td></tr>)}
              <tr style={{ borderTop: "2px solid var(--gray-300)", fontWeight: 700 }}><td colSpan={2}>Total Assets</td><td style={{ textAlign: "right" }}>${bs.total_assets?.toLocaleString()}</td></tr>
            </tbody></table>
          </div>
          <div>
            <div className="card"><h3>Liabilities</h3>
              <table><tbody>{bs.liabilities?.map((a: any) => <tr key={a.code}><td style={{ fontFamily: "monospace" }}>{a.code}</td><td>{a.name}</td><td style={{ textAlign: "right" }}>${a.balance?.toLocaleString()}</td></tr>)}
                <tr style={{ borderTop: "2px solid var(--gray-300)", fontWeight: 700 }}><td colSpan={2}>Total Liabilities</td><td style={{ textAlign: "right" }}>${bs.total_liabilities?.toLocaleString()}</td></tr>
              </tbody></table>
            </div>
            <div className="card" style={{ marginTop: "1rem" }}><h3>Equity</h3>
              <table><tbody>{bs.equity?.map((a: any) => <tr key={a.code}><td style={{ fontFamily: "monospace" }}>{a.code}</td><td>{a.name}</td><td style={{ textAlign: "right" }}>${a.balance?.toLocaleString()}</td></tr>)}
                <tr style={{ borderTop: "2px solid var(--gray-300)", fontWeight: 700 }}><td colSpan={2}>Total Equity</td><td style={{ textAlign: "right" }}>${bs.total_equity?.toLocaleString()}</td></tr>
              </tbody></table>
            </div>
          </div>
        </div>
      )}

      {tab === "cash-flow" && cashFlow && (
        <>
          <div className="stats-grid" style={{ marginBottom: "1rem" }}>
            <div className="stat-card"><div className="label">Inflows ({cashFlow.horizon_days}d)</div><div className="value" style={{ color: "var(--success)" }}>${cashFlow.total_inflow?.toLocaleString()}</div></div>
            <div className="stat-card"><div className="label">Outflows</div><div className="value" style={{ color: "var(--danger)" }}>${cashFlow.total_outflow?.toLocaleString()}</div></div>
            <div className="stat-card"><div className="label">Net</div><div className="value" style={{ color: cashFlow.net >= 0 ? "var(--success)" : "var(--danger)" }}>${cashFlow.net?.toLocaleString()}</div></div>
          </div>
          <div className="card">
            <table><thead><tr><th>Date</th><th>Label</th><th>Amount</th><th>Running</th></tr></thead><tbody>
              {cashFlow.events?.map((e: any, i: number) => <tr key={i}>
                <td>{e.date}</td><td>{e.label}</td>
                <td style={{ fontWeight: 600, color: e.amount >= 0 ? "var(--success)" : "var(--danger)" }}>${e.amount?.toLocaleString()}</td>
                <td>${e.running?.toLocaleString()}</td>
              </tr>)}
            </tbody></table>
          </div>
        </>
      )}

      {tab === "requisitions" && (
        <div className="card">
          <div className="card-header"><h3>Purchase Requisitions</h3>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const num = prompt("Requisition #:") || `REQ-${Date.now().toString().slice(-6)}`;
              const desc = prompt("Item description:"); if (!desc) return;
              const qty = parseFloat(prompt("Quantity:") || "1");
              const price = parseFloat(prompt("Unit price:") || "0");
              const just = prompt("Justification:") || "";
              await createReq({ project_id: projectId, req_number: num, justification: just,
                items: [{ description: desc, quantity: qty, unit_price: price }] });
              rReqs();
            }}>+ New</button>
          </div>
          <table><thead><tr><th>Number</th><th>Status</th><th>Amount</th><th>Needed By</th><th>Actions</th></tr></thead><tbody>
            {reqs.map((r: any) => <tr key={r.id}>
              <td style={{ fontWeight: 500 }}>{r.req_number}</td>
              <td>
                <select value={r.status} onChange={e => { updateReqStatus({ id: r.id, status: e.target.value }); rReqs(); }} style={{ fontSize: "0.8rem", padding: "0.2rem" }}>
                  {["draft","submitted","approved","rejected","converted"].map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </td>
              <td style={{ fontWeight: 600 }}>${r.estimated_amount?.toLocaleString()}</td>
              <td>{r.needed_by || "-"}</td>
              <td>
                {r.status === "approved" && !r.converted_po_id && vendors.length > 0 && (
                  <button className="btn btn-sm" onClick={async () => {
                    await convertReq({ id: r.id, body: { vendor_id: vendors[0].id } });
                    rReqs(); rPo();
                  }}>→ PO</button>
                )}
                {r.converted_po_id && <span className="badge badge-green">Converted</span>}
              </td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Add {tab.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</h3>
            <form onSubmit={handleSubmit}>
              {Object.keys(form).map(k => (
                <div className="form-group" key={k}>
                  <label>{k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</label>
                  {k === "account_type" ? (
                    <select value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}>{["asset","liability","equity","revenue","expense"].map(t => <option key={t} value={t}>{t}</option>)}</select>
                  ) : k === "category" ? (
                    <select value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}>{["labor","materials","equipment","travel","software","consulting","overhead","other"].map(t => <option key={t} value={t}>{t}</option>)}</select>
                  ) : k === "vendor_id" ? (
                    <select value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}>{vendors.map((v: any) => <option key={v.id} value={v.id}>{v.name}</option>)}</select>
                  ) : (
                    <input value={form[k] || ""} onChange={e => setForm({ ...form, [k]: e.target.value })} type={typeof form[k] === "number" ? "number" : "text"} required={k === "name" || k === "description" || k === "code" || k === "invoice_number" || k === "po_number"} />
                  )}
                </div>
              ))}
              <div className="modal-actions"><button type="button" className="btn" onClick={() => setShowForm(false)}>Cancel</button><button type="submit" className="btn btn-primary">Save</button></div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
