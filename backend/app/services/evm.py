"""Earned Value Management (EVM) calculator.

Metrics:
  PV  = Planned Value (budgeted cost of work scheduled)
  EV  = Earned Value (budgeted cost of work performed)
  AC  = Actual Cost (actual cost of work performed)
  BAC = Budget at Completion
  SV  = Schedule Variance = EV - PV
  CV  = Cost Variance = EV - AC
  SPI = Schedule Performance Index = EV / PV
  CPI = Cost Performance Index = EV / AC
  EAC = Estimate at Completion = BAC / CPI
  ETC = Estimate to Complete = EAC - AC
  VAC = Variance at Completion = BAC - EAC
  TCPI = To-Complete Performance Index = (BAC - EV) / (BAC - AC)
"""

from dataclasses import dataclass


@dataclass
class EVMResult:
    bac: float  # Budget at Completion
    pv: float   # Planned Value
    ev: float   # Earned Value
    ac: float   # Actual Cost
    sv: float   # Schedule Variance
    cv: float   # Cost Variance
    spi: float  # Schedule Performance Index
    cpi: float  # Cost Performance Index
    eac: float  # Estimate at Completion
    etc: float  # Estimate to Complete
    vac: float  # Variance at Completion
    tcpi: float # To-Complete Performance Index
    percent_complete: float
    percent_spent: float


def compute_evm(
    tasks: list[dict],
    project_budget: float | None = None,
) -> EVMResult:
    """Compute EVM metrics from task data.

    Each task dict should have:
      planned_cost: float (budgeted cost)
      actual_cost: float (actual cost spent)
      status: str (done = earned)
      completion_pct: float (0-100, optional for partial credit)
    """
    bac = project_budget or sum(t.get("planned_cost", 0) or 0 for t in tasks)
    pv = sum(t.get("planned_cost", 0) or 0 for t in tasks)  # all planned work
    ev = 0.0
    ac = sum(t.get("actual_cost", 0) or 0 for t in tasks)

    for t in tasks:
        planned = t.get("planned_cost", 0) or 0
        status = t.get("status", "")
        if status == "done":
            ev += planned
        elif status in ("in_progress", "in_review"):
            ev += planned * 0.5  # 50% rule for in-progress
        # backlog/todo/blocked = 0 earned

    # Avoid division by zero
    spi = ev / pv if pv > 0 else 0
    cpi = ev / ac if ac > 0 else 0
    sv = ev - pv
    cv = ev - ac
    eac = bac / cpi if cpi > 0 else bac
    etc = eac - ac if eac > ac else 0
    vac = bac - eac
    tcpi = (bac - ev) / (bac - ac) if (bac - ac) > 0 else 0
    pct_complete = (ev / bac * 100) if bac > 0 else 0
    pct_spent = (ac / bac * 100) if bac > 0 else 0

    return EVMResult(
        bac=round(bac, 2),
        pv=round(pv, 2),
        ev=round(ev, 2),
        ac=round(ac, 2),
        sv=round(sv, 2),
        cv=round(cv, 2),
        spi=round(spi, 4),
        cpi=round(cpi, 4),
        eac=round(eac, 2),
        etc=round(etc, 2),
        vac=round(vac, 2),
        tcpi=round(tcpi, 4),
        percent_complete=round(pct_complete, 1),
        percent_spent=round(pct_spent, 1),
    )
