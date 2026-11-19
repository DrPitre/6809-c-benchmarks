"""Render recorded host and 6809 checks without conflating their results."""
import argparse
import html
import json
from pathlib import Path

BENCHMARKS = ("crc16", "insertion_sort", "mix16")


def validate_shared_sources(reports):
    seen = {}
    for report in reports:
        if report.get("suite") != "kr16":
            continue
        for row in report["rows"]:
            if row["status"] != "PASS":
                continue
            digest = row.get("source_sha256")
            if not digest:
                raise ValueError("Missing kr16 source hash")
            if row["benchmark"] in seen and seen[row["benchmark"]] != digest:
                raise ValueError("kr16 compilers did not receive identical source")
            seen[row["benchmark"]] = digest


def render(reports):
    validate_shared_sources(reports)
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
    for group, title in (("kr16", "Shared kr16: C3 and CMOC runtime correctness"),
                         ("c89", "Original C89: 6809 correctness"), ("host", "Host correctness")):
        rows = []
        for report in reports:
            if report.get("kind") == "compile-compatibility":
                continue
            actual_group = "kr16" if report.get("suite") == "kr16" else ("c89" if report.get("target", "").startswith("6809") else "host")
            if actual_group != group:
                continue
            statuses = {r["benchmark"]: r["status"] for r in report["rows"]}
            rows.append([report.get("version", report["compiler"]), report.get("target", "Host"), report["flags"]] +
                        [statuses.get(name, "NOT RUN") for name in BENCHMARKS])
        table(title, ["Compiler", "Target", "Flags", *BENCHMARKS], rows)
    paragraph("The shared kr16 suite uses identical K&R-compatible source for C3 and CMOC, 16-bit unsigned arithmetic, and one bare-metal harness. Its sort stores values in unsigned words; the original C89 sort uses bytes and 32-bit arithmetic. Compare sizes within a suite, not between suites.")
    sizes = []
    for report in reports:
        if report.get("kind") == "compile-compatibility" or not report.get("target", "").startswith("6809"):
            continue
        for row in report["rows"]:
            valid = row["status"] == "PASS"
            sizes.append([report.get("suite", "c89"), report.get("version", report["compiler"]), report["flags"], row["benchmark"],
                          row.get("kernel_code_bytes", "Unavailable") if valid else "Excluded (FAIL)",
                          row.get("loaded_bytes", "Unavailable") if valid else "Excluded (FAIL)", "Not measured"])
    table("6809 sizes (bytes)", ["Suite", "Compiler", "Flags", "Benchmark", "Kernel code", "Loaded program", "Cycles"], sizes)
    paragraph("Kernel code excludes compiler helper routines. Loaded program includes the harness and linked helpers (plus the C library runner for c89), excluding BSS and S-record text overhead. The kr16 harness passes each seed in D and on the stack for the two calling conventions. C3 stack-check calls use a no-op stub; these bounded kernels have a reserved 4 KiB stack and no static storage. These are bare-metal kernel tests, not OS-9 application tests.")
    compatibility = [r for r in reports if r.get("kind") == "compile-compatibility"]
    if compatibility:
        content.append("<details><summary>Original C89 compatibility diagnostics</summary>")
        rows = []
        probes = []
        for report in compatibility:
            statuses = {r["benchmark"]: r["status"] for r in report["rows"]}
            rows.append([report.get("version", report["compiler"]), report["target"], report["flags"],
                         report.get("smoke_link", "ERROR")] + [statuses.get(name, "NOT RUN") for name in BENCHMARKS])
            probes.extend([report["version"], report["flags"], p["name"], p["status"]]
                          for p in report.get("probes", []))
        table("C3 compile compatibility (not executed)",
              ["Compiler", "Target", "Flags", "Smoke link", *BENCHMARKS], rows)
        table("C3 language probes", ["Compiler", "Flags", "Feature", "Compile result"], probes)
        paragraph("C3 is tested against the unchanged C89 kernels. COMPILE FAIL is an observed compatibility result, not a failed runtime checksum. ACCEPTED probes were compiled, not executed. C3 currently lacks limits.h and rejects unsigned short, unsigned long, and U-suffixed constants. These limitations apply to the original C89 suite; the shared kr16 results above execute real C3-generated code.")
        paragraph("The original compatibility check records rejections; the shared kr16 runtime check requires passing checksums. Infrastructure failures still fail CI. Full diagnostics are included in the raw JSON and workflow artifacts.")
        content.append("</details>")
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
