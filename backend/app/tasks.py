"""Celery tasks — CPU-heavy or I/O-heavy work offloaded from request handlers.

These run in Celery worker processes and store results in Redis.
The FastAPI endpoints submit tasks, then the frontend polls for results.
"""

import io
import json
import logging
from uuid import UUID

from app.celery_app import celery
from app.services.monte_carlo import run_monte_carlo

logger = logging.getLogger(__name__)


# ─── Monte Carlo Simulation ───────────────────────────────────────

@celery.task(name="run_monte_carlo_task", bind=True, max_retries=1)
def run_monte_carlo_task(self, tasks: list[dict], dependencies: list[dict], iterations: int = 1000):
    """Run Monte Carlo simulation in a worker (CPU-bound)."""
    try:
        result = run_monte_carlo(tasks, dependencies, iterations)
        return {
            "iterations": result.iterations,
            "duration": {
                "mean": result.duration_mean, "min": result.duration_min, "max": result.duration_max,
                "p10": result.duration_p10, "p50": result.duration_p50, "p75": result.duration_p75,
                "p90": result.duration_p90, "p95": result.duration_p95,
            },
            "cost": {"mean": result.cost_mean, "p50": result.cost_p50, "p90": result.cost_p90},
            "histogram": result.histogram,
        }
    except Exception as exc:
        logger.exception("Monte Carlo task failed")
        raise self.retry(exc=exc, countdown=5)


# ─── PDF Report Generation ────────────────────────────────────────

@celery.task(name="generate_pdf_report_task", bind=True, max_retries=1)
def generate_pdf_report_task(self, project_data: dict, tasks_data: list[dict], risks_data: list[dict]):
    """Generate a PDF report in a worker and return base64-encoded bytes."""
    import base64
    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"Project Report: {project_data['name']}", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, (
            f"Status: {project_data['status']} | "
            f"Approach: {project_data['approach']} | "
            f"Budget: ${project_data.get('budget', 0):,.0f}"
        ), ln=True)
        pdf.ln(5)

        # Tasks table
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, f"Tasks ({len(tasks_data)})", ln=True)
        pdf.set_font("Helvetica", "B", 8)
        for header, width in [("Title", 70), ("Status", 25), ("Priority", 25), ("Duration", 25), ("Cost", 25)]:
            pdf.cell(width, 6, header, 1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 8)
        for t in tasks_data:
            pdf.cell(70, 6, str(t.get("title", ""))[:35], 1)
            pdf.cell(25, 6, str(t.get("status", "")), 1)
            pdf.cell(25, 6, str(t.get("priority", "")), 1)
            pdf.cell(25, 6, f"{t.get('duration_days') or '-'}d", 1)
            pdf.cell(25, 6, f"${t.get('planned_cost') or 0:,.0f}", 1)
            pdf.ln()

        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, f"Risks ({len(risks_data)})", ln=True)
        pdf.set_font("Helvetica", "B", 8)
        for header, width in [("Title", 60), ("Category", 30), ("Probability", 25), ("Impact", 25), ("Strategy", 25)]:
            pdf.cell(width, 6, header, 1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 8)
        for r in risks_data:
            pdf.cell(60, 6, str(r.get("title", ""))[:30], 1)
            pdf.cell(30, 6, str(r.get("category", "")), 1)
            pdf.cell(25, 6, str(r.get("probability", "")), 1)
            pdf.cell(25, 6, str(r.get("impact", "")), 1)
            pdf.cell(25, 6, str(r.get("strategy", "")), 1)
            pdf.ln()

        raw = pdf.output()
        return {"pdf_base64": base64.b64encode(raw).decode("ascii"), "filename": project_data["name"]}
    except Exception as exc:
        logger.exception("PDF generation task failed")
        raise self.retry(exc=exc, countdown=5)


# ─── CSV Import ───────────────────────────────────────────────────

@celery.task(name="import_csv_task", bind=True, max_retries=1)
def import_csv_task(self, csv_text: str, project_id: str):
    """Parse CSV and return task dicts to be bulk-inserted by the caller.

    We do the parsing (CPU-bound for large files) in the worker,
    and return clean dicts that the endpoint can INSERT.
    """
    import csv
    try:
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = []
        for row in reader:
            title = row.get("title", "").strip()
            if not title:
                continue
            rows.append({
                "project_id": project_id,
                "title": title,
                "description": row.get("description", "").strip() or None,
                "status": row.get("status", "backlog").strip().lower() or "backlog",
                "priority": row.get("priority", "medium").strip().lower() or "medium",
                "duration_days": float(row["duration_days"]) if row.get("duration_days") else None,
                "story_points": int(row["story_points"]) if row.get("story_points") else None,
                "planned_cost": float(row["planned_cost"]) if row.get("planned_cost") else None,
            })
        return {"rows": rows, "count": len(rows)}
    except Exception as exc:
        logger.exception("CSV import task failed")
        raise self.retry(exc=exc, countdown=5)
