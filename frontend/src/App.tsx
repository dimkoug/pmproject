import { Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
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
import ErpPage from "./pages/ErpPage";
import CrmPage from "./pages/CrmPage";
import DmsPage from "./pages/DmsPage";
import AdminPage from "./pages/AdminPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/" element={<ProtectedRoute><ProjectList /></ProtectedRoute>} />
      <Route path="/portfolio" element={<ProtectedRoute><PortfolioPage /></ProtectedRoute>} />
      <Route path="/projects/:projectId" element={<ProtectedRoute><ProjectLayout /></ProtectedRoute>}>
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
        <Route path="erp" element={<ErpPage />} />
        <Route path="crm" element={<CrmPage />} />
        <Route path="dms" element={<DmsPage />} />
        <Route path="admin" element={<AdminPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
