import { Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import SuiteShell from "./layouts/SuiteShell";
import AppLayout from "./layouts/AppLayout";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import ProjectList from "./pages/ProjectList";
import PortfolioPage from "./pages/PortfolioPage";
import ProjectLayout from "./pages/ProjectLayout";
import DashboardPage from "./pages/DashboardPage";
import StakeholdersPage from "./pages/StakeholdersPage";
import TeamPage from "./pages/TeamPage";
import TasksPage from "./pages/TasksPage";
import RisksPage from "./pages/RisksPage";
import DeliverablesPage from "./pages/DeliverablesPage";
import MeasurementsPage from "./pages/MeasurementsPage";
import ChangeRequestsPage from "./pages/ChangeRequestsPage";
import SchedulePage from "./pages/SchedulePage";
import GanttPage from "./pages/GanttPage";
import EvmPage from "./pages/EvmPage";
import BurndownPage from "./pages/BurndownPage";
import WorkloadPage from "./pages/WorkloadPage";
import LessonsPage from "./pages/LessonsPage";
import ReportsPage from "./pages/ReportsPage";
import CalendarPage from "./pages/CalendarPage";
import TimeTrackingPage from "./pages/TimeTrackingPage";
import SprintPage from "./pages/SprintPage";
import BaselinePage from "./pages/BaselinePage";
import MonteCarloPage from "./pages/MonteCarloPage";
import ActivityLogPage from "./pages/ActivityLogPage";
import FinanceDashboardPage from "./pages/finance/FinanceDashboardPage";
import InvoicesPage from "./pages/finance/InvoicesPage";
import ExpensesPage from "./pages/finance/ExpensesPage";
import VendorsPage from "./pages/finance/VendorsPage";
import PurchaseOrdersPage from "./pages/finance/PurchaseOrdersPage";
import AssetsPage from "./pages/finance/AssetsPage";
import AccountsPage from "./pages/finance/AccountsPage";
import BudgetsPage from "./pages/finance/BudgetsPage";
import AgingPage from "./pages/finance/AgingPage";
import RecurringPage from "./pages/finance/RecurringPage";
import TaxPage from "./pages/finance/TaxPage";
import TrialBalancePage from "./pages/finance/TrialBalancePage";
import JournalPage from "./pages/finance/JournalPage";
import BankPage from "./pages/finance/BankPage";
import InventoryPage from "./pages/finance/InventoryPage";
import DepreciationPage from "./pages/finance/DepreciationPage";
import CreditNotesPage from "./pages/finance/CreditNotesPage";
import PnlPage from "./pages/finance/PnlPage";
import BalanceSheetPage from "./pages/finance/BalanceSheetPage";
import CashFlowPage from "./pages/finance/CashFlowPage";
import RequisitionsPage from "./pages/finance/RequisitionsPage";
import SalesDashboardPage from "./pages/sales/SalesDashboardPage";
import CompaniesPage from "./pages/sales/CompaniesPage";
import ContactsPage from "./pages/sales/ContactsPage";
import LeadsPage from "./pages/sales/LeadsPage";
import OpportunitiesPage from "./pages/sales/OpportunitiesPage";
import InteractionsPage from "./pages/sales/InteractionsPage";
import QuotesPage from "./pages/sales/QuotesPage";
import CampaignsPage from "./pages/sales/CampaignsPage";
import ForecastPage from "./pages/sales/ForecastPage";
import FollowUpsPage from "./pages/sales/FollowUpsPage";
import EmailsPage from "./pages/sales/EmailsPage";
import ContractsPage from "./pages/sales/ContractsPage";
import CommissionsPage from "./pages/sales/CommissionsPage";
import TerritoriesPage from "./pages/sales/TerritoriesPage";
import DripsPage from "./pages/sales/DripsPage";
import HealthPage from "./pages/sales/HealthPage";
import DmsLayout from "./pages/documents/DmsLayout";
import FilesPage from "./pages/documents/FilesPage";
import SignaturesPage from "./pages/documents/SignaturesPage";
import TemplatesPage from "./pages/documents/TemplatesPage";
import RetentionPage from "./pages/documents/RetentionPage";
import LocksPage from "./pages/documents/LocksPage";
import WorkflowsPage from "./pages/documents/WorkflowsPage";
import AnnotationsPage from "./pages/documents/AnnotationsPage";
import ScansPage from "./pages/documents/ScansPage";
import UsageReportPage from "./pages/documents/UsageReportPage";
import PendingApprovalsPage from "./pages/documents/PendingApprovalsPage";
import AdminPage from "./pages/AdminPage";
import AclGroupsPage from "./pages/admin/AclGroupsPage";
import AclPermissionsPage from "./pages/admin/AclPermissionsPage";
import AclUsersPage from "./pages/admin/AclUsersPage";
import AclInspectorPage from "./pages/admin/AclInspectorPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />

      <Route element={<ProtectedRoute><SuiteShell /></ProtectedRoute>}>
        {/* Projects app */}
        <Route element={<AppLayout />}>
          <Route index element={<ProjectList />} />
          <Route path="portfolio" element={<PortfolioPage />} />
        </Route>

        {/* Project workspace (inner sidebar) */}
        <Route path="projects/:projectId" element={<ProjectLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="tasks" element={<TasksPage />} />
          <Route path="gantt" element={<GanttPage />} />
          <Route path="calendar" element={<CalendarPage />} />
          <Route path="schedule" element={<SchedulePage />} />
          <Route path="sprints" element={<SprintPage />} />
          <Route path="team" element={<TeamPage />} />
          <Route path="workload" element={<WorkloadPage />} />
          <Route path="time-tracking" element={<TimeTrackingPage />} />
          <Route path="stakeholders" element={<StakeholdersPage />} />
          <Route path="risks" element={<RisksPage />} />
          <Route path="deliverables" element={<DeliverablesPage />} />
          <Route path="changes" element={<ChangeRequestsPage />} />
          <Route path="evm" element={<EvmPage />} />
          <Route path="burndown" element={<BurndownPage />} />
          <Route path="monte-carlo" element={<MonteCarloPage />} />
          <Route path="baselines" element={<BaselinePage />} />
          <Route path="measurements" element={<MeasurementsPage />} />
          <Route path="lessons" element={<LessonsPage />} />
          <Route path="activity" element={<ActivityLogPage />} />
          <Route path="reports" element={<ReportsPage />} />
        </Route>

        {/* Org-wide apps */}
        <Route path="sales" element={<AppLayout />}>
          <Route index element={<SalesDashboardPage />} />
          <Route path="companies" element={<CompaniesPage />} />
          <Route path="contacts" element={<ContactsPage />} />
          <Route path="leads" element={<LeadsPage />} />
          <Route path="opportunities" element={<OpportunitiesPage />} />
          <Route path="interactions" element={<InteractionsPage />} />
          <Route path="quotes" element={<QuotesPage />} />
          <Route path="campaigns" element={<CampaignsPage />} />
          <Route path="forecast" element={<ForecastPage />} />
          <Route path="follow-ups" element={<FollowUpsPage />} />
          <Route path="emails" element={<EmailsPage />} />
          <Route path="contracts" element={<ContractsPage />} />
          <Route path="commissions" element={<CommissionsPage />} />
          <Route path="territories" element={<TerritoriesPage />} />
          <Route path="drips" element={<DripsPage />} />
          <Route path="health" element={<HealthPage />} />
        </Route>

        <Route path="finance" element={<AppLayout />}>
          <Route index element={<FinanceDashboardPage />} />
          <Route path="invoices" element={<InvoicesPage />} />
          <Route path="recurring" element={<RecurringPage />} />
          <Route path="credit-notes" element={<CreditNotesPage />} />
          <Route path="aging" element={<AgingPage />} />
          <Route path="expenses" element={<ExpensesPage />} />
          <Route path="vendors" element={<VendorsPage />} />
          <Route path="purchase-orders" element={<PurchaseOrdersPage />} />
          <Route path="requisitions" element={<RequisitionsPage />} />
          <Route path="accounts" element={<AccountsPage />} />
          <Route path="journal" element={<JournalPage />} />
          <Route path="bank" element={<BankPage />} />
          <Route path="trial-balance" element={<TrialBalancePage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="assets" element={<AssetsPage />} />
          <Route path="depreciation" element={<DepreciationPage />} />
          <Route path="budgets" element={<BudgetsPage />} />
          <Route path="pnl" element={<PnlPage />} />
          <Route path="balance-sheet" element={<BalanceSheetPage />} />
          <Route path="cash-flow" element={<CashFlowPage />} />
          <Route path="tax" element={<TaxPage />} />
        </Route>

        <Route path="documents" element={<AppLayout />}>
          <Route element={<DmsLayout />}>
            <Route index element={<FilesPage />} />
            <Route path="signatures" element={<SignaturesPage />} />
            <Route path="templates" element={<TemplatesPage />} />
            <Route path="retention" element={<RetentionPage />} />
            <Route path="locks" element={<LocksPage />} />
            <Route path="workflows" element={<WorkflowsPage />} />
            <Route path="annotations" element={<AnnotationsPage />} />
            <Route path="scans" element={<ScansPage />} />
            <Route path="reports/usage" element={<UsageReportPage />} />
            <Route path="reports/pending" element={<PendingApprovalsPage />} />
          </Route>
        </Route>

        <Route path="admin" element={<AppLayout />}>
          <Route index element={<AdminPage />} />
          <Route path="activity" element={<ActivityLogPage />} />
          <Route path="acl/groups" element={<AclGroupsPage />} />
          <Route path="acl/permissions" element={<AclPermissionsPage />} />
          <Route path="acl/users" element={<AclUsersPage />} />
          <Route path="acl/inspector" element={<AclInspectorPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
