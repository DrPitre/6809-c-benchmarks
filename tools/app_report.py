"""Present whole OS-9 applications separately from the bare-metal kernels."""
import html
from focused_report import STYLE


def render_applications(reports):
    esc = lambda v: html.escape(str(v), quote=True)
    apps = [r for r in reports if r.get('suite') == 'os9-apps']
    chunks = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
              '<meta name="viewport" content="width=device-width,initial-scale=1">',
              '<title>NitrOS-9 application comparison</title><style>' + STYLE + '</style></head><body><main>',
              '<header><p><a href="index.html">Back to compiler bake-off</a></p>',
              '<h1>NitrOS-9 applications</h1>',
              '<p class="intro">Complete uniq and dgrep programs, including startup and linked C libraries.</p></header>']
    if not apps:
        return ''.join(chunks) + '<p>No application report received.</p></main></body></html>'
    if len(apps) != 1:
        raise ValueError('Expected exactly one OS-9 application report')
    report = apps[0]
    runtime = report.get('llvm_runtime')
    if runtime:
        link = runtime['url'].removesuffix('.git') + '/commit/' + runtime['revision']
        chunks.append('<p>LLVM RC2 uses the OS-9 text runtime fix from <a href="' + esc(link) + '">picolibc ' + esc(runtime['revision'][:12]) + '</a>. The compiler remains the released RC2 binary.</p>')
    probe = report.get('runtime_probe')
    if probe:
        chunks.append('<p>OS-9 text/binary runtime regression: <strong>' + esc(probe['status']) + '</strong> (including exact CR bytes on redirected standard output and error).</p>')
    rows = report['rows']
    cases = [c for r in rows for c in r['cases']]
    chunks.append('<p>' + str(sum(c['status'] == 'PASS' for c in cases)) + '/' + str(len(cases)) +
                  ' output checks passed. Programs execute under the pinned NitrOS-9 Level 2 kernel in Pico-Thing USIM.</p>')
    if report.get('run_started_at'):
        chunks.append('<p>Run started: ' + esc(report['run_started_at']) +
                      (' · <a href="' + esc(report['workflow_run_url']) + '">Workflow run</a>' if report.get('workflow_run_url') else '') + '</p>')
    chunks.append('<p>Only programs passing every fixture receive a size result. Module bytes include the OS-9 header, name, CRC, startup and linked runtime. Requested data is the module header’s allocation request, not measured peak RAM. These results do not enter the kernel rankings.</p>')
    for app in ('uniq', 'dgrep'):
        chunks.append('<section><h2>' + app + '</h2><div class="table-scroll"><table><thead><tr><th>Configuration</th><th>Output checks</th><th>Module bytes</th><th>Requested data bytes</th></tr></thead><tbody>')
        for row in [r for r in rows if r['application'] == app]:
            passed = sum(c['status'] == 'PASS' for c in row['cases'])
            valid = row['status'] == 'PASS'
            chunks.append('<tr><td>' + esc(row['configuration']) + '</td><td>' +
                          esc(row['status']) + ' ' + str(passed) + '/' + str(len(row['cases'])) +
                          '</td><td>' + (str(row['module_bytes']) if valid else '—') +
                          '</td><td>' + (str(row['requested_data_bytes']) if valid else '—') + '</td></tr>')
        chunks.append('</tbody></table></div></section>')
    chunks.append('<section><h2>What the fixtures exercise</h2><p>uniq: adjacent grouping, unique/repeated selection, counts, skipped fields and characters, empty input and nonadjacent repeats. dgrep: case-insensitive literals, anchors, character classes, repetition, digits, inversion, counts, line numbers, files and no matches.</p>')
    chunks.append('<p>Inputs use native OS-9 CR line endings. Output comparison normalizes CR and LF only; it checks every remaining byte. The runtime regression separately checks native CR output, binary data, memory/cookie streams, seeks and mode changes. Failed application outputs remain in the raw results and are excluded from size comparisons. No application speed claim is made.</p>')
    chunks.append('<p>A common source patch adds missing declarations, corrects the fopen failure test and lets dgrep’s end anchor match the newline retained by fgets. Every compiler receives identical prepared source. Inputs are short ASCII lines ending in CR; long lines and missing final newlines are outside this first suite.</p>')
    chunks.append('<p><a href="https://github.com/DrPitre/6809-c-benchmarks/blob/main/benchmarks/os9-apps/portable.patch">Common source patch</a> · <a href="https://github.com/DrPitre/6809-c-benchmarks/blob/main/benchmarks/os9-apps/cases.json">Fixtures</a> · <a href="results.json">Raw results and exact output differences</a></p></section>')
    chunks.append('<section><h2>Pinned sources</h2><ul>')
    for key, pin in report['sources'].items():
        chunks.append('<li>' + esc(key) + ': <a href="' + esc(pin['url'].removesuffix('.git') + '/commit/' + pin['revision']) + '">' + esc(pin['revision'][:12]) + '</a></li>')
    return ''.join(chunks) + '</ul></section></main></body></html>'
