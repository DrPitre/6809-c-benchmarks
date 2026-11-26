"""Render recorded host and 6809 checks without conflating their results."""
from assembly_report import SIZE_CONFIGURATIONS, size_configurations, size_assembly_url, COMPILERS, comparison_compilers, assembly_url, publish_assembly, changed_cmoc_results, cmoc_diff_url, publish_cmoc_diffs
import argparse
import html
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote
from shared_suite import BENCHMARKS, LABELS, PURPOSES, sources
from pathlib import Path

C89_BENCHMARKS = ("crc16", "insertion_sort", "mix16")


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


def overall_sizes(shared, enabled, compilers=None):
    """Equal-weight geometric mean, restricted to the common passing workload."""
    compilers = compilers or COMPILERS
    eligible = []
    for name in BENCHMARKS:
        results = [shared.get((name, enabled, compiler), {}) for compiler in compilers]
        if all(row.get("status") == "PASS" and
               type(row.get("code_bytes")) is int and row["code_bytes"] > 0
               for row in results):
            eligible.append(name)
    if not eligible:
        return [], eligible
    scores = {}
    totals = {}
    for compiler in compilers:
        ratios = []
        totals[compiler] = 0
        for name in eligible:
            size = shared[name, enabled, compiler]["code_bytes"]
            best = min(shared[name, enabled, other]["code_bytes"] for other in compilers)
            ratios.append(math.log(size / best))
            totals[compiler] += size
        scores[compiler] = math.exp(sum(ratios) / len(ratios))
    best_score = min(scores.values())
    # Rank at displayed precision so visually identical scores share a place.
    indexes = {compiler: round(score / best_score * 100, 2) for compiler, score in scores.items()}
    ordered = sorted(indexes.values())
    rows = []
    for compiler in sorted(compilers, key=lambda c: (indexes[c], c)):
        rank = ordered.index(indexes[compiler]) + 1
        passes = sum(shared.get((name, enabled, compiler), {}).get("status") == "PASS" for name in BENCHMARKS)
        rows.append([ordinal(rank), compiler,
                     f"{indexes[compiler]:.2f}", totals[compiler], f"{passes}/{len(BENCHMARKS)}"])
    return rows, eligible


def cmoc_version_comparison(reports, previous):
    changes = sorted(changed_cmoc_results(reports, previous), key=lambda item: (BENCHMARKS.index(item[0][0]), not item[0][1]))
    return [[SourceLink(LABELS[name], cmoc_diff_url(name, enabled)), "On" if enabled else "Off",
             f"{after['code_bytes'] - before['code_bytes']:+d}", f"{after['instructions'] - before['instructions']:+d}"]
            for (name, enabled), _, before, _, after in changes]


def ordinal(rank):
    return str(rank) + ({1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th") if rank % 100 not in (11, 12, 13) else "th")


def render(reports, previous_reports=None, historical=False,
           historical_label="CMOC 0.1.99", history_links=(),
           run_started_at=None, run_url=None):
    reports = [r for r in reports if r.get("suite") != "os9-apps"]
    compilers = comparison_compilers(reports)
    standard_compilers = "CMOC/LLVM" + ("/gcc6809" if "GCC6809" in compilers else "")
    validate_shared_sources(reports)
    markdown = ["# The Grand 6809 C Compiler Bake-Off!", ""]
    content = ["<h1>The Grand 6809 C Compiler Bake-Off!</h1>"]
    recorded_dates = {r['run_started_at'] for r in reports if r.get('run_started_at')}
    if len(recorded_dates) > 1:
        raise ValueError('Reports contain different benchmark run dates')
    run_started_at = run_started_at or next(iter(recorded_dates), None)
    run_url = run_url or next((r['workflow_run_url'] for r in reports if r.get('workflow_run_url')), None)
    if run_started_at:
        started = datetime.fromisoformat(run_started_at.replace('Z', '+00:00'))
        if started.tzinfo is None:
            raise ValueError('Run date must include a timezone')
        label = started.astimezone(ZoneInfo('America/New_York')).strftime('%B %-d, %Y at %-I:%M %p %Z')
        markdown.extend(['Run started: ' + label + ('. [Workflow run](' + run_url + ')' if run_url else ''), ''])
        content.append('<p>Run started: <time datetime="' + html.escape(run_started_at, quote=True) + '">' +
                       html.escape(label) + '</time>' +
                       ('. <a href="' + html.escape(run_url, quote=True) + '">Workflow run</a>' if run_url else '') + '</p>')
    else:
        markdown.extend(['Run date: not recorded', ''])
        content.append('<p>Run date: not recorded</p>')
    repository = "https://github.com/DrPitre/6809-c-benchmarks"
    markdown.extend(["[View repository on GitHub](" + repository + ")", ""])
    content.append('<p><a href="' + repository + '">View repository on GitHub</a></p>')

    if historical:
        content.append('<p><strong>Historical snapshot: ' + html.escape(historical_label) + '.</strong> These results are preserved from the published run before the upgrade. <a href="../../index.html">Return to the current Bake-Off</a>.</p>')
        markdown.extend(["Historical snapshot: " + historical_label + ". [Current Bake-Off](../../index.html)", ""])
    elif previous_reports:
        content.append('<p><a href="history/cmoc-0.1.99/index.html">Preserved results: CMOC 0.1.99</a> · <a href="#cmoc-release-comparison">Compare CMOC releases</a></p>')
        markdown.extend(["[Preserved results: CMOC 0.1.99](history/cmoc-0.1.99/index.html)", ""])

    if not historical:
        for directory, label in history_links:
            url = 'history/' + directory + '/index.html'
            content.append('<p><a href="' + html.escape(url, quote=True) + '">Preserved results: ' + html.escape(label) + '</a></p>')
            markdown.extend(['[Preserved results: ' + label + '](' + url + ')', ''])

    def paragraph(text):
        markdown.extend([text, ""])
        content.append("<p>" + html.escape(text) + "</p>")

    def table(title, headers, rows, highlights=None, grouped=False, ranks=None):
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
                if isinstance(cell, int) or (isinstance(cell, SourceLink) and cell.label.isdecimal()):
                    classes.append("number")
                if highlights and (row_index, column) in highlights:
                    classes.append("smaller")
                    value = "<strong>" + value + "</strong>"
                if ranks and (row_index, column) in ranks:
                    rank = ranks[row_index, column]
                    place = ordinal(rank)
                    value += (' <span class="rank rank-' + str(rank) + '" title="' + place +
                              ' place for this metric in this row">' + place + '</span>')
                if cell == "PASS":
                    classes.append("pass")
                elif cell in ("FAIL", "COMPILE FAIL", "Excluded (FAIL)"):
                    classes.append("fail")
                result.append(f'<{cell_tag}' + attributes + ' class="' + " ".join(classes) + '">' + value + f'</{cell_tag}>')
            return ('<tr class="group-start">' if grouped and row_index in spans else "<tr>") + "".join(result) + "</tr>"
        content.append('<div class="scroll"><table><thead>' + tr(headers, "th") +
                       "</thead><tbody>" + "".join(tr(r, "td", i) for i, r in enumerate(rows)) + "</tbody></table></div>")

    paragraph(", ".join(compilers) + ", side by side. Identical Shared 16-bit suite sources run on the same 6809 simulator. Sizes are in bytes; click a size to compare all participating assembly outputs side by side. Executed instruction counts cover four seed runs. Lower is better for both metrics; CPU cycles are not measured.")
    content.append('<section class="versions">')
    versions = []
    for compiler in compilers:
        seen = set()
        for report in reports:
            if report.get("suite") != "kr16" or report["compiler"].upper() != compiler:
                continue
            version = report.get("version", "Unavailable")
            release = report.get("release", report.get("toolchain_revision", "—"))
            if (version, release) not in seen:
                versions.append([compiler, version, release])
                seen.add((version, release))
    table("Compiler versions tested", ["Compiler", "Reported version", "Release / revision"], versions)
    content.append('</section>')
    if previous_reports:
        cmoc_versions = [re.search(r"\d+\.\d+\.\d+", r.get("version", "")) for r in reports if r["compiler"].upper() == "CMOC"]
        cmoc_release = next((m.group(0) for m in cmoc_versions if m), "Unavailable")
        content.append('<details id="cmoc-release-comparison" open><summary>CMOC 0.1.99 → ' + cmoc_release + '</summary>')
        paragraph(f"Old measurements are preserved from the published CMOC 0.1.99 run; the main rankings use CMOC {cmoc_release}. Only changed results are shown. Negative deltas mean fewer bytes or instructions. Click a benchmark name to compare old and new assembly with changes highlighted. Deltas require both results to pass with identical source hashes and harness sizes. Code includes runtime helpers and excludes the harness. Full measurements and assembly remain in the current and preserved reports.")
        table("CMOC release comparison", ["Benchmark", "Optimization", "Δ bytes", "Δ instructions"],
              cmoc_version_comparison(reports, previous_reports), grouped=True)
        content.append('</details>')

    shared = {}
    assembly_links = {}
    for report in reports:
        if report.get("suite") != "kr16":
            continue
        compiler = report["compiler"].upper()
        if compiler not in compilers:
            continue
        if report["flags"] in ("-Os", "-Oz"):
            continue
        enabled = report["flags"] in ("optimizer on", "-O2")
        for row in report["rows"]:
            key = (row["benchmark"], enabled, compiler)
            if key in shared:
                raise ValueError("Duplicate shared compiler configuration")
            shared[key] = row
            assembly_links[key] = assembly_url(report, row)

    content.append('<section class="versions">')
    paragraph("Overall compiler ranking by benchmark code size. Lower is better; the leading compiler scores 100. Each test has equal weight through the geometric mean of relative sizes. Only tests with valid sizes and passing results from all participating compilers enter the ranking. This measures this suite, not all possible C programs; linked runtime helpers, constants, and initialized data are included; only the test harness and uninitialized storage are excluded.")
    for enabled in (True, False):
        ranking, eligible = overall_sizes(shared, enabled, compilers)
        table("Overall code-size ranking — optimization " + ("on" if enabled else "off"),
              ["Place", "Compiler", "Relative size index", "Total code + helpers (B)", "Suite passes"], ranking,
              highlights={(i, 2) for i, row in enumerate(ranking) if row[0] == "1st"})
        excluded = [LABELS[name] for name in BENCHMARKS if name not in eligible]
        paragraph(str(len(eligible)) + "/" + str(len(BENCHMARKS)) + " tests included. " +
                  ("Excluded from every compiler's score: " + ", ".join(excluded) + "." if excluded else "All tests included.") +
                  " Total bytes use the same included tests; suite passes cover the entire suite. Ties share a place at two-decimal precision.")
    content.append('</section>')

    shared_revision = next((r["revision"] for r in reports if r.get("suite") == "kr16"), "local")
    labels = {name: source_link(LABELS[name], "benchmarks/kr16/" + name + ".c", shared_revision) for name in BENCHMARKS}
    for metric, title in (("code_bytes", "Code size including runtime helpers"),
                          ("loaded_bytes", "Complete test program size"),
                          ("instructions", "Executed instructions (four seeds)")):
        rows, highlights, ranks = [], set(), {}
        for name in BENCHMARKS:
            for enabled in (True, False):
                values = []
                for compiler in compilers:
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
                    for i, value in enumerate(values):
                        ranks[len(rows), i + 2] = ordered.index(value) + 1
                    winners = [i for i, value in enumerate(values) if value == ordered[0]]
                    if len(winners) > 1:
                        difference = "Tie: " + "/".join(compilers[i] for i in winners)
                    else:
                        difference = compilers[winners[0]] + " by " + str(ordered[1] - ordered[0]) + (" instructions" if metric == "instructions" else " B")
                    if len(winners) != len(values):
                        highlights.update((len(rows), i + 2) for i in winners)
                display_values = []
                for compiler, value in zip(compilers, values):
                    url = assembly_links.get((name, enabled, compiler))
                    display_values.append(SourceLink(str(value), url) if url and isinstance(value, int) and metric != "instructions" else value)
                rows.append([labels[name], "On" if enabled else "Off", *display_values, difference])
        table(title, ["Benchmark", "Optimization", *compilers, "Smallest"], rows, highlights, grouped=True, ranks=ranks)
        if metric == "instructions":
            paragraph("Instruction counts sum the four seeds and include the benchmark call/return, ABI register transfers, supporting functions, and linked runtime helpers. Startup, seed loading, result printing, and stack cleanup in the harness are excluded. Prefixed 6809 opcodes count as one instruction. Counts are not CPU cycles: instructions have different costs. Failed results are excluded; per-seed counts remain in the raw JSON and workflow artifacts.")
    paragraph("Ranked code size includes the benchmark, supporting functions, linked runtime helpers, constants, and initialized data. It is the complete loaded size minus the measured harness size. Complete test program size adds the test harness back in. Both measure bytes loaded into memory, excluding uninitialized storage and file-format overhead. Badges rank each complete compiler row by its metric (1st is lowest); ties share a place. Rows with failed or missing results have no ranking. Shaded bold values mark the smallest result; the byte gap is to the next-smallest compiler; failed or missing results are never ranked.")
    paragraph(f"Optimization on means C3's default optimizer and {standard_compilers} -O2 plus vbcc -O=1023 (vc -O2); off disables C3's optimizer and uses {standard_compilers} -O0 and vbcc -O=0. vbcc uses its standard assembler branch/offset relaxation at both settings. These settings do not imply identical optimization passes.")
    statuses = []
    for name in BENCHMARKS:
        for enabled in (True, False):
            statuses.append([labels[name], "On" if enabled else "Off"] +
                            [shared.get((name, enabled, compiler), {}).get("status", "NOT RUN")
                             for compiler in compilers])
    table("Shared-suite correctness", ["Benchmark", "Optimization", *compilers], statuses, grouped=True)
    size_reports = size_configurations(reports)
    if size_reports:
        variants = tuple(item[0] for item in SIZE_CONFIGURATIONS)
        size_shared = {(row['benchmark'], True, label): row
                       for label, report in size_reports.items() for row in report['rows']}
        paragraph("LLVM size optimization versus vbcc: compare the same sources at LLVM -O2, -Os and -Oz against vbcc -O=1023 (vc -O2). These are separate measured configurations; the original on/off rankings above continue to use -O2. Code includes linked runtime helpers and excludes the harness. Lower is better.")
        ranking, eligible = overall_sizes(size_shared, True, variants)
        table("LLVM size optimization versus vbcc — overall code size",
              ["Place", "Configuration", "Relative size index", "Total code + helpers (B)", "Suite passes"], ranking)
        paragraph(str(len(eligible)) + "/" + str(len(BENCHMARKS)) +
                  " tests included in this ranking; only passing, positive-sized results from all four configurations enter the score.")
        for metric, title in (("code_bytes", "LLVM size optimization versus vbcc — bytes"),
                              ("instructions", "LLVM size optimization versus vbcc — instructions")):
            rows, highlights = [], set()
            for name in BENCHMARKS:
                cells, valid = [], []
                for label in variants:
                    row = size_shared.get((name, True, label), {})
                    value = row.get(metric)
                    if row.get('status') == 'PASS' and isinstance(value, int) and value > 0:
                        cells.append(SourceLink(str(value), size_assembly_url(name)) if metric == 'code_bytes' else value)
                        valid.append(value)
                    else:
                        cells.append('Excluded (FAIL)' if row.get('status') else 'Not run')
                if len(valid) == len(variants) and len(set(valid)) > 1:
                    highlights.update((len(rows), i + 1) for i, value in enumerate(valid) if value == min(valid))
                rows.append([labels[name], *cells])
            table(title, ["Benchmark", *variants], rows, highlights)
        statuses = [[labels[name]] + [size_shared.get((name, True, label), {}).get('status', 'NOT RUN')
                                     for label in variants] for name in BENCHMARKS]
        table("LLVM size optimization versus vbcc — correctness", ["Benchmark", *variants], statuses)
        paragraph("PASS requires all four seeds to match independent references. Instructions sum those four seeds and are not CPU cycles. Click a byte size for a four-way assembly comparison; failed or missing results never receive a numeric size or enter the ranking.")
    failures = []
    for report in reports:
        if report.get("suite") != "kr16":
            continue
        if report.get("error"):
            failures.append(["All benchmarks", report["compiler"], report["flags"],
                             "Toolchain setup", report["error"]])
        for row in report["rows"]:
            if row["status"] != "PASS":
                failures.append([labels.get(row["benchmark"], row["benchmark"]), report["compiler"], report["flags"],
                                 row.get("failure_stage", "Unknown"), row.get("error", "Checksum mismatch")])
    if failures:
        content.append('<div id="failures"></div>')
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

    for group, title in (("kr16", "Shared 16-bit suite: compiler versions and runtime correctness"),
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
    paragraph("The Shared 16-bit suite uses identical K&R-compatible source for " + ", ".join(compilers) + ", 16-bit unsigned arithmetic, and one bare-metal harness. Its sort stores values in unsigned words; the original C89 sort uses bytes and 32-bit arithmetic. Compare sizes within a suite, not between suites.")
    def linked_size(report, row, metric):
        if row["status"] != "PASS":
            return "Excluded (FAIL)"
        value = row.get(metric, "Unavailable")
        url = assembly_url(report, row)
        return SourceLink(str(value), url) if url and isinstance(value, int) else value

    sizes = []
    for report in reports:
        if report.get("kind") == "compile-compatibility" or not report.get("target", "").startswith("6809"):
            continue
        for row in report["rows"]:
            valid = row["status"] == "PASS"
            sizes.append([source_link(("Shared 16-bit suite" if report.get("suite") == "kr16" else "Original C89 (function only)") + ": " + LABELS.get(row["benchmark"], row["benchmark"]),
                                      ("benchmarks/kr16/" if report.get("suite") == "kr16" else "benchmarks/") + row["benchmark"] + ".c", report["revision"]),
                          report.get("version", report["compiler"]), report["flags"],
                          linked_size(report, row, "code_bytes" if report.get("suite") == "kr16" else "kernel_code_bytes"),
                          linked_size(report, row, "loaded_bytes"),
                          row.get("instructions", "Not measured") if valid else "Excluded (FAIL)"])
    table("6809 sizes (bytes)", ["Benchmark", "Compiler", "Flags", "Code + helpers¹", "Complete test program", "Instructions"], sorted(sizes, key=lambda row: str(row[0])), grouped=True)
    paragraph("Shared-suite code sizes include linked runtime helpers and exclude the measured harness. ¹ Original C89 rows retain their historical function-only measurement and do not enter the shared-suite rankings. Complete test program size includes the test runner and linked helpers (plus the C library runner for c89), excluding BSS and S-record text overhead. The shared-suite harness passes each seed in D and on the stack for C3/CMOC; LLVM's branch moves the argument and result through X. LLVM reserves 24 bytes of direct-page register scratch RAM, excluded from complete test program bytes. The exact LLVM release is recorded above, with plain 6809 code, -std=c89, -fno-pie, and no LTO. C3 stack-check calls use a no-op stub; these bounded benchmark functions have a reserved 4 KiB stack and no static storage. These are bare-metal benchmark tests, not OS-9 application tests.")
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
        paragraph("C3 is tested against the unchanged C89 benchmark functions. COMPILE FAIL is an observed compatibility result, not a failed runtime checksum. ACCEPTED probes were compiled, not executed. C3 currently lacks limits.h and rejects unsigned short, unsigned long, and U-suffixed constants. These limitations apply to the original C89 suite; the Shared 16-bit suite results above execute real C3-generated code.")
        paragraph("The original compatibility check records rejections; the Shared 16-bit suite runtime check requires passing checksums. Infrastructure failures still fail CI. Full diagnostics are included in the raw JSON and workflow artifacts.")
        content.append("</details>")
    simulators = {(r['emulator_revision'], r.get('emulator_adapter_sha256', ''),
                   r.get('emulator_source_url', '')) for r in reports if r.get('emulator_revision')}
    if simulators:
        table("Simulator provenance", ["CPU core", "Source revision", "Machine adapter SHA-256"],
              [["markrvmurray/usim", SourceLink(revision, url), adapter]
               for revision, adapter, url in sorted(simulators)])
        paragraph("The unmodified 6809 CPU core is pinned independently of the compilers. The benchmark machine counts executed instructions through the CPU's pre-execution hook; it does not measure CPU cycles. Raw JSON, commands, assembly, linker maps, and executables are available in the workflow artifacts.")
    else:
        paragraph("USIM is bundled with CMOC 0.1.99. The shared-suite adapter counts executed instructions with an opt-in USIM patch; it does not measure CPU cycles. Raw JSON, commands, assembly, linker maps, and executables are available in the workflow artifacts.")
    paragraph("Source revisions: " + ", ".join(sorted({r["revision"] for r in reports})))
    content.append('<p><a href="results.json">Raw result data</a> · <a href="matrix.md">Markdown matrix</a></p>')
    document = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<title>The Grand 6809 C Compiler Bake-Off!</title><style>body{font:16px/1.55 system-ui;margin:2rem auto;padding:0 1.25rem;max-width:72rem;color:#172b3a;background:#f8fafc}h1{line-height:1.15}h2{margin-top:2rem;font-size:1.25rem}'
                'table{border-collapse:collapse;width:100%;background:white}th,td{border-bottom:1px solid #dbe3eb;padding:.65rem .8rem;text-align:left;white-space:nowrap}th{background:#eaf0f6;font-size:.9rem}td:nth-child(2){white-space:normal}.number{font-variant-numeric:tabular-nums;text-align:right}.smaller{background:#e0f2e9;color:#15583a}.pass{color:#14532d;background:#dcfce7;font-weight:700}.fail{color:#b91c1c;background:#fee2e2;font-weight:700}tr.group-start{border-top:2px solid #bccbd8}tbody th[scope=rowgroup]{vertical-align:middle;background:#f0f5fa;font-size:1rem}tbody th a{white-space:normal}'
                '.rank{display:inline-block;min-width:2.1rem;margin-left:.35rem;padding:.08rem .3rem;border:1px solid;border-radius:999px;font-size:.7rem;font-weight:700;text-align:center;vertical-align:middle}.rank-1{color:#714b00;background:#fff0b3;border-color:#d5af45}.rank-2{color:#334155;background:#e8edf3;border-color:#a8b4c3}.rank-3{color:#7c3d16;background:#f7e1cd;border-color:#cc9a70}.rank-4,.rank-5{color:#58616e;background:#f3f4f6;border-color:#d1d5db}.versions{padding:1rem;background:#eaf0f6;border:1px solid #bccbd8;border-radius:8px;margin:1.5rem 0}.versions h2{margin-top:0}.versions td{white-space:normal;overflow-wrap:anywhere}.versions td:first-child{font-weight:700}.scroll{overflow:auto;border:1px solid #dbe3eb;border-radius:8px}p{max-width:65rem}details{margin:1.5rem 0;padding:1rem;background:white;border:1px solid #dbe3eb;border-radius:8px}summary{cursor:pointer;font-weight:600}a{color:#145daa}@media(max-width:600px){body{margin:1rem auto;padding:0 .75rem}th,td{padding:.5rem}} </style></head><body>' + "".join(content) + '</body></html>')
    return "\n".join(markdown), document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-reports", type=int)
    parser.add_argument("--run-started-at", help="Workflow start time in ISO 8601 with timezone")
    parser.add_argument("--run-url", help="Workflow run URL")
    args = parser.parse_args()
    reports = [json.loads(p.read_text()) for p in sorted(args.input.glob("*.json"))]
    if not reports or (args.expected_reports is not None and len(reports) != args.expected_reports):
        raise SystemExit("Missing reports; refusing to publish an incomplete matrix")
    if args.run_started_at:
        for report in reports:
            report['run_started_at'] = args.run_started_at
            if args.run_url:
                report['workflow_run_url'] = args.run_url
    history_root = Path(__file__).resolve().parents[1] / 'history'
    histories = {}
    for snapshot in sorted(history_root.glob('*/results.json')):
        metadata = json.loads(snapshot.with_name('snapshot.json').read_text())
        data = snapshot.read_bytes()
        if hashlib.sha256(data).hexdigest() != metadata['results_sha256']:
            raise ValueError('Historical snapshot digest mismatch: ' + snapshot.parent.name)
        label = metadata.get('label', 'CMOC 0.1.99' if snapshot.parent.name == 'cmoc-0.1.99' else snapshot.parent.name)
        histories[snapshot.parent.name] = (json.loads(data), label, data, metadata)
    previous = histories.get('cmoc-0.1.99', (None,))[0]
    links = [(name, label) for name, (_, label, _, _) in histories.items() if name != 'cmoc-0.1.99']
    detailed_markdown, detailed_document = render(reports, previous_reports=previous, history_links=links)
    from focused_report import render_focused
    markdown, document = render_focused(reports, history_links=links, previous_reports=bool(previous))
    args.output.mkdir(parents=True, exist_ok=True)
    if any(r.get("suite") == "os9-apps" for r in reports):
        from app_report import render_applications
        (args.output / "applications.html").write_text(render_applications(reports))
    for name, (preserved, label, data, metadata) in histories.items():
        archive = args.output / 'history' / name
        archive.mkdir(parents=True, exist_ok=True)
        old_markdown, old_document = render(preserved, historical=True, historical_label=label,
                                             run_started_at=metadata.get("run_started_at"),
                                             run_url=("https://github.com/DrPitre/6809-c-benchmarks/actions/runs/" +
                                                      str(metadata["workflow_run"])) if metadata.get("workflow_run") else None)
        (archive / 'index.html').write_text(old_document)
        (archive / 'matrix.md').write_text(old_markdown)
        (archive / 'results.json').write_bytes(data)
        publish_assembly(preserved, archive)
    if previous:
        publish_cmoc_diffs(reports, previous, args.output)
    publish_assembly(reports, args.output)
    detailed_document = detailed_document.replace('<body>', '<body><p><a href="index.html">Back to focused comparison</a></p>', 1)
    (args.output / "details.html").write_text(detailed_document)
    (args.output / "details.md").write_text(detailed_markdown)
    (args.output / "matrix.md").write_text(markdown)
    (args.output / "index.html").write_text(document)
    (args.output / "results.json").write_text(json.dumps(reports, indent=2) + "\n")


if __name__ == "__main__":
    main()
