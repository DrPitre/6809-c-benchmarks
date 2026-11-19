"""Render recorded host and 6809 checks without conflating their results."""
import argparse
import html
import json
from pathlib import Path

BENCHMARKS = ("crc16", "insertion_sort", "mix16")


def render(reports):
    markdown = ["# 6809 C compiler benchmark matrix", ""]
    content = ["<h1>6809 C compiler benchmark matrix</h1>"]

    def paragraph(text):
        markdown.extend([text, ""])
        content.append("<p>" + html.escape(text) + "</p>")

    def table(title, headers, rows):
        markdown.extend(["## " + title, ""])
        content.append("<h2>" + html.escape(title) + "</h2>")
        def mdrow(cells):
            return "| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |"
        markdown.extend([mdrow(headers), mdrow(["---"] * len(headers))])
        markdown.extend(mdrow(row) for row in rows)
        markdown.append("")
        def tr(cells, tag):
            return "<tr>" + "".join(f"<{tag}>" + html.escape(str(c)) + f"</{tag}>" for c in cells) + "</tr>"
        content.append('<div class="scroll"><table><thead>' + tr(headers, "th") +
                       "</thead><tbody>" + "".join(tr(r, "td") for r in rows) + "</tbody></table></div>")

    paragraph("PASS means all four seeds matched independent reference results. Host checks do not measure 6809 performance.")
    for target, title in ((True, "6809 correctness"), (False, "Host correctness")):
        rows = []
        for report in reports:
            if (report.get("target") == "6809 / USIM") != target:
                continue
            statuses = {r["benchmark"]: r["status"] for r in report["rows"]}
            rows.append([report.get("version", report["compiler"]), report.get("target", "Host"), report["flags"]] +
                        [statuses.get(name, "NOT RUN") for name in BENCHMARKS])
        table(title, ["Compiler", "Target", "Flags", *BENCHMARKS], rows)
    sizes = []
    for report in reports:
        if report.get("target") != "6809 / USIM":
            continue
        for row in report["rows"]:
            valid = row["status"] == "PASS"
            sizes.append([report.get("version", report["compiler"]), report["flags"], row["benchmark"],
                          row.get("kernel_code_bytes", "Unavailable") if valid else "Excluded (FAIL)",
                          row.get("loaded_bytes", "Unavailable") if valid else "Excluded (FAIL)", "Not measured"])
    table("6809 sizes (bytes)", ["Compiler", "Flags", "Benchmark", "Kernel code", "Loaded program", "Cycles"], sizes)
    paragraph("Kernel code is the kernel object's code section only, excluding compiler helper routines. Loaded program counts unique S-record data bytes, including startup, runner, initialized data, and linked runtime; it excludes BSS and S-record text overhead. It is not a kernel-only size measurement.")
    paragraph("USIM is bundled with CMOC 0.1.99. This adapter does not measure cycles. Raw JSON, commands, assembly, linker maps, and executables are available in the workflow artifacts.")
    paragraph("Source revisions: " + ", ".join(sorted({r["revision"] for r in reports})))
    content.append('<p><a href="results.json">Raw result data</a> · <a href="matrix.md">Markdown matrix</a></p>')
    document = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<title>6809 compiler matrix</title><style>body{font:16px system-ui;margin:2rem;max-width:90rem}'
                'table{border-collapse:collapse}th,td{border:1px solid #bbb;padding:.6rem;text-align:left}'
                '.scroll{overflow:auto}p{max-width:65rem}</style></head><body>' + "".join(content) + '</body></html>')
    return "\n".join(markdown), document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-reports", type=int)
    args = parser.parse_args()
    reports = [json.loads(p.read_text()) for p in sorted(args.input.glob("*.json"))]
    if not reports or (args.expected_reports is not None and len(reports) != args.expected_reports):
        raise SystemExit("Missing reports; refusing to publish an incomplete matrix")
    markdown, document = render(reports)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "matrix.md").write_text(markdown)
    (args.output / "index.html").write_text(document)
    (args.output / "results.json").write_text(json.dumps(reports, indent=2) + "\n")


if __name__ == "__main__":
    main()
