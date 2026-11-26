"""Present whole OS-9 applications separately from the bare-metal kernels."""
import html
import re
from focused_report import STYLE


def render_applications(reports):
    esc = lambda v: html.escape(str(v), quote=True)
    apps = [r for r in reports if r.get('suite') == 'os9-apps']
    chunks = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
              '<meta name="viewport" content="width=device-width,initial-scale=1">',
              '<title>NitrOS-9 application comparison</title><style>' + STYLE + '</style></head><body><main>',
              '<header><p><a href="index.html">Back to compiler bake-off</a></p>',
              '<h1>NitrOS-9 applications</h1>',
              '<p class="intro">Complete uniq, dgrep, ed, cb, lb, ppc and MicroEMACS programs, including startup and linked C libraries.</p></header>']
    if not apps:
        return ''.join(chunks) + '<p>No application report received.</p></main></body></html>'
    if len(apps) != 1:
        raise ValueError('Expected exactly one OS-9 application report')
    report = apps[0]
    runtime = report.get('llvm_runtime')
    if runtime:
        link = runtime['url'].removesuffix('.git') + '/commit/' + runtime['revision']
        chunks.append('<p>LLVM RC2 uses the OS-9 text runtime fix from <a href="' + esc(link) + '">picolibc ' + esc(runtime['revision'][:12]) + '</a>. The compiler remains the released RC2 binary.</p>')
    if report.get('vbcc_compiler_patch'):
        chunks.append('<p>vbcc is rebuilt from the pinned preview with the <a href="https://github.com/DrPitre/6809-c-benchmarks/blob/main/patches/vbcc-array-offset/fix.patch">one-past array-offset fix</a>.</p>')
    if report.get('vbcc_os9_runtime'):
        chunks.append('<p>vbcc uses the <a href="https://github.com/DrPitre/6809-c-benchmarks/blob/main/tools/vbcc-os9-rw.patch">OS-9 EOF wrapper fix</a>, which returns a zero-byte read at native end of file.</p>')
    if report.get('ppc_clock'):
        chunks.append('<p>ppc page headers use a fixed clock: ' + esc(report['ppc_clock']['timestamp']) +
                      ' (<a href="https://github.com/DrPitre/6809-c-benchmarks/blob/main/benchmarks/os9-apps/ppc-clock.c">shared clock adapter</a>).</p>')
    if report.get('uemacs_terminal'):
        chunks.append('<p>MicroEMACS: ' + esc(report['uemacs_terminal']) +
                      '. Full editor loop and ANSI redisplay; saved files are checked byte-for-byte.</p>')
    probe = report.get('runtime_probe')
    if probe:
        chunks.append('<p>OS-9 text/binary runtime regression: <strong>' + esc(probe['status']) + '</strong> (including exact CR bytes on redirected standard output and error).</p>')
    for item in report.get('vbcc_pointer_probes', []):
        chunks.append('<p>vbcc array-offset regression (' + esc(item['configuration_id']) + '): <strong>' + esc(item['status']) + '</strong>.</p>')
    rows = report['rows']
    cases = [c for r in rows for c in r['cases']]
    chunks.append('<p>' + str(sum(c['status'] == 'PASS' for c in cases)) + '/' + str(len(cases)) +
                  ' application fixtures passed. Programs execute under the pinned NitrOS-9 Level 2 kernel in Pico-Thing USIM.</p>')
    if report.get('run_started_at'):
        chunks.append('<p>Run started: ' + esc(report['run_started_at']) +
                      (' · <a href="' + esc(report['workflow_run_url']) + '">Workflow run</a>' if report.get('workflow_run_url') else '') + '</p>')
    chunks.append('<p>Only programs passing every fixture receive a size result. Module bytes include the OS-9 header, name, CRC, startup and linked runtime. Requested data is the module header’s allocation request, not measured peak RAM. These results do not enter the kernel rankings.</p>')
    for app in ('uniq', 'dgrep', 'ed', 'cb', 'lb', 'ppc', 'uemacs'):
        chunks.append('<section><h2>' + ('MicroEMACS' if app == 'uemacs' else app) + '</h2><div class="table-scroll"><table><thead><tr><th>Configuration</th><th>Output checks</th><th>Module bytes</th><th>Requested data bytes</th></tr></thead><tbody>')
        for row in [r for r in rows if r['application'] == app]:
            passed = sum(c['status'] == 'PASS' for c in row['cases'])
            valid = row['status'] == 'PASS'
            chunks.append('<tr><td>' + esc(row['configuration']) + '</td><td>' +
                          esc(row['status']) + ' ' + str(passed) + '/' + str(len(row['cases'])) +
                          '</td><td>' + (str(row['module_bytes']) if valid else '—') +
                          '</td><td>' + (str(row['requested_data_bytes']) if valid else '—') + '</td></tr>')
        chunks.append('</tbody></table></div>')
        issues = sorted({r['known_failure'] for r in rows if r['application'] == app and r.get('known_failure')})
        for issue in issues:
            chunks.append('<p>' + esc(issue) + '. These failed builds are excluded. <a href="https://github.com/DrPitre/6809-c-benchmarks/blob/main/benchmarks/os9-apps/vbcc-ed-offset.c">Minimal reproducer</a>.</p>')
        chunks.append('</section>')
    chunks.append('<section><h2>What the fixtures exercise</h2><p>uniq: adjacent grouping, unique/repeated selection, counts, skipped fields and characters, empty input and nonadjacent repeats. dgrep: case-insensitive literals, anchors, character classes, repetition, digits, inversion, counts, line numbers, files and no matches. ed: append/print, substitution, delete, insert, move, global matching, native CR file input, and save/reopen with exact saved-file bytes. cb: blocks, nested conditionals, comments, quotes, loops, switch labels and preprocessor lines. lb: empty and multi-module archives, every byte value, symbols and relocation references; every extracted file is checked byte-for-byte. ppc: numbered and unnumbered output, automatic and forced page breaks, suppression, multiple files, empty input and column-one directives. MicroEMACS: insertion, native file input, deletion and joining, kill/yank, word case, search, regions, keyboard macros and automatic word wrapping, each saved to disk.</p>')
    chunks.append('<p>Inputs use native OS-9 CR line endings. Line-oriented stdout comparisons normalize line endings only. MicroEMACS terminal transcripts require expected write-status messages and reject script exhaustion, bell errors, NUL and non-ASCII corruption; they are not compared byte-for-byte. Saved-file checks compare raw bytes, including every ROF header, payload, reference and module listing. The runtime regression separately checks native CR output, binary data, memory/cookie streams, seeks and mode changes. Failed application outputs remain in the raw results and are excluded from size comparisons. No application speed claim is made.</p>')
    chunks.append('<p>A common source patch adds missing declarations, corrects the fopen failure test and lets dgrep’s end anchor match the newline retained by fgets. Every compiler receives identical prepared source. ed also receives missing declarations and a signal-handler return-type fix; only C3 enables its runtime’s explicit printf initialization. cb also receives EOF-safe input variables and renamed helpers; lb uses explicit 28-byte headers, three-byte references and big-endian words. C3 selects its native byte-stream file modes. ppc receives missing declarations and the same fixed getime replacement for every compiler (2026-11-26 13:45:06); its header formatting and pagination remain upstream. The clock adapter is included in prepared-source hashes. Text inputs are short CR-terminated ASCII lines; lb inputs are binary archives. Long text lines and missing final newlines are outside this suite.</p>')
    if report.get('uemacs_terminal'):
        chunks.append('<details><summary>MicroEMACS build and terminal profile</summary><p>MicroEMACS uses a shared raw redirected-stream adapter instead of interactive terminal setup, with fixed ANSI 80x24 geometry; terminal negotiation and subprocess commands are outside this suite. Its portability patch splits mixed pointer/integer zero initializers, initializes display allocations, corrects the macro-bound pointer and word-wrap pointer types, and uses stdarg for LLVM/vbcc messages (va_start precedes nested calls); C3 retains its stack convention. The <a href="https://github.com/DrPitre/6809-c-benchmarks/blob/main/benchmarks/os9-apps/uemacs-stream.c">stream adapter</a> is included in prepared-source hashes.</p></details>')
    chunks.append('<p><a href="https://github.com/DrPitre/6809-c-benchmarks/blob/main/benchmarks/os9-apps/portable.patch">Common source patch</a> · <a href="https://github.com/DrPitre/6809-c-benchmarks/blob/main/benchmarks/os9-apps/cases.json">Fixtures</a> · <a href="results.json">Raw results and exact output differences</a></p></section>')
    chunks.append('<section><h2>Pinned sources</h2><ul>')
    for key, pin in report['sources'].items():
        chunks.append('<li>' + esc(key) + ': <a href="' + esc(pin['url'].removesuffix('.git') + '/commit/' + pin['revision']) + '">' + esc(pin['revision'][:12]) + '</a></li>')
    revision = report.get('revision', '')
    revision = revision if re.fullmatch(r'[0-9a-fA-F]{40}', revision) else 'main'
    document = ''.join(chunks) + '</ul></section></main></body></html>'
    return document.replace('https://github.com/DrPitre/6809-c-benchmarks/blob/main/',
                            'https://github.com/DrPitre/6809-c-benchmarks/blob/' + revision + '/')
