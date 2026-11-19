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


def publish_assembly(reports, output):
    publish_individual_assembly(reports, output)
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
                 '<style>body{font:15px/1.5 system-ui;margin:1.5rem;color:#172b3a;background:#f8fafc}a{color:#145daa}.scroll{overflow:auto}table{border-collapse:collapse;table-layout:fixed;width:100%;min-width:1120px}th,td{width:25%;padding:.65rem;vertical-align:top;text-align:left;border:1px solid #cbd5e1;background:white}th{background:#eaf0f6;font-size:1.2rem}th small{display:block;font-size:.8rem;font-weight:400;overflow-wrap:anywhere}.file-heading th{font-size:1rem;background:#dce7f1}pre{height:32rem;overflow:auto;margin:.5rem 0 0;padding:.7rem;background:#f1f5f9;font:12px/1.5 ui-monospace,monospace;tab-size:4}.pass{color:#14532d;font-weight:700}.fail{color:#b91c1c;font-weight:700}.revision{overflow-wrap:anywhere;font-size:.8rem}details pre{height:20rem}h1{font-size:1.6rem}</style>',
                 '<a href="../index.html">← Back to comparison</a>', '<h1>' + html.escape(title) + '</h1>',
                 '<p>All four compiler outputs for this benchmark row. Each source file is aligned across columns; scroll within a pane to read its assembly. On smaller screens, scroll the table horizontally.</p>',
                 '<p>Code sizes include test support functions, linked runtime helpers, constants, and initialized data, excluding only the measured test harness. Complete program sizes also include the harness. Library helper assembly is not included here; linker maps are below.</p>',
                 '<div class="scroll"><table><thead><tr>']
        for compiler in COMPILERS:
            report, row = entries.get(compiler, ({}, {}))
            parts.append('<th scope="col">' + compiler + '<small>' + html.escape(report.get('version', 'Not run')) + '</small><small>' + html.escape(report.get('flags', '')) + '</small></th>')
        parts.append('</tr></thead><tbody><tr>')
        for compiler in COMPILERS:
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
            parts.append('<tr class="file-heading"><th colspan="4">' + html.escape(stem + '.c') + '</th></tr><tr>')
            for compiler in COMPILERS:
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
        for compiler in COMPILERS:
            _, row = entries.get(compiler, ({}, {}))
            parts.append('<td><details><summary>Linker map</summary><pre><code>' + html.escape(row.get('linker_map', 'Unavailable')) + '</code></pre></details></td>')
        parts.append('</tr></tbody></table></div></html>')
        path = Path(output) / url
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(parts))
