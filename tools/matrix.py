"""Render recorded host and 6809 checks without conflating their results."""
import argparse
import html
import json
import re
from dataclasses import dataclass
from urllib.parse import quote
from shared_suite import BENCHMARKS, LABELS, PURPOSES, sources
from pathlib import Path

C89_BENCHMARKS = ("crc16", "insertion_sort", "mix16")
COMPILERS = ("C3", "CMOC", "LLVM", "VBCC")


@dataclass(frozen=True)
class SourceLink:
    label: str
    url: str

    def __str__(self):
        return self.label


def source_link(label, path, revision):
    ref = revision if re.fullmatch(r"[0-9a-f]{40}", revision) else "main"
    return SourceLink(label, "https://github.com/DrPitre/6809-c-benchmarks/blob/" + ref + "/" + quote(path, safe="/"))


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

    def table(title, headers, rows, highlights=None, grouped=False):
        markdown.extend(["## " + title, ""])
        content.append("<h2>" + html.escape(title) + "</h2>")
        def mdrow(cells):
            return "| " + " | ".join(("[" + c.label + "](" + c.url + ")" if isinstance(c, SourceLink) else str(c)).replace("|", "\\|").replace("\n", " ") for c in cells) + " |"
        markdown.extend([mdrow(headers), mdrow(["---"] * len(headers))])
        spans = {}
        if grouped:
            for i, row in enumerate(rows):
                if i == 0 or row[0] != rows[i - 1][0]:
                    spans[i] = 1
                    start = i
                else:
                    spans[start] += 1
        markdown.extend(mdrow(([""] + list(row[1:])) if grouped and i not in spans else row)
                        for i, row in enumerate(rows))
        markdown.append("")
        def tr(cells, tag, row_index=-1):
            result = []
            for column, cell in enumerate(cells):
                if grouped and row_index >= 0 and column == 0 and row_index not in spans:
                    continue
                cell_tag = "th" if grouped and row_index >= 0 and column == 0 else tag
                attributes = (' rowspan="' + str(spans[row_index]) + '" scope="rowgroup"') if grouped and row_index >= 0 and column == 0 else ""
                value = html.escape(str(cell))
                if isinstance(cell, SourceLink):
                    value = '<a href="' + html.escape(cell.url, quote=True) + '">' + value + '</a>'
                classes = []
                if isinstance(cell, int):
                    classes.append("number")
                if highlights and (row_index, column) in highlights:
                    classes.append("smaller")
                    value = "<strong>" + value + "</strong>"
                if cell == "PASS":
                    classes.append("pass")
                elif cell in ("FAIL", "COMPILE FAIL", "Excluded (FAIL)"):
                    classes.append("fail")
                result.append(f'<{cell_tag}' + attributes + ' class="' + " ".join(classes) + '">' + value + f'</{cell_tag}>')
            return ('<tr class="group-start">' if grouped and row_index in spans else "<tr>") + "".join(result) + "</tr>"
        content.append('<div class="scroll"><table><thead>' + tr(headers, "th") +
                       "</thead><tbody>" + "".join(tr(r, "td", i) for i, r in enumerate(rows)) + "</tbody></table></div>")

    paragraph("C3, CMOC, LLVM-MC6809, and vbcc, side by side. Identical kr16 sources run on the same 6809 simulator. Sizes are in bytes; lower is smaller. Timing is not measured.")
    shared = {}
    for report in reports:
        if report.get("suite") != "kr16":
            continue
        compiler = report["compiler"].upper()
        if compiler not in COMPILERS:
            continue
        enabled = report["flags"] in ("optimizer on", "-O2")
        for row in report["rows"]:
            key = (row["benchmark"], enabled, compiler)
            if key in shared:
                raise ValueError("Duplicate shared compiler configuration")
            shared[key] = row

    shared_revision = next((r["revision"] for r in reports if r.get("suite") == "kr16"), "local")
    labels = {name: source_link(LABELS[name], "benchmarks/kr16/" + name + ".c", shared_revision) for name in BENCHMARKS}
    for metric, title in (("kernel_code_bytes", "Benchmark code size"),
                          ("loaded_bytes", "Complete test program size")):
        rows, highlights = [], set()
        for name in BENCHMARKS:
            for enabled in (True, False):
                values = []
                for compiler in COMPILERS:
                    result = shared.get((name, enabled, compiler))
                    if result is None:
                        values.append("Not run")
                    elif result["status"] != "PASS":
                        values.append("Excluded (FAIL)")
                    else:
                        values.append(result.get(metric, "Unavailable"))
                difference = "—"
                if all(isinstance(v, int) for v in values):
                    ordered = sorted(values)
                    winners = [i for i, value in enumerate(values) if value == ordered[0]]
                    if len(winners) > 1:
                        difference = "Tie: " + "/".join(COMPILERS[i] for i in winners)
                    else:
                        difference = COMPILERS[winners[0]] + " by " + str(ordered[1] - ordered[0]) + " B"
                    if len(winners) != len(values):
                        highlights.update((len(rows), i + 2) for i in winners)
                rows.append([labels[name], "On" if enabled else "Off", *values, difference])
        table(title, ["Benchmark", "Optimization", *COMPILERS, "Smallest"], rows, highlights, grouped=True)
    paragraph("Benchmark code size measures all test-supplied functions, including separately compiled support functions. Complete test program size also includes compiler helpers and the test runner, so its ranking can differ. Both measure bytes loaded into memory, excluding uninitialized storage and file-format overhead. Shaded bold values mark the smallest result; the byte gap is to the next-smallest compiler; failed or missing results are never ranked.")
    paragraph("Optimization on means C3's default optimizer and CMOC/LLVM -O2 plus vbcc -O=1023 (vc -O2); off disables C3's optimizer and uses CMOC/LLVM -O0 and vbcc -O=0. vbcc uses its standard assembler branch/offset relaxation at both settings. These settings do not imply identical optimization passes.")
    statuses = []
    for name in BENCHMARKS:
        for enabled in (True, False):
            statuses.append([labels[name], "On" if enabled else "Off"] +
                            [shared.get((name, enabled, compiler), {}).get("status", "NOT RUN")
                             for compiler in COMPILERS])
    table("Shared-suite correctness", ["Benchmark", "Optimization", *COMPILERS], statuses, grouped=True)
    failures = []
    for report in reports:
        if report.get("suite") != "kr16":
            continue
        for row in report["rows"]:
            if row["status"] != "PASS":
                failures.append([labels.get(row["benchmark"], row["benchmark"]), report["compiler"], report["flags"],
                                 row.get("failure_stage", "Unknown"), row.get("error", "Checksum mismatch")])
    if failures:
        table("Failures requiring investigation", ["Benchmark", "Compiler", "Flags", "Stage", "Diagnostic"], sorted(failures, key=lambda row: str(row[0])), grouped=True)
    paragraph("PASS means all four seeds match independent reference results. Each linked benchmark name groups its optimization settings. Supporting files are linked under Test purposes and source files. The shared sort uses unsigned words and 16-bit arithmetic; it is a distinct workload from the original C89 byte sort.")
    content.append("<details><summary>Test purposes and source files</summary>")
    source_rows = []
    for name in BENCHMARKS:
        for index, path in enumerate(sources(name)):
            source_rows.append([LABELS[name], PURPOSES[name] if index == 0 else "Separately compiled supporting function",
                                source_link(path, "benchmarks/kr16/" + path, shared_revision)])
    table("Test sources", ["Benchmark", "What it exercises", "Source"], source_rows)
    original_revision = next((r["revision"] for r in reports if r.get("suite") != "kr16"), None)
    if original_revision:
        table("Original C89 sources", ["Benchmark", "Source"], [
            [LABELS[name], source_link(name + ".c", "benchmarks/" + name + ".c", original_revision)]
            for name in C89_BENCHMARKS])
    content.append("</details>")
    content.append("<details><summary>Compiler versions, original-suite results, and measurement details</summary>")

    for group, title in (("kr16", "Shared kr16: compiler versions and runtime correctness"),
                         ("c89", "Original C89: 6809 correctness"), ("host", "Host correctness")):
        rows = []
        names = BENCHMARKS if group == "kr16" else C89_BENCHMARKS
        for report in reports:
            if report.get("kind") == "compile-compatibility":
                continue
            actual_group = "kr16" if report.get("suite") == "kr16" else ("c89" if report.get("target", "").startswith("6809") else "host")
            if actual_group != group:
                continue
            statuses = {r["benchmark"]: r["status"] for r in report["rows"]}
            rows.append([report.get("version", report["compiler"]), report.get("target", "Host"), report["flags"]] +
                        [statuses.get(name, "NOT RUN") for name in names])
        table(title, ["Compiler", "Target", "Flags", *names], rows)
    paragraph("The shared kr16 suite uses identical K&R-compatible source for C3, CMOC, LLVM, and vbcc, 16-bit unsigned arithmetic, and one bare-metal harness. Its sort stores values in unsigned words; the original C89 sort uses bytes and 32-bit arithmetic. Compare sizes within a suite, not between suites.")
    sizes = []
    for report in reports:
        if report.get("kind") == "compile-compatibility" or not report.get("target", "").startswith("6809"):
            continue
        for row in report["rows"]:
            valid = row["status"] == "PASS"
            sizes.append([source_link(report.get("suite", "c89") + ": " + LABELS.get(row["benchmark"], row["benchmark"]),
                                      ("benchmarks/kr16/" if report.get("suite") == "kr16" else "benchmarks/") + row["benchmark"] + ".c", report["revision"]),
                          report.get("version", report["compiler"]), report["flags"],
                          row.get("kernel_code_bytes", "Unavailable") if valid else "Excluded (FAIL)",
                          row.get("loaded_bytes", "Unavailable") if valid else "Excluded (FAIL)", "Not measured"])
    table("6809 sizes (bytes)", ["Benchmark", "Compiler", "Flags", "Benchmark code", "Complete test program", "Cycles"], sorted(sizes, key=lambda row: str(row[0])), grouped=True)
    paragraph("Benchmark code excludes compiler helper routines. Complete test program size includes the test runner and linked helpers (plus the C library runner for c89), excluding BSS and S-record text overhead. The kr16 harness passes each seed in D and on the stack for C3/CMOC; LLVM's branch moves the argument and result through X. LLVM reserves 24 bytes of direct-page register scratch RAM, excluded from complete test program bytes. Its release is pinned to 1.0, with plain 6809 code, -std=c89, -fno-pie, and no LTO. C3 stack-check calls use a no-op stub; these bounded benchmark functions have a reserved 4 KiB stack and no static storage. These are bare-metal benchmark tests, not OS-9 application tests.")
    content.append("</details>")
    compatibility = [r for r in reports if r.get("kind") == "compile-compatibility"]
    if compatibility:
        content.append("<details><summary>Original C89 compatibility diagnostics</summary>")
        rows = []
        probes = []
        for report in compatibility:
            statuses = {r["benchmark"]: r["status"] for r in report["rows"]}
            rows.append([report.get("version", report["compiler"]), report["target"], report["flags"],
                         report.get("smoke_link", "ERROR")] + [statuses.get(name, "NOT RUN") for name in C89_BENCHMARKS])
            probes.extend([report["version"], report["flags"], p["name"], p["status"]]
                          for p in report.get("probes", []))
        table("C3 compile compatibility (not executed)",
              ["Compiler", "Target", "Flags", "Smoke link", *C89_BENCHMARKS], rows)
        table("C3 language probes", ["Compiler", "Flags", "Feature", "Compile result"], probes)
        paragraph("C3 is tested against the unchanged C89 benchmark functions. COMPILE FAIL is an observed compatibility result, not a failed runtime checksum. ACCEPTED probes were compiled, not executed. C3 currently lacks limits.h and rejects unsigned short, unsigned long, and U-suffixed constants. These limitations apply to the original C89 suite; the shared kr16 results above execute real C3-generated code.")
        paragraph("The original compatibility check records rejections; the shared kr16 runtime check requires passing checksums. Infrastructure failures still fail CI. Full diagnostics are included in the raw JSON and workflow artifacts.")
        content.append("</details>")
    paragraph("USIM is bundled with CMOC 0.1.99. This adapter does not measure cycles. Raw JSON, commands, assembly, linker maps, and executables are available in the workflow artifacts.")
    paragraph("Source revisions: " + ", ".join(sorted({r["revision"] for r in reports})))
    content.append('<p><a href="results.json">Raw result data</a> · <a href="matrix.md">Markdown matrix</a></p>')
    document = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<title>6809 compiler matrix</title><style>body{font:16px/1.55 system-ui;margin:2rem auto;padding:0 1.25rem;max-width:72rem;color:#172b3a;background:#f8fafc}h1{line-height:1.15}h2{margin-top:2rem;font-size:1.25rem}'
                'table{border-collapse:collapse;width:100%;background:white}th,td{border-bottom:1px solid #dbe3eb;padding:.65rem .8rem;text-align:left;white-space:nowrap}th{background:#eaf0f6;font-size:.9rem}td:nth-child(2){white-space:normal}.number{font-variant-numeric:tabular-nums;text-align:right}.smaller{background:#e0f2e9;color:#15583a}.pass{color:#14532d;background:#dcfce7;font-weight:700}.fail{color:#b91c1c;background:#fee2e2;font-weight:700}tr.group-start{border-top:2px solid #bccbd8}tbody th[scope=rowgroup]{vertical-align:middle;background:#f0f5fa;font-size:1rem}tbody th a{white-space:normal}'
                '.scroll{overflow:auto;border:1px solid #dbe3eb;border-radius:8px}p{max-width:65rem}details{margin:1.5rem 0;padding:1rem;background:white;border:1px solid #dbe3eb;border-radius:8px}summary{cursor:pointer;font-weight:600}a{color:#145daa}@media(max-width:600px){body{margin:1rem auto;padding:0 .75rem}th,td{padding:.5rem}} </style></head><body>' + "".join(content) + '</body></html>')
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
