import { useMemo, useState } from "react";
import {
  useGetBankTransactionsQuery,
  useGetInvoicesQuery,
  useGetExpensesQuery,
  useGetJournalQuery,
  useGetAccountsQuery,
  useMatchBankTxnMutation,
  useUnmatchBankTxnMutation,
  useCreateJournalFromBankTxnMutation,
  useAutoMatchBankMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import EmptyState from "../../shell/EmptyState";
import { Icon } from "../../shell/icons";
import { useFormat } from "../../i18n/format";
import { promptForValues, confirmAction, notifyUser } from "../../shell/modalService";

type BankTxn = {
  id: string;
  description: string;
  amount: number;
  txn_date?: string | null;
  reference?: string | null;
  is_reconciled: boolean;
  matched_invoice_id?: string | null;
  matched_expense_id?: string | null;
  matched_journal_entry_id?: string | null;
};

type Candidate =
  | { kind: "invoice"; id: string; label: string; amount: number; date: string | null; matchKey: { invoice_id: string } }
  | { kind: "expense"; id: string; label: string; amount: number; date: string | null; matchKey: { expense_id: string } }
  | { kind: "journal"; id: string; label: string; amount: number; date: string | null; matchKey: { journal_entry_id: string } };

export default function BankReconciliationPage() {
  const { data: txns = [], refetch: refetchTxns, isLoading: loadingTxns } = useGetBankTransactionsQuery();
  const { data: invoices = [] } = useGetInvoicesQuery();
  const { data: expenses = [] } = useGetExpensesQuery();
  const { data: journal = [] } = useGetJournalQuery();
  const { data: accounts = [] } = useGetAccountsQuery();
  const [matchTxn] = useMatchBankTxnMutation();
  const [unmatchTxn] = useUnmatchBankTxnMutation();
  const [createJournal] = useCreateJournalFromBankTxnMutation();
  const [autoMatch] = useAutoMatchBankMutation();
  const { formatDate, formatCurrency } = useFormat();

  const [selectedTxnId, setSelectedTxnId] = useState<string | null>(null);
  const [showReconciled, setShowReconciled] = useState(false);

  const matchedInvoiceIds = useMemo(
    () => new Set((txns as BankTxn[]).filter((t) => t.matched_invoice_id).map((t) => t.matched_invoice_id!)),
    [txns],
  );
  const matchedExpenseIds = useMemo(
    () => new Set((txns as BankTxn[]).filter((t) => t.matched_expense_id).map((t) => t.matched_expense_id!)),
    [txns],
  );
  const matchedJournalIds = useMemo(
    () => new Set((txns as BankTxn[]).filter((t) => t.matched_journal_entry_id).map((t) => t.matched_journal_entry_id!)),
    [txns],
  );

  const visibleTxns = useMemo(
    () => (txns as BankTxn[]).filter((t) => showReconciled || !t.is_reconciled),
    [txns, showReconciled],
  );

  const selectedTxn = useMemo(
    () => (txns as BankTxn[]).find((t) => t.id === selectedTxnId) || null,
    [txns, selectedTxnId],
  );

  const candidates = useMemo<Candidate[]>(() => {
    if (!selectedTxn) return [];
    const targetAmt = Math.abs(selectedTxn.amount);
    const out: Candidate[] = [];
    for (const inv of invoices as any[]) {
      if (matchedInvoiceIds.has(inv.id)) continue;
      out.push({
        kind: "invoice",
        id: inv.id,
        label: `INV ${inv.invoice_number} · ${inv.invoice_type}`,
        amount: inv.total,
        date: inv.due_date || inv.issue_date || null,
        matchKey: { invoice_id: inv.id },
      });
    }
    for (const exp of expenses as any[]) {
      if (matchedExpenseIds.has(exp.id)) continue;
      out.push({
        kind: "expense",
        id: exp.id,
        label: `EXP ${exp.description}`,
        amount: exp.amount,
        date: exp.expense_date || null,
        matchKey: { expense_id: exp.id },
      });
    }
    for (const je of journal as any[]) {
      if (matchedJournalIds.has(je.id)) continue;
      out.push({
        kind: "journal",
        id: je.id,
        label: `JE ${je.entry_number}${je.memo ? " · " + je.memo : ""}`,
        amount: je.total || 0,
        date: je.entry_date || null,
        matchKey: { journal_entry_id: je.id },
      });
    }
    // Rank: smallest amount delta first
    out.sort((a, b) => Math.abs(a.amount - targetAmt) - Math.abs(b.amount - targetAmt));
    return out.slice(0, 50);
  }, [selectedTxn, invoices, expenses, journal, matchedInvoiceIds, matchedExpenseIds, matchedJournalIds]);

  const accountOptions = useMemo(
    () => (accounts as any[]).map((a) => ({ value: a.id, label: `${a.code} · ${a.name}` })),
    [accounts],
  );

  const totals = useMemo(() => {
    const all = txns as BankTxn[];
    const reconciled = all.filter((t) => t.is_reconciled).length;
    const total = all.length;
    return { reconciled, unreconciled: total - reconciled, total };
  }, [txns]);

  return (
    <div>
      <PageHeader
        title="Bank reconciliation"
        subtitle={`${totals.unreconciled} unreconciled · ${totals.reconciled} matched · ${totals.total} total bank transactions`}
      />
      <CommandBar
        items={[
          {
            key: "auto-match",
            label: "Auto-match by amount",
            onClick: async () => {
              const r: any = await autoMatch();
              await notifyUser({
                title: "Auto-match complete",
                description: `Matched ${r.data?.matched ?? 0} · ${r.data?.remaining ?? 0} still unmatched.`,
              });
              refetchTxns();
            },
          },
          {
            key: "show-reconciled",
            label: showReconciled ? "Hide matched" : "Show matched",
            onClick: () => setShowReconciled((s) => !s),
          },
        ]}
      />

      <div className="recon-workbench">
        <section className="recon-pane">
          <header className="recon-pane-head">
            <strong>Bank transactions</strong>
            <span className="recon-pane-subtitle">{visibleTxns.length} shown</span>
          </header>
          <div className="recon-list">
            {visibleTxns.length === 0 ? (
              <EmptyState
                compact
                icon="BarChart"
                title={showReconciled ? "No transactions" : "All caught up"}
                description={showReconciled ? "Import bank txns to start." : "Nothing left to reconcile."}
              />
            ) : (
              visibleTxns.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={`recon-row ${selectedTxnId === t.id ? "selected" : ""} ${t.is_reconciled ? "matched" : ""}`}
                  onClick={() => setSelectedTxnId(t.id === selectedTxnId ? null : t.id)}
                >
                  <div className="recon-row-main">
                    <span className="recon-row-desc">{t.description}</span>
                    <span className="recon-row-meta">
                      {formatDate(t.txn_date)}
                      {t.reference && <span> · {t.reference}</span>}
                    </span>
                  </div>
                  <div className="recon-row-side">
                    <span className={`recon-amount ${t.amount >= 0 ? "positive" : "negative"}`}>
                      {formatCurrency(t.amount)}
                    </span>
                    {t.is_reconciled && (
                      <span className="badge badge-green" style={{ display: "inline-flex", alignItems: "center", gap: "0.2rem" }}>
                        <Icon.Check size={10} /> matched
                      </span>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="recon-pane">
          <header className="recon-pane-head">
            <strong>{selectedTxn ? "Match candidates" : "Pick a bank transaction"}</strong>
            {selectedTxn && (
              <span className="recon-pane-subtitle">
                Looking for {formatCurrency(Math.abs(selectedTxn.amount))} · {candidates.length} options
              </span>
            )}
          </header>
          {!selectedTxn ? (
            <EmptyState
              compact
              icon="ArrowLeft"
              title="Nothing selected"
              description="Click a bank transaction on the left to see invoice / expense / journal candidates ranked by amount delta."
            />
          ) : selectedTxn.is_reconciled ? (
            <div className="card" style={{ margin: "0.75rem" }}>
              <div style={{ marginBottom: "0.5rem" }}>
                <span className="badge badge-green">Matched</span>
                {selectedTxn.matched_invoice_id && <div style={{ fontSize: "0.82rem", marginTop: "0.4rem" }}>Invoice: <code>{selectedTxn.matched_invoice_id.slice(0, 8)}…</code></div>}
                {selectedTxn.matched_expense_id && <div style={{ fontSize: "0.82rem", marginTop: "0.4rem" }}>Expense: <code>{selectedTxn.matched_expense_id.slice(0, 8)}…</code></div>}
                {selectedTxn.matched_journal_entry_id && <div style={{ fontSize: "0.82rem", marginTop: "0.4rem" }}>Journal: <code>{selectedTxn.matched_journal_entry_id.slice(0, 8)}…</code></div>}
              </div>
              <button
                className="btn btn-sm btn-danger"
                onClick={async () => {
                  const ok = await confirmAction({
                    title: "Unmatch this transaction?",
                    description: "It will return to the unreconciled list.",
                    submitLabel: "Unmatch",
                    dangerous: true,
                  });
                  if (!ok) return;
                  await unmatchTxn(selectedTxn.id);
                  refetchTxns();
                }}
              >
                Unmatch
              </button>
            </div>
          ) : (
            <>
              <div className="recon-cta-strip">
                <button
                  className="btn btn-sm btn-primary"
                  onClick={async () => {
                    if (accountOptions.length < 2) {
                      await notifyUser({ title: "Need accounts", description: "At least two chart-of-accounts entries are required." });
                      return;
                    }
                    const v = await promptForValues({
                      title: "Create journal entry from this txn",
                      submitLabel: "Post",
                      fields: [
                        { name: "debit_account_id", label: "Debit account", required: true, kind: "select", options: accountOptions },
                        { name: "credit_account_id", label: "Credit account", required: true, kind: "select", options: accountOptions },
                        { name: "memo", label: "Memo", kind: "textarea", defaultValue: selectedTxn.description },
                        { name: "entry_number", label: "Entry number", placeholder: "Auto if blank" },
                      ],
                    });
                    if (!v) return;
                    if (v.debit_account_id === v.credit_account_id) {
                      await notifyUser({ title: "Invalid entry", description: "Debit and credit accounts must differ." });
                      return;
                    }
                    const r: any = await createJournal({
                      id: selectedTxn.id,
                      body: {
                        debit_account_id: v.debit_account_id,
                        credit_account_id: v.credit_account_id,
                        memo: v.memo || undefined,
                        entry_number: v.entry_number || undefined,
                      },
                    });
                    if (r.error) {
                      await notifyUser({ title: "Failed", description: (r.error as any)?.data?.detail });
                    } else {
                      refetchTxns();
                      setSelectedTxnId(null);
                    }
                  }}
                >
                  + Create journal entry
                </button>
              </div>
              <div className="recon-list">
                {candidates.length === 0 ? (
                  <EmptyState
                    compact
                    icon="Filter"
                    title="No candidates"
                    description="Try creating a journal entry above to record this txn directly."
                  />
                ) : (
                  candidates.map((c) => {
                    const delta = c.amount - Math.abs(selectedTxn.amount);
                    const closeMatch = Math.abs(delta) < 0.5;
                    return (
                      <button
                        key={`${c.kind}-${c.id}`}
                        type="button"
                        className={`recon-row candidate ${closeMatch ? "close-match" : ""}`}
                        onClick={async () => {
                          await matchTxn({ id: selectedTxn.id, body: c.matchKey });
                          refetchTxns();
                          setSelectedTxnId(null);
                        }}
                      >
                        <div className="recon-row-main">
                          <span className="recon-row-desc">
                            <span className="badge badge-gray" style={{ marginRight: "0.4rem", fontSize: "0.65rem" }}>
                              {c.kind}
                            </span>
                            {c.label}
                          </span>
                          <span className="recon-row-meta">{formatDate(c.date)}</span>
                        </div>
                        <div className="recon-row-side">
                          <span className="recon-amount">{formatCurrency(c.amount)}</span>
                          {Math.abs(delta) >= 0.005 && (
                            <span style={{ fontSize: "0.7rem", color: closeMatch ? "var(--warning)" : "var(--gray-400)" }}>
                              Δ {formatCurrency(delta)}
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </>
          )}
        </section>
      </div>

      {loadingTxns && (
        <div style={{ textAlign: "center", color: "var(--gray-500)", padding: "0.5rem" }}>Loading…</div>
      )}
    </div>
  );
}
