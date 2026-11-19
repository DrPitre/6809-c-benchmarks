"""Render recorded checks as a Markdown matrix and a static Pages report."""
import argparse
import html
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("input", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--expected-reports", type=int)
args = parser.parse_args()
reports = [json.loads(p.read_text()) for p in sorted(args.input.glob("*.json"))]
if args.expected_reports is not None and len(reports) != args.expected_reports:
    raise SystemExit("Incomplete report set; refusing to publish a partial matrix")
if not reports:
    raise SystemExit("No reports found; refusing to publish an empty matrix")
lines = ["# 6809 C compiler benchmark matrix", "",
         "Host correctness only. No 6809 compiler measurements are available yet.", "",
         "PASS means all four seed checks matched independent reference results.", "",
         "| Compiler | Flags | CRC16 | Insertion sort | Mix16 |",
         "| --- | --- | --- | --- | --- |"]
for report in reports:
    statuses = {row["benchmark"]: row["status"] for row in report["rows"]}
    cells = [report["compiler"], report["flags"]] + [
        statuses.get(name, "NOT RUN") for name in ("crc16", "insertion_sort", "mix16")]
    lines.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
lines += ["", "6809 cycles, code size, and runtime size: **not measured**.", "",
          "Source revisions: " + ", ".join(sorted({r["revision"] for r in reports})), ""]
markdown = "\n".join(lines)
args.output.mkdir(parents=True, exist_ok=True)
(args.output / "matrix.md").write_text(markdown)
# Generate a real HTML table without third-party dependencies.
header = "".join("<th>" + html.escape(c.strip()) + "</th>" for c in lines[6].strip("|").split("|"))
body = ""
for line in lines[8:8 + len(reports)]:
    body += "<tr>" + "".join("<td>" + html.escape(c.strip()) + "</td>" for c in line.strip("|").split("|")) + "</tr>"
(args.output / "index.html").write_text(
    '<!doctype html><html lang="en"><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1">'
    '<title>6809 compiler matrix</title><style>body{font:16px system-ui;margin:2rem;}'
    'table{border-collapse:collapse}th,td{border:1px solid #bbb;padding:.6rem;text-align:left}'
    '.scroll{overflow:auto}</style><h1>6809 C compiler benchmark matrix</h1>'
    '<p>Host correctness only. No 6809 measurements are available yet.</p>'
    '<p>PASS means all four seeds matched independent reference results.</p>'
    '<div class="scroll"><table><thead><tr>' + header + '</tr></thead><tbody>' + body +
    '</tbody></table></div><p>6809 cycles, code size, runtime size: not measured.</p>'
    '<p>Source revisions: ' + html.escape(', '.join(sorted({r['revision'] for r in reports}))) +
    '</p><a href="matrix.md">Download Markdown matrix</a></html>')
