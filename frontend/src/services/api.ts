import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import type { RootState } from "../app/store";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const apiSlice = createApi({
  reducerPath: "api",
  baseQuery: fetchBaseQuery({
    baseUrl: `${API_URL}/api`,
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as RootState).auth.token;
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      return headers;
    },
  }),
  tagTypes: [
    "Project",
    "Stakeholder",
    "TeamMember",
    "Task",
    "Risk",
    "Deliverable",
    "Measurement",
    "ChangeRequest",
    "Dashboard",
  ],
  endpoints: (builder) => ({
    // Projects
    getProjects: builder.query<any[], void>({
      query: () => "/projects/",
      providesTags: ["Project"],
    }),
    getProject: builder.query<any, string>({
      query: (id) => `/projects/${id}`,
      providesTags: (_r, _e, id) => [{ type: "Project", id }],
    }),
    createProject: builder.mutation<any, any>({
      query: (body) => ({ url: "/projects/", method: "POST", body }),
      invalidatesTags: ["Project"],
    }),
    updateProject: builder.mutation<any, { id: string; body: any }>({
      query: ({ id, body }) => ({ url: `/projects/${id}`, method: "PATCH", body }),
      invalidatesTags: (_r, _e, { id }) => [{ type: "Project", id }, "Project", "Dashboard"],
    }),
    deleteProject: builder.mutation<void, string>({
      query: (id) => ({ url: `/projects/${id}`, method: "DELETE" }),
      invalidatesTags: ["Project"],
    }),

    // Stakeholders
    getStakeholders: builder.query<any[], string>({
      query: (projectId) => `/stakeholders/?project_id=${projectId}`,
      providesTags: ["Stakeholder"],
    }),
    createStakeholder: builder.mutation<any, any>({
      query: (body) => ({ url: "/stakeholders/", method: "POST", body }),
      invalidatesTags: ["Stakeholder", "Dashboard"],
    }),
    updateStakeholder: builder.mutation<any, { id: string; body: any }>({
      query: ({ id, body }) => ({ url: `/stakeholders/${id}`, method: "PATCH", body }),
      invalidatesTags: ["Stakeholder"],
    }),
    deleteStakeholder: builder.mutation<void, string>({
      query: (id) => ({ url: `/stakeholders/${id}`, method: "DELETE" }),
      invalidatesTags: ["Stakeholder", "Dashboard"],
    }),

    // Team Members
    getTeamMembers: builder.query<any[], string>({
      query: (projectId) => `/team-members/?project_id=${projectId}`,
      providesTags: ["TeamMember"],
    }),
    createTeamMember: builder.mutation<any, any>({
      query: (body) => ({ url: "/team-members/", method: "POST", body }),
      invalidatesTags: ["TeamMember", "Dashboard"],
    }),
    updateTeamMember: builder.mutation<any, { id: string; body: any }>({
      query: ({ id, body }) => ({ url: `/team-members/${id}`, method: "PATCH", body }),
      invalidatesTags: ["TeamMember"],
    }),
    deleteTeamMember: builder.mutation<void, string>({
      query: (id) => ({ url: `/team-members/${id}`, method: "DELETE" }),
      invalidatesTags: ["TeamMember", "Dashboard"],
    }),

    // Tasks
    getTasks: builder.query<any[], string>({
      query: (projectId) => `/tasks/?project_id=${projectId}`,
      providesTags: ["Task"],
    }),
    createTask: builder.mutation<any, any>({
      query: (body) => ({ url: "/tasks/", method: "POST", body }),
      invalidatesTags: ["Task", "Dashboard"],
    }),
    updateTask: builder.mutation<any, { id: string; body: any }>({
      query: ({ id, body }) => ({ url: `/tasks/${id}`, method: "PATCH", body }),
      invalidatesTags: ["Task", "Dashboard"],
    }),
    deleteTask: builder.mutation<void, string>({
      query: (id) => ({ url: `/tasks/${id}`, method: "DELETE" }),
      invalidatesTags: ["Task", "Dashboard"],
    }),

    // Risks
    getRisks: builder.query<any[], string>({
      query: (projectId) => `/risks/?project_id=${projectId}`,
      providesTags: ["Risk"],
    }),
    createRisk: builder.mutation<any, any>({
      query: (body) => ({ url: "/risks/", method: "POST", body }),
      invalidatesTags: ["Risk", "Dashboard"],
    }),
    updateRisk: builder.mutation<any, { id: string; body: any }>({
      query: ({ id, body }) => ({ url: `/risks/${id}`, method: "PATCH", body }),
      invalidatesTags: ["Risk", "Dashboard"],
    }),
    deleteRisk: builder.mutation<void, string>({
      query: (id) => ({ url: `/risks/${id}`, method: "DELETE" }),
      invalidatesTags: ["Risk", "Dashboard"],
    }),

    // Deliverables
    getDeliverables: builder.query<any[], string>({
      query: (projectId) => `/deliverables/?project_id=${projectId}`,
      providesTags: ["Deliverable"],
    }),
    createDeliverable: builder.mutation<any, any>({
      query: (body) => ({ url: "/deliverables/", method: "POST", body }),
      invalidatesTags: ["Deliverable", "Dashboard"],
    }),
    updateDeliverable: builder.mutation<any, { id: string; body: any }>({
      query: ({ id, body }) => ({ url: `/deliverables/${id}`, method: "PATCH", body }),
      invalidatesTags: ["Deliverable", "Dashboard"],
    }),
    deleteDeliverable: builder.mutation<void, string>({
      query: (id) => ({ url: `/deliverables/${id}`, method: "DELETE" }),
      invalidatesTags: ["Deliverable", "Dashboard"],
    }),

    // Measurements
    getMeasurements: builder.query<any[], string>({
      query: (projectId) => `/measurements/?project_id=${projectId}`,
      providesTags: ["Measurement"],
    }),
    createMeasurement: builder.mutation<any, any>({
      query: (body) => ({ url: "/measurements/", method: "POST", body }),
      invalidatesTags: ["Measurement", "Dashboard"],
    }),
    updateMeasurement: builder.mutation<any, { id: string; body: any }>({
      query: ({ id, body }) => ({ url: `/measurements/${id}`, method: "PATCH", body }),
      invalidatesTags: ["Measurement", "Dashboard"],
    }),
    deleteMeasurement: builder.mutation<void, string>({
      query: (id) => ({ url: `/measurements/${id}`, method: "DELETE" }),
      invalidatesTags: ["Measurement", "Dashboard"],
    }),

    // Change Requests
    getChangeRequests: builder.query<any[], string>({
      query: (projectId) => `/change-requests/?project_id=${projectId}`,
      providesTags: ["ChangeRequest"],
    }),
    createChangeRequest: builder.mutation<any, any>({
      query: (body) => ({ url: "/change-requests/", method: "POST", body }),
      invalidatesTags: ["ChangeRequest", "Dashboard"],
    }),
    updateChangeRequest: builder.mutation<any, { id: string; body: any }>({
      query: ({ id, body }) => ({ url: `/change-requests/${id}`, method: "PATCH", body }),
      invalidatesTags: ["ChangeRequest", "Dashboard"],
    }),
    deleteChangeRequest: builder.mutation<void, string>({
      query: (id) => ({ url: `/change-requests/${id}`, method: "DELETE" }),
      invalidatesTags: ["ChangeRequest", "Dashboard"],
    }),

    // Dashboard
    getDashboard: builder.query<any, string>({
      query: (projectId) => `/dashboard/${projectId}`,
      providesTags: ["Dashboard"],
    }),

    // Auth
    signup: builder.mutation<any, { name: string; email: string; password: string }>({
      query: (body) => ({ url: "/auth/signup", method: "POST", body }),
    }),
    login: builder.mutation<any, { email: string; password: string }>({
      query: (body) => ({ url: "/auth/login", method: "POST", body }),
    }),
    getMe: builder.query<any, void>({
      query: () => "/auth/me",
    }),

    // Schedule - Dependencies
    getDependencies: builder.query<any[], string>({
      query: (projectId) => `/projects/${projectId}/dependencies`,
      providesTags: ["Task"],
    }),
    createDependency: builder.mutation<any, any>({
      query: (body) => ({ url: `/projects/${body.project_id}/dependencies`, method: "POST", body }),
      invalidatesTags: ["Task"],
    }),
    deleteDependency: builder.mutation<void, { projectId: string; depId: string }>({
      query: ({ projectId, depId }) => ({ url: `/projects/${projectId}/dependencies/${depId}`, method: "DELETE" }),
      invalidatesTags: ["Task"],
    }),

    // CPM / PERT
    getCpm: builder.query<any, string>({
      query: (projectId) => `/projects/${projectId}/cpm`,
      providesTags: ["Task"],
    }),
    getPert: builder.query<any, { projectId: string; targets?: string }>({
      query: ({ projectId, targets }) =>
        `/projects/${projectId}/pert${targets ? `?target_durations=${targets}` : ""}`,
      providesTags: ["Task"],
    }),

    // Reports
    getReportSummary: builder.query<any, string>({
      query: (projectId) => `/projects/${projectId}/reports/summary`,
    }),
    getReportSchedule: builder.query<any, string>({
      query: (projectId) => `/projects/${projectId}/reports/schedule`,
      providesTags: ["Task"],
    }),
    getReportRisks: builder.query<any, string>({
      query: (projectId) => `/projects/${projectId}/reports/risks`,
      providesTags: ["Risk"],
    }),
    getReportPerformance: builder.query<any, string>({
      query: (projectId) => `/projects/${projectId}/reports/performance`,
    }),

    // EVM, Gantt, Burndown, Workload, Portfolio
    getEvm: builder.query<any, string>({
      query: (projectId) => `/projects/${projectId}/evm`,
      providesTags: ["Task"],
    }),
    getGantt: builder.query<any, string>({
      query: (projectId) => `/projects/${projectId}/gantt`,
      providesTags: ["Task"],
    }),
    getBurndown: builder.query<any, string>({
      query: (projectId) => `/projects/${projectId}/burndown`,
      providesTags: ["Task"],
    }),
    getWorkload: builder.query<any, string>({
      query: (projectId) => `/projects/${projectId}/workload`,
      providesTags: ["TeamMember", "Task"],
    }),
    getPortfolio: builder.query<any[], void>({
      query: () => "/projects/portfolio/overview",
      providesTags: ["Project"],
    }),

    // Comments
    getComments: builder.query<any[], { targetType: string; targetId: string }>({
      query: ({ targetType, targetId }) => `/comments/?target_type=${targetType}&target_id=${targetId}`,
    }),
    createComment: builder.mutation<any, any>({
      query: (body) => ({ url: "/comments/", method: "POST", body }),
    }),

    // Lessons Learned
    getLessons: builder.query<any[], string>({
      query: (projectId) => `/lessons/?project_id=${projectId}`,
    }),
    createLesson: builder.mutation<any, any>({
      query: (body) => ({ url: "/lessons/", method: "POST", body }),
    }),
    deleteLesson: builder.mutation<void, string>({
      query: (id) => ({ url: `/lessons/${id}`, method: "DELETE" }),
    }),

    // Notifications
    getNotifications: builder.query<any[], void>({
      query: () => "/notifications/",
    }),
    getUnreadCount: builder.query<any, void>({
      query: () => "/notifications/count",
    }),
    markAllRead: builder.mutation<any, void>({
      query: () => ({ url: "/notifications/read-all", method: "POST" }),
    }),

    // Templates
    getTemplates: builder.query<any[], void>({
      query: () => "/templates/",
    }),
    createTemplate: builder.mutation<any, any>({
      query: (body) => ({ url: "/templates/", method: "POST", body }),
    }),
    applyTemplate: builder.mutation<any, { templateId: string; projectId: string }>({
      query: ({ templateId, projectId }) => ({
        url: `/templates/${templateId}/apply?project_id=${projectId}`,
        method: "POST",
      }),
      invalidatesTags: ["Task", "Risk", "Dashboard"],
    }),

    // Time Tracking
    getTimeEntries: builder.query<any[], string>({
      query: (projectId) => `/time-entries/?project_id=${projectId}`,
    }),
    createTimeEntry: builder.mutation<any, any>({
      query: (body) => ({ url: "/time-entries/", method: "POST", body }),
    }),
    getTimeSummary: builder.query<any, string>({
      query: (projectId) => `/time-entries/summary?project_id=${projectId}`,
    }),

    // Sprints
    getSprints: builder.query<any[], string>({
      query: (projectId) => `/sprints/?project_id=${projectId}`,
    }),
    createSprint: builder.mutation<any, any>({
      query: (body) => ({ url: "/sprints/", method: "POST", body }),
    }),
    updateSprintStatus: builder.mutation<any, { sprintId: string; status: string }>({
      query: ({ sprintId, status }) => ({ url: `/sprints/${sprintId}?status=${status}`, method: "PATCH" }),
    }),
    getSprintVelocity: builder.query<any[], string>({
      query: (projectId) => `/sprints/velocity?project_id=${projectId}`,
    }),

    // Baselines
    getBaselines: builder.query<any[], string>({
      query: (projectId) => `/projects/${projectId}/baselines`,
    }),
    saveBaseline: builder.mutation<any, { projectId: string; name: string }>({
      query: ({ projectId, name }) => ({ url: `/projects/${projectId}/baselines?name=${encodeURIComponent(name)}`, method: "POST" }),
    }),
    compareBaseline: builder.query<any, { projectId: string; baselineId: string }>({
      query: ({ projectId, baselineId }) => `/projects/${projectId}/baselines/${baselineId}/compare`,
    }),

    // Activity Log
    getActivity: builder.query<any[], string>({
      query: (projectId) => `/projects/${projectId}/activity`,
    }),

    // Search
    search: builder.query<any[], { q: string; projectId?: string }>({
      query: ({ q, projectId }) => `/search?q=${encodeURIComponent(q)}${projectId ? `&project_id=${projectId}` : ""}`,
    }),

    // Monte Carlo
    getMonteCarlo: builder.query<any, { projectId: string; iterations?: number }>({
      query: ({ projectId, iterations }) => `/projects/${projectId}/monte-carlo${iterations ? `?iterations=${iterations}` : ""}`,
      providesTags: ["Task"],
    }),

    // Resource Leveling
    getResourceLeveling: builder.query<any, string>({
      query: (projectId) => `/projects/${projectId}/resource-leveling`,
      providesTags: ["Task", "TeamMember"],
    }),

    // Budget
    getBudget: builder.query<any, string>({
      query: (projectId) => `/projects/${projectId}/budget`,
      providesTags: ["Task"],
    }),

    // Dark mode
    toggleDarkMode: builder.mutation<any, void>({
      query: () => ({ url: "/auth/dark-mode", method: "POST" }),
    }),

    // Custom Fields
    getCustomFields: builder.query<any[], string>({
      query: (projectId) => `/custom-fields/?project_id=${projectId}`,
    }),
    createCustomField: builder.mutation<any, any>({
      query: (body) => ({ url: "/custom-fields/", method: "POST", body }),
    }),

    // ── ERP ──
    getErpDashboard: builder.query<any, string | void>({
      query: (projectId) => `/erp/dashboard${projectId ? `?project_id=${projectId}` : ""}`,
    }),
    getAccounts: builder.query<any[], void>({ query: () => "/erp/accounts" }),
    createAccount: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/accounts", method: "POST", body: b }) }),
    getVendors: builder.query<any[], void>({ query: () => "/erp/vendors" }),
    createVendor: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/vendors", method: "POST", body: b }) }),
    deleteVendor: builder.mutation<void, string>({ query: (id) => ({ url: `/erp/vendors/${id}`, method: "DELETE" }) }),
    getInvoices: builder.query<any[], string | void>({
      query: (pid) => `/erp/invoices${pid ? `?project_id=${pid}` : ""}`,
    }),
    createInvoice: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/invoices", method: "POST", body: b }) }),
    updateInvoiceStatus: builder.mutation<any, { id: string; status: string }>({
      query: ({ id, status }) => ({ url: `/erp/invoices/${id}?status=${status}`, method: "PATCH" }),
    }),
    getExpenses: builder.query<any[], string | void>({
      query: (pid) => `/erp/expenses${pid ? `?project_id=${pid}` : ""}`,
    }),
    createExpense: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/expenses", method: "POST", body: b }) }),
    getPurchaseOrders: builder.query<any[], string | void>({
      query: (pid) => `/erp/purchase-orders${pid ? `?project_id=${pid}` : ""}`,
    }),
    createPurchaseOrder: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/purchase-orders", method: "POST", body: b }) }),
    getAssets: builder.query<any[], string | void>({
      query: (pid) => `/erp/assets${pid ? `?project_id=${pid}` : ""}`,
    }),
    createAsset: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/assets", method: "POST", body: b }) }),

    // ── CRM ──
    getCrmDashboard: builder.query<any, void>({ query: () => "/crm/dashboard" }),
    getCompanies: builder.query<any[], void>({ query: () => "/crm/companies" }),
    createCompany: builder.mutation<any, any>({ query: (b) => ({ url: "/crm/companies", method: "POST", body: b }) }),
    deleteCompany: builder.mutation<void, string>({ query: (id) => ({ url: `/crm/companies/${id}`, method: "DELETE" }) }),
    getCrmContacts: builder.query<any[], string | void>({
      query: (cid) => `/crm/contacts${cid ? `?company_id=${cid}` : ""}`,
    }),
    createCrmContact: builder.mutation<any, any>({ query: (b) => ({ url: "/crm/contacts", method: "POST", body: b }) }),
    getLeads: builder.query<any[], void>({ query: () => "/crm/leads" }),
    createLead: builder.mutation<any, any>({ query: (b) => ({ url: "/crm/leads", method: "POST", body: b }) }),
    updateLeadStatus: builder.mutation<any, { id: string; status: string }>({
      query: ({ id, status }) => ({ url: `/crm/leads/${id}?status=${status}`, method: "PATCH" }),
    }),
    getOpportunities: builder.query<any[], void>({ query: () => "/crm/opportunities" }),
    createOpportunity: builder.mutation<any, any>({ query: (b) => ({ url: "/crm/opportunities", method: "POST", body: b }) }),
    updateOpportunityStage: builder.mutation<any, { id: string; stage: string }>({
      query: ({ id, stage }) => ({ url: `/crm/opportunities/${id}?stage=${stage}`, method: "PATCH" }),
    }),
    getInteractions: builder.query<any[], { contactId?: string; opportunityId?: string }>({
      query: ({ contactId, opportunityId }) => `/crm/interactions?${contactId ? `contact_id=${contactId}` : ""}${opportunityId ? `&opportunity_id=${opportunityId}` : ""}`,
    }),
    createInteraction: builder.mutation<any, any>({ query: (b) => ({ url: "/crm/interactions", method: "POST", body: b }) }),

    // ── DMS ──
    getDmsDashboard: builder.query<any, string | void>({
      query: (pid) => `/dms/dashboard${pid ? `?project_id=${pid}` : ""}`,
    }),
    getFolders: builder.query<any[], { projectId?: string; parentId?: string }>({
      query: ({ projectId, parentId }) => `/dms/folders?${projectId ? `project_id=${projectId}` : ""}${parentId ? `&parent_id=${parentId}` : ""}`,
    }),
    createFolder: builder.mutation<any, any>({ query: (b) => ({ url: "/dms/folders", method: "POST", body: b }) }),
    getDocuments: builder.query<any[], { folderId?: string; projectId?: string }>({
      query: ({ folderId, projectId }) => `/dms/documents?${folderId ? `folder_id=${folderId}` : ""}${projectId ? `&project_id=${projectId}` : ""}`,
    }),
    getDocVersions: builder.query<any[], string>({ query: (docId) => `/dms/documents/${docId}/versions` }),
    searchDocuments: builder.query<any[], { q: string; fullText?: boolean }>({
      query: ({ q, fullText }) => `/dms/search?q=${encodeURIComponent(q)}${fullText ? "&full_text=true" : ""}`,
    }),

    // ── ERP extensions ──
    getBudgets: builder.query<any[], string | void>({
      query: (pid) => `/erp/budgets${pid ? `?project_id=${pid}` : ""}`,
    }),
    createBudget: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/budgets", method: "POST", body: b }) }),
    getBudgetVariance: builder.query<any, string>({ query: (id) => `/erp/budgets/${id}/variance` }),
    getCurrencies: builder.query<any[], void>({ query: () => "/erp/currencies" }),
    createCurrency: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/currencies", method: "POST", body: b }) }),
    getFxRates: builder.query<any[], void>({ query: () => "/erp/fx-rates" }),
    createFxRate: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/fx-rates", method: "POST", body: b }) }),
    getPayments: builder.query<any[], string | void>({
      query: (iid) => `/erp/payments${iid ? `?invoice_id=${iid}` : ""}`,
    }),
    createPayment: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/payments", method: "POST", body: b }) }),
    getInvoiceAging: builder.query<any, string | void>({
      query: (pid) => `/erp/invoices/aging${pid ? `?project_id=${pid}` : ""}`,
    }),
    getRecurringInvoices: builder.query<any[], void>({ query: () => "/erp/recurring-invoices" }),
    createRecurringInvoice: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/recurring-invoices", method: "POST", body: b }) }),
    runRecurringInvoices: builder.mutation<any, void>({ query: () => ({ url: "/erp/recurring-invoices/run", method: "POST" }) }),
    getTaxReport: builder.query<any, { start?: string; end?: string }>({
      query: ({ start, end }) => `/erp/reports/tax?${start ? `start=${start}` : ""}${end ? `&end=${end}` : ""}`,
    }),
    getTrialBalance: builder.query<any, void>({ query: () => "/erp/reports/trial-balance" }),
    getJournal: builder.query<any[], void>({ query: () => "/erp/journal" }),
    createJournal: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/journal", method: "POST", body: b }) }),
    postJournal: builder.mutation<any, string>({ query: (id) => ({ url: `/erp/journal/${id}/post`, method: "POST" }) }),
    getBankTransactions: builder.query<any[], void>({ query: () => "/erp/bank-transactions" }),
    createBankTransaction: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/bank-transactions", method: "POST", body: b }) }),
    autoMatchBank: builder.mutation<any, void>({ query: () => ({ url: "/erp/bank-transactions/auto-match", method: "POST" }) }),

    // ── CRM extensions ──
    getForecast: builder.query<any, void>({ query: () => "/crm/forecast" }),
    scoreLead: builder.mutation<any, string>({ query: (id) => ({ url: `/crm/leads/${id}/score`, method: "POST" }) }),
    scoreAllLeads: builder.mutation<any, void>({ query: () => ({ url: "/crm/leads/score-all", method: "POST" }) }),
    getQuotes: builder.query<any[], string | void>({
      query: (oid) => `/crm/quotes${oid ? `?opportunity_id=${oid}` : ""}`,
    }),
    createQuote: builder.mutation<any, any>({ query: (b) => ({ url: "/crm/quotes", method: "POST", body: b }) }),
    updateQuoteStatus: builder.mutation<any, { id: string; status: string }>({
      query: ({ id, status }) => ({ url: `/crm/quotes/${id}?status=${status}`, method: "PATCH" }),
    }),
    convertQuote: builder.mutation<any, string>({ query: (id) => ({ url: `/crm/quotes/${id}/convert`, method: "POST" }) }),
    getCampaigns: builder.query<any[], void>({ query: () => "/crm/campaigns" }),
    createCampaign: builder.mutation<any, any>({ query: (b) => ({ url: "/crm/campaigns", method: "POST", body: b }) }),
    getCampaignRoi: builder.query<any, string>({ query: (id) => `/crm/campaigns/${id}/roi` }),
    addCampaignMember: builder.mutation<any, { campaignId: string; body: any }>({
      query: ({ campaignId, body }) => ({ url: `/crm/campaigns/${campaignId}/members`, method: "POST", body }),
    }),
    getFollowUpsDue: builder.query<any[], void>({ query: () => "/crm/follow-ups/due" }),
    setFollowUp: builder.mutation<any, { interactionId: string; body: any }>({
      query: ({ interactionId, body }) => ({ url: `/crm/interactions/${interactionId}/follow-up`, method: "PATCH", body }),
    }),
    completeFollowUp: builder.mutation<any, string>({
      query: (id) => ({ url: `/crm/interactions/${id}/follow-up/done`, method: "POST" }),
    }),

    // ── DMS extensions ──
    getSignatures: builder.query<any[], string | void>({
      query: (did) => `/dms/signatures${did ? `?document_id=${did}` : ""}`,
    }),
    createSignature: builder.mutation<any, any>({ query: (b) => ({ url: "/dms/signatures", method: "POST", body: b }) }),
    declineSignature: builder.mutation<any, string>({ query: (id) => ({ url: `/dms/signatures/${id}/decline`, method: "POST" }) }),
    getDmsTemplates: builder.query<any[], void>({ query: () => "/dms/templates" }),
    createDmsTemplate: builder.mutation<any, any>({ query: (b) => ({ url: "/dms/templates", method: "POST", body: b }) }),
    instantiateTemplate: builder.mutation<any, { templateId: string; body: any }>({
      query: ({ templateId, body }) => ({ url: `/dms/templates/${templateId}/instantiate`, method: "POST", body }),
    }),
    getFolderPermissions: builder.query<any[], string>({ query: (fid) => `/dms/folders/${fid}/permissions` }),
    grantFolderPermission: builder.mutation<any, any>({ query: (b) => ({ url: "/dms/folders/permissions", method: "POST", body: b }) }),
    revokeFolderPermission: builder.mutation<any, string>({
      query: (id) => ({ url: `/dms/folders/permissions/${id}`, method: "DELETE" }),
    }),
    getRetentionPolicies: builder.query<any[], void>({ query: () => "/dms/retention-policies" }),
    createRetentionPolicy: builder.mutation<any, any>({ query: (b) => ({ url: "/dms/retention-policies", method: "POST", body: b }) }),
    applyRetention: builder.mutation<any, void>({ query: () => ({ url: "/dms/retention-policies/apply", method: "POST" }) }),
    getEntityLinks: builder.query<any[], { entityType?: string; entityId?: string; documentId?: string }>({
      query: ({ entityType, entityId, documentId }) =>
        `/dms/entity-links?${entityType ? `entity_type=${entityType}` : ""}${entityId ? `&entity_id=${entityId}` : ""}${documentId ? `&document_id=${documentId}` : ""}`,
    }),
    createEntityLink: builder.mutation<any, any>({ query: (b) => ({ url: "/dms/entity-links", method: "POST", body: b }) }),

    // ── Cross-cutting ──
    getCompanyTimeline: builder.query<any, string>({ query: (cid) => `/timeline/company/${cid}` }),
    getApprovals: builder.query<any[], { status?: string; targetType?: string }>({
      query: ({ status, targetType }) =>
        `/approvals?${status ? `status=${status}` : ""}${targetType ? `&target_type=${targetType}` : ""}`,
    }),
    createApproval: builder.mutation<any, any>({ query: (b) => ({ url: "/approvals", method: "POST", body: b }) }),
    decideApproval: builder.mutation<any, { id: string; body: any }>({
      query: ({ id, body }) => ({ url: `/approvals/${id}/decide`, method: "POST", body }),
    }),
    getWebhooks: builder.query<any[], void>({ query: () => "/webhooks" }),
    createWebhook: builder.mutation<any, any>({ query: (b) => ({ url: "/webhooks", method: "POST", body: b }) }),
    deleteWebhook: builder.mutation<void, string>({ query: (id) => ({ url: `/webhooks/${id}`, method: "DELETE" }) }),
    testWebhook: builder.mutation<any, { id: string; body: any }>({
      query: ({ id, body }) => ({ url: `/webhooks/${id}/test`, method: "POST", body }),
    }),
    getWebhookDeliveries: builder.query<any[], string>({ query: (id) => `/webhooks/${id}/deliveries` }),
    getApiKeys: builder.query<any[], void>({ query: () => "/api-keys" }),
    createApiKey: builder.mutation<any, any>({ query: (b) => ({ url: "/api-keys", method: "POST", body: b }) }),
    revokeApiKey: builder.mutation<void, string>({ query: (id) => ({ url: `/api-keys/${id}`, method: "DELETE" }) }),

    // ── ERP v2 ──
    getWarehouses: builder.query<any[], void>({ query: () => "/erp/warehouses" }),
    createWarehouse: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/warehouses", method: "POST", body: b }) }),
    getProducts: builder.query<any[], void>({ query: () => "/erp/products" }),
    createProduct: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/products", method: "POST", body: b }) }),
    getStock: builder.query<any[], string | void>({ query: (wid) => `/erp/stock${wid ? `?warehouse_id=${wid}` : ""}` }),
    createMovement: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/stock/movements", method: "POST", body: b }) }),
    getReorderReport: builder.query<any[], void>({ query: () => "/erp/stock/reorder" }),
    getDepreciation: builder.query<any[], void>({ query: () => "/erp/depreciation" }),
    createDepreciation: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/depreciation", method: "POST", body: b }) }),
    runDepreciation: builder.mutation<any, void>({ query: () => ({ url: "/erp/depreciation/run", method: "POST" }) }),
    getCreditNotes: builder.query<any[], string | void>({
      query: (iid) => `/erp/credit-notes${iid ? `?invoice_id=${iid}` : ""}`,
    }),
    createCreditNote: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/credit-notes", method: "POST", body: b }) }),
    getPnl: builder.query<any, { start?: string; end?: string }>({
      query: ({ start, end }) => `/erp/reports/pnl?${start ? `start=${start}` : ""}${end ? `&end=${end}` : ""}`,
    }),
    getBalanceSheet: builder.query<any, void>({ query: () => "/erp/reports/balance-sheet" }),
    getCashFlow: builder.query<any, number | void>({ query: (days) => `/erp/reports/cash-flow${days ? `?days=${days}` : ""}` }),
    getRequisitions: builder.query<any[], void>({ query: () => "/erp/requisitions" }),
    createRequisition: builder.mutation<any, any>({ query: (b) => ({ url: "/erp/requisitions", method: "POST", body: b }) }),
    updateRequisitionStatus: builder.mutation<any, { id: string; status: string }>({
      query: ({ id, status }) => ({ url: `/erp/requisitions/${id}?status=${status}`, method: "PATCH" }),
    }),
    convertRequisition: builder.mutation<any, { id: string; body: any }>({
      query: ({ id, body }) => ({ url: `/erp/requisitions/${id}/convert`, method: "POST", body }),
    }),

    // ── CRM v2 ──
    getEmails: builder.query<any[], { contactId?: string; threadId?: string }>({
      query: ({ contactId, threadId }) => `/crm/emails?${contactId ? `contact_id=${contactId}` : ""}${threadId ? `&thread_id=${threadId}` : ""}`,
    }),
    ingestEmail: builder.mutation<any, any>({ query: (b) => ({ url: "/crm/emails/ingest", method: "POST", body: b }) }),
    getContracts: builder.query<any[], string | void>({
      query: (cid) => `/crm/contracts${cid ? `?company_id=${cid}` : ""}`,
    }),
    createContract: builder.mutation<any, any>({ query: (b) => ({ url: "/crm/contracts", method: "POST", body: b }) }),
    getContractMetrics: builder.query<any, void>({ query: () => "/crm/contracts/metrics" }),
    updateContractStatus: builder.mutation<any, { id: string; status: string }>({
      query: ({ id, status }) => ({ url: `/crm/contracts/${id}?status=${status}`, method: "PATCH" }),
    }),
    getCommissionRules: builder.query<any[], void>({ query: () => "/crm/commission-rules" }),
    createCommissionRule: builder.mutation<any, any>({ query: (b) => ({ url: "/crm/commission-rules", method: "POST", body: b }) }),
    computeCommissions: builder.mutation<any, void>({ query: () => ({ url: "/crm/commissions/compute", method: "POST" }) }),
    getCommissions: builder.query<any[], string | void>({
      query: (uid) => `/crm/commissions${uid ? `?user_id=${uid}` : ""}`,
    }),
    payCommission: builder.mutation<any, string>({ query: (id) => ({ url: `/crm/commissions/${id}/pay`, method: "POST" }) }),
    getTerritories: builder.query<any[], void>({ query: () => "/crm/territories" }),
    createTerritory: builder.mutation<any, any>({ query: (b) => ({ url: "/crm/territories", method: "POST", body: b }) }),
    autoAssignLeads: builder.mutation<any, void>({ query: () => ({ url: "/crm/territories/auto-assign", method: "POST" }) }),
    getDrips: builder.query<any[], void>({ query: () => "/crm/drips" }),
    createDrip: builder.mutation<any, any>({ query: (b) => ({ url: "/crm/drips", method: "POST", body: b }) }),
    enrollDrip: builder.mutation<any, any>({ query: (b) => ({ url: "/crm/drips/enroll", method: "POST", body: b }) }),
    dripTick: builder.mutation<any, void>({ query: () => ({ url: "/crm/drips/tick", method: "POST" }) }),
    computeHealth: builder.mutation<any, void>({ query: () => ({ url: "/crm/health/compute", method: "POST" }) }),
    getHealth: builder.query<any[], void>({ query: () => "/crm/health" }),

    // ── DMS v2 ──
    checkoutDoc: builder.mutation<any, { id: string; body: any }>({
      query: ({ id, body }) => ({ url: `/dms/documents/${id}/checkout`, method: "POST", body }),
    }),
    checkinDoc: builder.mutation<any, string>({
      query: (id) => ({ url: `/dms/documents/${id}/checkin`, method: "POST" }),
    }),
    getLocks: builder.query<any[], void>({ query: () => "/dms/locks" }),
    getDocDiff: builder.query<any, { id: string; v1: number; v2: number }>({
      query: ({ id, v1, v2 }) => `/dms/documents/${id}/diff?v1=${v1}&v2=${v2}`,
    }),
    getWorkflows: builder.query<any[], string | void>({
      query: (did) => `/dms/workflows${did ? `?document_id=${did}` : ""}`,
    }),
    createWorkflow: builder.mutation<any, any>({ query: (b) => ({ url: "/dms/workflows", method: "POST", body: b }) }),
    advanceWorkflow: builder.mutation<any, { id: string; body: any }>({
      query: ({ id, body }) => ({ url: `/dms/workflows/${id}/advance`, method: "POST", body }),
    }),
    getAnnotations: builder.query<any[], string>({ query: (did) => `/dms/annotations?document_id=${did}` }),
    createAnnotation: builder.mutation<any, any>({ query: (b) => ({ url: "/dms/annotations", method: "POST", body: b }) }),
    resolveAnnotation: builder.mutation<any, string>({ query: (id) => ({ url: `/dms/annotations/${id}/resolve`, method: "POST" }) }),
    getESignProviders: builder.query<any[], void>({ query: () => "/dms/esign-providers" }),
    createESignProvider: builder.mutation<any, any>({ query: (b) => ({ url: "/dms/esign-providers", method: "POST", body: b }) }),
    scanVersion: builder.mutation<any, string>({ query: (id) => ({ url: `/dms/versions/${id}/scan`, method: "POST" }) }),
    getScanResults: builder.query<any[], string | void>({
      query: (s) => `/dms/scan-results${s ? `?status=${s}` : ""}`,
    }),

    // ── Cross v2 ──
    getAudit: builder.query<any[], { domain?: string; entityType?: string; entityId?: string }>({
      query: ({ domain, entityType, entityId }) =>
        `/audit?${domain ? `domain=${domain}` : ""}${entityType ? `&entity_type=${entityType}` : ""}${entityId ? `&entity_id=${entityId}` : ""}`,
    }),
    getScheduledReports: builder.query<any[], void>({ query: () => "/scheduled-reports" }),
    createScheduledReport: builder.mutation<any, any>({ query: (b) => ({ url: "/scheduled-reports", method: "POST", body: b }) }),
    runScheduledReports: builder.mutation<any, void>({ query: () => ({ url: "/scheduled-reports/run", method: "POST" }) }),
    getReportRuns: builder.query<any[], string>({ query: (id) => `/scheduled-reports/${id}/runs` }),
    getDashboards: builder.query<any[], void>({ query: () => "/dashboards" }),
    getCustomDashboard: builder.query<any, string>({ query: (id) => `/dashboards/${id}` }),
    createDashboardBuilder: builder.mutation<any, any>({ query: (b) => ({ url: "/dashboards", method: "POST", body: b }) }),
    addWidget: builder.mutation<any, { dashboardId: string; body: any }>({
      query: ({ dashboardId, body }) => ({ url: `/dashboards/${dashboardId}/widgets`, method: "POST", body }),
    }),
    deleteDashboard: builder.mutation<void, string>({ query: (id) => ({ url: `/dashboards/${id}`, method: "DELETE" }) }),
    getSsoProviders: builder.query<any[], void>({ query: () => "/sso/providers" }),
    createSsoProvider: builder.mutation<any, any>({ query: (b) => ({ url: "/sso/providers", method: "POST", body: b }) }),
    getWorkspaces: builder.query<any[], void>({ query: () => "/workspaces" }),
    createWorkspace: builder.mutation<any, any>({ query: (b) => ({ url: "/workspaces", method: "POST", body: b }) }),

    // ── ACL ─────────────────────────────────────────────────────
    getMyPermissions: builder.query<{ role: string; granted: string[]; denied: string[] }, void>({
      query: () => "/me/permissions",
    }),
    getAclPermissions: builder.query<any[], void>({ query: () => "/admin/acl/permissions" }),
    getAclGroups: builder.query<any[], void>({ query: () => "/admin/acl/groups" }),
    createAclGroup: builder.mutation<any, { name: string; description?: string }>({
      query: (b) => ({ url: "/admin/acl/groups", method: "POST", body: b }),
    }),
    deleteAclGroup: builder.mutation<void, string>({
      query: (id) => ({ url: `/admin/acl/groups/${id}`, method: "DELETE" }),
    }),
    getGroupPermissions: builder.query<string[], string>({
      query: (groupId) => `/admin/acl/groups/${groupId}/permissions`,
    }),
    setGroupPermissions: builder.mutation<string[], { groupId: string; codenames: string[] }>({
      query: ({ groupId, codenames }) => ({
        url: `/admin/acl/groups/${groupId}/permissions`, method: "PUT", body: { codenames },
      }),
    }),
    getAdminUsers: builder.query<any[], void>({ query: () => "/admin/users" }),
    getUserAclGroups: builder.query<any[], string>({
      query: (userId) => `/admin/acl/users/${userId}/groups`,
    }),
    setUserAclGroups: builder.mutation<any, { userId: string; group_ids: string[] }>({
      query: ({ userId, group_ids }) => ({
        url: `/admin/acl/users/${userId}/groups`, method: "PUT", body: { group_ids },
      }),
    }),
    getUserDirectPermissions: builder.query<any[], string>({
      query: (userId) => `/admin/acl/users/${userId}/permissions`,
    }),
    upsertUserPermission: builder.mutation<any, { userId: string; codename: string; is_deny: boolean; reason?: string }>({
      query: ({ userId, ...body }) => ({
        url: `/admin/acl/users/${userId}/permissions`, method: "POST", body,
      }),
    }),
    deleteUserPermission: builder.mutation<void, { userId: string; codename: string }>({
      query: ({ userId, codename }) => ({
        url: `/admin/acl/users/${userId}/permissions/${encodeURIComponent(codename)}`, method: "DELETE",
      }),
    }),
    inspectPermission: builder.query<any, { userId: string; codename: string; projectId?: string }>({
      query: ({ userId, codename, projectId }) => {
        const p = new URLSearchParams({ user_id: userId, codename });
        if (projectId) p.set("project_id", projectId);
        return `/admin/acl/inspect?${p}`;
      },
    }),
    getProjectMembers: builder.query<any[], string>({
      query: (projectId) => `/projects/${projectId}/members`,
    }),
    addProjectMember: builder.mutation<any, { projectId: string; user_id: string; role?: string }>({
      query: ({ projectId, ...body }) => ({
        url: `/projects/${projectId}/members`, method: "POST", body,
      }),
    }),
    removeProjectMember: builder.mutation<void, { projectId: string; userId: string }>({
      query: ({ projectId, userId }) => ({
        url: `/projects/${projectId}/members/${userId}`, method: "DELETE",
      }),
    }),
  }),
});

export const {
  useGetProjectsQuery,
  useGetProjectQuery,
  useCreateProjectMutation,
  useUpdateProjectMutation,
  useDeleteProjectMutation,
  useGetStakeholdersQuery,
  useCreateStakeholderMutation,
  useUpdateStakeholderMutation,
  useDeleteStakeholderMutation,
  useGetTeamMembersQuery,
  useCreateTeamMemberMutation,
  useUpdateTeamMemberMutation,
  useDeleteTeamMemberMutation,
  useGetTasksQuery,
  useCreateTaskMutation,
  useUpdateTaskMutation,
  useDeleteTaskMutation,
  useGetRisksQuery,
  useCreateRiskMutation,
  useUpdateRiskMutation,
  useDeleteRiskMutation,
  useGetDeliverablesQuery,
  useCreateDeliverableMutation,
  useUpdateDeliverableMutation,
  useDeleteDeliverableMutation,
  useGetMeasurementsQuery,
  useCreateMeasurementMutation,
  useUpdateMeasurementMutation,
  useDeleteMeasurementMutation,
  useGetChangeRequestsQuery,
  useCreateChangeRequestMutation,
  useUpdateChangeRequestMutation,
  useDeleteChangeRequestMutation,
  useGetDashboardQuery,
  useSignupMutation,
  useLoginMutation,
  useGetMeQuery,
  useGetDependenciesQuery,
  useCreateDependencyMutation,
  useDeleteDependencyMutation,
  useGetCpmQuery,
  useGetPertQuery,
  useGetReportSummaryQuery,
  useGetReportScheduleQuery,
  useGetReportRisksQuery,
  useGetReportPerformanceQuery,
  useGetEvmQuery,
  useGetGanttQuery,
  useGetBurndownQuery,
  useGetWorkloadQuery,
  useGetPortfolioQuery,
  useGetCommentsQuery,
  useCreateCommentMutation,
  useGetLessonsQuery,
  useCreateLessonMutation,
  useDeleteLessonMutation,
  useGetNotificationsQuery,
  useGetUnreadCountQuery,
  useMarkAllReadMutation,
  useGetTemplatesQuery,
  useCreateTemplateMutation,
  useApplyTemplateMutation,
  useGetTimeEntriesQuery,
  useCreateTimeEntryMutation,
  useGetTimeSummaryQuery,
  useGetSprintsQuery,
  useCreateSprintMutation,
  useUpdateSprintStatusMutation,
  useGetSprintVelocityQuery,
  useGetBaselinesQuery,
  useSaveBaselineMutation,
  useCompareBaselineQuery,
  useGetActivityQuery,
  useSearchQuery,
  useGetMonteCarloQuery,
  useGetResourceLevelingQuery,
  useGetBudgetQuery,
  useToggleDarkModeMutation,
  useGetCustomFieldsQuery,
  useCreateCustomFieldMutation,
  // ERP
  useGetErpDashboardQuery,
  useGetAccountsQuery,
  useCreateAccountMutation,
  useGetVendorsQuery,
  useCreateVendorMutation,
  useDeleteVendorMutation,
  useGetInvoicesQuery,
  useCreateInvoiceMutation,
  useUpdateInvoiceStatusMutation,
  useGetExpensesQuery,
  useCreateExpenseMutation,
  useGetPurchaseOrdersQuery,
  useCreatePurchaseOrderMutation,
  useGetAssetsQuery,
  useCreateAssetMutation,
  // CRM
  useGetCrmDashboardQuery,
  useGetCompaniesQuery,
  useCreateCompanyMutation,
  useDeleteCompanyMutation,
  useGetCrmContactsQuery,
  useCreateCrmContactMutation,
  useGetLeadsQuery,
  useCreateLeadMutation,
  useUpdateLeadStatusMutation,
  useGetOpportunitiesQuery,
  useCreateOpportunityMutation,
  useUpdateOpportunityStageMutation,
  useGetInteractionsQuery,
  useCreateInteractionMutation,
  // DMS
  useGetDmsDashboardQuery,
  useGetFoldersQuery,
  useCreateFolderMutation,
  useGetDocumentsQuery,
  useGetDocVersionsQuery,
  useSearchDocumentsQuery,
  // ERP extensions
  useGetBudgetsQuery,
  useCreateBudgetMutation,
  useGetBudgetVarianceQuery,
  useGetCurrenciesQuery,
  useCreateCurrencyMutation,
  useGetFxRatesQuery,
  useCreateFxRateMutation,
  useGetPaymentsQuery,
  useCreatePaymentMutation,
  useGetInvoiceAgingQuery,
  useGetRecurringInvoicesQuery,
  useCreateRecurringInvoiceMutation,
  useRunRecurringInvoicesMutation,
  useGetTaxReportQuery,
  useGetTrialBalanceQuery,
  useGetJournalQuery,
  useCreateJournalMutation,
  usePostJournalMutation,
  useGetBankTransactionsQuery,
  useCreateBankTransactionMutation,
  useAutoMatchBankMutation,
  // CRM extensions
  useGetForecastQuery,
  useScoreLeadMutation,
  useScoreAllLeadsMutation,
  useGetQuotesQuery,
  useCreateQuoteMutation,
  useUpdateQuoteStatusMutation,
  useConvertQuoteMutation,
  useGetCampaignsQuery,
  useCreateCampaignMutation,
  useGetCampaignRoiQuery,
  useAddCampaignMemberMutation,
  useGetFollowUpsDueQuery,
  useSetFollowUpMutation,
  useCompleteFollowUpMutation,
  // DMS extensions
  useGetSignaturesQuery,
  useCreateSignatureMutation,
  useDeclineSignatureMutation,
  useGetDmsTemplatesQuery,
  useCreateDmsTemplateMutation,
  useInstantiateTemplateMutation,
  useGetFolderPermissionsQuery,
  useGrantFolderPermissionMutation,
  useRevokeFolderPermissionMutation,
  useGetRetentionPoliciesQuery,
  useCreateRetentionPolicyMutation,
  useApplyRetentionMutation,
  useGetEntityLinksQuery,
  useCreateEntityLinkMutation,
  // Cross-cutting
  useGetCompanyTimelineQuery,
  useGetApprovalsQuery,
  useCreateApprovalMutation,
  useDecideApprovalMutation,
  useGetWebhooksQuery,
  useCreateWebhookMutation,
  useDeleteWebhookMutation,
  useTestWebhookMutation,
  useGetWebhookDeliveriesQuery,
  useGetApiKeysQuery,
  useCreateApiKeyMutation,
  useRevokeApiKeyMutation,
  // ERP v2
  useGetWarehousesQuery,
  useCreateWarehouseMutation,
  useGetProductsQuery,
  useCreateProductMutation,
  useGetStockQuery,
  useCreateMovementMutation,
  useGetReorderReportQuery,
  useGetDepreciationQuery,
  useCreateDepreciationMutation,
  useRunDepreciationMutation,
  useGetCreditNotesQuery,
  useCreateCreditNoteMutation,
  useGetPnlQuery,
  useGetBalanceSheetQuery,
  useGetCashFlowQuery,
  useGetRequisitionsQuery,
  useCreateRequisitionMutation,
  useUpdateRequisitionStatusMutation,
  useConvertRequisitionMutation,
  // CRM v2
  useGetEmailsQuery,
  useIngestEmailMutation,
  useGetContractsQuery,
  useCreateContractMutation,
  useGetContractMetricsQuery,
  useUpdateContractStatusMutation,
  useGetCommissionRulesQuery,
  useCreateCommissionRuleMutation,
  useComputeCommissionsMutation,
  useGetCommissionsQuery,
  usePayCommissionMutation,
  useGetTerritoriesQuery,
  useCreateTerritoryMutation,
  useAutoAssignLeadsMutation,
  useGetDripsQuery,
  useCreateDripMutation,
  useEnrollDripMutation,
  useDripTickMutation,
  useComputeHealthMutation,
  useGetHealthQuery,
  // DMS v2
  useCheckoutDocMutation,
  useCheckinDocMutation,
  useGetLocksQuery,
  useGetDocDiffQuery,
  useGetWorkflowsQuery,
  useCreateWorkflowMutation,
  useAdvanceWorkflowMutation,
  useGetAnnotationsQuery,
  useCreateAnnotationMutation,
  useResolveAnnotationMutation,
  useGetESignProvidersQuery,
  useCreateESignProviderMutation,
  useScanVersionMutation,
  useGetScanResultsQuery,
  // Cross v2
  useGetAuditQuery,
  useGetScheduledReportsQuery,
  useCreateScheduledReportMutation,
  useRunScheduledReportsMutation,
  useGetReportRunsQuery,
  useGetDashboardsQuery,
  useGetCustomDashboardQuery,
  useCreateDashboardBuilderMutation,
  useAddWidgetMutation,
  useDeleteDashboardMutation,
  useGetSsoProvidersQuery,
  useCreateSsoProviderMutation,
  useGetWorkspacesQuery,
  useCreateWorkspaceMutation,
  // ACL
  useGetMyPermissionsQuery,
  useGetAclPermissionsQuery,
  useGetAclGroupsQuery,
  useCreateAclGroupMutation,
  useDeleteAclGroupMutation,
  useGetGroupPermissionsQuery,
  useSetGroupPermissionsMutation,
  useGetAdminUsersQuery,
  useGetUserAclGroupsQuery,
  useSetUserAclGroupsMutation,
  useGetUserDirectPermissionsQuery,
  useUpsertUserPermissionMutation,
  useDeleteUserPermissionMutation,
  useInspectPermissionQuery,
  useGetProjectMembersQuery,
  useAddProjectMemberMutation,
  useRemoveProjectMemberMutation,
} = apiSlice;
