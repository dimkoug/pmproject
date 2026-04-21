#!/usr/bin/env python3
"""Seed the database with realistic fake data via the API.

Usage:
    # Against local docker:
    python seed_fake_data.py

    # Against a custom host:
    python seed_fake_data.py --base-url http://myserver:8000

Requires: pip install faker httpx
"""

import argparse
import random
import sys
from datetime import datetime, timedelta

import httpx
from faker import Faker

fake = Faker()

# ── Config ────────────────────────────────────────────────────────────

BASE_URL = "http://localhost:8000"
NUM_PROJECTS = 3
TEAM_PER_PROJECT = (6, 12)
TASKS_PER_PROJECT = (20, 40)
RISKS_PER_PROJECT = (8, 15)
STAKEHOLDERS_PER_PROJECT = (5, 10)
DELIVERABLES_PER_PROJECT = (4, 8)
MEASUREMENTS_PER_PROJECT = (5, 10)
CHANGE_REQUESTS_PER_PROJECT = (3, 6)
SPRINTS_PER_PROJECT = (3, 5)
COMMENTS_PER_PROJECT = (10, 25)
LESSONS_PER_PROJECT = (3, 6)
TIME_ENTRIES_PER_PROJECT = (15, 30)
DEPENDENCIES_PER_PROJECT = (8, 15)

# ── Enum values ───────────────────────────────────────────────────────

APPROACHES = ["predictive", "adaptive", "hybrid", "agile"]
CADENCES = ["single", "multiple", "periodic"]
PROJECT_STATUSES = ["initiating", "planning", "executing", "monitoring", "closing"]
TASK_STATUSES = ["backlog", "todo", "in_progress", "in_review", "done", "blocked"]
TASK_PRIORITIES = ["critical", "high", "medium", "low"]
RISK_CATEGORIES = ["technical", "external", "organizational", "project_management"]
RISK_PROBABILITIES = ["very_low", "low", "medium", "high", "very_high"]
RISK_IMPACTS = ["very_low", "low", "medium", "high", "very_high"]
RISK_STATUSES = ["identified", "analyzing", "planned", "active", "resolved", "closed"]
RISK_STRATEGIES = ["avoid", "mitigate", "transfer", "accept", "escalate"]
STAKEHOLDER_CATEGORIES = ["sponsor", "customer", "end_user", "regulator", "supplier", "internal", "external"]
ENGAGEMENT_LEVELS = ["unaware", "resistant", "neutral", "supportive", "leading"]
TEAM_ROLES = ["project_manager", "scrum_master", "product_owner", "developer", "analyst", "tester", "designer", "architect"]
DELIVERABLE_STATUSES = ["planned", "in_progress", "ready_for_review", "accepted", "rejected"]
QUALITY_LEVELS = ["not_assessed", "below_standard", "meets_standard", "exceeds_standard"]
METRIC_TYPES = ["kpi", "leading", "lagging", "outcome"]
MEASUREMENT_DOMAINS = ["schedule", "cost", "quality", "scope", "risk", "stakeholder", "team", "value"]
CHANGE_STATUSES = ["submitted", "under_review", "approved", "rejected", "implemented", "deferred"]
CHANGE_IMPACTS = ["low", "medium", "high", "critical"]
LESSON_CATEGORIES = ["process", "technical", "team", "communication", "risk", "stakeholder"]

# ── Realistic project data ────────────────────────────────────────────

PROJECT_TEMPLATES = [
    {
        "name": "Enterprise CRM Platform Migration",
        "description": "Migrate the legacy CRM system to a modern cloud-native platform with enhanced analytics, real-time dashboards, and AI-powered lead scoring.",
        "approach": "hybrid",
        "cadence": "periodic",
        "budget": 750000,
        "vision": "Become the industry leader in customer relationship management with real-time insights and predictive analytics.",
        "objectives": "Complete migration of 50k+ customer records, implement 15 new automation workflows, achieve 99.9% uptime SLA.",
        "success_criteria": "Zero data loss during migration, 30% improvement in sales team productivity, NPS score above 70.",
    },
    {
        "name": "Smart Factory IoT Monitoring System",
        "description": "Design and deploy an IoT-based real-time monitoring system for factory equipment with predictive maintenance alerts and energy optimization.",
        "approach": "agile",
        "cadence": "periodic",
        "budget": 1200000,
        "vision": "Transform manufacturing operations through intelligent automation and predictive analytics.",
        "objectives": "Connect 500+ sensors, reduce downtime by 40%, implement real-time anomaly detection.",
        "success_criteria": "95% sensor uptime, 30% reduction in maintenance costs, real-time alerts within 5 seconds.",
    },
    {
        "name": "Digital Banking Mobile App v3.0",
        "description": "Major redesign of the mobile banking application with biometric authentication, peer-to-peer payments, budgeting tools, and accessibility compliance.",
        "approach": "agile",
        "cadence": "periodic",
        "budget": 500000,
        "vision": "Deliver the most user-friendly and secure mobile banking experience in the market.",
        "objectives": "Launch on iOS and Android, integrate 3 payment providers, achieve WCAG 2.1 AA compliance.",
        "success_criteria": "4.5+ app store rating, 60% DAU increase, zero critical security vulnerabilities.",
    },
]

TASK_TEMPLATES = [
    # Design phase
    ("Requirements gathering & analysis", "Conduct stakeholder interviews and document functional/non-functional requirements", "done", 5, 3, 5, 8, 5000),
    ("System architecture design", "Design high-level system architecture including infrastructure, APIs, and data flow", "done", 8, 5, 8, 13, 8000),
    ("Database schema design", "Design normalized database schema with entity relationships", "done", 3, 2, 3, 5, 3000),
    ("UI/UX wireframe design", "Create wireframes and interactive prototypes for all major screens", "done", 5, 3, 5, 8, 6000),
    ("API contract definition", "Define RESTful API endpoints, request/response schemas, and authentication flow", "done", 3, 2, 3, 5, 3500),
    ("Security architecture review", "Review and document security controls, encryption, and access patterns", "done", 3, 2, 3, 5, 4000),
    # Development phase
    ("User authentication & authorization", "Implement JWT-based auth with role-based access control", "done", 5, 3, 5, 8, 5500),
    ("Core data models implementation", "Build SQLAlchemy models with migrations and seed data", "done", 5, 3, 5, 8, 5000),
    ("REST API - CRUD operations", "Implement create, read, update, delete endpoints for all entities", "in_progress", 8, 5, 8, 13, 8000),
    ("Real-time WebSocket integration", "Add WebSocket support for live updates and notifications", "in_progress", 5, 3, 5, 8, 5500),
    ("Search & filtering engine", "Build full-text search with faceted filtering", "in_progress", 5, 3, 5, 8, 5000),
    ("Dashboard & analytics module", "Build aggregation queries and chart data endpoints", "todo", 8, 5, 8, 13, 7000),
    ("Report generation engine", "Implement PDF and Excel export with templated reports", "todo", 5, 3, 5, 8, 5000),
    ("Email notification service", "Set up transactional email system with templates", "todo", 3, 2, 3, 5, 3000),
    ("File upload & storage", "Implement file upload with S3-compatible object storage", "todo", 3, 2, 3, 5, 3500),
    ("Caching layer implementation", "Add Redis caching for frequently accessed data", "backlog", 3, 2, 3, 5, 3000),
    ("Background job processing", "Set up Celery workers for async task execution", "backlog", 3, 2, 3, 5, 3500),
    ("Rate limiting & throttling", "Implement API rate limiting per user/endpoint", "backlog", 2, 1, 2, 4, 2000),
    # Testing phase
    ("Unit test suite", "Write comprehensive unit tests for all service modules", "in_progress", 8, 5, 8, 13, 6000),
    ("Integration test suite", "Write API integration tests with database fixtures", "todo", 8, 5, 8, 13, 6000),
    ("Performance & load testing", "Run load tests simulating 1000 concurrent users", "backlog", 5, 3, 5, 8, 4000),
    ("Security penetration testing", "Conduct OWASP Top 10 security audit", "backlog", 5, 3, 5, 8, 8000),
    ("UAT environment setup", "Configure staging environment for user acceptance testing", "todo", 3, 2, 3, 5, 2500),
    # Deployment phase
    ("CI/CD pipeline setup", "Configure GitHub Actions with automated testing and deployment", "in_review", 3, 2, 3, 5, 3000),
    ("Docker containerization", "Create production Dockerfiles and docker-compose configuration", "in_review", 3, 2, 3, 5, 2500),
    ("Production infrastructure provisioning", "Set up cloud infrastructure with Terraform", "todo", 5, 3, 5, 8, 5000),
    ("Database migration & seeding", "Run production migrations and seed initial data", "backlog", 2, 1, 2, 4, 1500),
    ("Monitoring & alerting setup", "Configure Prometheus, Grafana, and PagerDuty alerts", "backlog", 3, 2, 3, 5, 3000),
    ("SSL certificate & DNS setup", "Configure SSL termination and DNS records", "backlog", 1, 1, 1, 2, 500),
    ("Go-live runbook creation", "Document step-by-step deployment and rollback procedures", "backlog", 2, 1, 2, 3, 1500),
    ("Post-deployment smoke testing", "Verify critical flows in production after deploy", "blocked", 2, 1, 2, 3, 1500),
]

RISK_TEMPLATES = [
    ("Key developer leaves mid-project", "technical", "medium", "very_high", "mitigate",
     "Cross-train team members, maintain documentation, offer retention bonuses",
     "Unexpected resignation or extended leave announcement"),
    ("Third-party API rate limits exceeded", "external", "high", "medium", "mitigate",
     "Implement request queuing, add caching layer, negotiate higher rate limits",
     "API response returns 429 status codes frequently"),
    ("Scope creep from stakeholder requests", "project_management", "very_high", "high", "avoid",
     "Enforce change request process, prioritize backlog weekly, maintain clear scope boundaries",
     "More than 3 unplanned features requested in a sprint"),
    ("Database performance degradation under load", "technical", "medium", "high", "mitigate",
     "Add indexes, implement query optimization, set up read replicas",
     "Query response times exceed 500ms for critical endpoints"),
    ("Security vulnerability in dependency", "technical", "medium", "very_high", "transfer",
     "Enable Dependabot alerts, schedule monthly dependency audits, have incident response plan",
     "CVE reported for a production dependency"),
    ("Cloud provider service outage", "external", "low", "very_high", "accept",
     "Design for multi-AZ redundancy, maintain offline fallback mode",
     "Cloud provider status page shows major incident"),
    ("Integration partner delays delivery", "external", "high", "medium", "mitigate",
     "Build mock services, add buffer time to schedule, identify backup vendors",
     "Partner misses two consecutive milestone dates"),
    ("Budget overrun exceeds 15% threshold", "project_management", "medium", "high", "escalate",
     "Weekly budget reviews, flag variances early, prepare cost reduction options",
     "EVM shows CPI below 0.85"),
    ("Team burnout during crunch period", "organizational", "high", "medium", "avoid",
     "Enforce sustainable pace, rotate on-call, provide mental health resources",
     "Team velocity drops 30% or multiple team members report exhaustion"),
    ("Regulatory compliance gap discovered", "external", "low", "very_high", "mitigate",
     "Engage compliance consultant, conduct monthly audits, maintain compliance checklist",
     "Audit reveals non-compliance with data protection regulations"),
    ("Data migration causes data loss", "technical", "low", "very_high", "avoid",
     "Run parallel systems during migration, validate data checksums, maintain rollback plan",
     "Automated tests detect data inconsistencies after migration batch"),
    ("Production deployment fails", "technical", "medium", "high", "mitigate",
     "Blue-green deployment strategy, automated rollback, canary releases",
     "Health checks fail after deployment to production"),
]

DELIVERABLE_TEMPLATES = [
    ("Technical Architecture Document", "Comprehensive system architecture including infrastructure diagrams, API specifications, and data flow models", "accepted", "exceeds_standard", 100, "Peer reviewed by senior architect; covers scalability, security, and disaster recovery"),
    ("Database Schema & Migration Scripts", "Normalized database schema with Alembic migration scripts and seed data", "accepted", "meets_standard", 100, "All tables created with proper indexes and constraints"),
    ("REST API v1.0", "Full CRUD API with 100+ endpoints, authentication, pagination, and OpenAPI documentation", "in_progress", "not_assessed", 65, "All endpoints return valid responses and pass schema validation"),
    ("Frontend Application v1.0", "React SPA with responsive design, state management, and real-time updates", "in_progress", "not_assessed", 50, "Lighthouse score above 90, WCAG 2.1 AA compliant"),
    ("Test Suite & Coverage Report", "Unit, integration, and E2E tests with 85%+ code coverage", "planned", "not_assessed", 20, "Coverage report generated, all critical paths covered"),
    ("CI/CD Pipeline", "Automated build, test, and deploy pipeline with staging and production environments", "ready_for_review", "meets_standard", 90, "Pipeline runs in under 10 minutes, includes security scanning"),
    ("User Documentation", "End-user guide with screenshots, FAQ, and video tutorials", "planned", "not_assessed", 10, "Documentation covers all major workflows"),
    ("Operations Runbook", "Deployment procedures, monitoring setup, incident response, and escalation paths", "planned", "not_assessed", 5, "Runbook tested through tabletop exercise"),
]

MEASUREMENT_TEMPLATES = [
    ("Schedule Performance Index (SPI)", "schedule", "kpi", 1.0, "ratio", 0.8, 0.9, 1.0),
    ("Cost Performance Index (CPI)", "cost", "kpi", 1.0, "ratio", 0.8, 0.9, 1.0),
    ("Sprint Velocity", "team", "leading", 30, "story points", 15, 22, 28),
    ("Defect Density", "quality", "lagging", 0.5, "defects/KLOC", 2.0, 1.0, 0.5),
    ("Code Coverage", "quality", "kpi", 85, "%", 60, 75, 85),
    ("Customer Satisfaction (CSAT)", "stakeholder", "outcome", 90, "%", 60, 75, 85),
    ("API Response Time (p95)", "quality", "kpi", 200, "ms", 1000, 500, 200),
    ("Team Utilization Rate", "team", "kpi", 80, "%", 50, 65, 75),
    ("Open Risk Count", "risk", "leading", 5, "risks", 15, 10, 5),
    ("Requirements Traceability", "scope", "kpi", 100, "%", 70, 85, 95),
]

STAKEHOLDER_TEMPLATES = [
    ("Sarah Mitchell", "Executive Sponsor", "sponsor", "supportive", "leading", "high", "high"),
    ("James Rodriguez", "Product Owner", "customer", "leading", "leading", "high", "high"),
    ("Dr. Emily Chen", "Compliance Officer", "regulator", "neutral", "supportive", "high", "medium"),
    ("Michael Thompson", "VP of Engineering", "internal", "supportive", "leading", "high", "high"),
    ("Lisa Park", "End User Representative", "end_user", "neutral", "supportive", "low", "high"),
    ("David Kim", "Infrastructure Manager", "internal", "supportive", "supportive", "medium", "medium"),
    ("Amanda Foster", "QA Lead", "internal", "supportive", "leading", "medium", "high"),
    ("Robert Chen", "External Auditor", "regulator", "unaware", "neutral", "high", "low"),
    ("Jennifer Walsh", "Marketing Director", "customer", "resistant", "supportive", "medium", "medium"),
    ("Tom Bradley", "Cloud Vendor Account Manager", "supplier", "supportive", "supportive", "medium", "low"),
]

TEAM_TEMPLATES = [
    ("Alex Morgan", "alex.morgan@company.com", "project_manager", "Overall project coordination, risk management, stakeholder communication", "PMP, Agile, Leadership, Budgeting", 100),
    ("Priya Patel", "priya.patel@company.com", "scrum_master", "Sprint facilitation, impediment removal, team coaching", "Scrum, Kanban, Facilitation, Conflict resolution", 100),
    ("Marcus Johnson", "marcus.j@company.com", "architect", "System design, technical decisions, code reviews", "Python, AWS, Microservices, System design", 80),
    ("Sofia Hernandez", "sofia.h@company.com", "developer", "Backend API development, database optimization", "Python, FastAPI, PostgreSQL, Redis", 100),
    ("James Lee", "james.lee@company.com", "developer", "Backend services, background jobs, integrations", "Python, Celery, Docker, Kubernetes", 100),
    ("Emma Wilson", "emma.w@company.com", "developer", "Frontend development, UI components, state management", "React, TypeScript, Redux, CSS", 100),
    ("Ryan Chen", "ryan.chen@company.com", "developer", "Full-stack development, WebSocket, real-time features", "React, Python, WebSocket, REST APIs", 100),
    ("Olivia Brown", "olivia.b@company.com", "tester", "Test automation, CI/CD integration, quality assurance", "Pytest, Selenium, Jest, Load testing", 100),
    ("Noah Davis", "noah.d@company.com", "analyst", "Requirements analysis, user stories, acceptance criteria", "Business analysis, SQL, Jira, Figma", 80),
    ("Mia Taylor", "mia.t@company.com", "designer", "UI/UX design, prototyping, design system", "Figma, Adobe XD, User research, Accessibility", 60),
    ("Ethan Martinez", "ethan.m@company.com", "developer", "DevOps, infrastructure, monitoring, deployment", "Docker, Terraform, GitHub Actions, Prometheus", 80),
    ("Isabella Garcia", "isabella.g@company.com", "product_owner", "Backlog prioritization, feature definition, stakeholder alignment", "Product management, Analytics, A/B testing", 50),
]


def log(msg: str):
    print(f"  {msg}")


def run(base_url: str):
    client = httpx.Client(base_url=base_url, timeout=30)

    # ── 1. Create user & authenticate ────────────────────────────────
    print("\n[1/12] Creating user account...")
    signup_resp = client.post("/api/auth/signup", json={
        "name": "PM Admin",
        "email": f"admin_{fake.random_int(1000,9999)}@pmproject.dev",
        "password": "Admin123!@#",
    })
    if signup_resp.status_code == 409:
        # User exists, try login
        login_resp = client.post("/api/auth/login", json={
            "email": "admin@pmproject.dev",
            "password": "Admin123!@#",
        })
        token = login_resp.json()["access_token"]
    else:
        signup_resp.raise_for_status()
        token = signup_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    log(f"Authenticated successfully")

    for proj_idx in range(NUM_PROJECTS):
        tmpl = PROJECT_TEMPLATES[proj_idx % len(PROJECT_TEMPLATES)]
        print(f"\n{'='*60}")
        print(f"[Project {proj_idx+1}/{NUM_PROJECTS}] {tmpl['name']}")
        print(f"{'='*60}")

        # ── 2. Create project ────────────────────────────────────────
        print("\n[2/12] Creating project...")
        start_date = fake.date_between(start_date="-60d", end_date="-30d")
        end_date = start_date + timedelta(days=random.randint(90, 180))
        project = client.post("/api/projects/", headers=headers, json={
            "name": tmpl["name"],
            "description": tmpl["description"],
            "development_approach": tmpl["approach"],
            "delivery_cadence": tmpl["cadence"],
            "budget": tmpl["budget"],
            "vision": tmpl["vision"],
            "objectives": tmpl["objectives"],
            "success_criteria": tmpl["success_criteria"],
            "status": random.choice(["planning", "executing", "monitoring"]),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }).json()
        pid = project["id"]
        log(f"Created: {project['name']} ({pid[:8]}...)")

        # ── 3. Create team members ───────────────────────────────────
        print("\n[3/12] Creating team members...")
        n_team = random.randint(*TEAM_PER_PROJECT)
        team_ids = []
        for i in range(n_team):
            t = TEAM_TEMPLATES[i % len(TEAM_TEMPLATES)]
            suffix = f"_{proj_idx}" if i >= len(TEAM_TEMPLATES) else ""
            member = client.post("/api/team-members/", headers=headers, json={
                "project_id": pid,
                "name": t[0] + suffix,
                "email": t[1].replace("@", f"{suffix}@"),
                "role": t[2],
                "responsibilities": t[3],
                "skills": t[4],
                "availability": t[5],
            }).json()
            team_ids.append(member["id"])
        log(f"Created {n_team} team members")

        # ── 4. Create stakeholders ───────────────────────────────────
        print("\n[4/12] Creating stakeholders...")
        n_sh = random.randint(*STAKEHOLDERS_PER_PROJECT)
        for i in range(n_sh):
            s = STAKEHOLDER_TEMPLATES[i % len(STAKEHOLDER_TEMPLATES)]
            client.post("/api/stakeholders/", headers=headers, json={
                "project_id": pid,
                "name": s[0],
                "role": s[1],
                "email": fake.company_email(),
                "category": s[2],
                "engagement_level": s[3],
                "desired_engagement": s[4],
                "influence": s[5],
                "interest": s[6],
                "expectations": fake.paragraph(nb_sentences=2),
                "communication_needs": random.choice(["Weekly email updates", "Bi-weekly meetings", "Monthly reports", "Daily standup"]),
            })
        log(f"Created {n_sh} stakeholders")

        # ── 5. Create sprints ────────────────────────────────────────
        print("\n[5/12] Creating sprints...")
        n_sprints = random.randint(*SPRINTS_PER_PROJECT)
        sprint_ids = []
        sprint_start = start_date
        for i in range(n_sprints):
            sprint_end = sprint_start + timedelta(days=14)
            statuses = ["completed"] * (n_sprints - 2) + ["active", "planning"]
            sprint_status = statuses[i] if i < len(statuses) else "completed"
            sprint = client.post("/api/sprints/", headers=headers, json={
                "project_id": pid,
                "name": f"Sprint {i+1}",
                "goal": fake.sentence(nb_words=8),
                "sprint_number": i + 1,
                "start_date": sprint_start.isoformat(),
                "end_date": sprint_end.isoformat(),
            }).json()
            sprint_ids.append(sprint["id"])
            if sprint_status in ("completed", "active"):
                client.patch(f"/api/sprints/{sprint['id']}?status={sprint_status}", headers=headers)
            sprint_start = sprint_end + timedelta(days=1)
        log(f"Created {n_sprints} sprints")

        # ── 6. Create tasks ──────────────────────────────────────────
        print("\n[6/12] Creating tasks...")
        n_tasks = random.randint(*TASKS_PER_PROJECT)
        task_ids = []
        for i in range(n_tasks):
            t = TASK_TEMPLATES[i % len(TASK_TEMPLATES)]
            title, desc, status, duration, opt, ml, pess, cost = t
            actual_cost_ratio = random.uniform(0.7, 1.4)
            completed_date = None
            if status == "done":
                completed_date = fake.date_between(start_date=start_date, end_date="today").isoformat()
            task = client.post("/api/tasks/", headers=headers, json={
                "project_id": pid,
                "title": title,
                "description": desc,
                "status": status,
                "priority": random.choice(TASK_PRIORITIES),
                "story_points": random.choice([1, 2, 3, 5, 8, 13]),
                "duration_days": duration,
                "optimistic_duration": opt,
                "most_likely_duration": ml,
                "pessimistic_duration": pess,
                "planned_cost": cost,
                "actual_cost": round(cost * actual_cost_ratio, 2) if status in ("done", "in_progress", "in_review") else 0,
                "assignee_id": random.choice(team_ids),
                "sprint_id": random.choice(sprint_ids) if sprint_ids else None,
                "wbs_code": f"{proj_idx+1}.{(i//5)+1}.{(i%5)+1}",
                "start_date": (start_date + timedelta(days=i * 2)).isoformat(),
                "due_date": (start_date + timedelta(days=i * 2 + duration)).isoformat(),
                "completed_date": completed_date,
            }).json()
            task_ids.append(task["id"])
        log(f"Created {n_tasks} tasks")

        # ── 7. Create task dependencies ──────────────────────────────
        print("\n[7/12] Creating task dependencies...")
        n_deps = min(random.randint(*DEPENDENCIES_PER_PROJECT), len(task_ids) - 1)
        created_deps = set()
        deps_created = 0
        for _ in range(n_deps * 3):  # try more times than needed to account for rejections
            if deps_created >= n_deps:
                break
            i = random.randint(0, len(task_ids) - 2)
            j = random.randint(i + 1, len(task_ids) - 1)
            pair = (task_ids[i], task_ids[j])
            if pair in created_deps:
                continue
            resp = client.post(f"/api/projects/{pid}/dependencies", headers=headers, json={
                "project_id": pid,
                "predecessor_id": task_ids[i],
                "successor_id": task_ids[j],
                "dependency_type": "finish_to_start",
                "lag_days": random.choice([0, 0, 0, 1, 2]),
            })
            if resp.status_code == 201:
                created_deps.add(pair)
                deps_created += 1
        log(f"Created {deps_created} dependencies")

        # ── 8. Create risks ──────────────────────────────────────────
        print("\n[8/12] Creating risks...")
        n_risks = random.randint(*RISKS_PER_PROJECT)
        risk_ids = []
        for i in range(n_risks):
            r = RISK_TEMPLATES[i % len(RISK_TEMPLATES)]
            title, cat, prob, impact, strategy, response, trigger = r
            risk = client.post("/api/risks/", headers=headers, json={
                "project_id": pid,
                "title": title,
                "description": fake.paragraph(nb_sentences=3),
                "category": cat,
                "probability": prob,
                "impact": impact,
                "status": random.choice(RISK_STATUSES[:4]),  # mostly open
                "strategy": strategy,
                "response_plan": response,
                "trigger_conditions": trigger,
                "owner_id": random.choice(team_ids),
            }).json()
            risk_ids.append(risk["id"])
        log(f"Created {n_risks} risks")

        # ── 9. Create deliverables ───────────────────────────────────
        print("\n[9/12] Creating deliverables...")
        n_del = random.randint(*DELIVERABLES_PER_PROJECT)
        deliverable_ids = []
        for i in range(n_del):
            d = DELIVERABLE_TEMPLATES[i % len(DELIVERABLE_TEMPLATES)]
            name, desc, status, quality, pct, criteria = d
            due = start_date + timedelta(days=random.randint(30, 120))
            deliverable = client.post("/api/deliverables/", headers=headers, json={
                "project_id": pid,
                "name": name,
                "description": desc,
                "status": status,
                "quality_level": quality,
                "completion_percentage": pct,
                "acceptance_criteria": criteria,
                "due_date": due.isoformat(),
                "delivered_date": due.isoformat() if status == "accepted" else None,
            }).json()
            deliverable_ids.append(deliverable["id"])
        log(f"Created {n_del} deliverables")

        # ── 10. Create measurements ──────────────────────────────────
        print("\n[10/12] Creating measurements...")
        n_meas = random.randint(*MEASUREMENTS_PER_PROJECT)
        for i in range(n_meas):
            m = MEASUREMENT_TEMPLATES[i % len(MEASUREMENT_TEMPLATES)]
            name, domain, mtype, target, unit, red, yellow, green = m
            # Simulate realistic actual values
            noise = random.uniform(0.7, 1.15)
            actual = round(target * noise, 2)
            client.post("/api/measurements/", headers=headers, json={
                "project_id": pid,
                "name": name,
                "description": f"Tracks {name.lower()} across the project lifecycle",
                "metric_type": mtype,
                "domain": domain,
                "target_value": target,
                "actual_value": actual,
                "unit": unit,
                "threshold_red": red,
                "threshold_yellow": yellow,
                "threshold_green": green,
            })
        log(f"Created {n_meas} measurements")

        # ── 11. Create change requests ───────────────────────────────
        print("\n[11/12] Creating change requests...")
        n_cr = random.randint(*CHANGE_REQUESTS_PER_PROJECT)
        cr_titles = [
            "Add multi-language support to the UI",
            "Migrate from REST to GraphQL for mobile app",
            "Increase server capacity for Black Friday traffic",
            "Integrate single sign-on (SSO) with Okta",
            "Add audit trail logging for compliance",
            "Switch payment provider from Stripe to Adyen",
        ]
        for i in range(n_cr):
            client.post("/api/change-requests/", headers=headers, json={
                "project_id": pid,
                "title": cr_titles[i % len(cr_titles)],
                "description": fake.paragraph(nb_sentences=3),
                "justification": fake.paragraph(nb_sentences=2),
                "status": random.choice(CHANGE_STATUSES),
                "impact": random.choice(CHANGE_IMPACTS),
                "impact_analysis": fake.paragraph(nb_sentences=4),
                "requested_by_id": random.choice(team_ids),
                "reviewed_by_id": random.choice(team_ids),
            })
        log(f"Created {n_cr} change requests")

        # ── 12. Create comments, lessons, time entries ───────────────
        print("\n[12/12] Creating comments, lessons & time entries...")

        # Comments on tasks and risks
        n_comments = random.randint(*COMMENTS_PER_PROJECT)
        comment_bodies = [
            "Great progress on this! Let's keep the momentum going.",
            "Blocked on this due to a dependency — need input from the architecture team.",
            "I've updated the acceptance criteria based on today's stakeholder call.",
            "This needs a code review before we can move it to done.",
            "Flagging a potential risk here — we should discuss in tomorrow's standup.",
            "Completed the initial implementation. Ready for testing.",
            "Can we break this into smaller subtasks? It's getting complex.",
            "Updated the estimate — original was too optimistic.",
            "This is now on the critical path. Let's prioritize it.",
            "Nice work! The test coverage on this is excellent.",
        ]
        for _ in range(n_comments):
            target_type = random.choice(["task", "risk"])
            target_id = random.choice(task_ids) if target_type == "task" else random.choice(risk_ids)
            client.post("/api/comments/", headers=headers, json={
                "project_id": pid,
                "target_type": target_type,
                "target_id": target_id,
                "body": random.choice(comment_bodies),
            })
        log(f"Created {n_comments} comments")

        # Lessons learned
        n_lessons = random.randint(*LESSONS_PER_PROJECT)
        lesson_data = [
            ("Early stakeholder alignment saves rework", "process", "We spent 2 weeks building a feature the sponsor didn't want.", "2 weeks of wasted effort and team frustration", "Always validate features with stakeholders before starting development"),
            ("Automated testing catches regressions early", "technical", "A manual-only testing approach let a critical bug slip to staging.", "4-hour production incident and emergency hotfix", "Invest in CI/CD and automated test suites from day one"),
            ("Cross-training prevents knowledge silos", "team", "When our lead developer was on vacation, the team couldn't resolve a critical issue.", "3-day delay on a sprint commitment", "Ensure at least 2 team members are familiar with each system component"),
            ("Daily standups improve transparency", "communication", "Switching from weekly to daily standups improved issue visibility.", "30% faster impediment resolution", "Keep standups short (15 min) and focused on blockers"),
            ("Risk register must be a living document", "risk", "Risks identified at project start became stale and irrelevant.", "Missed emerging risks that caused schedule delays", "Review and update the risk register every sprint retrospective"),
        ]
        for i in range(n_lessons):
            ld = lesson_data[i % len(lesson_data)]
            client.post("/api/lessons/", headers=headers, json={
                "project_id": pid,
                "title": ld[0],
                "category": ld[1],
                "what_happened": ld[2],
                "impact": ld[3],
                "recommendation": ld[4],
            })
        log(f"Created {n_lessons} lessons learned")

        # Time entries
        n_time = random.randint(*TIME_ENTRIES_PER_PROJECT)
        for _ in range(n_time):
            work_date = fake.date_between(start_date=start_date, end_date="today")
            client.post("/api/time-entries/", headers=headers, json={
                "project_id": pid,
                "task_id": random.choice(task_ids),
                "hours": round(random.uniform(1, 8), 1),
                "work_date": work_date.isoformat(),
                "description": random.choice([
                    "Development work", "Code review", "Bug fixing",
                    "Testing and QA", "Documentation", "Meetings",
                    "Architecture design", "Deployment tasks",
                ]),
            })
        log(f"Created {n_time} time entries")

    # ── Summary ──────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("SEEDING COMPLETE!")
    print(f"{'='*60}")
    print(f"  Projects:      {NUM_PROJECTS}")
    print(f"  Base URL:      {base_url}")
    print(f"  Dashboard:     {base_url}/api/dashboard/<project_id>")
    print(f"  Health:        {base_url}/api/health")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the PM project with realistic fake data")
    parser.add_argument("--base-url", default=BASE_URL, help=f"API base URL (default: {BASE_URL})")
    args = parser.parse_args()
    run(args.base_url)
