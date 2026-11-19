"""Publish compiler output alongside the benchmark matrix."""
import hashlib
import html
import json
from pathlib import Path


def assembly_url(report, row):
    if not row.get('assembly'):
        return None
    key = [report.get('suite', 'c89'), report['compiler'], report['flags'], row['benchmark']]
    digest = hashlib.sha256(json.dumps(key).encode()).hexdigest()[:16]
    return 'assembly/' + digest + '.html'


def publish_assembly(reports, output):
    for report in reports:
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
