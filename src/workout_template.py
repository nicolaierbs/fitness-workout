from pathlib import Path
import argparse
import re

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm

from data_connection import load_table

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)


def sanitize(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", s).strip("_")


def find_pairs_map(paired_sets):
    pairs = {}
    for pair in paired_sets:
        if not any(pair) or len(pair) < 2:
            continue
        a, b = int(pair[0]), int(pair[1])
        pairs.setdefault(a, []).append(b)
        pairs.setdefault(b, []).append(a)
    return pairs


def draw_boxes(c, x, y, sets, box_w=14 * mm, box_h=8 * mm, gap=4 * mm):
    start_x = x
    for i in range(sets):
        c.rect(start_x, y - box_h, box_w, box_h, stroke=1, fill=0)
        c.setFont("Helvetica", 6)
        c.drawCentredString(start_x + box_w / 2, y - box_h + 1.5 * mm, "reps")
        start_x += box_w # + 0.5 * mm
        c.rect(start_x, y - box_h, box_w, box_h, stroke=1, fill=0)
        c.drawCentredString(start_x + box_w / 2, y - box_h + 1.5 * mm, "kg")
        start_x += box_w + gap


def _draw_exercise_entry(c, x_left, y, ex_name, sets, reps, comment, rest, indent=0):
    """
    Draw a single exercise line (name, meta and boxes).
    - c: canvas
    - x_left: left margin x
    - y: baseline y coordinate
    - ex_name: exercise name
    - sets: number of sets
    - reps: number of expected reps
    - comment: optional comment string
    - rest: optional rest seconds
    - indent: additional indent in mm
    Returns: None
    """
    indent_x = x_left + indent
    c.setFont("Helvetica-Bold", 10)
    c.drawString(indent_x, y + 1 * mm, f"{ex_name}")

    meta_parts = []
    if reps is not None:
        reps = reps.replace("-99", "+")
        meta_parts.append(f"{reps} reps")
    if rest is not None:
        meta_parts.append(f"{rest}s rest")
    if comment:
        meta_parts.append(comment)
    if meta_parts:
        c.setFont("Helvetica", 7)
        # c.drawString(x_left + 25 * mm, y, " • ".join(meta_parts))
        c.drawString(indent_x,  y - 2 * mm, ", ".join(meta_parts))

    draw_boxes(c, x_left + 50 * mm, y + 6 * mm, sets)

def render_workout_pdf(workout, exercises_map, out_path: Path):
    page_w, page_h = A4
    margin = 12 * mm
    c = canvas.Canvas(str(out_path), pagesize=A4)
    title = workout.get("name", f"Workout {workout.get('id', '')}")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, page_h - margin, title)
    c.setFont("Helvetica", 9)
    y = page_h - margin - 10 * mm

    exercises = [int(i) for i in workout.get("exercises", [])]
    paired_sets = workout.get("paired_sets", [])
    pairs_map = find_pairs_map(paired_sets)

    rendered = set()
    normal_gap = 7 * mm
    paired_gap = 1 * mm

    for ex_id in exercises:
        if ex_id in rendered:
            continue
        ex = exercises_map.get(ex_id)
        if ex is None:
            ex_name = f"Exercise #{ex_id} (missing)"
            sets = 3
            comment = ""
            rest = None
        else:
            ex_name = ex.get("name", f"#{ex_id}")
            sets = int(ex.get("sets", 3))
            reps = "-".join(map(str, ex.get("reps")))
            comment = (ex.get("comment") or "").strip()
            rest = ex.get("rest")

        if y < margin + 30 * mm:
            c.showPage()
            c.setFont("Helvetica-Bold", 14)
            c.drawString(margin, page_h - margin, title)
            c.setFont("Helvetica", 9)
            y = page_h - margin - 10 * mm

        # draw the exercise row using a single helper so pairs render identically
        _draw_exercise_entry(c, margin, y, ex_name, sets, reps, comment, rest, indent=0)
        y -= 8 * mm

        rendered.add(ex_id)

        partners = [p for p in pairs_map.get(ex_id, []) if p in exercises and p not in rendered]
        if partners:
            for partner_id in partners:
                partner = exercises_map.get(partner_id)
                if partner is None:
                    partner_name = f"Exercise #{partner_id} (missing)"
                    partner_sets = 3
                    partner_comment = ""
                    partner_rest = None
                else:
                    partner_name = partner.get("name", f"#{partner_id}")
                    partner_sets = int(partner.get("sets", 3))
                    partner_reps = "-".join(map(str, partner.get("reps")))
                    partner_comment = (partner.get("comment") or "").strip()
                    partner_rest = partner.get("rest")

                if y < margin + 30 * mm:
                    c.showPage()
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(margin, page_h - margin, title)
                    c.setFont("Helvetica", 9)
                    y = page_h - margin - 10 * mm

                # draw partner line using same helper but indented
                _draw_exercise_entry(c, margin, y, f"{partner_name}", partner_sets, partner_reps, partner_comment, partner_rest) #, indent=6 * mm)
                y -= 7 * mm
                rendered.add(partner_id)

            y -= paired_gap
            
        y -= normal_gap

    c.save()


def main(args):
    exercises_df = load_table("exercises")
    exercises = exercises_df.to_dict(orient="records") if hasattr(exercises_df, "to_dict") else []
    exercises_map = {int(e["id"]): e for e in (exercises or [])}

    workouts_df = load_table("workouts")
    workouts = workouts_df.to_dict(orient="records") if hasattr(workouts_df, "to_dict") else []

    to_render = []
    if args.workout_id is not None:
        for w in workouts:
            if int(w.get("id", -1)) == args.workout_id:
                to_render.append(w)
                break
    else:
        to_render = workouts or []

    if not to_render:
        print("No workouts to render.")
        return

    for w in to_render:
        name = w.get("name", f"workout_{w.get('id','')}")
        fname = f"workout_{w.get('id','')}_{sanitize(name)}.pdf"
        out_path = OUT_DIR / fname
        render_workout_pdf(w, exercises_map, out_path)
        print("written", out_path)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Render workout fill-in PDFs")
    p.add_argument("--workout-id", type=int, help="render single workout id")
    args = p.parse_args()
    main(args)