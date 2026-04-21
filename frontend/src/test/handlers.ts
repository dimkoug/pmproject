import { http, HttpResponse } from "msw";

const API_URL = "http://localhost:8000/api";

// Mock data
const mockProjects = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    name: "PMBOK Test Project",
    description: "A test project for PMBOK 7th Edition",
    status: "executing",
    development_approach: "agile",
    delivery_cadence: "periodic",
    budget: 100000,
    vision: "Test vision",
    objectives: "Test objectives",
    success_criteria: "All tests pass",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

const mockStakeholders = [
  {
    id: "22222222-2222-2222-2222-222222222222",
    project_id: "11111111-1111-1111-1111-111111111111",
    name: "John Sponsor",
    role: "Executive Sponsor",
    email: "john@example.com",
    category: "sponsor",
    engagement_level: "supportive",
    desired_engagement: "leading",
    influence: "high",
    interest: "high",
    expectations: "ROI within 12 months",
    communication_needs: "Monthly report",
    created_at: "2026-01-01T00:00:00Z",
  },
];

const mockTeamMembers = [
  {
    id: "33333333-3333-3333-3333-333333333333",
    project_id: "11111111-1111-1111-1111-111111111111",
    name: "Alice PM",
    email: "alice@example.com",
    role: "project_manager",
    responsibilities: "Project coordination",
    skills: "Leadership, Agile",
    availability: 100,
    created_at: "2026-01-01T00:00:00Z",
  },
];

const mockTasks = [
  {
    id: "44444444-4444-4444-4444-444444444444",
    project_id: "11111111-1111-1111-1111-111111111111",
    title: "Set up CI/CD",
    description: "Configure pipeline",
    status: "in_progress",
    priority: "high",
    story_points: 5,
    assignee_id: "33333333-3333-3333-3333-333333333333",
    completed_date: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "44444444-4444-4444-4444-444444444445",
    project_id: "11111111-1111-1111-1111-111111111111",
    title: "Write tests",
    description: "Add test coverage",
    status: "backlog",
    priority: "medium",
    story_points: 8,
    assignee_id: null,
    completed_date: null,
    created_at: "2026-01-02T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
  },
];

const mockRisks = [
  {
    id: "55555555-5555-5555-5555-555555555555",
    project_id: "11111111-1111-1111-1111-111111111111",
    title: "Key person dependency",
    description: "Single point of failure",
    category: "organizational",
    probability: "high",
    impact: "very_high",
    status: "active",
    strategy: "mitigate",
    response_plan: "Cross-train team",
    owner_id: "33333333-3333-3333-3333-333333333333",
    trigger_conditions: "Lead leaves",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

const mockDeliverables = [
  {
    id: "66666666-6666-6666-6666-666666666666",
    project_id: "11111111-1111-1111-1111-111111111111",
    name: "API Module",
    description: "REST API backend",
    status: "in_progress",
    quality_level: "meets_standard",
    acceptance_criteria: "All endpoints tested",
    completion_percentage: 75.0,
    due_date: null,
    delivered_date: null,
    created_at: "2026-01-01T00:00:00Z",
  },
];

const mockMeasurements = [
  {
    id: "77777777-7777-7777-7777-777777777777",
    project_id: "11111111-1111-1111-1111-111111111111",
    name: "Sprint Velocity",
    description: "Story points per sprint",
    metric_type: "kpi",
    domain: "team",
    target_value: 30,
    actual_value: 28,
    unit: "points",
    threshold_red: 20,
    threshold_yellow: 25,
    threshold_green: 30,
    measured_at: null,
    created_at: "2026-01-01T00:00:00Z",
  },
];

const mockChangeRequests = [
  {
    id: "88888888-8888-8888-8888-888888888888",
    project_id: "11111111-1111-1111-1111-111111111111",
    title: "Add OAuth2 support",
    description: "Implement OAuth2 for third-party auth",
    justification: "Customer requirement",
    status: "under_review",
    impact: "high",
    impact_analysis: "2 sprint delay",
    requested_by_id: "33333333-3333-3333-3333-333333333333",
    reviewed_by_id: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

const mockDashboard = {
  task_stats: { backlog: 1, in_progress: 1, done: 0 },
  risk_stats: { active: 1 },
  deliverable_stats: { in_progress: 1 },
  stakeholder_count: 1,
  team_count: 1,
  change_request_count: 1,
  measurements: [
    { id: "77777777-7777-7777-7777-777777777777", name: "Sprint Velocity", domain: "team", target_value: 30, actual_value: 28, unit: "points" },
  ],
};

export const handlers = [
  // Projects
  http.get(`${API_URL}/projects/`, () => HttpResponse.json(mockProjects)),
  http.get(`${API_URL}/projects/:id`, () => HttpResponse.json(mockProjects[0])),
  http.post(`${API_URL}/projects/`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockProjects[0], ...body, id: crypto.randomUUID() }, { status: 201 });
  }),
  http.patch(`${API_URL}/projects/:id`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockProjects[0], ...body });
  }),
  http.delete(`${API_URL}/projects/:id`, () => new HttpResponse(null, { status: 204 })),

  // Stakeholders
  http.get(`${API_URL}/stakeholders/`, () => HttpResponse.json(mockStakeholders)),
  http.post(`${API_URL}/stakeholders/`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockStakeholders[0], ...body, id: crypto.randomUUID() }, { status: 201 });
  }),
  http.delete(`${API_URL}/stakeholders/:id`, () => new HttpResponse(null, { status: 204 })),

  // Team Members
  http.get(`${API_URL}/team-members/`, () => HttpResponse.json(mockTeamMembers)),
  http.post(`${API_URL}/team-members/`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockTeamMembers[0], ...body, id: crypto.randomUUID() }, { status: 201 });
  }),
  http.delete(`${API_URL}/team-members/:id`, () => new HttpResponse(null, { status: 204 })),

  // Tasks
  http.get(`${API_URL}/tasks/`, () => HttpResponse.json(mockTasks)),
  http.post(`${API_URL}/tasks/`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockTasks[0], ...body, id: crypto.randomUUID() }, { status: 201 });
  }),
  http.patch(`${API_URL}/tasks/:id`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockTasks[0], ...body });
  }),
  http.delete(`${API_URL}/tasks/:id`, () => new HttpResponse(null, { status: 204 })),

  // Risks
  http.get(`${API_URL}/risks/`, () => HttpResponse.json(mockRisks)),
  http.post(`${API_URL}/risks/`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockRisks[0], ...body, id: crypto.randomUUID() }, { status: 201 });
  }),
  http.patch(`${API_URL}/risks/:id`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockRisks[0], ...body });
  }),
  http.delete(`${API_URL}/risks/:id`, () => new HttpResponse(null, { status: 204 })),

  // Deliverables
  http.get(`${API_URL}/deliverables/`, () => HttpResponse.json(mockDeliverables)),
  http.post(`${API_URL}/deliverables/`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockDeliverables[0], ...body, id: crypto.randomUUID() }, { status: 201 });
  }),
  http.patch(`${API_URL}/deliverables/:id`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockDeliverables[0], ...body });
  }),
  http.delete(`${API_URL}/deliverables/:id`, () => new HttpResponse(null, { status: 204 })),

  // Measurements
  http.get(`${API_URL}/measurements/`, () => HttpResponse.json(mockMeasurements)),
  http.post(`${API_URL}/measurements/`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockMeasurements[0], ...body, id: crypto.randomUUID() }, { status: 201 });
  }),
  http.patch(`${API_URL}/measurements/:id`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockMeasurements[0], ...body });
  }),
  http.delete(`${API_URL}/measurements/:id`, () => new HttpResponse(null, { status: 204 })),

  // Change Requests
  http.get(`${API_URL}/change-requests/`, () => HttpResponse.json(mockChangeRequests)),
  http.post(`${API_URL}/change-requests/`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockChangeRequests[0], ...body, id: crypto.randomUUID() }, { status: 201 });
  }),
  http.patch(`${API_URL}/change-requests/:id`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...mockChangeRequests[0], ...body });
  }),
  http.delete(`${API_URL}/change-requests/:id`, () => new HttpResponse(null, { status: 204 })),

  // Dashboard
  http.get(`${API_URL}/dashboard/:id`, () => HttpResponse.json(mockDashboard)),
];
