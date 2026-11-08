"""Auto-fill week (CREW-5): OR-Tools CP-SAT proposes crew assignments.

Hard constraints: required certifications, published weekly hours, no overlap with any
existing booking (any employer), slot headcount, and the CREW-3 rules (minimum rest
between shifts, maximum consecutive days, maximum weekly hours). The objective fills as
many open spots as possible, then prefers workers holding the slot's preferred cert.
Proposals are saved as ghost assignments ('proposed') for the manager to accept.
"""

from datetime import date, datetime, timedelta
from ortools.sat.python import cp_model
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from .crew import bookings, covers, hours_by_weekday, overlapping, rules_for, slot_times
from .market_models import CrewAssignment, CrewMember, CrewSlot
from .wallet import held

STATUS = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
    cp_model.UNKNOWN: "UNKNOWN",
}


def week_slots(db: Session, org_id: str, start: date) -> list[CrewSlot]:
    return list(
        db.scalars(
            select(CrewSlot)
            .where(CrewSlot.org_id == org_id, CrewSlot.day >= start, CrewSlot.day < start + timedelta(days=7))
            .order_by(CrewSlot.day, CrewSlot.start_minute)
        )
    )


def clear_proposals(db: Session, slots: list[CrewSlot]) -> None:
    ids = [s.id for s in slots]
    if ids:
        db.execute(
            delete(CrewAssignment).where(
                CrewAssignment.slot_id.in_(ids), CrewAssignment.status == "proposed"
            )
        )


def autofill(db: Session, org_id: str, start: date, seconds: float = 5.0) -> dict:
    rules = rules_for(db, org_id)
    slots = week_slots(db, org_id, start)
    clear_proposals(db, slots)
    db.flush()
    crew = list(db.scalars(select(CrewMember.user_id).where(CrewMember.org_id == org_id)))
    filled = {
        s.id: set(
            db.scalars(
                select(CrewAssignment.user_id).where(
                    CrewAssignment.slot_id == s.id, CrewAssignment.status == "assigned"
                )
            )
        )
        for s in slots
    }
    open_spots = {s.id: max(0, s.needed - len(filled[s.id])) for s in slots}
    times = {s.id: slot_times(s) for s in slots}
    model = cp_model.CpModel()
    x: dict[tuple[str, str], cp_model.IntVar] = {}
    existing: dict[str, list] = {}
    for w in crew:
        hours = hours_by_weekday(db, w)
        wallet = held(db, w, start)
        shifts = bookings(db, w, start - timedelta(days=7), start + timedelta(days=7))
        existing[w] = shifts
        for s in slots:
            if not open_spots[s.id] or w in filled[s.id]:
                continue
            if any(c not in wallet for c in s.required_certs) or not covers(hours, s):
                continue
            if overlapping(shifts, times[s.id]):
                continue
            st, en = times[s.id]
            # Rest against shifts already booked is a hard rule for the solver.
            if any(
                0 <= (st - e).total_seconds() / 3600 < rules.min_rest_hours
                or 0 <= (b - en).total_seconds() / 3600 < rules.min_rest_hours
                for b, e, _ in shifts
            ):
                continue
            x[w, s.id] = model.NewBoolVar(f"x_{w}_{s.id}")
    for s in slots:
        vars_ = [v for (w, sid), v in x.items() if sid == s.id]
        if vars_:
            model.Add(sum(vars_) <= open_spots[s.id])
    week_end = datetime.combine(start + timedelta(days=7), datetime.min.time())
    week_begin = datetime.combine(start, datetime.min.time())
    for w in crew:
        mine = [(sid, v) for (ww, sid), v in x.items() if ww == w]
        if not mine:
            continue
        # No overlaps and minimum rest between proposed shifts.
        for i, (a, va) in enumerate(mine):
            for b, vb in mine[i + 1 :]:
                a0, a1 = times[a]
                b0, b1 = times[b]
                gap = max((b0 - a1).total_seconds(), (a0 - b1).total_seconds()) / 3600
                if gap < rules.min_rest_hours:
                    model.Add(va + vb <= 1)
        # Weekly hours, counting shifts already booked this week.
        booked_minutes = sum(
            int((min(e, week_end) - max(b, week_begin)).total_seconds() // 60)
            for b, e, _ in existing[w]
            if e > week_begin and b < week_end
        )
        model.Add(
            sum(int((times[sid][1] - times[sid][0]).total_seconds() // 60) * v for sid, v in mine)
            <= max(0, rules.max_weekly_hours * 60 - booked_minutes)
        )
        # Maximum consecutive working days (window of max+1 days holds at most max).
        worked = {b.date() for b, _, _ in existing[w]}
        day_vars = {}
        for offset in range(-rules.max_consecutive_days, 7):
            d = start + timedelta(days=offset)
            todays = [v for sid, v in mine if times[sid][0].date() == d]
            if d in worked:
                day_vars[d] = 1
            elif todays:
                y = model.NewBoolVar(f"y_{w}_{d}")
                for v in todays:
                    model.Add(y >= v)
                day_vars[d] = y
        span = rules.max_consecutive_days + 1
        for offset in range(-rules.max_consecutive_days, 7):
            window = [day_vars.get(start + timedelta(days=offset + k), 0) for k in range(span)]
            if any(not isinstance(v, int) for v in window):
                model.Add(sum(window) <= rules.max_consecutive_days)
    preferred = {s.id: s.preferred_cert for s in slots}
    wallets = {w: held(db, w, start) for w in crew}
    model.Maximize(
        sum(
            v * (1000 + (50 if preferred[sid] and preferred[sid] in wallets[w] else 0))
            for (w, sid), v in x.items()
        )
    )
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_workers = 8
    status = solver.Solve(model)
    proposed = 0
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (w, sid), v in x.items():
            if solver.Value(v):
                db.add(CrewAssignment(slot_id=sid, user_id=w, status="proposed"))
                proposed += 1
    db.flush()
    unfilled = []
    for s in slots:
        count = len(
            db.scalars(select(CrewAssignment.id).where(CrewAssignment.slot_id == s.id)).all()
        )
        if count < s.needed:
            unfilled.append(s.id)
    db.commit()
    return {"proposed": proposed, "unfilled_slot_ids": unfilled, "solver_status": STATUS.get(status, "UNKNOWN")}
