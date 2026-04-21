import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  useGetCrmDashboardQuery, useGetCompaniesQuery, useCreateCompanyMutation,
  useGetCrmContactsQuery, useCreateCrmContactMutation, useGetLeadsQuery, useCreateLeadMutation,
  useUpdateLeadStatusMutation, useGetOpportunitiesQuery, useCreateOpportunityMutation,
  useUpdateOpportunityStageMutation, useGetInteractionsQuery, useCreateInteractionMutation,
  useGetForecastQuery, useScoreAllLeadsMutation, useGetQuotesQuery, useCreateQuoteMutation,
  useConvertQuoteMutation, useGetCampaignsQuery, useCreateCampaignMutation,
  useGetFollowUpsDueQuery, useCompleteFollowUpMutation, useGetCompanyTimelineQuery,
  useGetEmailsQuery, useIngestEmailMutation,
  useGetContractsQuery, useCreateContractMutation, useGetContractMetricsQuery, useUpdateContractStatusMutation,
  useGetCommissionRulesQuery, useCreateCommissionRuleMutation, useComputeCommissionsMutation,
  useGetCommissionsQuery, usePayCommissionMutation,
  useGetTerritoriesQuery, useCreateTerritoryMutation, useAutoAssignLeadsMutation,
  useGetDripsQuery, useCreateDripMutation, useEnrollDripMutation, useDripTickMutation,
  useComputeHealthMutation, useGetHealthQuery,
} from "../services/api";
import BoardContainer from "../components/dnd/BoardContainer";
import BoardColumn from "../components/dnd/BoardColumn";
import DraggableCard from "../components/dnd/DraggableCard";

const TABS = ["dashboard", "companies", "contacts", "leads", "opportunities", "interactions",
  "quotes", "campaigns", "forecast", "follow-ups", "timeline",
  "emails", "contracts", "commissions", "territories", "drips", "health"] as const;
const OPP_STAGES = ["prospecting", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"];
const LEAD_STATUSES = ["new", "contacted", "qualified", "unqualified", "converted"];

export default function CrmPage() {
  const { tab: urlTab } = useParams<{ tab?: string }>();
  const [tab, setTab] = useState<typeof TABS[number]>(
    (TABS as readonly string[]).includes(urlTab || "") ? (urlTab as typeof TABS[number]) : "dashboard"
  );
  useEffect(() => {
    if (urlTab && (TABS as readonly string[]).includes(urlTab)) setTab(urlTab as typeof TABS[number]);
  }, [urlTab]);
  const { data: dash } = useGetCrmDashboardQuery();
  const { data: companies = [], refetch: rCo } = useGetCompaniesQuery();
  const { data: contacts = [], refetch: rCt } = useGetCrmContactsQuery(undefined);
  const { data: leads = [], refetch: rLe } = useGetLeadsQuery();
  const { data: opps = [], refetch: rOp } = useGetOpportunitiesQuery();
  const { data: interactions = [], refetch: rIn } = useGetInteractionsQuery({});
  const [createCompany] = useCreateCompanyMutation();
  const [createContact] = useCreateCrmContactMutation();
  const [createLead] = useCreateLeadMutation();
  const [createOpp] = useCreateOpportunityMutation();
  const [createInteraction] = useCreateInteractionMutation();
  const [updateLeadStatus] = useUpdateLeadStatusMutation();
  const [updateOppStage] = useUpdateOpportunityStageMutation();
  const [scoreAll] = useScoreAllLeadsMutation();
  const { data: forecast } = useGetForecastQuery(undefined, { skip: tab !== "forecast" });
  const { data: quotes = [], refetch: rQu } = useGetQuotesQuery(undefined, { skip: tab !== "quotes" });
  const [createQuote] = useCreateQuoteMutation();
  const [convertQuote] = useConvertQuoteMutation();
  const { data: campaigns = [], refetch: rCam } = useGetCampaignsQuery(undefined, { skip: tab !== "campaigns" });
  const [createCampaign] = useCreateCampaignMutation();
  const { data: followUps = [], refetch: rFol } = useGetFollowUpsDueQuery(undefined, { skip: tab !== "follow-ups" });
  const [completeFollowUp] = useCompleteFollowUpMutation();
  const [timelineCompany, setTimelineCompany] = useState<string | null>(null);
  const { data: timeline } = useGetCompanyTimelineQuery(timelineCompany!, { skip: !timelineCompany });
  const { data: emails = [], refetch: rEmails } = useGetEmailsQuery({}, { skip: tab !== "emails" });
  const [ingestEmail] = useIngestEmailMutation();
  const { data: contracts = [], refetch: rContracts } = useGetContractsQuery(undefined, { skip: tab !== "contracts" });
  const [createContract] = useCreateContractMutation();
  const { data: contractMetrics } = useGetContractMetricsQuery(undefined, { skip: tab !== "contracts" });
  const [updateContractStatus] = useUpdateContractStatusMutation();
  const { data: commRules = [], refetch: rCommRules } = useGetCommissionRulesQuery(undefined, { skip: tab !== "commissions" });
  const [createCommRule] = useCreateCommissionRuleMutation();
  const [computeComm] = useComputeCommissionsMutation();
  const { data: commissions = [], refetch: rComm } = useGetCommissionsQuery(undefined, { skip: tab !== "commissions" });
  const [payComm] = usePayCommissionMutation();
  const { data: territories = [], refetch: rTerr } = useGetTerritoriesQuery(undefined, { skip: tab !== "territories" });
  const [createTerritory] = useCreateTerritoryMutation();
  const [autoAssign] = useAutoAssignLeadsMutation();
  const { data: drips = [], refetch: rDrips } = useGetDripsQuery(undefined, { skip: tab !== "drips" });
  const [createDrip] = useCreateDripMutation();
  const [enrollDrip] = useEnrollDripMutation();
  const [dripTick] = useDripTickMutation();
  const [computeHealthFn] = useComputeHealthMutation();
  const { data: health = [], refetch: rHealth } = useGetHealthQuery(undefined, { skip: tab !== "health" });
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<any>({});

  const openForm = (defaults: any = {}) => { setForm(defaults); setShowForm(true); };
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (tab === "companies") { await createCompany(form); rCo(); }
    else if (tab === "contacts") { await createContact(form); rCt(); }
    else if (tab === "leads") { await createLead(form); rLe(); }
    else if (tab === "opportunities") { await createOpp(form); rOp(); }
    else if (tab === "interactions") { await createInteraction(form); rIn(); }
    setShowForm(false);
  };

  return (
    <div>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "0.3rem" }}>CRM System</h2>
        <p style={{ color: "var(--gray-400)", fontSize: "0.85rem" }}>Customer relationship management, sales pipeline, leads</p>
      </div>

      <div style={{ display: "flex", gap: "0.35rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        {TABS.map(t => <button key={t} className={`btn btn-sm ${tab === t ? "btn-primary" : ""}`} onClick={() => setTab(t)}>{t.charAt(0).toUpperCase() + t.slice(1)}</button>)}
      </div>

      {tab === "dashboard" && dash && (
        <>
          <div className="stats-grid">
            <div className="stat-card"><div className="label">Companies</div><div className="value">{dash.companies}</div></div>
            <div className="stat-card"><div className="label">Contacts</div><div className="value">{dash.contacts}</div></div>
            <div className="stat-card"><div className="label">Active Leads</div><div className="value">{dash.active_leads}</div></div>
            <div className="stat-card"><div className="label">Open Opportunities</div><div className="value">{dash.open_opportunities}</div></div>
            <div className="stat-card"><div className="label">Pipeline Value</div><div className="value">${dash.pipeline_value?.toLocaleString()}</div></div>
            <div className="stat-card"><div className="label">Won Revenue</div><div className="value" style={{ color: "var(--success)" }}>${dash.won_value?.toLocaleString()}</div></div>
          </div>
          {dash.pipeline_by_stage?.length > 0 && (
            <div className="card"><h3 style={{ marginBottom: "0.75rem" }}>Pipeline by Stage</h3><table><thead><tr><th>Stage</th><th>Count</th><th>Value</th></tr></thead><tbody>
              {dash.pipeline_by_stage.map((s: any) => <tr key={s.stage}><td><span className="badge badge-blue">{s.stage.replace(/_/g, " ")}</span></td><td>{s.count}</td><td>${s.value?.toLocaleString()}</td></tr>)}
            </tbody></table></div>
          )}
        </>
      )}

      {tab !== "dashboard" && (
        <div className="card-header" style={{ marginBottom: "1rem" }}>
          <span />
          <button className="btn btn-primary btn-sm" onClick={() => openForm(tab === "companies" ? { name: "", industry: "" } : tab === "contacts" ? { first_name: "", last_name: "", email: "" } : tab === "leads" ? { contact_name: "", email: "", source: "other" } : tab === "opportunities" ? { title: "", amount: 0, probability: 50 } : { subject: "", interaction_type: "note" })}>+ Add</button>
        </div>
      )}

      {tab === "companies" && (
        <div className="card"><table><thead><tr><th>Name</th><th>Industry</th><th>Website</th><th>Revenue</th><th>Employees</th></tr></thead><tbody>
          {companies.map((c: any) => <tr key={c.id}><td style={{ fontWeight: 500 }}>{c.name}</td><td>{c.industry || "-"}</td><td>{c.website || "-"}</td><td>{c.annual_revenue ? `$${c.annual_revenue.toLocaleString()}` : "-"}</td><td>{c.employee_count || "-"}</td></tr>)}
        </tbody></table></div>
      )}
      {tab === "contacts" && (
        <div className="card"><table><thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Title</th></tr></thead><tbody>
          {contacts.map((c: any) => <tr key={c.id}><td style={{ fontWeight: 500 }}>{c.first_name} {c.last_name || ""}</td><td>{c.email || "-"}</td><td>{c.phone || "-"}</td><td>{c.job_title || "-"}</td></tr>)}
        </tbody></table></div>
      )}
      {tab === "leads" && (
        <div className="card"><table><thead><tr><th>Name</th><th>Company</th><th>Source</th><th>Status</th><th>Value</th></tr></thead><tbody>
          {leads.map((l: any) => <tr key={l.id}><td style={{ fontWeight: 500 }}>{l.contact_name}</td><td>{l.company_name || "-"}</td><td><span className="badge badge-gray">{l.source}</span></td><td>
            <select value={l.status} onChange={e => { updateLeadStatus({ id: l.id, status: e.target.value }); rLe(); }} style={{ fontSize: "0.8rem", padding: "0.2rem" }}>
              {LEAD_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </td><td>{l.estimated_value ? `$${l.estimated_value.toLocaleString()}` : "-"}</td></tr>)}
        </tbody></table></div>
      )}
      {tab === "opportunities" && (
        <>
          <BoardContainer
            onDragEnd={(itemId, newStage) => { updateOppStage({ id: itemId, stage: newStage }); rOp(); }}
            renderOverlay={(activeId) => {
              const o = opps.find((x: any) => x.id === activeId);
              return o ? <div className="board-card" style={{ opacity: 0.9, boxShadow: "0 8px 24px rgba(0,0,0,0.15)", width: 240 }}><div className="title">{o.title}</div></div> : null;
            }}
          >
          <div className="board" style={{ marginBottom: "1rem" }}>
            {OPP_STAGES.map(stage => (
              <BoardColumn key={stage} id={stage} title={stage.replace(/_/g, " ")} count={opps.filter((o: any) => o.stage === stage).length}>
                {opps.filter((o: any) => o.stage === stage).map((o: any) => (
                  <DraggableCard key={o.id} id={o.id}>
                    <div className="title">{o.title}</div>
                    <div className="meta">{o.amount ? `$${o.amount.toLocaleString()}` : ""} {o.probability ? `${o.probability}%` : ""}</div>
                  </DraggableCard>
                ))}
              </BoardColumn>
            ))}
          </div>
          </BoardContainer>
        </>
      )}
      {tab === "interactions" && (
        <div className="card"><table><thead><tr><th>Type</th><th>Subject</th><th>Date</th><th>Notes</th></tr></thead><tbody>
          {interactions.map((i: any) => <tr key={i.id}><td><span className="badge badge-blue">{i.interaction_type}</span></td><td style={{ fontWeight: 500 }}>{i.subject}</td><td>{i.interaction_date || "-"}</td><td style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{i.body?.slice(0, 80) || "-"}</td></tr>)}
        </tbody></table></div>
      )}

      {tab === "quotes" && (
        <div className="card">
          <div className="card-header"><h3>Quotes</h3>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const num = prompt("Quote number:") || `Q-${Date.now().toString().slice(-6)}`;
              const desc = prompt("Line item description:"); const price = parseFloat(prompt("Unit price:") || "0");
              if (!desc || !price) return;
              await createQuote({ quote_number: num, items: [{ description: desc, quantity: 1, unit_price: price }] });
              rQu();
            }}>+ New Quote</button>
          </div>
          <table><thead><tr><th>Number</th><th>Status</th><th>Total</th><th>Valid</th><th>Actions</th></tr></thead><tbody>
            {quotes.map((q: any) => <tr key={q.id}>
              <td style={{ fontWeight: 500 }}>{q.quote_number}</td>
              <td><span className="badge badge-blue">{q.status}</span></td>
              <td style={{ fontWeight: 600 }}>${q.total?.toLocaleString()}</td>
              <td>{q.valid_until || "-"}</td>
              <td>{!q.invoice_id ? <button className="btn btn-sm" onClick={async () => { await convertQuote(q.id); rQu(); }}>Convert to Invoice</button> : <span className="badge badge-green">Converted</span>}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "campaigns" && (
        <div className="card">
          <div className="card-header"><h3>Campaigns</h3>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const name = prompt("Campaign name:"); if (!name) return;
              const budget = parseFloat(prompt("Budget:") || "0");
              await createCampaign({ name, budget, actual_cost: 0, status: "planned" });
              rCam();
            }}>+ New Campaign</button>
          </div>
          <table><thead><tr><th>Name</th><th>Status</th><th>Budget</th><th>Actual</th><th>Dates</th></tr></thead><tbody>
            {campaigns.map((c: any) => <tr key={c.id}>
              <td style={{ fontWeight: 500 }}>{c.name}</td>
              <td><span className="badge badge-blue">{c.status}</span></td>
              <td>${c.budget?.toLocaleString()}</td>
              <td>${c.actual_cost?.toLocaleString()}</td>
              <td style={{ fontSize: "0.82rem" }}>{c.start_date || "-"} → {c.end_date || "-"}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "forecast" && forecast && (
        <>
          <div className="stats-grid" style={{ marginBottom: "1rem" }}>
            <div className="stat-card"><div className="label">Weighted Pipeline</div><div className="value" style={{ color: "var(--success)" }}>${forecast.weighted_total?.toLocaleString()}</div></div>
          </div>
          <div className="card"><h3 style={{ marginBottom: "0.75rem" }}>By Stage</h3>
            <table><thead><tr><th>Stage</th><th>Count</th><th>Amount</th><th>Weighted</th></tr></thead><tbody>
              {forecast.by_stage?.map((s: any) => <tr key={s.stage}>
                <td><span className="badge badge-blue">{s.stage.replace(/_/g, " ")}</span></td>
                <td>{s.count}</td><td>${s.amount?.toLocaleString()}</td>
                <td style={{ fontWeight: 600 }}>${s.weighted?.toLocaleString()}</td>
              </tr>)}
            </tbody></table>
          </div>
          {forecast.by_month?.length > 0 && (
            <div className="card" style={{ marginTop: "1rem" }}><h3 style={{ marginBottom: "0.75rem" }}>By Expected Close Month</h3>
              <table><thead><tr><th>Month</th><th>Count</th><th>Amount</th><th>Weighted</th></tr></thead><tbody>
                {forecast.by_month.map((m: any) => <tr key={m.month}>
                  <td>{m.month}</td><td>{m.count}</td>
                  <td>${m.amount?.toLocaleString()}</td>
                  <td style={{ fontWeight: 600 }}>${m.weighted?.toLocaleString()}</td>
                </tr>)}
              </tbody></table>
            </div>
          )}
        </>
      )}

      {tab === "follow-ups" && (
        <div className="card">
          <div className="card-header"><h3>Due Follow-ups</h3>
            <button className="btn btn-sm" onClick={async () => { await scoreAll(); alert("Re-scored all leads"); rLe(); }}>Re-score Leads</button>
          </div>
          {followUps.length === 0 ? <div style={{ padding: "1rem", color: "var(--gray-500)" }}>Nothing due.</div> :
          <table><thead><tr><th>Subject</th><th>Due</th><th>Contact</th><th>Actions</th></tr></thead><tbody>
            {followUps.map((f: any) => <tr key={f.id}>
              <td style={{ fontWeight: 500 }}>{f.subject}</td>
              <td>{f.follow_up_date}</td>
              <td style={{ fontSize: "0.75rem" }}>{f.contact_id ? `${f.contact_id.slice(0, 8)}…` : "-"}</td>
              <td><button className="btn btn-sm" onClick={async () => { await completeFollowUp(f.id); rFol(); }}>Done</button></td>
            </tr>)}
          </tbody></table>}
        </div>
      )}

      {tab === "timeline" && (
        <div className="card">
          <div className="card-header"><h3>Customer Timeline</h3>
            <select value={timelineCompany || ""} onChange={e => setTimelineCompany(e.target.value || null)} style={{ padding: "0.3rem 0.5rem" }}>
              <option value="">Select company…</option>
              {companies.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          {timeline?.events?.length > 0 ? (
            <div style={{ padding: "0 1rem 1rem" }}>
              {timeline.events.map((ev: any, idx: number) => (
                <div key={idx} style={{ padding: "0.5rem 0", borderBottom: "1px solid var(--gray-100)", display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
                  <span className="badge badge-blue" style={{ minWidth: 90, textAlign: "center" }}>{ev.type}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500 }}>{ev.title}</div>
                    <div style={{ fontSize: "0.8rem", color: "var(--gray-500)" }}>{ev.detail}</div>
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--gray-500)" }}>{ev.date ? new Date(ev.date).toLocaleDateString() : ""}</div>
                </div>
              ))}
            </div>
          ) : timelineCompany ? <div style={{ padding: "1rem", color: "var(--gray-500)" }}>No events.</div> : null}
        </div>
      )}

      {tab === "emails" && (
        <div className="card">
          <div className="card-header"><h3>Emails (contact-linked)</h3>
            <button className="btn btn-sm btn-primary" onClick={async () => {
              const from = prompt("From email:"); if (!from) return;
              const to = prompt("To email:"); if (!to) return;
              const subject = prompt("Subject:") || "";
              const body = prompt("Body:") || "";
              await ingestEmail({ direction: "inbound", from_email: from, to_email: to, subject, body });
              rEmails();
            }}>+ Log Email</button>
          </div>
          <table><thead><tr><th>Dir</th><th>Subject</th><th>From</th><th>To</th><th>When</th></tr></thead><tbody>
            {emails.map((e: any) => <tr key={e.id}>
              <td><span className={`badge ${e.direction === "inbound" ? "badge-blue" : "badge-green"}`}>{e.direction}</span></td>
              <td style={{ fontWeight: 500 }}>{e.subject || "(no subject)"}</td>
              <td style={{ fontSize: "0.82rem" }}>{e.from_email}</td>
              <td style={{ fontSize: "0.82rem" }}>{e.to_email}</td>
              <td style={{ fontSize: "0.75rem" }}>{e.sent_at ? new Date(e.sent_at).toLocaleDateString() : ""}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "contracts" && (
        <>
          {contractMetrics && (
            <div className="stats-grid" style={{ marginBottom: "1rem" }}>
              <div className="stat-card"><div className="label">Active</div><div className="value">{contractMetrics.active_count}</div></div>
              <div className="stat-card"><div className="label">MRR</div><div className="value">${contractMetrics.mrr?.toLocaleString()}</div></div>
              <div className="stat-card"><div className="label">ARR</div><div className="value" style={{ color: "var(--success)" }}>${contractMetrics.arr?.toLocaleString()}</div></div>
              <div className="stat-card"><div className="label">Renewals ≤30d</div><div className="value" style={{ color: contractMetrics.renewals_due_30d?.length ? "var(--warning)" : "inherit" }}>{contractMetrics.renewals_due_30d?.length}</div></div>
              <div className="stat-card"><div className="label">Churned</div><div className="value" style={{ color: "var(--danger)" }}>{contractMetrics.churned_total}</div></div>
            </div>
          )}
          <div className="card">
            <div className="card-header"><h3>Contracts</h3>
              <button className="btn btn-sm btn-primary" onClick={async () => {
                if (!companies.length) { alert("Add a company first"); return; }
                const num = prompt("Contract #:") || `C-${Date.now().toString().slice(-6)}`;
                const amt = parseFloat(prompt("Amount:") || "0");
                const cycle = prompt("Billing (monthly/quarterly/yearly/one_time):", "monthly") || "monthly";
                const start = prompt("Start date (YYYY-MM-DD):", new Date().toISOString().slice(0, 10)) || "";
                await createContract({ company_id: companies[0].id, contract_number: num, amount: amt, billing_cycle: cycle, start_date: start, status: "active" });
                rContracts();
              }}>+ New</button>
            </div>
            <table><thead><tr><th>Number</th><th>Status</th><th>Cycle</th><th>Amount</th><th>MRR</th><th>Dates</th></tr></thead><tbody>
              {contracts.map((c: any) => <tr key={c.id}>
                <td style={{ fontWeight: 500 }}>{c.contract_number}</td>
                <td>
                  <select value={c.status} onChange={e => { updateContractStatus({ id: c.id, status: e.target.value }); rContracts(); }} style={{ fontSize: "0.8rem", padding: "0.2rem" }}>
                    {["draft","active","renewing","churned","expired"].map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </td>
                <td><span className="badge badge-blue">{c.billing_cycle}</span></td>
                <td style={{ fontWeight: 600 }}>${c.amount?.toLocaleString()}</td>
                <td>${c.mrr?.toLocaleString()}</td>
                <td style={{ fontSize: "0.82rem" }}>{c.start_date} → {c.end_date || "—"}</td>
              </tr>)}
            </tbody></table>
          </div>
        </>
      )}

      {tab === "commissions" && (
        <>
          <div className="card">
            <div className="card-header"><h3>Commission Rules</h3>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button className="btn btn-sm" onClick={async () => { const r: any = await computeComm(); alert(`Computed ${r.data?.created || 0}`); rComm(); }}>Compute for Won Opps</button>
                <button className="btn btn-sm btn-primary" onClick={async () => {
                  const name = prompt("Rule name:"); if (!name) return;
                  const pct = parseFloat(prompt("Percentage (e.g. 10):") || "0");
                  await createCommRule({ name, percentage: pct, min_amount: 0 });
                  rCommRules();
                }}>+ Rule</button>
              </div>
            </div>
            <table><thead><tr><th>Name</th><th>%</th><th>Min</th><th>Max</th><th>Active</th></tr></thead><tbody>
              {commRules.map((r: any) => <tr key={r.id}>
                <td style={{ fontWeight: 500 }}>{r.name}</td>
                <td>{r.percentage}%</td>
                <td>${r.min_amount}</td>
                <td>{r.max_amount ? `$${r.max_amount}` : "—"}</td>
                <td>{r.is_active ? "Yes" : "No"}</td>
              </tr>)}
            </tbody></table>
          </div>
          <div className="card" style={{ marginTop: "1rem" }}>
            <h3 style={{ marginBottom: "0.5rem" }}>Commissions</h3>
            <table><thead><tr><th>User</th><th>Base</th><th>Commission</th><th>Paid</th><th>Actions</th></tr></thead><tbody>
              {commissions.map((c: any) => <tr key={c.id}>
                <td style={{ fontSize: "0.75rem" }}>{c.user_id.slice(0, 8)}…</td>
                <td>${c.base_amount?.toLocaleString()}</td>
                <td style={{ fontWeight: 600 }}>${c.commission?.toLocaleString()}</td>
                <td>{c.paid ? <span className="badge badge-green">Paid</span> : <span className="badge badge-yellow">Due</span>}</td>
                <td>{!c.paid && <button className="btn btn-sm" onClick={async () => { await payComm(c.id); rComm(); }}>Mark Paid</button>}</td>
              </tr>)}
            </tbody></table>
          </div>
        </>
      )}

      {tab === "territories" && (
        <div className="card">
          <div className="card-header"><h3>Territories</h3>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-sm" onClick={async () => { const r: any = await autoAssign(); alert(`Assigned ${r.data?.assigned || 0} leads`); rLe(); }}>Auto-Assign Leads</button>
              <button className="btn btn-sm btn-primary" onClick={async () => {
                const name = prompt("Territory name:"); if (!name) return;
                const industry = prompt("Match industry (optional):") || undefined;
                const minRev = parseFloat(prompt("Min revenue (optional):") || "0");
                await createTerritory({ name, rule_industry: industry, rule_min_revenue: minRev || undefined });
                rTerr();
              }}>+ Territory</button>
            </div>
          </div>
          <table><thead><tr><th>Name</th><th>Region</th><th>Industry</th><th>Min Revenue</th><th>Owner</th></tr></thead><tbody>
            {territories.map((t: any) => <tr key={t.id}>
              <td style={{ fontWeight: 500 }}>{t.name}</td>
              <td>{t.rule_region || "-"}</td>
              <td>{t.rule_industry || "-"}</td>
              <td>{t.rule_min_revenue ? `$${t.rule_min_revenue?.toLocaleString()}` : "-"}</td>
              <td style={{ fontSize: "0.75rem" }}>{t.owner_id ? `${t.owner_id.slice(0, 8)}…` : "-"}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "drips" && (
        <div className="card">
          <div className="card-header"><h3>Drip Sequences</h3>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-sm" onClick={async () => { const r: any = await dripTick(); alert(`Advanced ${r.data?.advanced || 0}, sent ${r.data?.emails_sent || 0}`); rDrips(); }}>Run Tick</button>
              <button className="btn btn-sm btn-primary" onClick={async () => {
                const name = prompt("Sequence name:"); if (!name) return;
                const subj = prompt("Step 1 subject:"); if (!subj) return;
                const body = prompt("Step 1 body:") || "";
                await createDrip({ name, steps: [{ step_order: 0, delay_days: 0, subject: subj, body }] });
                rDrips();
              }}>+ Sequence</button>
            </div>
          </div>
          <table><thead><tr><th>Name</th><th>Steps</th><th>Active</th><th>Actions</th></tr></thead><tbody>
            {drips.map((d: any) => <tr key={d.id}>
              <td style={{ fontWeight: 500 }}>{d.name}</td>
              <td>{d.step_count}</td>
              <td>{d.is_active ? "Yes" : "No"}</td>
              <td><button className="btn btn-sm" onClick={async () => {
                if (!contacts.length) { alert("No contacts"); return; }
                const cid = prompt("Contact ID (or leave blank for first):", contacts[0].id) || contacts[0].id;
                await enrollDrip({ sequence_id: d.id, contact_id: cid });
                alert("Enrolled.");
              }}>Enroll Contact</button></td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {tab === "health" && (
        <div className="card">
          <div className="card-header"><h3>Customer Health</h3>
            <button className="btn btn-sm btn-primary" onClick={async () => { const r: any = await computeHealthFn(); alert(`Created ${r.data?.snapshots || 0} snapshots`); rHealth(); }}>Compute</button>
          </div>
          <table><thead><tr><th>Company</th><th>Score</th><th>Factors</th><th>Date</th></tr></thead><tbody>
            {health.map((h: any) => <tr key={h.company_id}>
              <td style={{ fontWeight: 500 }}>{h.name}</td>
              <td style={{ fontWeight: 700, color: h.score >= 70 ? "var(--success)" : h.score >= 40 ? "var(--warning)" : "var(--danger)" }}>{h.score}</td>
              <td style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{h.factors || "-"}</td>
              <td>{h.date}</td>
            </tr>)}
          </tbody></table>
        </div>
      )}

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Add {tab.charAt(0).toUpperCase() + tab.slice(1)}</h3>
            <form onSubmit={handleSubmit}>
              {Object.keys(form).map(k => (
                <div className="form-group" key={k}>
                  <label>{k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</label>
                  {k === "source" ? (
                    <select value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}>{["website","referral","cold_call","advertising","social_media","event","other"].map(s => <option key={s} value={s}>{s}</option>)}</select>
                  ) : k === "interaction_type" ? (
                    <select value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}>{["call","email","meeting","note","demo"].map(s => <option key={s} value={s}>{s}</option>)}</select>
                  ) : (
                    <input value={form[k] || ""} onChange={e => setForm({ ...form, [k]: e.target.value })} type={typeof form[k] === "number" ? "number" : "text"} />
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
