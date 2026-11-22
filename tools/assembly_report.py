"""Publish compiler output alongside the benchmark matrix."""
import hashlib
import html
import json
from pathlib import Path


def assembly_url(report, row):
    if not row.get('assembly'):
        return None
    if report.get('suite') == 'kr16':
        key = ['kr16', report['flags'] in ('optimizer on', '-O2'), row['benchmark']]
    else:
        key = [report.get('suite', 'c89'), report['compiler'], report['flags'], row['benchmark']]
    digest = hashlib.sha256(json.dumps(key).encode()).hexdigest()[:16]
    return 'assembly/' + digest + '.html'


def publish_individual_assembly(reports, output):
    for report in reports:
        if report.get('suite') == 'kr16':
            continue
        for row in report['rows']:
            url = assembly_url(report, row)
            if not url:
                continue
            title = ' / '.join([report['compiler'], report['flags'], report.get('suite', 'c89'), row['benchmark']])
            parts = ['<!doctype html><html lang="en"><meta charset="utf-8">',
                     '<meta name="viewport" content="width=device-width, initial-scale=1">',
                     '<title>' + html.escape(title) + '</title>',
                     '<style>body{font:16px/1.5 system-ui;max-width:80rem;margin:2rem auto;padding:0 1rem;color:#172b3a}pre{overflow:auto;background:#f1f5f9;padding:1rem;border:1px solid #dbe3eb;border-radius:6px}a{color:#145daa}</style>',
                     '<a href="../index.html">← Back to comparison</a>', '<h1>' + html.escape(title) + '</h1>',
                     '<p>' + html.escape(report.get('version', report['compiler'])) + '</p>',
                     '<p>Source revision: ' + html.escape(report['revision']) + '</p>',
                     '<p>Compiler-generated assembly supplied to the assembler. Benchmark code size covers these test objects, including support functions. Complete program size also includes the harness and linked runtime helpers; their placement is shown in the linker map below.</p>']
            for filename, text in row['assembly'].items():
                parts.extend(['<h2>' + html.escape(filename) + '</h2>', '<pre><code>' + html.escape(text) + '</code></pre>'])
            if row.get('linker_map'):
                parts.extend(['<h2>Linker map</h2>', '<pre><code>' + html.escape(row['linker_map']) + '</code></pre>'])
            parts.append('</html>')
            path = Path(output) / url
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('\n'.join(parts))


COMPILERS = ('C3', 'CMOC', 'LLVM', 'VBCC')


def comparison_compilers(reports):
    """Keep preserved reports at four columns; add GCC when its report exists."""
    has_gcc = any(r.get("suite") == "kr16" and r["compiler"].upper() == "GCC6809" for r in reports)
    return COMPILERS + (("GCC6809",) if has_gcc else ())


def publish_assembly(reports, output):
    publish_individual_assembly(reports, output)
    compilers = comparison_compilers(reports)
    groups = {}
    for report in reports:
        if report.get('suite') != 'kr16':
            continue
        enabled = report['flags'] in ('optimizer on', '-O2')
        for row in report['rows']:
            groups.setdefault((row['benchmark'], enabled), {})[report['compiler'].upper()] = (report, row)
    for (benchmark, enabled), entries in groups.items():
        url = next((assembly_url(report, row) for report, row in entries.values() if row.get('assembly')), None)
        if not url:
            continue
        title = benchmark + ' — optimization ' + ('on' if enabled else 'off')
        parts = ['<!doctype html><html lang="en"><meta charset="utf-8">',
                 '<meta name="viewport" content="width=device-width, initial-scale=1">',
                 '<title>' + html.escape(title) + '</title>',
                 '<style>body{font:15px/1.5 system-ui;margin:1.5rem;color:#172b3a;background:#f8fafc}a{color:#145daa}.scroll{overflow:auto}table{border-collapse:collapse;table-layout:fixed;width:100%;min-width:' + str(280 * len(compilers)) + 'px}th,td{min-width:19rem;padding:.65rem;vertical-align:top;text-align:left;border:1px solid #cbd5e1;background:white}th{background:#eaf0f6;font-size:1.2rem}th small{display:block;font-size:.8rem;font-weight:400;overflow-wrap:anywhere}.file-heading th{font-size:1rem;background:#dce7f1}pre{height:32rem;overflow:auto;margin:.5rem 0 0;padding:.7rem;background:#f1f5f9;font:12px/1.5 ui-monospace,monospace;tab-size:4}.pass{color:#14532d;font-weight:700}.fail{color:#b91c1c;font-weight:700}.revision{overflow-wrap:anywhere;font-size:.8rem}details pre{height:20rem}h1{font-size:1.6rem}</style>',
                 '<a href="../index.html">← Back to comparison</a>', '<h1>' + html.escape(title) + '</h1>',
                 '<p>All participating compiler outputs for this benchmark row. Each source file is aligned across columns; scroll within a pane to read its assembly. On smaller screens, scroll the table horizontally.</p>',
                 '<p>Code sizes include test support functions, linked runtime helpers, constants, and initialized data, excluding only the measured test harness. Complete program sizes also include the harness. Library helper assembly is not included here; linker maps are below.</p>',
                 '<div class="scroll"><table><thead><tr>']
        for compiler in compilers:
            report, row = entries.get(compiler, ({}, {}))
            parts.append('<th scope="col">' + compiler + '<small>' + html.escape(report.get('version', 'Not run')) + '</small><small>' + html.escape(report.get('flags', '')) + '</small></th>')
        parts.append('</tr></thead><tbody><tr>')
        for compiler in compilers:
            report, row = entries.get(compiler, ({}, {}))
            status = row.get('status', 'NOT RUN')
            parts.append('<td><span class="' + ('pass' if status == 'PASS' else 'fail') + '">' + html.escape(status) + '</span>')
            if status == 'PASS':
                parts.append('<p>Code: ' + str(row.get('code_bytes', 'Unavailable')) + ' B<br>Complete: ' + str(row.get('loaded_bytes', 'Unavailable')) + ' B</p>')
            else:
                parts.append('<p>' + html.escape(row.get('error', 'No result available')) + '</p>')
            parts.append('<p class="revision">Source revision: ' + html.escape(report.get('revision', 'Unavailable')) + '</p></td>')
        parts.append('</tr>')
        # Group translation units by source stem, not compiler-specific suffixes.
        stems = []
        for report, row in entries.values():
            for filename in row.get('assembly', {}):
                stem = filename.split('.')[0]
                if stem not in stems:
                    stems.append(stem)
        stems.sort(key=lambda stem: (stem != benchmark, stem))
        for stem in stems:
            parts.append('<tr class="file-heading"><th colspan="' + str(len(compilers)) + '">' + html.escape(stem + '.c') + '</th></tr><tr>')
            for compiler in compilers:
                _, row = entries.get(compiler, ({}, {}))
                assembly = [(filename, text) for filename, text in row.get('assembly', {}).items() if filename.split('.')[0] == stem]
                parts.append('<td>')
                if assembly:
                    for filename, text in assembly:
                        parts.append('<div>' + html.escape(filename) + '</div><pre><code>' + html.escape(text) + '</code></pre>')
                else:
                    parts.append('<p>Assembly unavailable for this build.</p>')
                parts.append('</td>')
            parts.append('</tr>')
        parts.append('<tr>')
        for compiler in compilers:
            _, row = entries.get(compiler, ({}, {}))
            parts.append('<td><details><summary>Linker map</summary><pre><code>' + html.escape(row.get('linker_map', 'Unavailable')) + '</code></pre></details></td>')
        parts.append('</tr></tbody></table></div></html>')
        path = Path(output) / url
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(parts))


def changed_cmoc_results(reports, previous):
    def configurations(items):
        return {(row['benchmark'], report['flags'] == '-O2'): (report, row)
                for report in items if report.get('suite') == 'kr16' and report['compiler'].upper() == 'CMOC'
                for row in report['rows']}
    old, new = configurations(previous), configurations(reports)
    for key, (new_report, after) in new.items():
        old_report, before = old.get(key, ({}, {}))
        if not (before.get('status') == after.get('status') == 'PASS' and
                before.get('source_sha256') and before.get('source_sha256') == after.get('source_sha256') and
                type(before.get('harness_bytes')) is int and before.get('harness_bytes') == after.get('harness_bytes')):
            continue
        if not all(type(row.get(metric)) is int for row in (before, after) for metric in ('code_bytes', 'instructions')):
            continue
        if any(before[metric] != after[metric] for metric in ('code_bytes', 'instructions')):
            yield key, old_report, before, new_report, after


def cmoc_diff_url(benchmark, enabled):
    digest = hashlib.sha256(json.dumps([benchmark, enabled]).encode()).hexdigest()[:16]
    return 'cmoc-diffs/' + digest + '.html'


def publish_cmoc_diffs(reports, previous, output):
    import difflib
    for (benchmark, enabled), old_report, before, new_report, after in changed_cmoc_results(reports, previous):
        title = benchmark + ' — CMOC release comparison — optimization ' + ('on' if enabled else 'off')
        parts = ['<!doctype html><html lang="en"><meta charset="utf-8">',
                 '<meta name="viewport" content="width=device-width, initial-scale=1">',
                 '<title>' + html.escape(title) + '</title>',
                 '<style>body{font:15px/1.5 system-ui;margin:1.5rem;color:#172b3a}a{color:#145daa}.scroll{overflow:auto}table.diff{font:12px/1.5 ui-monospace,monospace;border-collapse:collapse;width:100%}table.diff td{padding:0 .3rem;vertical-align:top}.diff_header{background:#eaf0f6}.diff_next{background:#f1f5f9}.diff_add{background:#dcfce7;color:#14532d}.diff_sub{background:#fee2e2;color:#991b1b}.diff_chg{background:#fef3c7;color:#713f12}.metadata{display:grid;grid-template-columns:1fr 1fr;gap:1rem}.metadata article{background:#f1f5f9;padding:1rem;overflow-wrap:anywhere}pre{overflow:auto;max-height:30rem}h1{font-size:1.5rem}</style>',
                 '<a href="../index.html#cmoc-release-comparison">← Back to changed results</a>',
                 '<h1>' + html.escape(title) + '</h1>',
                 '<p>Old assembly on the left; new assembly on the right. <span class="diff_sub">Removed</span>, <span class="diff_add">added</span>, and <span class="diff_chg">changed</span> text is highlighted. Line numbers refer to the generated assembly.</p>',
                 '<div class="metadata">']
        for report, row in ((old_report, before), (new_report, after)):
            parts.append('<article><strong>' + html.escape(report.get('version', 'CMOC')) + '</strong><p>Code including helpers: ' + str(row['code_bytes']) + ' B<br>Instructions: ' + str(row['instructions']) + '</p><small>Source revision: ' + html.escape(report.get('revision', 'Unavailable')) + '</small></article>')
        parts.append('</div>')
        stems = sorted({filename.split('.')[0] for row in (before, after) for filename in row.get('assembly', {})}, key=lambda stem: (stem != benchmark, stem))
        for stem in stems:
            texts = []
            for row in (before, after):
                texts.append('\n'.join(text for filename, text in row.get('assembly', {}).items() if filename.split('.')[0] == stem))
            parts.append('<h2>' + html.escape(stem + '.c') + '</h2><div class="scroll">')
            parts.append(difflib.HtmlDiff(tabsize=4).make_table(texts[0].splitlines(), texts[1].splitlines(),
                         fromdesc=html.escape(old_report.get('version', 'Old CMOC')), todesc=html.escape(new_report.get('version', 'New CMOC'))))
            parts.append('</div>')
        if not stems:
            parts.append('<p>Assembly is unavailable for this comparison.</p>')
        parts.append('<p>Generated source assembly excludes library-helper implementations. Code-size totals include linked helpers; consult the maps for their contributions.</p><div class="metadata">')
        for label, row in (('Old linker map', before), ('New linker map', after)):
            parts.append('<details><summary>' + label + '</summary><pre>' + html.escape(row.get('linker_map', 'Unavailable')) + '</pre></details>')
        parts.append('</div></html>')
        path = Path(output) / cmoc_diff_url(benchmark, enabled)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(parts))
