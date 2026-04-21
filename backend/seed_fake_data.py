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

# Large-project counts — scaled up for realism (hundreds of tasks, dozens of risks).
LARGE_TEAM = (30, 60)
LARGE_TASKS_FLOOR = 150        # minimum tasks to generate per large project
LARGE_RISKS = (25, 40)
LARGE_STAKEHOLDERS = (20, 35)
LARGE_DELIVERABLES = (15, 25)
LARGE_MEASUREMENTS = (15, 25)
LARGE_CHANGE_REQUESTS = (15, 30)
LARGE_SPRINTS = (8, 16)
LARGE_COMMENTS = (80, 150)
LARGE_LESSONS = (10, 20)
LARGE_TIME_ENTRIES = (200, 400)
LARGE_DEPENDENCIES = (80, 150)

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


# ────────────────────────────────────────────────────────────────────────
# LARGE PROJECTS — each one is self-contained: metadata + tasks + risks +
# deliverables + measurements + stakeholders + team all tailored to the
# domain. These represent multi-year, multi-million-dollar programs so the
# UI has meaningful density for demos.
# ────────────────────────────────────────────────────────────────────────

def _phase_tasks(phase: str, titles: list[tuple[str, str, int, int]]) -> list[tuple]:
    """Expand a phase's task titles into the 8-tuple TASK_TEMPLATES shape:
    (title, description, status, duration_days, optimistic, most_likely, pessimistic, planned_cost).
    """
    tasks = []
    for title, desc, days, cost in titles:
        opt = max(1, int(days * 0.8))
        ml = days
        pess = int(days * 1.3)
        # Mix of statuses — early phases mostly done, later phases mostly upcoming
        tasks.append((title, f"[{phase}] {desc}", "done", days, opt, ml, pess, cost))
    return tasks


LARGE_PROJECTS = [
    # ══════════════════════════════════════════════════════════════════
    # 1. 40-STOREY DOWNTOWN OFFICE TOWER — construction site
    # ══════════════════════════════════════════════════════════════════
    {
        "meta": {
            "name": "Meridian One — 40-Storey Office Tower",
            "description": "Ground-up construction of a 1.2M sq-ft Class-A office tower in the central business district, including 4 levels of below-grade parking, a LEED Platinum envelope, and 38 tenant floors above a two-storey podium.",
            "approach": "predictive",
            "cadence": "single",
            "budget": 280_000_000,
            "vision": "Deliver a landmark tower that redefines sustainable high-rise construction in the region.",
            "objectives": "Reach topping-out by month 22; achieve LEED Platinum; hit a temporary occupancy permit by month 28.",
            "success_criteria": "Zero lost-time incidents; cost variance under 3%; 95% tenant-fit-out-ready floors at TCO.",
            "duration_days": 900,
        },
        "tasks":
            _phase_tasks("Pre-construction", [
                ("Boundary & topographic survey", "Certified land survey with easements and encroachments marked", 14, 45_000),
                ("Geotechnical investigation", "20 boreholes to 45m with SPT, lab analysis, and foundation recommendations", 35, 280_000),
                ("Environmental impact assessment", "Phase I/II ESA, traffic study, and stormwater modelling", 60, 320_000),
                ("Demolition of existing structures", "Controlled demolition of 3 low-rise buildings and utility abandonment", 45, 1_100_000),
                ("Excavation & shoring design", "Secant pile wall design and tiedback anchoring for 22m deep pit", 30, 650_000),
                ("Tower crane logistics plan", "Crane selection, jumping schedule, and over-sail permit coordination", 21, 120_000),
                ("Building-permit package", "Submission, RFI responses, and final issuance of construction permit", 120, 480_000),
            ])
            + _phase_tasks("Substructure", [
                ("Bulk excavation (220,000 m³)", "Hauling, dewatering, and stockpiling with truck cycle monitoring", 75, 4_800_000),
                ("Secant pile wall installation", "Installation of 880 interlocking secant piles with tiebacks", 90, 9_200_000),
                ("Mat foundation rebar & formwork", "3.5m thick raft with 2,800 tonnes of rebar and post-tensioning ducts", 60, 6_500_000),
                ("Mass concrete pour — raft slab", "8,200 m³ continuous pour with thermal-control instrumentation", 5, 4_100_000),
                ("Waterproofing membrane — below-grade", "HDPE membrane with protection board and drainage composite", 40, 1_900_000),
                ("Core wall slip-form setup", "Jump-form system setup, rebar cages, and MEP block-outs", 30, 2_400_000),
                ("Parking levels P1–P4 columns & slabs", "Precast columns and post-tensioned slabs for 4 levels", 180, 22_000_000),
            ])
            + _phase_tasks("Superstructure", [
                ("Core walls — floors 1–10", "Jump-form core wall construction with MEP openings and elevator rails", 90, 11_500_000),
                ("Core walls — floors 11–20", "Continued slip-form with high-strength concrete", 90, 11_800_000),
                ("Core walls — floors 21–30", "Slip-form with transitions for mechanical floor at 25", 90, 11_900_000),
                ("Core walls — floors 31–40", "Top-out sequence with crown block preparation", 90, 12_200_000),
                ("Post-tensioned floor slabs (38 typical floors)", "On-site rebar, formwork, PT tendons, pour, and stressing per floor", 380, 38_500_000),
                ("Steel framing — sky lobby at L25", "Transfer trusses and outrigger beams for mechanical floor", 45, 3_800_000),
                ("Stair core — all floors", "Precast stair units installation and balustrades", 120, 2_400_000),
                ("Tower crane jumping & dismantle", "Hydraulic jumps every 6 floors and final dismantle", 30, 850_000),
            ])
            + _phase_tasks("Envelope", [
                ("Unitized curtain-wall procurement", "750 tonnes aluminium + 92,000 m² double-glazed IGU units", 150, 18_500_000),
                ("Curtain-wall installation — lower half", "Floors 1–20 with sky-climbers and monorail hoists", 180, 12_000_000),
                ("Curtain-wall installation — upper half", "Floors 21–40 with wind-load compliance", 180, 12_800_000),
                ("Roof waterproofing & green roof", "PVC membrane with inverted roof, paver support, and sedum trays", 60, 2_400_000),
                ("Spandrel & fritting detailing", "Ceramic-frit patterning for solar control and bird-strike mitigation", 45, 1_200_000),
            ])
            + _phase_tasks("MEP rough-in", [
                ("HVAC chilled water risers", "Two 300mm risers with vibration isolation and pressure testing", 120, 7_800_000),
                ("HVAC AHUs & VAV boxes", "38 AHU installations with DDC controls and VAV per floor", 180, 14_500_000),
                ("Electrical bus ducts & switchgear", "13.8kV to 480V step-down, 4,000A bus risers, and ATS units", 150, 11_000_000),
                ("Emergency generator & fuel system", "2 × 2MW diesel gensets with 96-hour fuel and fire-rated enclosure", 60, 3_200_000),
                ("Plumbing risers & booster pumps", "Domestic cold/hot water, sanitary, storm drainage per floor", 150, 6_800_000),
                ("Fire suppression — sprinklers & standpipes", "Wet/dry systems with fire pumps and pre-action zones for IT rooms", 120, 4_500_000),
                ("Elevators — installation of 28 cars", "High-speed traction elevators with destination dispatch", 240, 16_500_000),
                ("Low-voltage — data, security, AV backbone", "Cat6A, single-mode fibre riser, and DAS headend", 120, 5_200_000),
                ("BMS integration & commissioning wiring", "Niagara-based BMS with 40,000+ tagged points", 90, 3_800_000),
            ])
            + _phase_tasks("Interior fit-out", [
                ("Drywall & partitions — typical floors", "Metal stud + 2 × gypsum boards with acoustic insulation", 180, 6_800_000),
                ("Suspended ceilings — typical floors", "Metal grid with acoustic tile, light-cove integration", 120, 3_400_000),
                ("Raised-access flooring — typical floors", "600 × 600 steel panels with understructure for cabling", 120, 5_200_000),
                ("Finish carpentry & millwork — public areas", "Veneer wall panels, reception joinery, executive suites", 90, 4_500_000),
                ("Stone & tile — lobby & bathrooms", "Granite cladding in lobby, porcelain in 180 bathrooms", 100, 6_200_000),
                ("Paint & wall finishes — all areas", "Two coats with primer, specialty finishes in public areas", 150, 3_100_000),
                ("Doors, frames, and hardware", "1,800 openings with access-control integration", 90, 2_800_000),
            ])
            + _phase_tasks("Site & landscape", [
                ("Plaza hardscape & street improvements", "Granite pavers, bollards, water feature, and seating areas", 90, 4_200_000),
                ("Tree planting & irrigation", "42 mature trees with structural soil cells and automated irrigation", 30, 750_000),
                ("Public art installation", "Commissioned sculpture with structural review and lighting", 30, 1_500_000),
                ("Exterior signage & wayfinding", "Tower-top identification, address plinth, and ADA signage program", 45, 850_000),
                ("Loading dock & service area equipment", "Dock levellers, trash compactors, and access control", 30, 620_000),
            ])
            + _phase_tasks("Commissioning & handover", [
                ("TAB — Test, Adjust, Balance", "Air and water-side TAB with independent third-party verification", 60, 1_800_000),
                ("Fire-alarm & life-safety inspection", "Full functional test, code official walkthrough, and sign-off", 21, 420_000),
                ("Elevator certification & witness", "Acceptance testing per ASME A17.1 and state inspection", 30, 280_000),
                ("LEED Platinum final submission", "Performance documentation, energy modelling, and USGBC review", 45, 320_000),
                ("Owner training — BMS & operations", "80 hours of FM training on BMS, elevators, generators, fire systems", 14, 180_000),
                ("Punch-list walk & closeout", "Architect/consultant walks, deficiency rectification, lien releases", 60, 1_200_000),
                ("Certificate of occupancy — temporary", "Authority walkthroughs and TCO issuance", 7, 75_000),
                ("Warranty & O&M manuals handover", "Digital BIM model, 15 binders of O&M, warranties indexed", 21, 120_000),
            ]),
        "risks": [
            ("Dewatering system failure during deep excavation", "technical", "medium", "very_high", "mitigate",
             "Redundant pumps, continuous monitoring, immediate grout-backfill plan",
             "Piezometers show water-table rise > 0.5m under dewatering"),
            ("Tower crane collapse during storm", "technical", "low", "very_high", "mitigate",
             "Wind-speed cut-offs, monthly rigging inspections, insurance coverage reviewed",
             "Site anemometer exceeds 72 km/h sustained wind"),
            ("Concrete strength shortfall on core walls", "technical", "low", "very_high", "avoid",
             "Third-party cube testing, pre-qualified mix design, backup supplier under contract",
             "28-day compressive strength < 95% of design"),
            ("Curtain-wall supplier delivery delay", "external", "high", "high", "mitigate",
             "Lock in 60% production 6 months early, secondary fabricator qualified",
             "Vendor monthly production report lags schedule by > 15%"),
            ("Union labour strike", "external", "medium", "high", "mitigate",
             "Maintain good-faith negotiation, subcontractor diversification, extended-schedule contingency",
             "Strike notice served or trade council votes no-confidence"),
            ("Hazardous material discovery during excavation", "external", "medium", "high", "transfer",
             "Environmental consultant on standby, specialised remediation contractor pre-qualified",
             "Soil sample positive for petroleum hydrocarbons or asbestos"),
            ("Permit delays from municipal authority", "external", "high", "medium", "mitigate",
             "Weekly expediter meetings, parallel submission where allowed, owner relationship with city",
             "Any permit in review for > 45 days"),
            ("Neighbour-property damage claim", "external", "medium", "high", "mitigate",
             "Pre-construction condition surveys, vibration monitoring, insurance coverage",
             "Vibration sensor exceeds DIN 4150 threshold at adjacent building"),
            ("Cost escalation — rebar/structural steel", "external", "very_high", "high", "mitigate",
             "Fixed-price contracts for 70% of steel, quarterly escalation reviews",
             "Commodity index rises > 12% quarter-over-quarter"),
            ("Fall-from-height incident", "organizational", "medium", "very_high", "avoid",
             "100% fall-protection enforcement, daily JHA, behaviour-based safety program",
             "Any near-miss report involving fall hazards"),
            ("Fire during MEP installation", "technical", "low", "very_high", "mitigate",
             "Hot-work permit program, fire watch protocol, portable extinguishers on every floor",
             "Hot-work incident report or near-miss fire event"),
            ("LEED Platinum target not achievable", "project_management", "medium", "high", "mitigate",
             "Monthly credit tracking, value-engineering review for ECM packages, backup Gold rating strategy",
             "Quarterly LEED scorecard projects < 80 points"),
            ("Elevator commissioning behind schedule", "technical", "high", "high", "mitigate",
             "Early vertical-transport engagement, parallel car commissioning, contingency manlift rental",
             "Certification lags structural-complete by > 60 days"),
            ("Tenant-fit-out coordination conflicts", "project_management", "very_high", "medium", "mitigate",
             "Landlord work letter, tenant-coordinator role, monthly tenant-meeting cycle",
             "More than 3 tenant change orders per month"),
            ("Weather delays — winter concrete work", "external", "high", "medium", "accept",
             "Heated enclosures, cold-weather concrete mix, 10% schedule contingency",
             "Sub-zero forecast for > 5 consecutive days"),
        ],
        "deliverables": [
            ("Shoring & Excavation Permit Package", "Design drawings, soil reports, and municipal submission documents", "accepted", "meets_standard", 100, "Permit issued by city engineering"),
            ("Structural Drawings Set — IFC", "40 sheets of superstructure drawings issued for construction", "accepted", "meets_standard", 100, "Stamped and signed by SE of record"),
            ("Curtain-Wall Shop Drawings", "Unitized mullion and anchor details, IGU cross-sections", "accepted", "exceeds_standard", 100, "Peer-reviewed by facade consultant"),
            ("MEP Coordination BIM Model", "Clash-free federated model from trades at LOD 400", "in_progress", "meets_standard", 65, "Weekly clash report < 50 unresolved clashes"),
            ("Commissioning Plan", "Full Cx plan including test protocols for HVAC, electrical, fire, elevators", "in_progress", "not_assessed", 40, "CxA signs off at design and pre-construction phases"),
            ("LEED Platinum Scorecard", "Running credit tally with supporting documentation index", "in_progress", "not_assessed", 55, "Projected points ≥ 80 at each milestone"),
            ("Punch List — Substantial Completion", "Full deficiency list with photos and assignments", "planned", "not_assessed", 0, "Architect walk-through complete"),
            ("Operations & Maintenance Manuals", "15 binders covering all systems, vendor contacts, warranties", "planned", "not_assessed", 0, "Accepted by FM team at handover"),
            ("Fire Safety Plan & Drill Records", "Approved fire safety plan with quarterly drill logs", "planned", "not_assessed", 0, "Approved by fire marshal"),
            ("As-Built Drawings", "Red-lined, digital, and BIM as-built deliverable", "planned", "not_assessed", 0, "Delivered 60 days post-TCO"),
            ("Warranty Documentation Package", "Unified manufacturer warranties indexed by system", "planned", "not_assessed", 0, "All systems ≥ 1 year standard + extended where specified"),
            ("Temporary Certificate of Occupancy", "TCO issued by building department", "planned", "not_assessed", 0, "Life-safety items 100% complete"),
            ("Final Certificate of Occupancy", "Full CofO after all outstanding items closed", "planned", "not_assessed", 0, "All deficiencies rectified"),
            ("Structural Load Test Report", "Load-test results for transfer trusses and key connections", "planned", "not_assessed", 0, "Results within design tolerance"),
            ("LEED Platinum Certification", "USGBC certification issued", "planned", "not_assessed", 0, "USGBC final review approved"),
        ],
        "measurements": [
            ("Schedule Performance Index (SPI)", "schedule", "kpi", 1.0, "ratio", 0.8, 0.9, 1.0),
            ("Cost Performance Index (CPI)", "cost", "kpi", 1.0, "ratio", 0.85, 0.92, 1.0),
            ("Lost Time Injury Rate (LTIR)", "team", "lagging", 0, "per 200k hrs", 2.0, 1.0, 0.0),
            ("Concrete pour compliance rate", "quality", "kpi", 99, "%", 90, 95, 99),
            ("Drawing RFI turnaround", "schedule", "leading", 3, "days", 10, 7, 5),
            ("Daily concrete m³ placed", "schedule", "leading", 300, "m³/day", 150, 220, 280),
            ("Rework percentage", "quality", "lagging", 1.5, "%", 5, 3, 2),
            ("Near-miss reports logged", "team", "leading", 40, "per month", 5, 15, 30),
            ("Waste diversion rate (LEED)", "quality", "kpi", 80, "%", 50, 65, 75),
            ("Energy-model compliance gap", "quality", "kpi", 0, "%", 10, 5, 2),
            ("Critical-path task float", "schedule", "leading", 10, "days", 0, 5, 10),
            ("Change-order value vs contingency", "cost", "leading", 50, "% used", 90, 75, 60),
            ("MEP clash resolution rate", "quality", "kpi", 95, "% per week", 60, 80, 90),
            ("Permits approved on first submission", "schedule", "kpi", 80, "%", 40, 60, 75),
            ("Subcontractor DBE participation", "stakeholder", "kpi", 25, "%", 10, 18, 22),
        ],
        "stakeholders": [
            ("Lucas Harrington", "Owner / Developer CEO", "sponsor", "supportive", "leading", "high", "high"),
            ("Aiko Tanaka", "Design Architect", "internal", "supportive", "leading", "high", "high"),
            ("Daniela Rossi", "Structural Engineer of Record", "supplier", "supportive", "leading", "high", "high"),
            ("Viktor Petrov", "MEP Engineer of Record", "supplier", "supportive", "supportive", "high", "high"),
            ("Mayor's Office Liaison", "City Planning Representative", "regulator", "neutral", "supportive", "high", "medium"),
            ("Building Department Chief", "Code Official", "regulator", "neutral", "neutral", "high", "medium"),
            ("Fire Marshal", "Life-safety authority", "regulator", "neutral", "neutral", "high", "high"),
            ("Transit Authority Coordinator", "Subway adjacency authority", "regulator", "resistant", "neutral", "high", "low"),
            ("Adjacent-property owners assoc.", "Neighbour coalition", "external", "resistant", "neutral", "medium", "medium"),
            ("Community Board chair", "Local residents voice", "end_user", "neutral", "supportive", "medium", "medium"),
            ("LEED Commissioning Agent", "Independent Cx authority", "supplier", "supportive", "leading", "high", "high"),
            ("Tenant-coordination lead — Anchor tenant", "200,000 sq-ft tenant PM", "customer", "supportive", "leading", "high", "high"),
            ("Primary lender — construction loan", "Bank construction-finance officer", "sponsor", "supportive", "supportive", "high", "high"),
            ("Union business manager", "Ironworkers local", "external", "neutral", "supportive", "medium", "medium"),
            ("Historical preservation board", "Adjacent heritage building oversight", "regulator", "resistant", "neutral", "high", "low"),
            ("Environmental consultant", "Sustainability advisor", "supplier", "supportive", "leading", "medium", "high"),
            ("Insurance underwriter", "Builder's-risk carrier", "supplier", "neutral", "supportive", "high", "medium"),
            ("Crane operators' steward", "Safety-critical labour rep", "external", "supportive", "supportive", "medium", "medium"),
            ("Public art commission chair", "Plaza art curator", "stakeholder", "neutral", "supportive", "low", "medium"),
            ("FM operations director", "Building-ops leadership for handover", "customer", "supportive", "leading", "high", "high"),
        ],
        "team": [
            ("Raj Malhotra", "raj.m@meridianone.com", "project_manager", "Overall program management, owner liaison", "PMP, Construction management, RICS", 100),
            ("Hannah O'Connell", "hannah.o@meridianone.com", "project_manager", "Field operations and schedule control", "P6 scheduling, lean construction, OSHA 30", 100),
            ("Diego Vargas", "diego.v@meridianone.com", "architect", "Design coordination and IFC reviews", "BIM, Revit, construction detailing", 80),
            ("Yuki Sato", "yuki.s@meridianone.com", "developer", "Structural superintendent — substructure", "Concrete, post-tensioning, formwork", 100),
            ("Marcus O'Brien", "marcus.o@meridianone.com", "developer", "Structural superintendent — superstructure", "High-rise concrete, slip-form cores", 100),
            ("Chidinma Eze", "chi.e@meridianone.com", "developer", "MEP superintendent", "HVAC, electrical, plumbing coordination", 100),
            ("Kasey Lindqvist", "kasey.l@meridianone.com", "developer", "Envelope superintendent", "Curtain wall, waterproofing, roofing", 100),
            ("Omar Farouk", "omar.f@meridianone.com", "developer", "Site logistics and crane operations", "Tower cranes, hoist systems, traffic plans", 100),
            ("Elena Gutierrez", "elena.g@meridianone.com", "analyst", "Cost control & EVM analyst", "Cost engineering, EVM, procurement", 100),
            ("Bao Nguyen", "bao.n@meridianone.com", "analyst", "Scheduling engineer — P6 master", "Primavera P6, CPM, delay analysis", 100),
            ("Grace Munroe", "grace.m@meridianone.com", "tester", "Quality manager", "ACI, CWI, ASNT Level II NDT", 100),
            ("Ivan Kolesnik", "ivan.k@meridianone.com", "developer", "Safety director", "CSP, OSHA 500, incident investigation", 100),
            ("Abena Owusu", "abena.o@meridianone.com", "analyst", "Sustainability / LEED coordinator", "LEED AP BD+C, energy modelling", 80),
            ("Natasha Romanova", "natasha.r@meridianone.com", "designer", "Interiors coordination", "Interior construction, millwork, finishes", 60),
            ("Khaled Mostafa", "khaled.m@meridianone.com", "analyst", "Procurement & subcontractor management", "MEP buyouts, contract admin", 100),
        ],
    },

    # ══════════════════════════════════════════════════════════════════
    # 2. 75,000-SEAT FOOTBALL STADIUM
    # ══════════════════════════════════════════════════════════════════
    {
        "meta": {
            "name": "Aurora Park — 75,000-Seat Football Stadium",
            "description": "Purpose-built 75,000-seat football stadium with retractable roof, 120 luxury suites, multi-sport capability, 8,500 parking spaces, and integrated transit plaza. Operational target: host first league match at month 34.",
            "approach": "hybrid",
            "cadence": "single",
            "budget": 1_200_000_000,
            "vision": "Create an iconic venue that anchors a new sports-and-entertainment district and sets the standard for fan experience.",
            "objectives": "Deliver bowl ready for match operations at month 34; commission retractable roof by month 30; achieve FIFA Category 4 accreditation.",
            "success_criteria": "Sold-out first match; FIFA inspection pass on first attempt; ≤0.5% no-shows of club-seat holders due to facility issues.",
            "duration_days": 1080,
        },
        "tasks":
            _phase_tasks("Site & earthworks", [
                ("Land acquisition closeout", "Final parcel assembly and title insurance issuance", 60, 2_400_000),
                ("Mass grading and earthworks", "1.5M m³ of cut-and-fill with balanced earthwork plan", 90, 7_800_000),
                ("Stormwater & retention ponds", "Two 40,000 m³ retention ponds with drainage network", 60, 3_200_000),
                ("Utility relocations", "Sanitary, storm, water, gas, electric re-routes with franchise utilities", 120, 8_500_000),
                ("Pitch drainage subgrade", "Herringbone drain pattern with gravel layer and geotextile", 30, 2_100_000),
                ("Ring road & site access construction", "Primary ring road, fire lanes, and service access with curb and gutter", 90, 6_400_000),
            ])
            + _phase_tasks("Foundations", [
                ("Foundations — bowl perimeter ring", "Drilled shafts for 800 perimeter columns with cross-bracing", 120, 22_000_000),
                ("Foundations — roof-truss super columns", "Deep piles for 8 super columns supporting roof truss", 90, 18_500_000),
                ("Foundations — concourse and suite columns", "Spread footings for interior columns and mezzanines", 120, 9_400_000),
                ("Grade-level utilities rough-in", "Major electrical duct banks, IT conduit, sanitary risers under bowl", 90, 7_500_000),
            ])
            + _phase_tasks("Bowl & seating", [
                ("Precast seating unit fabrication", "18,000 precast seating units cast off-site in 3 phases", 240, 42_000_000),
                ("Precast erection — lower bowl", "Installation of lower-tier seating units with shoring", 120, 14_500_000),
                ("Precast erection — upper bowl", "Installation of upper-tier seating and vomitory stairs", 120, 16_000_000),
                ("Vomitories & stair cores", "Cast-in-place vomitory stairs and fire exits per code", 90, 6_800_000),
                ("Seat installation — 75,000 seats", "Seat procurement and installation with section-colour plan", 60, 9_500_000),
                ("Field-level tunnel & team entries", "Players' tunnel, officials' tunnel, and field-level emergency egress", 60, 3_400_000),
            ])
            + _phase_tasks("Roof & canopy", [
                ("Primary roof truss fabrication", "2,400 tonnes of structural steel fabricated over 10 months", 300, 68_000_000),
                ("Primary truss erection", "Segmented erection with strand-jacking over 5 months", 150, 42_000_000),
                ("Retractable roof mechanism", "Two 9,500 m² panels on 140 bogies each, rack-and-pinion drive", 180, 85_000_000),
                ("Retractable roof commissioning", "Open/close cycle testing under varied wind conditions", 45, 6_500_000),
                ("Roof fabric panels — ETFE", "ETFE cushion panels for translucent sections over concourses", 90, 18_000_000),
                ("Perimeter canopy edge lighting", "LED perimeter lighting with RGB show-mode capability", 30, 3_200_000),
            ])
            + _phase_tasks("Pitch & field systems", [
                ("Grow-in period for hybrid turf", "Seed establishment and knit-in period for hybrid pitch", 120, 1_800_000),
                ("Undersoil heating system", "Glycol-based heating loops under entire pitch", 45, 4_200_000),
                ("Pitch irrigation & moisture sensors", "Automated irrigation with soil-moisture telemetry", 30, 1_400_000),
                ("Tray-based retractable pitch system", "Optional — retractable pitch tray for multi-sport mode", 120, 28_000_000),
                ("Field lighting — 4K broadcast-grade", "Class V floodlights meeting UEFA/FIFA Category A standards", 45, 6_800_000),
                ("Scoreboard & ribbon boards", "Dual 60m × 20m HD video boards + 900m of ribbon boards", 60, 32_000_000),
            ])
            + _phase_tasks("Fan amenities", [
                ("Concourse finishes — main concourse", "Polished concrete, wayfinding, and themed fan zones", 120, 12_500_000),
                ("Concessions — 220 points of sale", "Kitchen equipment, POS, hoods, and utilities per stand", 180, 28_000_000),
                ("Restrooms — 1,800 fixtures", "High-traffic fixtures, queuing design, family/accessible restrooms", 120, 11_500_000),
                ("Luxury suites — 120 units", "Full interior fit-out, AV, HVAC, catering pantries per suite", 180, 48_000_000),
                ("Club lounges — 6 premium clubs", "Premium food and beverage clubs with kitchen and bars", 150, 22_000_000),
                ("Team locker rooms — home & away", "Locker rooms, hydrotherapy, coaches' suites, medical rooms", 150, 14_500_000),
                ("Media & broadcast facilities", "Press box for 600, broadcast bay, camera platforms, interview rooms", 120, 16_000_000),
                ("Merchandise — flagship team store", "2,400 m² team store with loading and inventory systems", 90, 8_500_000),
            ])
            + _phase_tasks("Technology & broadcast", [
                ("Stadium-wide Wi-Fi (HD Wi-Fi 6E)", "2,200 access points with 160 Gbps aggregate backhaul", 90, 14_000_000),
                ("Distributed antenna system (DAS)", "Multi-carrier 5G DAS with 450 remote nodes", 60, 8_500_000),
                ("Ticketing & turnstile integration", "RFID turnstiles with mobile-first ticketing platform", 45, 6_400_000),
                ("CCTV & command centre", "1,200 cameras, AI-analytics, integrated command centre with 54 operators", 90, 14_500_000),
                ("Access control & credentialing", "Back-of-house access control with 250 readers and biometric override", 45, 4_200_000),
                ("Audio — distributed PA & evac", "Life-safety-code compliant PA with 1,800 zones", 60, 11_000_000),
                ("Scoreboard control room", "Production suite with switchers, replay, and graphics engines", 60, 9_500_000),
                ("IPTV backbone", "Over 2,400 screens with IPTV feed, advertising, and replay overlays", 75, 8_800_000),
            ])
            + _phase_tasks("Exterior & plaza", [
                ("Exterior facade panels", "Pre-weathered aluminium cladding with LED-integration channels", 120, 22_000_000),
                ("North plaza hardscape", "Granite pavers, seating, and water feature for fan gathering", 60, 6_200_000),
                ("South transit plaza", "Canopies, wayfinding, ticket kiosks, integration with metro line", 90, 12_500_000),
                ("Parking deck — 6,500 stalls", "6-level parking deck with LPR entry/exit system", 240, 92_000_000),
                ("Surface parking — 2,000 stalls", "Lined surface lot with shuttle bus layover", 45, 3_800_000),
                ("Perimeter security bollards & CVP", "Crash-rated bollards around plaza perimeter, vehicle-ram protection", 45, 4_500_000),
                ("Ticket portal & entry gates — 42 gates", "Main entry gates with canopies and screening lanes", 60, 9_800_000),
                ("Landscape — 1,200 trees & native planting", "Native species with automated drip irrigation and biodiverse mix", 45, 3_500_000),
            ])
            + _phase_tasks("Commissioning & opening", [
                ("Integrated systems commissioning", "All MEP, AV, IT, life-safety cross-functionally tested", 60, 6_500_000),
                ("Crowd-flow simulation — Phase 1", "Agent-based simulation validated against live drill", 30, 1_100_000),
                ("Fire & evacuation drill — 20,000 extras", "Full-scale drill with fire, medical, and police services", 7, 850_000),
                ("FIFA Category 4 inspection", "Inspection and certification for international fixtures", 14, 220_000),
                ("Test-event matches — 3 events", "Progressive capacity test events with lessons-learned", 45, 3_500_000),
                ("Stewarding & security training", "Certification of 4,500 stewards under SGSA equivalent", 60, 4_800_000),
                ("Game-day playbook & runbooks", "Full runbook for match-day operations across all departments", 60, 1_200_000),
                ("Opening match kickoff", "First fixture of inaugural season with media and ceremonies", 7, 2_500_000),
            ]),
        "risks": [
            ("Retractable roof commissioning delay", "technical", "high", "very_high", "mitigate",
             "Factory acceptance testing, phased commissioning, manual-override contingency for opening match",
             "Factory FAT slips > 30 days from baseline"),
            ("Pitch establishment fails before first match", "technical", "medium", "very_high", "mitigate",
             "Start turf grow-in early, secondary pitch field as backup, specialist agronomist on retainer",
             "Grass coverage < 95% at T-60 days"),
            ("Roof steel fabrication delay", "external", "medium", "very_high", "mitigate",
             "Long-lead orders 18 months out, two fabricator qualification, expeditor on-site at mill",
             "Mill production lags contract by > 15%"),
            ("Parking-deck concrete strength issue", "technical", "low", "high", "avoid",
             "Third-party cube testing, pre-qualified mix design, weather-protection protocols",
             "28-day cube < 95% specified"),
            ("FIFA inspection fails (broadcast / field)", "external", "medium", "very_high", "mitigate",
             "FIFA consultant engaged early, mock-inspection 90 days prior, preemptive remediation",
             "Mock inspection returns > 3 material non-conformances"),
            ("Technology-integration failure at opening", "technical", "medium", "very_high", "mitigate",
             "3 test events with progressive capacity, 24-hour command-centre dry runs, roll-back plans",
             "Test event reveals any critical system failure"),
            ("Transit-authority timeline slippage", "external", "high", "high", "escalate",
             "Joint-venture coordination agreements, independent transit plaza completion path, MOU with city",
             "Transit construction lag > 90 days vs plaza completion"),
            ("Labour shortage — specialty trades", "external", "high", "high", "mitigate",
             "Out-of-area recruitment, apprenticeship program, premium incentive pools",
             "Manpower report < 85% required for 3 consecutive weeks"),
            ("Cost overrun — commodity escalation", "external", "very_high", "high", "mitigate",
             "Fixed-price steel contracts, escalation reserve within contingency, quarterly rebaseline",
             "Commodity index rises > 10% in a quarter"),
            ("Crowd-flow modelling reveals evac gaps", "technical", "medium", "high", "mitigate",
             "Early simulation with independent reviewer, physical drill with 20,000 extras, layout rework window",
             "Simulation shows evac > 8 minutes anywhere in bowl"),
            ("Weather cancellation of opening match", "external", "low", "high", "accept",
             "Weather contingency date, insurance coverage for event cancellation",
             "Extreme weather forecast at T-72 hours"),
            ("Public-private financing dispute", "organizational", "medium", "high", "escalate",
             "Maintain strong public relations, transparent cost reporting, independent auditor",
             "Political opposition initiates audit or payment delay"),
            ("Major tenant sponsorship falls through", "external", "medium", "high", "mitigate",
             "Parallel sponsor conversations, naming-rights reserve, flexible signage design",
             "Lead sponsor issues termination notice"),
            ("Regulatory — alcohol/security licensing", "external", "low", "high", "mitigate",
             "Early licensing application, good-standing audit, pre-event compliance walkthrough",
             "License application receives conditional approval"),
            ("Opening-match security incident", "organizational", "low", "very_high", "mitigate",
             "Close coordination with police and federal agencies, multi-agency drills, intelligence sharing",
             "Any credible threat intelligence received"),
            ("Suite-holder experience issues", "organizational", "medium", "medium", "mitigate",
             "Dedicated hospitality team, soft-opening with VIP holders, issue-resolution SLA",
             "NPS score from test-event suite holders < 60"),
            ("Scoreboard manufacturer bankruptcy", "external", "low", "very_high", "transfer",
             "Performance bond, escrow for progress payments, alternate supplier pre-qualified",
             "Vendor misses 2 consecutive milestones or files Chapter 11"),
            ("Roof leak after first rainstorm", "technical", "medium", "high", "avoid",
             "Watertight tests per ASTM E1105, roof mock-up testing, independent QA",
             "Water test identifies any failure on mock-up panels"),
        ],
        "deliverables": [
            ("Masterplan — Issued for Construction", "Full civil and architectural MP at LOD 350+", "accepted", "meets_standard", 100, "Owner and authority approvals issued"),
            ("Roof Structural Package", "Full structural set for retractable roof including fabrication drawings", "accepted", "exceeds_standard", 100, "Third-party reviewed, fabricator validated"),
            ("Precast Seating Shop Drawings", "Shop drawings for 18,000 seating units", "accepted", "meets_standard", 100, "Approved by SE of record"),
            ("FIFA Cat 4 Accreditation", "FIFA certification for international match hosting", "planned", "not_assessed", 0, "Inspection pass with no major findings"),
            ("Pitch Establishment Certificate", "Agronomist certification of pitch readiness", "planned", "not_assessed", 0, "Turf coverage > 98% at match minus 14 days"),
            ("Crowd-Flow Simulation Report", "Agent-based simulation for evacuation and general flow", "in_progress", "not_assessed", 65, "Evac < 8 minutes from any section"),
            ("Commissioning Plan — Integrated", "Multi-discipline Cx plan covering MEP, AV, IT, life-safety", "in_progress", "not_assessed", 50, "CxA signoff at each milestone"),
            ("Broadcast Standards Compliance Pack", "Documentation of camera positions, lighting levels, audio noise floor", "in_progress", "not_assessed", 40, "Broadcaster approval at walkthrough"),
            ("Game-Day Runbook", "Full operations runbook covering every department", "planned", "not_assessed", 0, "Tabletop exercise completed successfully"),
            ("Security & Evacuation Plan", "Integrated plan approved by police, fire, medical services", "planned", "not_assessed", 0, "All agency signoff obtained"),
            ("Test Event Lessons-Learned Reports", "One LL report per test event with corrective actions", "planned", "not_assessed", 0, "Report issued within 7 days of each event"),
            ("Retractable Roof Acceptance Test Report", "Mechanical, electrical, and control-systems acceptance", "planned", "not_assessed", 0, "All acceptance criteria met"),
            ("Sponsorship Activation Rulebook", "Signage, digital, and experiential rules for sponsors", "planned", "not_assessed", 0, "Tenant and sponsor approvals"),
            ("Operations & Maintenance Manuals", "Comprehensive O&M library for FM team", "planned", "not_assessed", 0, "FM team signoff"),
            ("Opening-Match Report", "Post-event report with attendance, operations, and issues", "planned", "not_assessed", 0, "Delivered within 30 days of opening match"),
        ],
        "measurements": [
            ("Schedule Performance Index (SPI)", "schedule", "kpi", 1.0, "ratio", 0.8, 0.9, 1.0),
            ("Cost Performance Index (CPI)", "cost", "kpi", 1.0, "ratio", 0.85, 0.92, 1.0),
            ("Days to retractable-roof FAT", "schedule", "leading", 180, "days", 240, 210, 190),
            ("Turf establishment coverage", "quality", "leading", 98, "%", 80, 90, 95),
            ("Crowd-flow evac time — upper bowl", "quality", "kpi", 7, "minutes", 12, 9, 8),
            ("Stewarding certification pass rate", "team", "kpi", 98, "%", 80, 90, 95),
            ("Lost Time Injury Rate (LTIR)", "team", "lagging", 0, "per 200k hrs", 2.0, 1.0, 0.0),
            ("Test-event NPS (fan experience)", "stakeholder", "outcome", 80, "NPS", 30, 55, 70),
            ("RFI turnaround", "schedule", "leading", 3, "days", 10, 7, 5),
            ("Punch-list closure rate", "quality", "lagging", 95, "% per week", 60, 80, 90),
            ("BIM clash count — weekly", "quality", "leading", 30, "clashes", 300, 150, 60),
            ("Commodity escalation index", "cost", "leading", 100, "index", 115, 108, 103),
            ("Sponsorship revenue committed", "stakeholder", "leading", 100, "%", 60, 80, 92),
            ("Change-order volume", "cost", "leading", 200, "#", 800, 500, 350),
            ("Ticketing system load-test capacity", "quality", "kpi", 500_000, "req/sec at peak", 100_000, 250_000, 400_000),
        ],
        "stakeholders": [
            ("Marcella Di Santo", "Authority President", "sponsor", "supportive", "leading", "high", "high"),
            ("Thierry Abidal", "Club President (anchor tenant)", "customer", "leading", "leading", "high", "high"),
            ("Alessia Conti", "FIFA Inspection Delegate", "regulator", "neutral", "supportive", "high", "medium"),
            ("UEFA technical liaison", "Confederation representative", "regulator", "neutral", "supportive", "high", "medium"),
            ("National League Commissioner", "League representative", "regulator", "neutral", "supportive", "high", "high"),
            ("Broadcast partner — lead rights holder", "Broadcasting senior production", "customer", "supportive", "leading", "high", "high"),
            ("Title Sponsor CEO — Naming Rights", "Lead sponsor executive", "sponsor", "supportive", "leading", "high", "high"),
            ("Transit Authority Director", "Metro station integration", "regulator", "neutral", "supportive", "high", "medium"),
            ("City Fire Chief", "Public safety authority", "regulator", "neutral", "neutral", "high", "high"),
            ("Police Commissioner", "Matchday security", "regulator", "neutral", "supportive", "high", "high"),
            ("Local Residents Association", "Neighbourhood coalition", "external", "resistant", "neutral", "medium", "medium"),
            ("Chamber of Commerce", "Local business rep", "external", "supportive", "supportive", "medium", "medium"),
            ("Stadium operations director", "Building-ops leader for handover", "customer", "supportive", "leading", "high", "high"),
            ("Premium-suite holders association", "Luxury suite VIP representatives", "customer", "neutral", "supportive", "medium", "high"),
            ("Season-ticket holders panel", "Fan experience advisory panel", "end_user", "neutral", "supportive", "low", "high"),
            ("Environmental defence league", "Watchdog group on runoff & wildlife", "external", "resistant", "neutral", "medium", "low"),
            ("Historical preservation board", "Surrounding heritage-district oversight", "regulator", "resistant", "neutral", "medium", "low"),
            ("ADA & accessibility advocates", "Accessibility compliance watchdog", "regulator", "neutral", "supportive", "medium", "high"),
            ("Players' Association liaison", "Player welfare representative", "end_user", "neutral", "supportive", "medium", "high"),
            ("Anchor broadcaster graphic director", "Broadcast-graphics coordination", "customer", "supportive", "supportive", "medium", "medium"),
            ("Insurance underwriter", "Builder's risk carrier", "supplier", "neutral", "supportive", "high", "medium"),
            ("Pitch agronomist consultant", "Specialist grass advisor", "supplier", "supportive", "leading", "high", "high"),
            ("Lead structural contractor — Roof JV", "Steel-truss JV lead", "supplier", "supportive", "leading", "high", "high"),
            ("Lead technology contractor", "Tech-integration systems integrator", "supplier", "supportive", "leading", "high", "high"),
            ("Emergency medical services director", "Matchday EMS", "regulator", "neutral", "supportive", "high", "medium"),
        ],
        "team": [
            ("Ilse Bergmann", "ilse.b@aurorapark.com", "project_manager", "Program director — overall delivery", "PMP, major-stadium delivery, PgMP", 100),
            ("Santiago Lopez", "santi.l@aurorapark.com", "project_manager", "Bowl construction PM", "High-rise/structural PM, Primavera", 100),
            ("Chloe Dubois", "chloe.d@aurorapark.com", "project_manager", "Roof & envelope PM", "Steel structures, long-span roofs", 100),
            ("Yosef Halevi", "yosef.h@aurorapark.com", "project_manager", "Technology & broadcast PM", "Venue technology, AV-over-IP", 100),
            ("Mariko Ishikawa", "mariko.i@aurorapark.com", "architect", "Design manager", "Sports architecture, BIM, codes", 80),
            ("Pierre Lefebvre", "pierre.l@aurorapark.com", "developer", "Structural superintendent", "Precast erection, tower crane ops", 100),
            ("Adanna Okafor", "adanna.o@aurorapark.com", "developer", "MEP superintendent", "Large-venue HVAC, fire systems", 100),
            ("Luca Bianchi", "luca.b@aurorapark.com", "developer", "Facade superintendent", "Aluminium cladding, ETFE", 100),
            ("Sven Johansson", "sven.j@aurorapark.com", "developer", "Technology superintendent", "Stadium networks, DAS, Wi-Fi", 100),
            ("Farida Al-Mansoori", "farida.a@aurorapark.com", "analyst", "Master scheduler", "Primavera P6, multi-contractor interface", 100),
            ("Dmitri Sokolov", "dmitri.s@aurorapark.com", "analyst", "Cost & risk manager", "EVM, risk register, contingency modelling", 100),
            ("Ngozi Achebe", "ngozi.a@aurorapark.com", "tester", "Quality director", "ACI, CWI, AISC SSPC", 100),
            ("Rafael Torres", "rafa.t@aurorapark.com", "developer", "Safety director", "CSP, major-event construction safety", 100),
            ("Hana Park", "hana.p@aurorapark.com", "analyst", "Sustainability & LEED", "LEED AP, energy modelling", 80),
            ("Ben Carter", "ben.c@aurorapark.com", "designer", "Fan-experience lead", "Venue UX, concessions, wayfinding", 80),
            ("Gabriela Paz", "gab.p@aurorapark.com", "analyst", "Stakeholder manager — city relations", "Public engagement, permits", 80),
            ("Ahmed Farouk", "ahmed.f@aurorapark.com", "developer", "Pitch & field systems specialist", "Agronomy, irrigation, heating", 60),
            ("Valeria Cassano", "val.c@aurorapark.com", "developer", "Broadcast & scoreboard lead", "Video production, scoreboard control", 100),
            ("Roy Nakamura", "roy.n@aurorapark.com", "developer", "Life-safety systems lead", "Fire, PA, emergency-lighting", 100),
            ("Tara Mackenzie", "tara.m@aurorapark.com", "analyst", "Commissioning manager", "MEP Cx, retro-Cx, CxA", 100),
        ],
    },

    # ══════════════════════════════════════════════════════════════════
    # 3. CORE BANKING PLATFORM MODERNIZATION — large software program
    # ══════════════════════════════════════════════════════════════════
    {
        "meta": {
            "name": "Helios — Core Banking Platform Modernization",
            "description": "30-month replacement of a 30-year-old mainframe core banking system with a cloud-native, event-sourced microservices platform serving 12M retail customers across 4 countries. Covers accounts, payments, loans, cards, mobile, internet banking, and all regulatory/AML interfaces.",
            "approach": "agile",
            "cadence": "periodic",
            "budget": 180_000_000,
            "vision": "A resilient, composable core that enables real-time banking, 10x developer throughput, and a decade of extensibility.",
            "objectives": "Deliver new core with feature parity by month 24; dual-run for 6 months; retire legacy by month 30.",
            "success_criteria": "Zero customer-visible data loss; 99.99% API SLO in prod; 4x improvement in time-to-market for new features; core TCO reduced 40%.",
            "duration_days": 900,
        },
        "tasks":
            _phase_tasks("Discovery & architecture", [
                ("Current-state mainframe assessment", "Inventory of CICS programs, DB2 tables, and batch jobs with dependencies", 45, 950_000),
                ("Regulatory-mapping workstream", "Map regulation to capability for 4 jurisdictions with compliance counsel", 60, 1_200_000),
                ("Reference architecture — event sourcing + CQRS", "Design reference architecture covering CQRS, outbox, saga patterns", 45, 850_000),
                ("Capability model & domain map", "Strategic DDD workshop producing bounded contexts and capability map", 30, 420_000),
                ("Non-functional requirements baseline", "SLOs for latency, throughput, availability, durability, DR", 21, 180_000),
                ("Vendor selection — core banking vendor", "RFP, shortlist, proof-of-concept, and final selection", 120, 2_200_000),
                ("Cloud landing zone design", "Multi-region VPC, IAM, logging, and security tooling baseline", 45, 650_000),
                ("Data strategy — event store & lakehouse", "Event store, schema registry, data lakehouse, feature store", 30, 320_000),
                ("Security & zero-trust architecture", "mTLS, service identity, secrets, key management, HSM integration", 30, 420_000),
                ("Disaster-recovery strategy", "Multi-region active-active with < 30s RPO and < 5 min RTO", 21, 250_000),
            ])
            + _phase_tasks("Platform foundation", [
                ("Kubernetes platform on two regions", "EKS clusters, GitOps flow, service mesh, observability stack", 90, 3_800_000),
                ("Event backbone — Kafka clusters", "Multi-region MSK with tiered storage, governance, quotas", 60, 2_400_000),
                ("API gateway & identity platform", "API gateway, OAuth2/OIDC, token service, rate limiting, replay protection", 60, 1_800_000),
                ("CI/CD platform — trunk-based with quality gates", "Monorepo, build, test, security scans, deployment pipelines", 60, 1_400_000),
                ("Observability — metrics, logs, traces", "OTel instrumentation, Prometheus, Loki, Tempo, Grafana", 45, 1_100_000),
                ("Secrets and key management (HSM)", "Cloud HSM, secrets rotation, key lifecycle management", 45, 1_250_000),
                ("Compliance-as-code controls", "Policy engine, SOC2, PCI-DSS, ISO 27001 controls automation", 60, 1_450_000),
                ("Chaos engineering program", "Fault injection framework and weekly game-day cadence", 30, 480_000),
                ("Data quality tooling", "Expectation tests, lineage tracking, dashboards", 30, 380_000),
                ("SRE playbooks & oncall rota", "Runbooks for all services, oncall schedule, training", 30, 220_000),
            ])
            + _phase_tasks("Core accounts & ledger", [
                ("Customer & party service", "Customer, beneficial-owner, KYC state service with event sourcing", 120, 3_800_000),
                ("Accounts service — retail DDA/savings", "Full account lifecycle with support for 8 account types", 150, 6_200_000),
                ("General ledger — double-entry core", "Event-sourced general ledger with journals and postings", 150, 7_400_000),
                ("Interest accrual & capitalization", "Daily accrual engine with 14 interest models and capitalization", 90, 2_600_000),
                ("Statement generation service", "PDF and machine-readable statements with transaction categorization", 60, 1_100_000),
                ("Account-closure lifecycle", "Dormancy, closure, escheatment workflow", 45, 680_000),
                ("Entitlements & role-based access", "Account-level entitlements for joint/authorized/power-of-attorney", 45, 820_000),
                ("Audit-trail service — immutable", "Append-only audit service for all core mutations", 30, 420_000),
            ])
            + _phase_tasks("Payments", [
                ("SWIFT gateway — MT and MX", "MT103/202, MX pacs.008/009 with full sanctions screening", 120, 4_200_000),
                ("Domestic ACH/RTGS adapter", "Real-time and batch clearing integration for each country", 120, 3_900_000),
                ("Instant-payment scheme adapter", "SEPA-Inst/FedNow/RTP scheme adapter per jurisdiction", 90, 3_200_000),
                ("Card authorization engine", "ISO 8583 and ISO 20022 dual rails with routing", 120, 5_800_000),
                ("Fraud & AML detection integration", "Real-time transaction screening integration with FICO/Actimize", 60, 1_800_000),
                ("Payment repair workflow", "Exception queue, repair UI, and resubmission flow", 60, 1_100_000),
                ("Sanctions screening — real-time", "OFAC, UN, EU list screening with fuzzy-match and case management", 45, 980_000),
                ("Payments analytics & reporting", "Near-real-time analytics for operations and regulators", 45, 780_000),
                ("High-volume batch settlement", "Batch settlement framework with cut-off windows and holiday calendar", 45, 620_000),
                ("Cross-border FX pricing", "Multi-currency with real-time FX rate engine and hedging", 60, 1_650_000),
            ])
            + _phase_tasks("Loans & cards", [
                ("Loan origination platform", "Application intake, credit decisioning, disbursement workflow", 120, 4_100_000),
                ("Loan servicing — repayment schedules", "Scheduled and unscheduled payments, delinquency workflows", 90, 2_900_000),
                ("Cards lifecycle — issuing", "Issuance, embossing integration, activation, PIN management", 90, 3_200_000),
                ("Card controls — mobile-first", "Freeze, unfreeze, spending limits, merchant-category blocks", 45, 980_000),
                ("Delinquency & collections engine", "Bucketed delinquency, reminder cadence, write-off flow", 60, 1_200_000),
                ("Credit-bureau reporting", "Monthly reporting to 3 bureaus per country", 45, 720_000),
                ("Merchant-category-group management", "MCG mapping and business-rule engine", 30, 380_000),
                ("Dispute & chargeback workflow", "Disputes, representments, arbitration per scheme", 60, 1_100_000),
            ])
            + _phase_tasks("Channels — digital", [
                ("Mobile banking app — iOS/Android", "Native apps with biometric auth, 50+ core flows, accessibility", 180, 6_800_000),
                ("Internet banking web", "Responsive web app, feature parity with mobile", 150, 4_500_000),
                ("Contact-centre agent desktop", "Agent UI with 360 customer view and call scripting", 120, 3_200_000),
                ("Partner & fintech sandbox portal", "Developer portal, sandbox, SLA, and analytics", 90, 1_400_000),
                ("BFF API layer — customer-facing", "Backend-for-frontend aggregation optimized per channel", 90, 1_800_000),
                ("Push-notification service", "Transactional and marketing push with opt-in/consent", 45, 520_000),
                ("Secure-messaging service", "In-app secure messaging with agent routing", 45, 650_000),
                ("Accessibility & WCAG 2.2 AA", "Accessibility program across all channels with external audit", 60, 450_000),
            ])
            + _phase_tasks("Regulatory & operations", [
                ("AML platform integration", "Case-management integration with alert flow and SAR filing", 75, 1_800_000),
                ("KYC & customer due diligence", "Identity verification, enhanced DD, periodic refresh", 60, 1_400_000),
                ("GDPR data-subject rights portal", "Access, erasure, portability request automation", 45, 620_000),
                ("PCI-DSS certification", "PCI-DSS Level 1 certification for card environment", 90, 1_200_000),
                ("SOX controls evidence automation", "Evidence collection and attestation automation", 45, 480_000),
                ("CBC regulatory-reporting suite", "Central-bank reporting for 4 jurisdictions", 120, 2_400_000),
                ("FATCA/CRS reporting", "Tax reporting automation for cross-border accounts", 60, 780_000),
                ("Record-retention & legal hold", "Automated retention policy and legal-hold workflow", 45, 520_000),
            ])
            + _phase_tasks("Migration", [
                ("Data-migration factory", "ETL toolchain, migration harness, reconciliation framework", 90, 2_800_000),
                ("Customer data migration — pilot", "Pilot migration of 200k customers from sandbox branch", 45, 1_200_000),
                ("Customer data migration — wave 1", "3M customers migrated with validation & rollback plan", 60, 2_400_000),
                ("Customer data migration — wave 2", "5M customers migrated", 60, 2_800_000),
                ("Customer data migration — wave 3", "Remaining 4M customers migrated", 60, 2_500_000),
                ("Ledger balance reconciliation", "Full legacy vs new ledger reconciliation daily", 90, 1_400_000),
                ("Dual-run operations — 6 months", "Run legacy and new in parallel with daily reconciliation", 180, 8_200_000),
                ("Legacy decommissioning", "Final shutdown, archive, vendor contracts closeout", 60, 780_000),
            ])
            + _phase_tasks("Testing & release", [
                ("Functional test automation — 12,000 tests", "End-to-end test suite with 85% critical-path coverage", 180, 3_200_000),
                ("Performance & load testing", "50,000 TPS peak, 24-hour soak, multi-region failover", 60, 1_400_000),
                ("Disaster-recovery failover test — cross-region", "Full DR exercise with board observation", 14, 620_000),
                ("Penetration testing — external", "Red-team engagement, with remediation sprint", 60, 980_000),
                ("UAT with 12 pilot branches", "Progressive UAT with real transactions and mirror books", 90, 2_100_000),
                ("Staff training — 14,000 employees", "Multi-modal training curriculum and certification", 120, 3_400_000),
                ("Customer-communication campaign", "Customer education on new app, notices, in-branch support", 90, 1_600_000),
                ("Branch go-live — pilot 5 branches", "Progressive rollout, hypercare, issue resolution", 60, 1_100_000),
                ("Regional rollout — country 1", "First full-country rollout with 90-day hypercare", 90, 2_200_000),
                ("Regional rollout — countries 2–4", "Phased rollout to remaining markets", 180, 5_800_000),
                ("Hypercare and stabilization", "90-day hypercare per market, SRE on-call at elevated levels", 90, 2_400_000),
                ("Final project closeout & lessons learned", "Formal closeout, LL workshop, benefits-realization report", 30, 320_000),
            ]),
        "risks": [
            ("Data migration corrupts customer balances", "technical", "low", "very_high", "avoid",
             "Parallel systems with daily reconciliation; pilot-first; cryptographic checksums; rollback plan",
             "Reconciliation flags > 0.01% discrepancy"),
            ("Regulator rejects new architecture", "external", "medium", "very_high", "mitigate",
             "Early engagement with regulators, quarterly reviews, architectural submission",
             "Any regulator raises material objection at review"),
            ("Key vendor files for bankruptcy", "external", "low", "very_high", "transfer",
             "Contractual escrow, alternate vendor on retainer, exit strategy documented",
             "Vendor issues going-concern notice or missed consecutive milestones"),
            ("Cybersecurity breach during dual-run", "technical", "medium", "very_high", "mitigate",
             "Zero-trust architecture, 24/7 SOC, regular red-team, breach-response retainer",
             "Any P1 security alert or IOC detected"),
            ("SWIFT/scheme adapter certification delay", "external", "medium", "high", "mitigate",
             "Early sandbox testing, scheme-agent engagement, buffer in schedule",
             "Scheme certification misses planned date by > 30 days"),
            ("Talent attrition from legacy team", "organizational", "high", "high", "mitigate",
             "Retention bonuses, dual-track staffing, documentation of legacy as you go",
             "Attrition of > 10% legacy team in a quarter"),
            ("Fraud models underperform post-migration", "technical", "medium", "high", "mitigate",
             "Shadow-mode operation for 90 days, model monitoring, human-in-the-loop",
             "Fraud rate rises > 25% vs baseline"),
            ("Customer-app adoption lags target", "organizational", "medium", "high", "mitigate",
             "Customer-education campaign, branch support, incentives for early adoption",
             "Adoption < 60% at 90 days post-launch"),
            ("Hypercare capacity overwhelmed", "organizational", "high", "high", "mitigate",
             "Tiered support, extra staffing, circuit-breakers, rollback capability",
             "Support ticket volume > 3x forecast for > 48 hours"),
            ("Event-sourcing complexity causes defects", "technical", "high", "medium", "mitigate",
             "Pattern reuse, architecture office hours, automated schema validation, early spike",
             "Defect clusters in aggregate/event logic"),
            ("Regulatory-reporting deadline miss", "external", "medium", "very_high", "avoid",
             "Parallel reporting during dual-run, pre-submission validation, regulator liaison",
             "First submission fails validation or misses deadline"),
            ("AML false-positive rate too high", "technical", "high", "medium", "mitigate",
             "Model tuning, tiered review, threshold optimization, ML-assisted triage",
             "FP rate > 90% in pilot or rollout"),
            ("Payment-scheme downtime during rollout", "external", "low", "very_high", "accept",
             "Redundant rails, failover mode, manual-process playbook",
             "Scheme outage > 30 minutes"),
            ("Dual-run reconciliation backlog", "technical", "medium", "high", "mitigate",
             "Automated reconciliation, daily review, exception-driven attention",
             "Unreconciled items > 0.05% daily"),
            ("Third-party contract dispute", "external", "medium", "high", "escalate",
             "Clear SLAs, escalation paths, contractual dispute-resolution, alternative providers",
             "Vendor refuses to acknowledge issue or delivers notice of dispute"),
            ("Cost overrun on cloud infrastructure", "project_management", "high", "medium", "mitigate",
             "FinOps team, reservation strategy, workload right-sizing, monthly reviews",
             "Cloud spend exceeds budget by > 15%"),
            ("Privacy regulation changes mid-program", "external", "medium", "high", "accept",
             "Privacy counsel on retainer, quarterly regulatory reviews, flexible consent design",
             "New regulation passed in any operating country"),
            ("Critical model biased or unfair", "organizational", "low", "very_high", "avoid",
             "Model-bias testing, explainability, review board, diverse training data",
             "Any fairness metric outside acceptable range"),
            ("Branch-network readiness insufficient", "organizational", "medium", "high", "mitigate",
             "Branch-readiness audits, train-the-trainer, just-in-time materials, hypercare floaters",
             "Branch readiness score < 80% at T-30"),
            ("Sanctions screening latency too high", "technical", "medium", "high", "mitigate",
             "Pre-screening cache, async screening for non-real-time, scheme-level fallback",
             "Screening p99 > 800 ms"),
        ],
        "deliverables": [
            ("Reference Architecture Document", "Target-state architecture with event sourcing, CQRS, saga patterns", "accepted", "exceeds_standard", 100, "Reviewed by external architecture board"),
            ("Regulatory Mapping Matrix", "Regulation-to-capability mapping for 4 jurisdictions", "accepted", "meets_standard", 100, "Compliance counsel and regulator signoff"),
            ("Platform Landing Zone", "Multi-region cloud landing zone with guardrails", "accepted", "meets_standard", 100, "Security and cloud-ops signoff"),
            ("Accounts & Ledger Service — v1", "Core accounts and general-ledger services in production", "in_progress", "not_assessed", 70, "SLOs met in staging"),
            ("Payments Hub — SWIFT + Domestic", "Unified payments hub supporting SWIFT and domestic rails", "in_progress", "not_assessed", 55, "Scheme certifications issued"),
            ("Mobile App — Public Beta", "Mobile app available in public beta", "in_progress", "not_assessed", 40, "App-store approval with 4+ rating"),
            ("Migration Factory & Reconciliation", "End-to-end data-migration toolchain", "in_progress", "not_assessed", 65, "Pilot migration reconciles < 0.01%"),
            ("AML/KYC Integration", "AML platform integration with end-to-end alert flow", "planned", "not_assessed", 30, "Compliance committee signoff"),
            ("PCI-DSS Level 1 Attestation", "Full PCI-DSS certification", "planned", "not_assessed", 0, "QSA signs off on ROC"),
            ("DR & BCP Runbook", "Runbooks for cross-region failover and BCP scenarios", "planned", "not_assessed", 50, "Board-observed DR drill passes"),
            ("Regulatory Reporting Suite", "Suite of regulatory reports per jurisdiction", "planned", "not_assessed", 20, "First submission passes validation"),
            ("UAT Signoff — Pilot Branches", "UAT sign-off from 12 pilot branches", "planned", "not_assessed", 0, "All pilot branches sign off"),
            ("Training Certification — 14,000 staff", "Certification records for all operational staff", "planned", "not_assessed", 0, ">= 95% staff certified"),
            ("Legacy Decommissioning Certificate", "Formal decommissioning of mainframe", "planned", "not_assessed", 0, "CIO and CTO attestation"),
            ("Benefits Realization Report", "Post-program benefits realization analysis", "planned", "not_assessed", 0, "Finance validates savings claims"),
        ],
        "measurements": [
            ("Schedule Performance Index (SPI)", "schedule", "kpi", 1.0, "ratio", 0.8, 0.9, 1.0),
            ("Cost Performance Index (CPI)", "cost", "kpi", 1.0, "ratio", 0.85, 0.92, 1.0),
            ("Production API SLO (availability)", "quality", "kpi", 99.99, "%", 99.9, 99.95, 99.99),
            ("API p99 latency — core", "quality", "kpi", 150, "ms", 500, 300, 200),
            ("Payments throughput peak", "quality", "kpi", 50000, "tps", 10000, 25000, 40000),
            ("Change-failure rate", "quality", "kpi", 5, "%", 20, 10, 7),
            ("Deployment frequency", "schedule", "leading", 50, "per day", 5, 20, 35),
            ("Lead time for changes", "schedule", "kpi", 4, "hours", 48, 16, 8),
            ("MTTR — production incidents", "quality", "kpi", 15, "minutes", 120, 45, 25),
            ("Test-automation coverage", "quality", "kpi", 85, "%", 60, 75, 80),
            ("Data-reconciliation discrepancy", "quality", "lagging", 0.01, "%", 1.0, 0.1, 0.05),
            ("Vulnerability backlog (critical)", "risk", "leading", 0, "#", 20, 10, 3),
            ("AML false-positive rate", "quality", "lagging", 60, "%", 90, 80, 70),
            ("Customer NPS (mobile)", "stakeholder", "outcome", 55, "NPS", 10, 30, 45),
            ("Dual-run reconciliation gap", "quality", "lagging", 0.05, "%", 1.0, 0.3, 0.15),
            ("Migration throughput per day", "schedule", "leading", 120000, "customers", 30000, 70000, 100000),
            ("Cloud cost — month over month", "cost", "leading", 0, "% variance", 15, 8, 3),
            ("Feature-flag coverage", "quality", "leading", 90, "%", 50, 70, 85),
            ("Sprint velocity", "team", "leading", 120, "SP", 60, 85, 110),
            ("Regulator engagement cadence", "stakeholder", "leading", 4, "/year", 1, 2, 3),
        ],
        "stakeholders": [
            ("Helena Weiss", "Group CEO", "sponsor", "supportive", "leading", "high", "high"),
            ("Raphael Moreau", "Group CTO", "sponsor", "supportive", "leading", "high", "high"),
            ("Inga Lindgren", "Group CFO", "sponsor", "supportive", "supportive", "high", "high"),
            ("Akira Yoshida", "Chief Risk Officer", "internal", "supportive", "leading", "high", "high"),
            ("Dominique Pinto", "Chief Compliance Officer", "internal", "supportive", "leading", "high", "high"),
            ("Siobhan Connolly", "Chief Information Security Officer", "internal", "supportive", "leading", "high", "high"),
            ("Central Bank — Country 1", "Home-market regulator", "regulator", "neutral", "neutral", "high", "medium"),
            ("Central Bank — Country 2", "Regulator — second market", "regulator", "neutral", "neutral", "high", "medium"),
            ("Central Bank — Country 3", "Regulator — third market", "regulator", "neutral", "neutral", "high", "medium"),
            ("Central Bank — Country 4", "Regulator — fourth market", "regulator", "neutral", "neutral", "high", "medium"),
            ("SWIFT compliance officer", "Scheme representative", "regulator", "neutral", "supportive", "medium", "medium"),
            ("Card scheme manager — Visa", "Scheme relationship", "supplier", "supportive", "supportive", "high", "medium"),
            ("Card scheme manager — Mastercard", "Scheme relationship", "supplier", "supportive", "supportive", "high", "medium"),
            ("Core banking vendor CEO", "Vendor executive sponsor", "supplier", "supportive", "leading", "high", "high"),
            ("Systems integrator partner lead", "SI program executive", "supplier", "supportive", "leading", "high", "high"),
            ("Cloud provider — TAM", "Cloud technical account manager", "supplier", "supportive", "supportive", "medium", "high"),
            ("Retail banking CEO", "Main internal client", "customer", "supportive", "leading", "high", "high"),
            ("Commercial banking COO", "Commercial operations client", "customer", "supportive", "supportive", "high", "high"),
            ("Branch operations director", "14,000-staff branch network lead", "customer", "neutral", "supportive", "high", "high"),
            ("Customer advocacy council", "Customer-voice forum", "end_user", "neutral", "supportive", "low", "high"),
            ("External auditor (Big-4)", "Independent audit partner", "regulator", "neutral", "neutral", "high", "medium"),
            ("Data-protection authorities", "Privacy regulator across markets", "regulator", "neutral", "neutral", "high", "medium"),
            ("Union representative — ops", "Employee representative for rollout", "external", "resistant", "neutral", "medium", "medium"),
            ("Board risk committee", "Risk oversight body", "sponsor", "supportive", "supportive", "high", "high"),
            ("Strategic consulting partner", "Program management consultancy", "supplier", "supportive", "leading", "high", "high"),
            ("Chief Data Officer", "Data strategy and governance lead", "internal", "supportive", "leading", "high", "high"),
            ("Chief People Officer", "Talent and change management", "internal", "supportive", "supportive", "medium", "medium"),
            ("Fintech partner consortium", "Partner developer network", "customer", "supportive", "supportive", "low", "medium"),
            ("FIU — financial intelligence units", "Anti-financial-crime authorities", "regulator", "neutral", "neutral", "high", "medium"),
            ("Press & analyst relations", "External communications", "external", "neutral", "supportive", "medium", "medium"),
        ],
        "team": [
            ("Amit Chakraborty", "amit.c@helios.bank", "project_manager", "Program director — Helios", "PMP, PgMP, core-banking transformations", 100),
            ("Rebekka Vos", "rebekka.v@helios.bank", "architect", "Chief architect", "Event sourcing, CQRS, Kafka, DDD", 100),
            ("Daniel Nyström", "daniel.n@helios.bank", "project_manager", "Platform engineering lead", "Kubernetes, SRE, FinOps", 100),
            ("Leilani Tupou", "leilani.t@helios.bank", "project_manager", "Accounts & ledger stream lead", "Banking domain, ledgers, regulatory", 100),
            ("Björn Karlsson", "bjorn.k@helios.bank", "project_manager", "Payments stream lead", "ISO 20022, SWIFT, instant payments", 100),
            ("Zara Ahmed", "zara.a@helios.bank", "project_manager", "Cards & loans stream lead", "Card issuing, lending origination", 100),
            ("Hugo Ribeiro", "hugo.r@helios.bank", "project_manager", "Digital channels stream lead", "Mobile, BFF, accessibility", 100),
            ("Fatou Diop", "fatou.d@helios.bank", "project_manager", "Regulatory & risk stream lead", "AML, KYC, reporting, SOX", 100),
            ("Mei-Ling Chen", "meiling.c@helios.bank", "project_manager", "Migration stream lead", "Legacy migrations, reconciliation", 100),
            ("Javier Salas", "javier.s@helios.bank", "analyst", "SRE lead", "SLOs, incident management, chaos engineering", 100),
            ("Anna Kowalski", "anna.k@helios.bank", "tester", "QA director", "Test automation, performance testing", 100),
            ("Rohan Ghosh", "rohan.g@helios.bank", "developer", "Security engineering lead", "Zero-trust, HSM, app-sec", 100),
            ("Lorenzo Rizzo", "lorenzo.r@helios.bank", "developer", "Data platform lead", "Lakehouse, feature store, governance", 100),
            ("Karen Okonkwo", "karen.o@helios.bank", "developer", "Staff engineer — accounts", "Event sourcing, microservices", 100),
            ("Maximilian Schneider", "max.s@helios.bank", "developer", "Staff engineer — payments", "ISO 20022, real-time settlement", 100),
            ("Priyanka Rao", "priyanka.r@helios.bank", "developer", "Staff engineer — cards", "Card systems, ISO 8583", 100),
            ("Tomás Pereira", "tomas.p@helios.bank", "developer", "Staff engineer — mobile", "iOS, Android, React Native", 100),
            ("Sara Heikkilä", "sara.h@helios.bank", "developer", "Staff engineer — web", "React, TypeScript, accessibility", 100),
            ("Olufemi Adebayo", "olufemi.a@helios.bank", "architect", "Integration architect", "APIs, ESB, saga orchestration", 100),
            ("Ruth Cohen", "ruth.c@helios.bank", "analyst", "Business analyst lead", "Banking domain, requirements", 100),
            ("Kenji Watanabe", "kenji.w@helios.bank", "developer", "DevEx & platform team", "Developer tools, CI/CD", 100),
            ("Elise Vandenberg", "elise.v@helios.bank", "analyst", "Change-management lead", "Org change, communications", 100),
            ("Nadia Volkov", "nadia.v@helios.bank", "designer", "UX lead — digital channels", "Banking UX, accessibility", 100),
            ("Gabriel Santana", "gabriel.s@helios.bank", "analyst", "Program governance officer", "PMO, governance, reporting", 100),
            ("Priyal Jain", "priyal.j@helios.bank", "tester", "Performance test lead", "JMeter, k6, cloud load testing", 100),
            ("Omar Hassan", "omar.h@helios.bank", "developer", "Staff SRE — reliability", "Observability, error budgets", 100),
            ("Ingrid Sørensen", "ingrid.s@helios.bank", "analyst", "FinOps lead", "Cloud cost optimization, budgeting", 100),
            ("Klaus Berger", "klaus.b@helios.bank", "developer", "Chaos engineering lead", "Fault injection, resilience testing", 80),
        ],
    },
]


# ────────────────────────────────────────────────────────────────────────
# ENTERPRISE DATA — realistic CRM companies (Microsoft, SAP, Oracle, etc.)
# plus their contacts, leads, opportunities, contracts; ERP vendors;
# campaigns and drip sequences. Workspace-scoped, NOT tied to any project.
# ────────────────────────────────────────────────────────────────────────

ENTERPRISE_COMPANIES = [
    # (name, industry, website, revenue, employees, country, hq_city, description)
    ("Microsoft Corporation", "Software / Cloud", "microsoft.com", 245_000_000_000, 228_000, "USA", "Redmond, WA",
     "Global technology company producing Windows, Office 365, Azure cloud, GitHub, LinkedIn, Xbox, and enterprise AI services."),
    ("SAP SE", "Enterprise Software", "sap.com", 36_200_000_000, 107_000, "Germany", "Walldorf",
     "Market leader in enterprise application software for ERP, supply chain, HR, and CRM across 440,000 customers."),
    ("Oracle Corporation", "Database / Cloud", "oracle.com", 53_000_000_000, 159_000, "USA", "Austin, TX",
     "Flagship database vendor expanding into OCI cloud, NetSuite ERP, Cerner healthcare, and autonomous database services."),
    ("Salesforce Inc.", "SaaS CRM", "salesforce.com", 34_900_000_000, 76_000, "USA", "San Francisco, CA",
     "Pioneer in SaaS CRM covering Sales, Service, Marketing, Commerce, Data Cloud, and the MuleSoft integration platform."),
    ("Alphabet / Google Cloud", "Cloud / Advertising", "cloud.google.com", 307_400_000_000, 181_000, "USA", "Mountain View, CA",
     "Parent company of Google, Android, YouTube, and Google Cloud Platform (BigQuery, Vertex AI, Anthos, Workspace)."),
    ("Amazon Web Services", "Cloud Infrastructure", "aws.amazon.com", 90_800_000_000, 120_000, "USA", "Seattle, WA",
     "Largest public cloud provider with 200+ services across compute, storage, databases, AI/ML, and enterprise SaaS."),
    ("IBM", "Consulting / Hybrid Cloud", "ibm.com", 61_800_000_000, 282_000, "USA", "Armonk, NY",
     "Enterprise IT services, Red Hat OpenShift, watsonx AI, z/OS mainframes, and global consulting via IBM Consulting."),
    ("Adobe Inc.", "Creative / Marketing SaaS", "adobe.com", 19_400_000_000, 29_000, "USA", "San Jose, CA",
     "Creative Cloud (Photoshop, Illustrator), Document Cloud, and Experience Cloud marketing platform."),
    ("ServiceNow", "ITSM / Workflow", "servicenow.com", 8_970_000_000, 22_000, "USA", "Santa Clara, CA",
     "Now Platform for IT service management, customer service, HR, security operations, and low-code workflow automation."),
    ("Workday", "HR / Finance SaaS", "workday.com", 7_260_000_000, 18_800, "USA", "Pleasanton, CA",
     "Cloud-based HCM and financial management suite serving 10,000+ organizations including half the Fortune 500."),
    ("Siemens AG", "Industrial / Digital Twin", "siemens.com", 83_000_000_000, 320_000, "Germany", "Munich",
     "Industrial automation, smart infrastructure, mobility, and Siemens Digital Industries Software (MindSphere, Teamcenter)."),
    ("Deutsche Telekom / T-Systems", "Telecom / IT Services", "t-systems.com", 122_000_000_000, 208_000, "Germany", "Bonn",
     "Largest European telecom operator with T-Systems providing managed IT, cloud, and cybersecurity to enterprises."),
    ("Accenture", "Consulting / Integration", "accenture.com", 64_900_000_000, 774_000, "Ireland", "Dublin",
     "Global consulting firm delivering digital transformation, cloud migration, and managed services across every industry."),
    ("Cisco Systems", "Networking / Security", "cisco.com", 53_800_000_000, 84_000, "USA", "San Jose, CA",
     "Enterprise networking hardware, Webex collaboration, Cisco Security (Talos), and the full-stack Cisco Observability."),
    ("Dell Technologies", "Hardware / Data Center", "dell.com", 88_400_000_000, 108_000, "USA", "Round Rock, TX",
     "Servers, storage, client devices, VMware hypervisor, and Apex infrastructure-as-a-service offerings."),
    ("HP Enterprise", "Hybrid Cloud / Networking", "hpe.com", 29_100_000_000, 61_600, "USA", "Spring, TX",
     "Edge-to-cloud infrastructure, Aruba networking, GreenLake consumption platform, and HPC supercomputing."),
    ("VMware (Broadcom)", "Virtualization / Cloud", "vmware.com", 13_400_000_000, 38_000, "USA", "Palo Alto, CA",
     "vSphere hypervisor, NSX networking, Tanzu Kubernetes, and cross-cloud management (now part of Broadcom)."),
    ("Atlassian", "DevTools / Collaboration", "atlassian.com", 4_360_000_000, 11_500, "Australia", "Sydney",
     "Jira, Confluence, Bitbucket, and Jira Service Management for software teams and enterprise ITSM."),
    ("Snowflake", "Data Cloud", "snowflake.com", 3_630_000_000, 7_600, "USA", "Bozeman, MT",
     "Cloud data warehouse and data platform with data sharing across AWS, Azure, and GCP."),
    ("Databricks", "Data / AI Platform", "databricks.com", 2_400_000_000, 7_800, "USA", "San Francisco, CA",
     "Unified analytics platform for data engineering, data science, and large-scale ML built around Lakehouse."),
    ("Red Hat (IBM)", "Open Source Enterprise", "redhat.com", 5_600_000_000, 19_000, "USA", "Raleigh, NC",
     "RHEL, OpenShift Kubernetes, Ansible automation, and the industry reference for open source in enterprise."),
    ("Intel Corporation", "Semiconductors", "intel.com", 54_200_000_000, 108_000, "USA", "Santa Clara, CA",
     "Processor design and fabrication (Xeon, Core), Intel Foundry Services, and Mobileye autonomous-driving subsidiary."),
    ("NVIDIA", "AI Hardware / Software", "nvidia.com", 60_900_000_000, 29_600, "USA", "Santa Clara, CA",
     "Industry-leading GPUs for AI training and inference, CUDA, DGX systems, Omniverse, and automotive AI."),
    ("Nokia", "Networking / 5G", "nokia.com", 23_800_000_000, 86_000, "Finland", "Espoo",
     "5G radio access networks, optical, IP routing, Nokia Bell Labs, and cloud-native network operations."),
    ("BT Group", "Telecom", "bt.com", 26_700_000_000, 104_000, "United Kingdom", "London",
     "Leading UK communications provider with BT Business, BT Enterprise, and Openreach broadband infrastructure."),
    ("Infosys", "IT Services", "infosys.com", 18_600_000_000, 317_000, "India", "Bengaluru",
     "Global IT services and consulting — digital transformation, managed services, BPO, and SAP/Salesforce partnerships."),
    ("Tata Consultancy Services", "IT Services / Consulting", "tcs.com", 29_100_000_000, 601_000, "India", "Mumbai",
     "Largest Indian IT services firm — BFSI, retail, telecom, healthcare transformation at Fortune 500 clients."),
    ("Capgemini", "Consulting / Digital", "capgemini.com", 23_800_000_000, 340_000, "France", "Paris",
     "European IT services leader with strong practices in cloud, data, cybersecurity, and industry verticals."),
]

# Executive-level contact role templates — applied per company
EXEC_CONTACT_ROLES = [
    ("Chief Executive Officer", "CEO", True),
    ("Chief Technology Officer", "CTO", True),
    ("Chief Information Officer", "CIO", True),
    ("Chief Financial Officer", "CFO", False),
    ("Chief Information Security Officer", "CISO", True),
    ("VP of Engineering", "VP Eng", True),
    ("VP of Product", "VP Product", False),
    ("VP of Sales", "VP Sales", False),
    ("VP of Procurement", "VP Procurement", True),
    ("Director of IT", "Director IT", True),
    ("Director of Cloud Architecture", "Director Cloud", True),
    ("Director of Data Engineering", "Director Data", True),
    ("Head of Security", "Head Security", True),
    ("Head of Digital Transformation", "Head DT", True),
    ("Senior Manager — Enterprise Architecture", "Sr. Mgr. EA", True),
]

# Opportunity templates — deal types enterprise customers buy from us
OPPORTUNITY_TEMPLATES = [
    ("Enterprise license — 5-year master agreement", "prospecting", 850_000, 15),
    ("Annual platform subscription renewal", "closed_won", 450_000, 100),
    ("New business — 3-year commitment", "proposal", 1_200_000, 55),
    ("Cloud migration services engagement", "negotiation", 680_000, 75),
    ("Managed services — 24×7 operations", "qualification", 540_000, 30),
    ("Implementation services — Phase 1", "proposal", 320_000, 60),
    ("Upsell — additional modules", "negotiation", 175_000, 80),
    ("Security audit & remediation engagement", "qualification", 95_000, 35),
    ("Training & certification bundle (200 seats)", "proposal", 62_000, 55),
    ("Proof of concept — AI/ML use case", "prospecting", 45_000, 20),
    ("Multi-region DR architecture project", "negotiation", 890_000, 70),
    ("Data migration — legacy system retirement", "proposal", 1_450_000, 50),
    ("Custom integration — SAP <-> Salesforce", "qualification", 220_000, 35),
    ("Expansion — EMEA regional deployment", "negotiation", 2_100_000, 65),
    ("Renewal with 25% uplift", "closed_won", 780_000, 100),
    ("Losing deal — customer went with competitor", "closed_lost", 320_000, 0),
    ("Strategic partnership — co-sell motion", "prospecting", 3_500_000, 10),
    ("Premium support tier upgrade", "proposal", 145_000, 70),
    ("Platform consolidation — vendor rationalization", "negotiation", 1_800_000, 60),
    ("Industry-specific vertical solution", "qualification", 420_000, 25),
]

INTERACTION_TEMPLATES = [
    ("call", "Initial discovery call — understand current stack"),
    ("email", "Follow-up: sent proposal document"),
    ("meeting", "Executive briefing with VP of Engineering"),
    ("demo", "Live product demo — focus on integration capabilities"),
    ("call", "Pricing alignment call with procurement"),
    ("email", "Sent updated SOW with revised scope"),
    ("meeting", "Technical deep-dive with architecture team"),
    ("demo", "Custom demo tailored to customer's use case"),
    ("call", "Renewal discussion — contract up in Q3"),
    ("email", "Shared security whitepaper and SOC 2 Type II report"),
    ("meeting", "QBR — quarterly business review"),
    ("call", "Escalation call — production incident resolution"),
    ("email", "Introduced new account executive"),
    ("meeting", "In-person meeting at customer HQ"),
    ("demo", "Sandbox access walkthrough"),
    ("note", "Stakeholder map updated — new CIO started"),
    ("call", "Check-in on pilot milestone delivery"),
    ("email", "Reference-customer intro arranged"),
    ("meeting", "Steering committee — project go-live readiness"),
    ("demo", "Roadmap presentation — next 12 months"),
]

CAMPAIGN_TEMPLATES = [
    ("Q1 Enterprise Webinar Series", "planned", 85_000),
    ("Gartner Magic Quadrant Launch Blitz", "active", 320_000),
    ("AI/ML Thought-Leadership Content", "active", 180_000),
    ("SAP & Salesforce Integration Summit", "active", 240_000),
    ("Cloud Migration Assessment Offer", "completed", 95_000),
    ("CISO Roundtable — Security & Compliance", "active", 65_000),
    ("FY24 Customer Advocacy Program", "completed", 140_000),
    ("Financial Services Vertical Launch", "active", 410_000),
    ("Account-Based Marketing — Top 50", "active", 550_000),
    ("Annual User Conference Sponsorship", "planned", 280_000),
    ("LinkedIn Executive Targeting Campaign", "active", 120_000),
    ("Partner Marketing Co-Fund Program", "active", 95_000),
]

DRIP_TEMPLATES = [
    ("New Trial Signup Nurture", [
        ("Welcome — quick-start guide", 0),
        ("Day 3 — top features to try first", 3),
        ("Day 7 — case study: Fortune 500 customer", 7),
        ("Day 14 — schedule a demo with an SE", 14),
        ("Day 21 — upgrade offer with 10% discount", 21),
    ]),
    ("Lost-Opportunity Re-engagement", [
        ("We've added features you asked about", 0),
        ("Customer success story in your industry", 14),
        ("Free 90-day re-evaluation offer", 30),
    ]),
    ("Upsell — Existing Customer", [
        ("New premium-tier capabilities announced", 0),
        ("ROI calculator for your team size", 7),
        ("Book a 30-minute upgrade discussion", 14),
    ]),
    ("Event Follow-up Sequence", [
        ("Thanks for stopping by our booth", 0),
        ("Slides + demo video from the keynote", 2),
        ("Schedule a 1:1 follow-up", 7),
    ]),
    ("Renewal 90-Day Warning", [
        ("Your contract renews in 90 days", 0),
        ("Usage report — value delivered this year", 30),
        ("Renewal proposal with multi-year discount", 60),
    ]),
]

# Vendors we (the seeding workspace) buy from — tool / service providers
VENDOR_TEMPLATES = [
    ("Amazon Web Services", "AWS Billing", "billing@amazon.com", "Net 30", "US-12-3456789"),
    ("Microsoft Azure", "Azure Commercial", "msft-billing@microsoft.com", "Net 30", "US-23-4567890"),
    ("Google Cloud Platform", "GCP Billing", "cloud-billing@google.com", "Net 30", "US-34-5678901"),
    ("Okta Inc.", "Okta Finance", "billing@okta.com", "Net 30", "US-45-6789012"),
    ("Datadog Inc.", "Datadog Billing", "ap@datadog.com", "Net 30", "US-56-7890123"),
    ("Cloudflare Inc.", "Cloudflare Finance", "finance@cloudflare.com", "Net 15", "US-67-8901234"),
    ("GitHub Enterprise", "GitHub Billing", "billing@github.com", "Net 30", "US-78-9012345"),
    ("Snowflake Inc.", "Snowflake AR", "ar@snowflake.com", "Net 45", "US-89-0123456"),
    ("Stripe Inc.", "Stripe Billing", "billing@stripe.com", "Net 15", "US-90-1234567"),
    ("Twilio Inc.", "Twilio AR", "billing@twilio.com", "Net 30", "US-01-2345678"),
    ("Slack (Salesforce)", "Slack Billing", "billing@slack.com", "Net 30", "US-12-9876543"),
    ("Atlassian", "Atlassian AR", "ar@atlassian.com", "Net 30", "AU-00-1234567"),
    ("PagerDuty Inc.", "PagerDuty Finance", "finance@pagerduty.com", "Net 30", "US-22-3344556"),
    ("Splunk Inc.", "Splunk AR", "ar@splunk.com", "Net 45", "US-33-4455667"),
    ("New Relic", "New Relic Billing", "billing@newrelic.com", "Net 30", "US-44-5566778"),
    ("Elastic N.V.", "Elastic AR", "ar@elastic.co", "Net 30", "NL-55-6677889"),
    ("MongoDB Inc.", "MongoDB Billing", "billing@mongodb.com", "Net 30", "US-66-7788990"),
    ("HashiCorp (IBM)", "HashiCorp AR", "ar@hashicorp.com", "Net 30", "US-77-8899001"),
    ("Zoom Video Communications", "Zoom Billing", "billing@zoom.us", "Net 30", "US-88-9900112"),
    ("Adobe Creative Cloud", "Adobe Billing", "billing@adobe.com", "Net 30", "US-99-0011223"),
    ("LinkedIn Sales Navigator", "LinkedIn AR", "ar@linkedin.com", "Net 30", "US-10-1112223"),
    ("Gartner Inc.", "Gartner AR", "ar@gartner.com", "Net 45", "US-11-2223334"),
    ("Forrester Research", "Forrester AR", "ar@forrester.com", "Net 30", "US-12-3334445"),
    ("Cisco Webex", "Cisco Billing", "billing@cisco.com", "Net 30", "US-13-4445556"),
    ("Tableau (Salesforce)", "Tableau Billing", "billing@tableau.com", "Net 30", "US-14-5556667"),
]

CONTRACT_CYCLES = ["monthly", "quarterly", "yearly", "one_time"]
TERRITORY_TEMPLATES = [
    ("North America — Enterprise", "North America", "Software / Cloud", 500_000_000),
    ("EMEA — Enterprise", "EMEA", "Enterprise Software", 250_000_000),
    ("APAC — Enterprise", "APAC", None, 100_000_000),
    ("LATAM — Enterprise", "LATAM", None, 50_000_000),
    ("Financial Services — Global", None, "BFSI", 1_000_000_000),
    ("Public Sector — Global", None, "Government", 500_000_000),
    ("Healthcare — Global", None, "Healthcare", 250_000_000),
    ("Retail & CPG — Global", None, "Retail", 100_000_000),
]


def _slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")


def _seed_enterprise_data(client: httpx.Client, headers: dict):
    print(f"\n{'#'*60}")
    print("SEEDING ENTERPRISE CRM + ERP DATA")
    print(f"{'#'*60}")

    # ── 1. Territories ──────────────────────────────────────────────
    print("\n[ENT 1/9] Creating territories...")
    terr_ids = []
    for name, region, industry, min_rev in TERRITORY_TEMPLATES:
        t = client.post("/api/crm/territories", headers=headers, json={
            "name": name, "rule_region": region, "rule_industry": industry, "rule_min_revenue": min_rev,
        }).json()
        terr_ids.append(t.get("id"))
    log(f"Created {len(TERRITORY_TEMPLATES)} territories")

    # ── 2. Companies ────────────────────────────────────────────────
    print(f"\n[ENT 2/9] Creating {len(ENTERPRISE_COMPANIES)} enterprise companies...")
    company_ids = []
    for (name, industry, website, revenue, employees, country, city, desc) in ENTERPRISE_COMPANIES:
        c = client.post("/api/crm/companies", headers=headers, json={
            "name": name, "industry": industry, "website": f"https://{website}",
            "phone": fake.phone_number(), "address": f"{fake.street_address()}, {city}, {country}",
            "annual_revenue": revenue, "employee_count": employees,
            "notes": desc,
        }).json()
        company_ids.append((c["id"], name, website))
    log(f"Created {len(ENTERPRISE_COMPANIES)} companies")

    # ── 3. Contacts (6-10 per company) ──────────────────────────────
    print("\n[ENT 3/9] Creating contacts per company...")
    contact_ids_by_company: dict[str, list[str]] = {}
    total_contacts = 0
    for cid, cname, cdomain in company_ids:
        n_contacts = random.randint(5, 10)
        selected_roles = random.sample(EXEC_CONTACT_ROLES, min(n_contacts, len(EXEC_CONTACT_ROLES)))
        ids = []
        for role_full, _short, is_dm in selected_roles:
            first = fake.first_name()
            last = fake.last_name()
            email = f"{first.lower()}.{last.lower()}@{cdomain}"
            contact = client.post("/api/crm/contacts", headers=headers, json={
                "company_id": cid, "first_name": first, "last_name": last,
                "email": email, "phone": fake.phone_number(),
                "job_title": role_full,
                "notes": "Decision maker" if is_dm else "Influencer",
            }).json()
            ids.append(contact["id"])
            total_contacts += 1
        contact_ids_by_company[cid] = ids
    log(f"Created {total_contacts} contacts across {len(company_ids)} companies")

    # ── 4. Leads ────────────────────────────────────────────────────
    print("\n[ENT 4/9] Creating leads...")
    lead_count = 60
    for i in range(lead_count):
        first = fake.first_name(); last = fake.last_name()
        company_hint = random.choice(ENTERPRISE_COMPANIES)[0]
        lead = client.post("/api/crm/leads", headers=headers, json={
            "contact_name": f"{first} {last}", "company_name": company_hint,
            "email": fake.company_email(), "phone": fake.phone_number(),
            "source": random.choice(["website", "referral", "cold_call", "advertising", "social_media", "event", "other"]),
            "estimated_value": random.choice([15_000, 25_000, 50_000, 80_000, 150_000, 250_000, 500_000]),
            "notes": random.choice([
                "Inbound inquiry from website contact form",
                "Referred by existing customer at partner event",
                "Met at Gartner summit — interested in AI capabilities",
                "Responded to LinkedIn outreach campaign",
                "Submitted RFP — comparing 3 vendors",
            ]),
        }).json()
        # ~40% of leads progress beyond "new"
        if random.random() < 0.4:
            new_status = random.choice(["contacted", "qualified", "unqualified", "converted"])
            client.patch(f"/api/crm/leads/{lead['id']}?status={new_status}", headers=headers)
    log(f"Created {lead_count} leads")

    # ── 5. Opportunities (1-3 per company) ──────────────────────────
    print("\n[ENT 5/9] Creating opportunities per company...")
    opp_ids = []
    opp_by_company: dict[str, list[str]] = {}
    total_opps = 0
    for cid, cname, _ in company_ids:
        n_opps = random.randint(1, 3)
        templates = random.sample(OPPORTUNITY_TEMPLATES, min(n_opps, len(OPPORTUNITY_TEMPLATES)))
        ids = []
        contacts = contact_ids_by_company.get(cid, [])
        for (title, stage, amount, prob) in templates:
            contact_id = random.choice(contacts) if contacts else None
            # Add some noise to amounts
            amount_noisy = int(amount * random.uniform(0.8, 1.2))
            close_date = (datetime.utcnow() + timedelta(days=random.randint(15, 180))).date().isoformat()
            op = client.post("/api/crm/opportunities", headers=headers, json={
                "company_id": cid, "contact_id": contact_id,
                "title": f"{cname} — {title}",
                "description": fake.paragraph(nb_sentences=3),
                "stage": stage, "amount": amount_noisy, "probability": prob,
                "expected_close": close_date,
            }).json()
            ids.append(op["id"]); opp_ids.append(op["id"])
            total_opps += 1
        opp_by_company[cid] = ids
    log(f"Created {total_opps} opportunities")

    # ── 6. Interactions (4-10 per opportunity) ──────────────────────
    print("\n[ENT 6/9] Creating interactions per opportunity...")
    total_interactions = 0
    for cid, contacts in contact_ids_by_company.items():
        opps = opp_by_company.get(cid, [])
        if not opps or not contacts:
            continue
        for opp_id in opps:
            n_int = random.randint(4, 10)
            for _ in range(n_int):
                itype, subject = random.choice(INTERACTION_TEMPLATES)
                client.post("/api/crm/interactions", headers=headers, json={
                    "contact_id": random.choice(contacts), "opportunity_id": opp_id,
                    "interaction_type": itype, "subject": subject,
                    "body": fake.paragraph(nb_sentences=2),
                })
                total_interactions += 1
    log(f"Created {total_interactions} interactions")

    # ── 7. Quotes & Contracts ───────────────────────────────────────
    print("\n[ENT 7/9] Creating quotes and contracts...")
    quote_count = 0
    for cid, _, _ in company_ids:
        # ~50% of companies get a quote
        if random.random() < 0.5:
            client.post("/api/crm/quotes", headers=headers, json={
                "quote_number": f"Q-{fake.random_int(10000, 99999)}",
                "valid_until": (datetime.utcnow() + timedelta(days=random.randint(14, 60))).date().isoformat(),
                "items": [
                    {"description": "Platform license (1-year)", "quantity": 1, "unit_price": random.choice([120_000, 250_000, 500_000])},
                    {"description": "Professional services (hours)", "quantity": random.randint(50, 400), "unit_price": 280},
                    {"description": "Premium support (1-year)", "quantity": 1, "unit_price": random.choice([15_000, 35_000, 80_000])},
                ],
            })
            quote_count += 1
    log(f"Created {quote_count} quotes")

    contract_count = 0
    for cid, cname, _ in company_ids:
        # ~60% of companies have an active contract
        if random.random() < 0.6:
            start = datetime.utcnow().date() - timedelta(days=random.randint(30, 700))
            end = start + timedelta(days=365 * random.choice([1, 2, 3]))
            cycle = random.choice(CONTRACT_CYCLES)
            amount = random.choice([120_000, 250_000, 500_000, 1_000_000, 2_500_000])
            client.post("/api/crm/contracts", headers=headers, json={
                "company_id": cid,
                "contract_number": f"C-{fake.random_int(10000, 99999)}",
                "amount": amount, "billing_cycle": cycle,
                "start_date": start.isoformat(), "end_date": end.isoformat(),
                "status": random.choice(["active", "active", "active", "renewing", "expired"]),
            })
            contract_count += 1
    log(f"Created {contract_count} contracts")

    # ── 8. Campaigns + Drip sequences ───────────────────────────────
    print("\n[ENT 8/9] Creating campaigns and drip sequences...")
    for (name, status, budget) in CAMPAIGN_TEMPLATES:
        start = datetime.utcnow().date() - timedelta(days=random.randint(0, 90))
        end = start + timedelta(days=random.randint(30, 120))
        client.post("/api/crm/campaigns", headers=headers, json={
            "name": name, "status": status, "budget": budget,
            "actual_cost": int(budget * random.uniform(0.3, 1.05)),
            "start_date": start.isoformat(), "end_date": end.isoformat(),
        })
    log(f"Created {len(CAMPAIGN_TEMPLATES)} campaigns")

    for (name, steps) in DRIP_TEMPLATES:
        client.post("/api/crm/drips", headers=headers, json={
            "name": name,
            "steps": [
                {"step_order": i, "delay_days": delay, "subject": subj, "body": fake.paragraph(nb_sentences=3)}
                for i, (subj, delay) in enumerate(steps)
            ],
        })
    log(f"Created {len(DRIP_TEMPLATES)} drip sequences")

    # ── 9. ERP vendors + purchase orders + invoices ─────────────────
    print("\n[ENT 9/9] Creating ERP vendors + POs + AP invoices...")
    vendor_ids = []
    for (name, contact, email, terms, tax_id) in VENDOR_TEMPLATES:
        v = client.post("/api/erp/vendors", headers=headers, json={
            "name": name, "contact_person": contact, "email": email,
            "phone": fake.phone_number(), "address": fake.address().replace("\n", ", "),
            "tax_id": tax_id, "payment_terms": terms,
        }).json()
        vendor_ids.append(v.get("id"))
    log(f"Created {len(VENDOR_TEMPLATES)} vendors")

    # 2-4 purchase orders per vendor
    po_count = 0
    for vid in vendor_ids:
        if not vid: continue
        for _ in range(random.randint(2, 4)):
            amount = round(random.uniform(5_000, 250_000), 2)
            client.post("/api/erp/purchase-orders", headers=headers, json={
                "vendor_id": vid,
                "po_number": f"PO-{fake.random_int(100000, 999999)}",
                "total_amount": amount,
                "description": random.choice([
                    "Annual software subscription",
                    "Professional services engagement",
                    "Hardware procurement",
                    "Training and certification",
                    "Premium support tier",
                    "Capacity expansion — additional seats",
                ]),
            })
            po_count += 1
    log(f"Created {po_count} purchase orders")

    # 1-3 AP invoices per vendor
    inv_count = 0
    for vid in vendor_ids:
        if not vid: continue
        for _ in range(random.randint(1, 3)):
            invoice_num = f"INV-{fake.random_int(100000, 999999)}"
            subtotal = round(random.uniform(2_000, 180_000), 2)
            client.post("/api/erp/invoices", headers=headers, json={
                "vendor_id": vid,
                "invoice_number": invoice_num,
                "invoice_type": "payable",
                "subtotal": subtotal,
                "tax_rate": random.choice([0, 7, 10, 19, 20, 23]),
                "due_date": (datetime.utcnow() + timedelta(days=random.randint(-30, 60))).date().isoformat(),
            })
            inv_count += 1
    log(f"Created {inv_count} AP invoices")


def _seed_large_project(client: httpx.Client, headers: dict, tmpl: dict, proj_idx: int):
    """Seed a single large project using its embedded templates. Scales counts up."""
    meta = tmpl["meta"]
    tasks_tmpl = tmpl["tasks"]
    risks_tmpl = tmpl["risks"]
    deliverables_tmpl = tmpl["deliverables"]
    measurements_tmpl = tmpl["measurements"]
    stakeholders_tmpl = tmpl["stakeholders"]
    team_tmpl = tmpl["team"]

    print(f"\n{'='*60}")
    print(f"[LARGE {proj_idx+1}/3] {meta['name']}")
    print(f"  Budget: ${meta['budget']:,}  Duration: {meta['duration_days']}d  Tasks: {len(tasks_tmpl)}")
    print(f"{'='*60}")

    # Project
    start_date = datetime.utcnow().date() - timedelta(days=random.randint(120, 240))
    end_date = start_date + timedelta(days=meta["duration_days"])
    project = client.post("/api/projects/", headers=headers, json={
        "name": meta["name"],
        "description": meta["description"],
        "development_approach": meta["approach"],
        "delivery_cadence": meta["cadence"],
        "budget": meta["budget"],
        "vision": meta["vision"],
        "objectives": meta["objectives"],
        "success_criteria": meta["success_criteria"],
        "status": "executing",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }).json()
    pid = project["id"]
    log(f"Created project ({pid[:8]}…)")

    # Team
    team_ids = []
    for t in team_tmpl:
        member = client.post("/api/team-members/", headers=headers, json={
            "project_id": pid, "name": t[0], "email": t[1],
            "role": t[2], "responsibilities": t[3], "skills": t[4], "availability": t[5],
        }).json()
        team_ids.append(member["id"])
    log(f"Created {len(team_tmpl)} team members")

    # Stakeholders
    for s in stakeholders_tmpl:
        client.post("/api/stakeholders/", headers=headers, json={
            "project_id": pid, "name": s[0], "role": s[1],
            "email": fake.company_email(), "category": s[2],
            "engagement_level": s[3], "desired_engagement": s[4],
            "influence": s[5], "interest": s[6],
            "expectations": fake.paragraph(nb_sentences=2),
            "communication_needs": random.choice(["Weekly email", "Bi-weekly meetings", "Monthly reports", "Steering committee"]),
        })
    log(f"Created {len(stakeholders_tmpl)} stakeholders")

    # Sprints / phases
    n_sprints = random.randint(*LARGE_SPRINTS)
    sprint_ids = []
    sprint_start = start_date
    sprint_span = max(14, meta["duration_days"] // n_sprints)
    for i in range(n_sprints):
        sprint_end = sprint_start + timedelta(days=sprint_span)
        sprint = client.post("/api/sprints/", headers=headers, json={
            "project_id": pid,
            "name": f"Phase {i+1}",
            "goal": fake.sentence(nb_words=10),
            "sprint_number": i + 1,
            "start_date": sprint_start.isoformat(),
            "end_date": sprint_end.isoformat(),
        }).json()
        sprint_ids.append(sprint["id"])
        status = "completed" if i < n_sprints - 2 else ("active" if i == n_sprints - 2 else "planning")
        if status in ("completed", "active"):
            client.patch(f"/api/sprints/{sprint['id']}?status={status}", headers=headers)
        sprint_start = sprint_end + timedelta(days=1)
    log(f"Created {n_sprints} phases")

    # Tasks — use the full tasks_tmpl list, staggering status across the timeline
    task_ids = []
    total_tasks = len(tasks_tmpl)
    offset_days = 0
    for i, (title, desc, _, duration, opt, ml, pess, cost) in enumerate(tasks_tmpl):
        # Status progression: first 55% done, next 20% in_progress, rest upcoming
        if i / total_tasks < 0.55:
            status = "done"
        elif i / total_tasks < 0.75:
            status = random.choice(["in_progress", "in_review"])
        else:
            status = random.choice(["todo", "backlog"])
        actual_cost_ratio = random.uniform(0.85, 1.15)
        task_start = start_date + timedelta(days=offset_days)
        task_due = task_start + timedelta(days=duration)
        task = client.post("/api/tasks/", headers=headers, json={
            "project_id": pid,
            "title": title, "description": desc, "status": status,
            "priority": random.choice(TASK_PRIORITIES),
            "story_points": random.choice([1, 2, 3, 5, 8, 13, 21]),
            "duration_days": duration,
            "optimistic_duration": opt, "most_likely_duration": ml, "pessimistic_duration": pess,
            "planned_cost": cost,
            "actual_cost": round(cost * actual_cost_ratio, 2) if status in ("done", "in_progress", "in_review") else 0,
            "assignee_id": random.choice(team_ids),
            "sprint_id": sprint_ids[min(len(sprint_ids) - 1, i * n_sprints // total_tasks)] if sprint_ids else None,
            "wbs_code": f"{proj_idx+1}.{(i//10)+1}.{(i%10)+1}",
            "start_date": task_start.isoformat(),
            "due_date": task_due.isoformat(),
            "completed_date": task_due.isoformat() if status == "done" else None,
        }).json()
        task_ids.append(task["id"])
        offset_days += max(1, duration // 6)  # stagger tasks
    log(f"Created {total_tasks} tasks")

    # Dependencies
    n_deps = random.randint(*LARGE_DEPENDENCIES)
    created_deps = set()
    deps_created = 0
    for _ in range(n_deps * 3):
        if deps_created >= n_deps:
            break
        i = random.randint(0, len(task_ids) - 2)
        j = random.randint(i + 1, min(i + 10, len(task_ids) - 1))
        pair = (task_ids[i], task_ids[j])
        if pair in created_deps:
            continue
        resp = client.post(f"/api/projects/{pid}/dependencies", headers=headers, json={
            "project_id": pid,
            "predecessor_id": task_ids[i], "successor_id": task_ids[j],
            "dependency_type": "finish_to_start",
            "lag_days": random.choice([0, 0, 0, 1, 2, 3]),
        })
        if resp.status_code == 201:
            created_deps.add(pair)
            deps_created += 1
    log(f"Created {deps_created} dependencies")

    # Risks
    risk_ids = []
    for r in risks_tmpl:
        title, cat, prob, impact, strategy, response, trigger = r
        risk = client.post("/api/risks/", headers=headers, json={
            "project_id": pid,
            "title": title, "description": fake.paragraph(nb_sentences=3),
            "category": cat, "probability": prob, "impact": impact,
            "status": random.choice(RISK_STATUSES[:4]),
            "strategy": strategy, "response_plan": response, "trigger_conditions": trigger,
            "owner_id": random.choice(team_ids),
        }).json()
        risk_ids.append(risk["id"])
    log(f"Created {len(risks_tmpl)} risks")

    # Deliverables
    for i, d in enumerate(deliverables_tmpl):
        name, desc, status, quality, pct, criteria = d
        due = start_date + timedelta(days=(i + 1) * (meta["duration_days"] // (len(deliverables_tmpl) + 1)))
        client.post("/api/deliverables/", headers=headers, json={
            "project_id": pid,
            "name": name, "description": desc, "status": status,
            "quality_level": quality, "completion_percentage": pct,
            "acceptance_criteria": criteria,
            "due_date": due.isoformat(),
            "delivered_date": due.isoformat() if status == "accepted" else None,
        })
    log(f"Created {len(deliverables_tmpl)} deliverables")

    # Measurements
    for m in measurements_tmpl:
        name, domain, mtype, target, unit, red, yellow, green = m
        noise = random.uniform(0.75, 1.1)
        actual = round(target * noise, 2)
        client.post("/api/measurements/", headers=headers, json={
            "project_id": pid,
            "name": name, "description": f"Tracks {name.lower()} across the program.",
            "metric_type": mtype, "domain": domain,
            "target_value": target, "actual_value": actual, "unit": unit,
            "threshold_red": red, "threshold_yellow": yellow, "threshold_green": green,
        })
    log(f"Created {len(measurements_tmpl)} measurements")

    # Change requests
    n_cr = random.randint(*LARGE_CHANGE_REQUESTS)
    for _ in range(n_cr):
        client.post("/api/change-requests/", headers=headers, json={
            "project_id": pid,
            "title": fake.sentence(nb_words=8).rstrip("."),
            "description": fake.paragraph(nb_sentences=3),
            "justification": fake.paragraph(nb_sentences=2),
            "status": random.choice(CHANGE_STATUSES),
            "impact": random.choice(CHANGE_IMPACTS),
            "impact_analysis": fake.paragraph(nb_sentences=4),
            "requested_by_id": random.choice(team_ids),
            "reviewed_by_id": random.choice(team_ids),
        })
    log(f"Created {n_cr} change requests")

    # Comments — on tasks and risks
    n_comments = random.randint(*LARGE_COMMENTS)
    for _ in range(n_comments):
        target_type = random.choice(["task", "risk"])
        target_id = random.choice(task_ids) if target_type == "task" else random.choice(risk_ids)
        client.post("/api/comments/", headers=headers, json={
            "project_id": pid, "target_type": target_type, "target_id": target_id,
            "body": fake.sentence(nb_words=random.randint(8, 22)),
        })
    log(f"Created {n_comments} comments")

    # Lessons learned
    n_lessons = random.randint(*LARGE_LESSONS)
    for _ in range(n_lessons):
        client.post("/api/lessons/", headers=headers, json={
            "project_id": pid,
            "title": fake.sentence(nb_words=6).rstrip("."),
            "category": random.choice(LESSON_CATEGORIES),
            "what_happened": fake.paragraph(nb_sentences=3),
            "impact": fake.paragraph(nb_sentences=2),
            "recommendation": fake.paragraph(nb_sentences=2),
        })
    log(f"Created {n_lessons} lessons")

    # Time entries
    n_time = random.randint(*LARGE_TIME_ENTRIES)
    for _ in range(n_time):
        work_date = fake.date_between(start_date=start_date, end_date="today")
        client.post("/api/time-entries/", headers=headers, json={
            "project_id": pid, "task_id": random.choice(task_ids),
            "hours": round(random.uniform(1, 10), 1),
            "work_date": work_date.isoformat(),
            "description": random.choice([
                "Field supervision", "Design coordination", "Inspection",
                "Sprint development", "Integration testing", "Vendor management",
                "Safety walk", "Cost analysis", "Procurement", "Client meeting",
                "Code review", "Commissioning", "Stakeholder workshop",
            ]),
        })
    log(f"Created {n_time} time entries")


SEED_EMAIL = "seed-admin@pmproject.dev"
SEED_PASSWORD = "Seed123!@#"


def _promote_to_admin(email: str) -> bool:
    """Promote the seed user to ADMIN via docker compose exec. Required since
    every create endpoint now needs require_permission()."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "db",
             "psql", "-U", "pmuser", "-d", "pmproject",
             "-c", f"UPDATE users SET role='ADMIN' WHERE email='{email}';"],
            capture_output=True, text=True, timeout=15,
        )
        return "UPDATE 1" in result.stdout
    except Exception as e:
        print(f"  WARN: couldn't auto-promote via docker exec: {e}")
        return False


def run(base_url: str, skip_small: bool = False, skip_large: bool = False, skip_enterprise: bool = False):
    client = httpx.Client(base_url=base_url, timeout=30)

    # ── 1. Create / reuse seed admin account ──────────────────────────
    print("\n[1/12] Creating seed admin account...")
    signup_resp = client.post("/api/auth/signup", json={
        "name": "Seed Admin",
        "email": SEED_EMAIL,
        "password": SEED_PASSWORD,
    })

    if signup_resp.status_code == 201:
        # Brand-new user — promote via SQL so gated endpoints work
        if _promote_to_admin(SEED_EMAIL):
            log(f"Created {SEED_EMAIL} and promoted to ADMIN")
        else:
            log(f"Created {SEED_EMAIL} but promotion failed — gated endpoints may 403")
        # Log in again so the fresh JWT has no stale role claim
        login_resp = client.post("/api/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
        login_resp.raise_for_status()
        token = login_resp.json()["access_token"]
    elif signup_resp.status_code == 409:
        # User already exists — just log in (assumes already promoted from a prior run)
        login_resp = client.post("/api/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
        login_resp.raise_for_status()
        token = login_resp.json()["access_token"]
        # Defensive re-promote in case a prior run failed
        _promote_to_admin(SEED_EMAIL)
        log(f"Reusing {SEED_EMAIL}")
    else:
        signup_resp.raise_for_status()
        token = signup_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    if skip_small:
        small_range = []
    else:
        small_range = range(NUM_PROJECTS)

    for proj_idx in small_range:
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

    # ── Enterprise CRM + ERP data (workspace-scoped) ─────────────────
    if not skip_enterprise:
        _seed_enterprise_data(client, headers)

    # ── Large projects ───────────────────────────────────────────────
    if not skip_large:
        print(f"\n{'#'*60}")
        print("SEEDING LARGE PROJECTS")
        print(f"{'#'*60}")
        for i, ltmpl in enumerate(LARGE_PROJECTS):
            _seed_large_project(client, headers, ltmpl, i)

    # ── Summary ──────────────────────────────────────────────────────
    total_small = 0 if skip_small else NUM_PROJECTS
    total_large = 0 if skip_large else len(LARGE_PROJECTS)
    print(f"\n{'='*60}")
    print("SEEDING COMPLETE!")
    print(f"{'='*60}")
    print(f"  Small projects:   {total_small}")
    print(f"  Large projects:   {total_large}  (construction / stadium / core banking)")
    print(f"  Enterprise data:  {'skipped' if skip_enterprise else f'{len(ENTERPRISE_COMPANIES)} companies, {len(VENDOR_TEMPLATES)} vendors'}")
    print(f"  Base URL:         {base_url}")
    print(f"  Dashboard:        {base_url}/api/dashboard/<project_id>")
    print(f"  Health:           {base_url}/api/health")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the PM project with realistic fake data")
    parser.add_argument("--base-url", default=BASE_URL, help=f"API base URL (default: {BASE_URL})")
    parser.add_argument("--no-small", action="store_true", help="Skip the 3 small software projects")
    parser.add_argument("--no-large", action="store_true", help="Skip the 3 large projects (construction / stadium / banking)")
    parser.add_argument("--no-enterprise", action="store_true", help="Skip enterprise CRM/ERP data (Microsoft, SAP, Oracle, etc.)")
    args = parser.parse_args()
    run(args.base_url, skip_small=args.no_small, skip_large=args.no_large, skip_enterprise=args.no_enterprise)
