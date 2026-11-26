"""A compact, goal-oriented landing page for the recorded shared suite."""
import html
import math
from datetime import datetime
from zoneinfo import ZoneInfo

from assembly_report import assembly_url
from shared_suite import BENCHMARKS, LABELS


def configurations(reports, optimized=True):
    result = []
    seen = set()
    for report in reports:
        if report.get('suite') != 'kr16':
            continue
        flags = report['flags']
        if (flags not in ('-O0', 'optimizer off')) != optimized:
            continue
        compiler = report['compiler'].upper()
        label = compiler + ' ' + ('default optimizer' if flags == 'optimizer on' else flags)
        if label in seen:
            raise ValueError('Duplicate configuration: ' + label)
        seen.add(label)
        result.append({'label': label, 'report': report,
                       'rows': {row['benchmark']: row for row in report['rows']}})
    return sorted(result, key=lambda item: item['label'])


def summarize(configs):
    # Both metrics use exactly the same tests, including when a build fails.
    eligible = [name for name in BENCHMARKS if configs and all(
        c['rows'].get(name, {}).get('status') == 'PASS' and
        all(isinstance(c['rows'][name].get(metric), int) and c['rows'][name][metric] > 0
            for metric in ('code_bytes', 'instructions')) for c in configs)]
    summaries = []
    for config in configs:
        item = dict(config)
        item['passes'] = sum(row.get('status') == 'PASS' for row in config['rows'].values())
        for metric in ('code_bytes', 'instructions'):
            item[metric] = sum(config['rows'][name][metric] for name in eligible) if eligible else None
            item[metric + '_score'] = (math.exp(sum(math.log(
                config['rows'][name][metric] / min(c['rows'][name][metric] for c in configs))
                for name in eligible) / len(eligible)) if eligible else None)
        summaries.append(item)
    for metric in ('code_bytes', 'instructions'):
        best = min((c[metric + '_score'] for c in summaries if c[metric + '_score'] is not None), default=None)
        for item in summaries:
            item[metric + '_index'] = item[metric + '_score'] / best * 100 if best else None
    for item in summaries:
        item['frontier'] = bool(eligible) and not any(
            other['code_bytes_index'] <= item['code_bytes_index'] and
            other['instructions_index'] <= item['instructions_index'] and
            (other['code_bytes_index'] < item['code_bytes_index'] or
             other['instructions_index'] < item['instructions_index'])
            for other in summaries)
    return summaries, eligible


def render_focused(reports, history_links=(), previous_reports=False):
    esc = lambda value: html.escape(str(value), quote=True)
    configs = configurations(reports)
    summaries, eligible = summarize(configs)
    off, off_eligible = summarize(configurations(reports, optimized=False))
    shared = [r for r in reports if r.get('suite') == 'kr16']
    passed = sum(row.get('status') == 'PASS' for r in shared for row in r['rows']) * 4
    expected = len(shared) * len(BENCHMARKS) * 4
    dates = {r['run_started_at'] for r in reports if r.get('run_started_at')}
    if len(dates) > 1:
        raise ValueError('Reports contain different benchmark run dates')
    stamp = next(iter(dates), None)
    run_url = next((r['workflow_run_url'] for r in reports if r.get('workflow_run_url')), None)
    date_text = 'Run date: not recorded'
    if stamp:
        date = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        if date.tzinfo is None:
            raise ValueError('Run date must include a timezone')
        date_text = 'Run started: ' + date.astimezone(ZoneInfo('America/New_York')).strftime('%B %-d, %Y at %-I:%M %p %Z')
    chunks = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
              '<meta name="viewport" content="width=device-width,initial-scale=1">',
              '<title>The Grand 6809 C Compiler Bake-Off!</title>', '<style>' + STYLE + '</style>',
              '<noscript><style>.panel[hidden]{display:block}.tabs{display:none}</style></noscript>',
              '</head><body><main>', '<header><p class="eyebrow">Motorola 6809 · Shared 16-bit suite</p>',
              '<h1>The Grand 6809 C Compiler Bake-Off!</h1>',
              '<p class="intro">Choose what matters: smaller programs, fewer instructions, or a balance of both.</p>',
              '<p class="meta">' + ('<time datetime="' + esc(stamp) + '">' + esc(date_text) + '</time>' if stamp else esc(date_text)) +
              (' · <a href="' + esc(run_url) + '">Workflow run</a>' if run_url else '') + '</p>',
              '<p class="checks ' + ('ok' if passed == expected and expected else 'issue') + '">' +
              str(passed) + '/' + str(expected) + ' shared checksum checks passed · ' + str(len(BENCHMARKS)) +
              ' benchmarks · 4 seeds per configuration</p></header>']
    if any(r.get('suite') == 'os9-apps' for r in reports):
        chunks.append('<p><a href="applications.html">Real NitrOS-9 applications: uniq and dgrep</a></p>')
    markdown = ['# The Grand 6809 C Compiler Bake-Off!', '', date_text, '',
                f'{passed}/{expected} shared checksum checks passed.', '']
    if passed != expected:
        chunks.append('<p class="issue">Some results failed. Failed or missing measurements are excluded from rankings. <a href="details.html#failures">See diagnostics</a>.</p>')
    chunks.append('<nav class="tabs" role="tablist" aria-label="Comparison goal">')
    views = (('size', 'Smallest code'), ('instructions', 'Fewest instructions'), ('tradeoffs', 'Size versus execution'))
    for key, label in views:
        chunks.append('<button type="button" role="tab" id="tab-' + key + '" aria-controls="' + key +
                      '" aria-selected="' + ('true' if key == 'size' else 'false') + '" tabindex="' +
                      ('0' if key == 'size' else '-1') + '" data-goal="' + key + '">' + label + '</button>')
    chunks.append('</nav><p class="scope">Optimized configurations are shown by default. Instruction counts are not cycle timing or measured speed.</p>')

    def link(text, url):
        return '<a href="' + esc(url) + '">' + esc(text) + '</a>'

    def number(value):
        return f'{value:,}' if isinstance(value, int) else 'Excluded'

    def index(value):
        return f'{value:.1f}' if value is not None else 'Excluded'

    def table(headers, rows, classes=()):
        return '<div class="table-scroll"><table><thead><tr>' + ''.join('<th scope="col">' + esc(h) + '</th>' for h in headers) + '</tr></thead><tbody>' + ''.join(
            '<tr' + (' class="' + classes[i] + '"' if classes else '') + '>' + ''.join(
                ('<th scope="row">' if j == 0 else '<td>') + cell + ('</th>' if j == 0 else '</td>')
                for j, cell in enumerate(row)) + '</tr>' for i, row in enumerate(rows)) + '</tbody></table></div>'

    def by_test(metric, both=False):
        rows = []
        for name in BENCHMARKS:
            cells = [esc(LABELS[name])]
            valid = [c['rows'].get(name, {}).get(metric) for c in configs]
            complete = bool(configs) and all(c['rows'].get(name, {}).get('status') == 'PASS' and isinstance(v, int) and v > 0
                           for c, v in zip(configs, valid))
            minimum = min(valid) if complete else None
            for c, value in zip(configs, valid):
                row = c['rows'].get(name, {})
                if not row:
                    cells.append('Not run')
                    continue
                if row.get('status') != 'PASS':
                    cells.append('Excluded (FAIL)')
                    continue
                if not isinstance(value, int) or value <= 0 or (both and not isinstance(row.get('instructions'), int)):
                    cells.append('Unavailable')
                    continue
                text = number(value)
                if both:
                    text += ' B / ' + number(row.get('instructions')) + ' instructions'
                url = assembly_url(c['report'], row)
                cell = link(text, url) if url else esc(text)
                cells.append('<strong>' + cell + '</strong>' if value == minimum and not both else cell)
            rows.append(cells)
        return table(['Benchmark'] + [c['label'] for c in configs], rows)

    for key, title in views:
        metric = 'instructions' if key == 'instructions' else 'code_bytes'
        ordered = sorted(summaries, key=lambda c: (c[metric + '_index'] is None, c[metric + '_index'] or 0, c['label']))
        chunks.append('<section class="panel" id="' + key + '" role="tabpanel" aria-labelledby="tab-' + key +
                      '" tabindex="0"' + (' hidden' if key != 'size' else '') + '><h2>' + title + '</h2>')
        markdown.extend(['## ' + title, ''])
        if key == 'tradeoffs':
            chunks.append('<p>No combined score: compare both indices. Highlighted configurations have no tested alternative that is at least as good in both metrics and better in one.</p>')
            headers = ['Configuration', 'Size index', 'Instruction index', 'Total bytes', 'Total instructions', 'Tradeoff']
            rows = [[esc(c['label']), index(c['code_bytes_index']), index(c['instructions_index']),
                     number(c['code_bytes']), number(c['instructions']),
                     ('Efficient tradeoff' if c['frontier'] else 'Excluded' if not eligible else 'Better alternative exists')]
                    for c in ordered]
            chunks.append(table(headers, rows, ['frontier' if c['frontier'] else '' for c in ordered]))
            chunks.append('<p class="note">Tradeoff labels use the two indices. Totals are provided for reference.</p>')
        else:
            headers = ['Configuration', 'Size index' if key == 'size' else 'Instruction index',
                       'Total code + helpers (B)' if key == 'size' else 'Total instructions',
                       'Total instructions' if key == 'size' else 'Total code + helpers (B)', 'Suite passes']
            other = 'instructions' if metric == 'code_bytes' else 'code_bytes'
            rows = [[esc(c['label']), index(c[metric + '_index']), number(c[metric]), number(c[other]),
                     str(c['passes']) + '/' + str(len(BENCHMARKS))] for c in ordered]
            chunks.append(table(headers, rows, ['leader' if eligible and c[metric + '_index'] == 100 else '' for c in ordered]))
        markdown.extend(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'])
        markdown.extend('| ' + ' | '.join(html.unescape(cell) for cell in row) + ' |' for row in rows)
        markdown.append('')
        chunks.append('<p class="note">Lower is better. Index 100 leads this view; each benchmark has equal weight. ' +
                      str(len(eligible)) + '/' + str(len(BENCHMARKS)) + ' benchmarks are comparable across all configurations.</p>')
        if len(eligible) < len(BENCHMARKS):
            chunks.append('<p class="issue">Excluded from every index: ' + esc(', '.join(LABELS[n] for n in BENCHMARKS if n not in eligible)) + '.</p>')
        chunks.append('<details><summary>Per-benchmark results and assembly</summary><p class="note">Click a measurement to inspect assembly. Bold values mark the lowest result in a complete row.</p>' +
                      by_test(metric, key == 'tradeoffs') + '</details></section>')

    chunks.append('<section class="support"><details><summary>Unoptimized builds</summary><p>These configurations are compared separately; they do not enter the optimized indices above.</p>')
    rows = [[esc(c['label']), number(c['code_bytes']), number(c['instructions']), str(c['passes']) + '/' + str(len(BENCHMARKS))]
            for c in sorted(off, key=lambda c: (c['code_bytes'] is None, c['code_bytes'] or 0))]
    chunks.append(table(['Configuration', 'Total code + helpers (B)', 'Total instructions', 'Suite passes'], rows))
    chunks.append('<p class="note">Totals use ' + str(len(off_eligible)) + '/' + str(len(BENCHMARKS)) +
                  ' benchmarks with valid results from every unoptimized configuration. <a href="details.html">Full unoptimized per-test results</a>.</p></details>')
    chunks.append('<details><summary>Toolchains and measurement notes</summary>')
    versions = sorted({(r['compiler'].upper(), r.get('version', 'Unavailable')) for r in shared})
    chunks.append(table(['Compiler', 'Version tested'], [[esc(a), esc(b)] for a, b in versions]))
    chunks.append('<ul><li>Identical shared sources and four seeds run on the same 6809 simulator.</li><li>Code size includes support routines, linked runtime helpers, constants, and initialized data. The harness and BSS are excluded.</li><li>Instructions include calls, returns, ABI shims, and helpers; startup and output are excluded. CPU cycles are not measured.</li><li>Indices use the geometric mean of each test’s ratio to the smallest result, scaled so the leader is 100. Every index uses the same comparable tests.</li><li>C3 uses its default optimizer; VBCC -O2 means -O=1023. LLVM -Os/-Oz are separate configurations.</li></ul>')
    chunks.append('<p><a href="details.html">Full methodology, simulator provenance, diagnostics and compatibility results</a></p></details>')
    if history_links or previous_reports:
        chunks.append('<details><summary>Previous runs and release comparisons</summary><ul>')
        if previous_reports:
            chunks.append('<li><a href="history/cmoc-0.1.99/index.html">Preserved results: CMOC 0.1.99</a> · <a href="details.html#cmoc-release-comparison">Compare CMOC releases</a></li>')
        for directory, label in history_links:
            chunks.append('<li>' + link('Preserved results: ' + label, 'history/' + directory + '/index.html') + '</li>')
        chunks.append('</ul></details>')
    chunks.append('</section><footer><a href="results.json">Raw results</a> · <a href="matrix.md">Markdown summary</a> · <a href="details.html">Detailed tables</a> · <a href="https://github.com/DrPitre/6809-c-benchmarks">Source repository</a></footer></main><script>' + SCRIPT + '</script></body></html>')
    markdown.extend(['[Per-benchmark tables, assembly and methodology](index.html)', '', '[Detailed tables](details.html) · [Raw results](results.json)', ''])
    return '\n'.join(markdown), ''.join(chunks)


STYLE = '''
:root{color-scheme:light;font-family:system-ui,-apple-system,sans-serif;color:#172b3a;background:#f5f8fc}
*{box-sizing:border-box}body{margin:0}main{max-width:1180px;margin:0 auto;padding:2.5rem 1.25rem}
h1{font-size:clamp(1.8rem,4vw,2.7rem);letter-spacing:-.04em;line-height:1.15;margin:.4rem 0 1rem}
h2{font-size:1.45rem;letter-spacing:-.02em;margin:0 0 .6rem}p{line-height:1.6}a{color:#155ab0;text-underline-offset:.18em}
.eyebrow{font-size:.875rem;font-weight:650;color:#43617e;margin:0}.intro{font-size:1.125rem;margin:.5rem 0}.meta,.scope,.note{font-size:.875rem;color:#4c6175}.meta{margin:.5rem 0}.checks{font-size:.875rem;margin:1.1rem 0 1.7rem}.ok{color:#17633c}.issue{color:#8b2d20;background:#fff0eb;padding:.7rem;border-radius:6px}
.tabs{display:flex;gap:.3rem;border-bottom:1px solid #c8d6e6}.tabs button{font:inherit;font-size:1rem;font-weight:650;border:0;border-bottom:3px solid transparent;background:none;padding:.9rem 1.1rem;color:#465d74;cursor:pointer}.tabs button[aria-selected=true]{color:#104f9d;border-color:#1766bd}.tabs button:hover{background:#eaf1fb}.tabs button:focus-visible,summary:focus-visible{outline:3px solid #4595ed;outline-offset:2px}.scope{margin:.7rem 0 1.4rem}.panel{background:white;border:1px solid #d9e3ee;border-radius:10px;padding:1.4rem}.panel>p{max-width:58rem}.panel[hidden]{display:none}.table-scroll{overflow:auto;margin:1.1rem 0;border:1px solid #dbe3ec;border-radius:7px}table{border-collapse:collapse;width:100%;font-size:.95rem;font-variant-numeric:tabular-nums}th,td{padding:.85rem .9rem;border-bottom:1px solid #e4ebf3;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}thead th{background:#edf3fa;color:#415975;font-size:.875rem;font-weight:650}tbody th{font-weight:600}tbody tr:last-child>*{border-bottom:0}.leader,.frontier{background:#eaf7f0}.leader th,.frontier th{color:#14613d}details{margin-top:1rem}summary{cursor:pointer;font-weight:650;line-height:1.5;padding:.6rem 0}details[open]>summary{margin-bottom:.4rem}.support{padding:1rem .1rem}.support>details{border-bottom:1px solid #d9e3ee;margin:0;padding:.35rem 0}.support p,.support li{font-size:.95rem;line-height:1.65}footer{font-size:.875rem;color:#536b83;line-height:2;margin-top:1rem}li{margin:.45rem 0}
@media(max-width:640px){main{padding:1.4rem .8rem}.tabs button{font-size:.875rem;padding:.8rem .55rem;flex:1}.panel{padding:1rem .8rem}.intro{font-size:1rem}th,td{padding:.7rem .65rem}}
'''

SCRIPT = '''
const tabs=[...document.querySelectorAll('[role=tab]')];
function selectGoal(goal,focus=false){
 const selected=tabs.find(t=>t.dataset.goal===goal)||tabs[0];
 tabs.forEach(t=>{const active=t===selected;t.setAttribute('aria-selected',String(active));t.tabIndex=active?0:-1;document.getElementById(t.dataset.goal).hidden=!active});
 if(focus)selected.focus();
}
tabs.forEach((tab,index)=>{
 tab.addEventListener('click',()=>{selectGoal(tab.dataset.goal);history.replaceState(null,'','#'+tab.dataset.goal)});
 tab.addEventListener('keydown',event=>{let next;if(event.key==='ArrowRight')next=(index+1)%tabs.length;else if(event.key==='ArrowLeft')next=(index+tabs.length-1)%tabs.length;else if(event.key==='Home')next=0;else if(event.key==='End')next=tabs.length-1;else return;event.preventDefault();selectGoal(tabs[next].dataset.goal,true);history.replaceState(null,'','#'+tabs[next].dataset.goal)});
});
selectGoal(location.hash.slice(1));
window.addEventListener('hashchange',()=>selectGoal(location.hash.slice(1)));
'''
