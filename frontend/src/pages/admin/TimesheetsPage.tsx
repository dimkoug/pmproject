import { useMemo, useState } from "react";
import {
  useGetMyTimesheetsQuery,
  useGetTimesheetInboxQuery,
  useCreateOrGetTimesheetMutation,
  useSubmitTimesheetMutation,
  useDecideTimesheetMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import EmptyState from "../../shell/EmptyState";
import { useFormat } from "../../i18n/format";
import { confirmAction, notifyUser, promptForValues } from "../../shell/modalService";
import { Icon } from "../../shell/icons";

type Sheet = {
  id: string;
  user_id: string;
  user_name?: string | null;
  week_start: string;
  status: string;
  submitted_at?: string | null;
  decided_at?: string | null;
  decision_note?: string | null;
  total_hours: number;
  is_locked: boolean;
};

const STATUS_BADGE: Record<string, string> = {
  draft: "badge-gray",
  submitted: "badge-yellow",
  approved: "badge-green",
  rejected: "badge-red",
};

function thisMonday(): string {
  const d = new Date();
  const diff = (d.getDay() + 6) % 7; // 0 = Mon
  d.setDate(d.getDate() - diff);
  return d.toISOString().slice(0, 10);
}

export default function TimesheetsPage() {
  const [tab, setTab] = useState<"mine" | "inbox">("mine");
  const { data: mine = [], isLoading: lm } = useGetMyTimesheetsQuery();
  const { data: inbox = [], isLoading: li } = useGetTimesheetInboxQuery();
  const [createOrGet] = useCreateOrGetTimesheetMutation();
  const [submitTs] = useSubmitTimesheetMutation();
  const [decideTs] = useDecideTimesheetMutation();
  const { formatDate, formatDateTime, formatNumber } = useFormat();

  const data = (tab === "mine" ? mine : inbox) as Sheet[];
  const isLoading = tab === "mine" ? lm : li;

  const totals = useMemo(() => {
    const list = data || [];
    const submitted = list.filter((t) => t.status === "submitted").length;
    const approved = list.filter((t) => t.status === "approved").length;
    return { submitted, approved, total: list.length };
  }, [data]);

  return (
    <div>
      <PageHeader
        title="Timesheets"
        subtitle="Group your weekly time entries into a sheet, submit it for approval, and approve teammates'."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { to: "/admin/hr", label: "HR" }, { label: "Timesheets" }]}
        meta={
          <span style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>
            {totals.total} sheet{totals.total === 1 ? "" : "s"} · {totals.submitted} pending · {totals.approved} approved
          </span>
        }
      />
      <div style={{ display: "inline-flex", gap: "0.25rem", marginBottom: "0.75rem" }}>
        <button className={`btn btn-sm ${tab === "mine" ? "btn-primary" : ""}`} onClick={() => setTab("mine")}>
          My timesheets
        </button>
        <button className={`btn btn-sm ${tab === "inbox" ? "btn-primary" : ""}`} onClick={() => setTab("inbox")}>
          Approval inbox
        </button>
      </div>
      {tab === "mine" && (
        <CommandBar
          items={[
            {
              key: "new",
              label: "Open this week",
              variant: "primary",
              onClick: async () => {
                const r: any = await createOrGet({ week_start: thisMonday() });
                if (r.error) {
                  await notifyUser({ title: "Failed", description: (r.error as any)?.data?.detail });
                } else {
                  await notifyUser({
                    title: "Sheet ready",
                    description: `${r.data?.total_hours ?? 0} hours pulled in for week of ${r.data?.week_start}.`,
                  });
                }
              },
            },
            {
              key: "pick",
              label: "Open another week…",
              onClick: async () => {
                const v = await promptForValues({
                  title: "Open week",
                  submitLabel: "Open",
                  fields: [
                    { name: "week_start", label: "Any date in the target week", required: true, kind: "date", defaultValue: thisMonday() },
                  ],
                });
                if (!v) return;
                await createOrGet({ week_start: v.week_start });
              },
            },
          ]}
        />
      )}
      <div className="card" style={{ padding: 0 }}>
        {isLoading ? (
          <div style={{ padding: "1rem", color: "var(--gray-500)" }}>Loading…</div>
        ) : data.length === 0 ? (
          <EmptyState
            compact
            icon="Clock"
            title={tab === "mine" ? "No timesheets yet" : "Nothing to approve"}
            description={
              tab === "mine"
                ? "Click \"Open this week\" to bundle your time entries into a draft sheet."
                : "Submitted sheets from your team will appear here."
            }
          />
        ) : (
          <table>
            <thead>
              <tr>
                {tab === "inbox" && <th>Owner</th>}
                <th>Week</th>
                <th>Hours</th>
                <th>Status</th>
                <th>Submitted</th>
                <th>Note</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((t) => (
                <tr key={t.id}>
                  {tab === "inbox" && <td style={{ fontWeight: 500 }}>{t.user_name || "—"}</td>}
                  <td>{formatDate(t.week_start)}</td>
                  <td style={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{formatNumber(t.total_hours, { maximumFractionDigits: 2 })}</td>
                  <td>
                    <span className={`badge ${STATUS_BADGE[t.status] || "badge-gray"}`} style={{ display: "inline-flex", alignItems: "center", gap: "0.2rem" }}>
                      {t.is_locked && <Icon.Lock size={10} />} {t.status}
                    </span>
                  </td>
                  <td style={{ fontSize: "0.78rem" }}>{formatDateTime(t.submitted_at)}</td>
                  <td style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>{t.decision_note || ""}</td>
                  <td>
                    {tab === "mine" && t.status === "draft" && (
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={async () => {
                          const ok = await confirmAction({
                            title: `Submit week of ${t.week_start}?`,
                            description: `${t.total_hours.toFixed(2)} hours will be locked until your approver decides.`,
                            submitLabel: "Submit",
                          });
                          if (!ok) return;
                          const r: any = await submitTs(t.id);
                          if (r.error) {
                            await notifyUser({ title: "Failed", description: (r.error as any)?.data?.detail });
                          }
                        }}
                      >
                        Submit
                      </button>
                    )}
                    {tab === "inbox" && t.status === "submitted" && (
                      <div style={{ display: "inline-flex", gap: "0.25rem" }}>
                        <button
                          className="btn btn-sm"
                          onClick={async () => {
                            const v = await promptForValues({
                              title: `Approve ${t.user_name}'s timesheet`,
                              description: `${t.total_hours.toFixed(2)} hours for week of ${t.week_start}`,
                              submitLabel: "Approve",
                              fields: [{ name: "note", label: "Note (optional)", kind: "textarea" }],
                            });
                            if (!v) return;
                            await decideTs({ id: t.id, decision: "approved", note: v.note || null });
                          }}
                        >
                          Approve
                        </button>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={async () => {
                            const v = await promptForValues({
                              title: `Reject ${t.user_name}'s timesheet`,
                              submitLabel: "Reject",
                              fields: [{ name: "note", label: "Reason (recommended)", kind: "textarea" }],
                            });
                            if (!v) return;
                            await decideTs({ id: t.id, decision: "rejected", note: v.note || null });
                          }}
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
