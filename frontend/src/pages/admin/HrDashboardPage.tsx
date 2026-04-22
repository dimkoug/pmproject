import { useGetHrDashboardQuery, useGetMyEmployeeQuery, useCheckInMutation, useCheckOutMutation } from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import { Icon } from "../../shell/icons";
import { useFormat } from "../../i18n/format";
import { notifyUser } from "../../shell/modalService";

export default function HrDashboardPage() {
  const { data: dash } = useGetHrDashboardQuery();
  const { data: me, refetch: refetchMe } = useGetMyEmployeeQuery();
  const [checkIn] = useCheckInMutation();
  const [checkOut] = useCheckOutMutation();
  const { formatNumber, formatTime } = useFormat();

  return (
    <div>
      <PageHeader
        title="HR overview"
        subtitle="Workforce snapshot — headcount, leave queue, today's attendance."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { label: "HR" }]}
      />

      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Active employees</div>
          <div className="value">{dash ? formatNumber(dash.active_employees) : "—"}</div>
        </div>
        <div className="stat-card">
          <div className="label">Pending leave requests</div>
          <div className="value">{dash ? formatNumber(dash.pending_leave) : "—"}</div>
        </div>
        <div className="stat-card">
          <div className="label">On leave today</div>
          <div className="value">{dash ? formatNumber(dash.on_leave_today) : "—"}</div>
        </div>
        <div className="stat-card">
          <div className="label">Today's check-ins</div>
          <div className="value">{dash ? formatNumber(dash.today_checkins) : "—"}</div>
        </div>
        <div className="stat-card">
          <div className="label">Hours logged (7d)</div>
          <div className="value">{dash ? formatNumber(dash.hours_logged_7d, { maximumFractionDigits: 1 }) : "—"}</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: "1rem" }}>
        <div className="card-header">
          <h2>My status</h2>
        </div>
        {me ? (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: "1rem", fontWeight: 600 }}>{me.full_name}</div>
              <div style={{ fontSize: "0.78rem", color: "var(--gray-500)" }}>
                {me.job_title || "—"}{me.department ? ` · ${me.department}` : ""} · #{me.employee_number}
              </div>
            </div>
            <div style={{ display: "inline-flex", gap: "0.4rem" }}>
              <button
                className="btn btn-sm btn-primary"
                onClick={async () => {
                  const r: any = await checkIn();
                  if (r.error) {
                    await notifyUser({ title: "Check-in failed", description: (r.error as any)?.data?.detail });
                  } else {
                    await notifyUser({ title: "Checked in", description: r.data?.check_in ? `at ${formatTime(r.data.check_in)}` : "" });
                  }
                  refetchMe();
                }}
              >
                <Icon.Clock size={14} /> Check in
              </button>
              <button
                className="btn btn-sm"
                onClick={async () => {
                  const r: any = await checkOut();
                  if (r.error) {
                    await notifyUser({ title: "Check-out failed", description: (r.error as any)?.data?.detail });
                  } else {
                    await notifyUser({ title: "Checked out", description: r.data?.hours_worked ? `${r.data.hours_worked.toFixed(2)} hours` : "" });
                  }
                  refetchMe();
                }}
              >
                Check out
              </button>
            </div>
          </div>
        ) : (
          <div style={{ color: "var(--gray-500)", fontSize: "0.82rem" }}>
            No employee record linked to your user. Ask your HR admin to create one.
          </div>
        )}
      </div>
    </div>
  );
}
