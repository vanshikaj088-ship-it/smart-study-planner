from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
from pathlib import Path
from html import escape

BASE = Path(__file__).parent


def create_plan(hours, session, break_time, subjects):
    remaining = int(hours * 60)
    plan = []
    index = 0

    while remaining > 0:
        duration = min(session, remaining)

        plan.append({
            "type": "study",
            "name": subjects[index % len(subjects)],
            "minutes": duration
        })
        remaining -= duration
        index += 1

        if remaining > 0:
            pause = min(break_time, remaining)
            plan.append({
                "type": "break",
                "name": "Relax and recharge",
                "minutes": pause
            })
            remaining -= pause

    return plan


def build_result(plan):
    study = sum(x["minutes"] for x in plan if x["type"] == "study")
    breaks = sum(x["minutes"] for x in plan if x["type"] == "break")
    sessions = sum(1 for x in plan if x["type"] == "study")

    items = ""

    for number, item in enumerate(plan, 1):
        is_study = item["type"] == "study"
        css_class = "study-item" if is_study else "break-item"
        tag = "STUDY SESSION" if is_study else "BREAK"
        symbol = "✦" if is_study else "☕"

        items += f"""
        <div class="schedule-item {css_class}">
            <div class="item-number">{number:02}</div>
            <div class="item-info">
                <span class="item-tag">{tag}</span>
                <h3>{escape(item["name"])}</h3>
            </div>
            <strong>{item["minutes"]} min</strong>
            <span class="item-symbol">{symbol}</span>
        </div>
        """

    return f"""
    <section class="results">
        <div class="result-heading">
            <div>
                <span class="eyebrow">YOUR PERSONAL PLAN</span>
                <h2>Your timetable is ready!</h2>
                <p>A little progress every day adds up.</p>
            </div>
            <span class="success-mark">✓</span>
        </div>

        <div class="stats">
            <div class="stat-card">
                <span>Total study time</span>
                <strong>{study // 60}h {study % 60}m</strong>
            </div>
            <div class="stat-card">
                <span>Break time</span>
                <strong>{breaks} min</strong>
            </div>
            <div class="stat-card">
                <span>Study sessions</span>
                <strong>{sessions}</strong>
            </div>
        </div>

        <h3 class="timeline-title">Your study schedule</h3>
        <div class="timeline">{items}</div>
        <a class="edit-link" href="/">← Make another plan</a>
    </section>
    """


class PlannerHandler(BaseHTTPRequestHandler):

    def send_page(self, page, status=200, content_type="text/html; charset=utf-8"):
        data = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/style.css":
            css = (BASE / "style.css").read_text(encoding="utf-8")
            self.send_page(css, content_type="text/css; charset=utf-8")
            return

        page = (BASE / "index.html").read_text(encoding="utf-8")
        self.send_page(page)

    def do_POST(self):
        if self.path != "/generate":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        raw_data = self.rfile.read(length).decode("utf-8")
        values = parse_qs(raw_data)

        try:
            hours = float(values.get("hours", ["4"])[0])
            session = int(values.get("session", ["45"])[0])
            break_time = int(values.get("break", ["10"])[0])

            subject_text = values.get("subjects", ["General Study"])[0]
            subjects = [s.strip() for s in subject_text.split(",") if s.strip()]

            if not 1 <= hours <= 12:
                raise ValueError("Available hours must be between 1 and 12.")
            if not 15 <= session <= 120:
                raise ValueError("Study sessions must be 15–120 minutes.")
            if not 5 <= break_time <= 30:
                raise ValueError("Breaks must be 5–30 minutes.")
            if not subjects:
                raise ValueError("Please enter at least one subject.")

            plan = create_plan(hours, session, break_time, subjects)
            result = build_result(plan)

        except ValueError as error:
            result = f"""
            <div class="error-message">
                <h3>Check your details</h3>
                <p>{escape(str(error))}</p>
                <a href="/">Go back</a>
            </div>
            """

        page = (BASE / "index.html").read_text(encoding="utf-8")
        page = page.replace("<!-- RESULTS -->", result)
        self.send_page(page)

    def log_message(self, format, *args):
        print(format % args)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8000), PlannerHandler)
    print("Smart Study Planner is running at http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()