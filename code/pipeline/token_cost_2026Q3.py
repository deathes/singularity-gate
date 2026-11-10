"""Token use and API-equivalent cost per respondent model, 2026Q3 (user, 2026-11-02; scored answers updated 2026-11-03
for the question fixes and the GPT harness redo).

Same basis for every model, as in cost_estimate.md of the original GPT runs (SG_GPT_ORIGINALS): input tokens (cached included), cached input, output
tokens (reasoning/thinking INCLUDED: billed as output), reasoning alone, total = input + output, API-equivalent USD at
standard list prices. Two scopes:
  scored : the answers that are in the judge prompts (judge_prompts_2026Q3/<config.SET>/label_mappings.json), taken from the
           source the prompt builder used, in this order: the answer to the fixed question (items in the config's fix
           list), the fresh isolated-session answer (GPT sample and redo runs), the 2026-11-01 rerun, the original
           (a Claude answer missing from its main folder comes from the config fallback folder that holds it)
  spent  : every try on any version of the question (Claude: all attempts incl. failed, killed, blocked, budget and
           rerouted tries, the 2026-11-02 Opus retry of 022, the fix runs and the fallback folders; GPT: the 80 original agents, interrupted
           turns included, plus every attempt of the reruns, fix, sample and redo runs)
Claude: _usage.json of the model's answer folder, the fix folder and the fallback folders the config names (respondent_run.py usage; input =
input + cache writes + cache reads, cached = cache reads; cost per call from PRICES). GPT originals:
<run>/token_usage.csv and cost_per_agent.csv. GPT codex runs: _work/codex_reruns/<run>/audit.json usage, priced at
rates copied from the runs' cost_basis.json (no request near the 272K long-context threshold).
item_usage() gives the per-item split of these totals.
Writes answers/token_cost_2026Q3<config.SUFFIX>.json and .md.
"""
import csv
import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg  # noqa: E402

N = cfg.ROOT / 'new_corpus'
X = cfg.GPT_ORIGINALS
CFG = json.loads((N / f'judge_inputs_2026Q3_{cfg.SET}.json').read_text(encoding='utf-8'))
FIXCFG = CFG.get('fix') or {}
FIX = set(FIXCFG.get('items', []))
MCFG = {m['key']: m for m in CFG['models']}   # judge-config entry of each model in the set
MAP = json.loads((N / 'judge_prompts_2026Q3' / cfg.SET / 'label_mappings.json').read_text(encoding='utf-8'))['mappings']
CLAUDE = [('Claude Opus 5.5 xhigh', 'opus55_xhigh', 'opus 5.5 xhigh', ['opus 5.5 xhigh (retry 2026-11-02)']),
          ('Claude Sonnet 5.5 xhigh', 'sonnet55_xhigh', 'sonnet 5.5 xhigh', []),
          ('Claude Haiku 5.5 xhigh', 'haiku55_xhigh', 'haiku 5.5 xhigh', []),
          ('Claude Fable 5.1 xhigh', 'fable51_xhigh', 'fable 5.1 xhigh', []),
          ('Claude Fable 5.2 xhigh', 'fable52_xhigh', 'fable 5.2 xhigh', [])]
GPT = [('GPT-6.1 Sol xhigh', 'gpt61sol_xhigh', 'gpt61sol_2026Q3_2026-10-25T01-11-56-755Z', 'gpt61sol',
        {'normal': 2, 'cached': 0.1, 'write': 2.5, 'output': 10}),
       ('GPT-6 Astra xhigh', 'gpt6astra_xhigh', 'gpt6astra_2026Q3_2026-10-25T02-07-34-437Z', 'gpt6astra',
        {'normal': 10, 'cached': 1, 'write': 12.5, 'output': 50}),
       ('GPT-6.1 Terra xhigh', 'gpt61terra_xhigh', 'gpt61terra_2026Q3_2026-10-27T16-39-36-327Z', 'gpt61terra',
        {'normal': 1, 'cached': 0.05, 'write': 1.25, 'output': 5})]
CLAUDE = [c for c in CLAUDE if c[1] in MCFG]   # only the models of the chosen set
GPT = [g for g in GPT if g[1] in MCFG]
KEYS = ['answers', 'input', 'cached_input', 'output', 'reasoning', 'total', 'cost_usd']


def zero():
    return {k: 0 for k in KEYS}


def add(t, v, n=1):
    inp, cached, out, reas, cost = v
    t['answers'] += n
    t['input'] += inp
    t['cached_input'] += cached
    t['output'] += out
    t['reasoning'] += reas
    t['total'] += inp + out
    t['cost_usd'] += cost


def claude_vals(u):
    if not u:
        return None
    inp = (u.get('input_tokens') or 0) + (u.get('cache_write_tokens') or 0) + (u.get('cache_read_tokens') or 0)
    return (inp, u.get('cache_read_tokens') or 0, u.get('output_tokens') or 0, u.get('thinking_tokens') or 0,
            u.get('cost_usd') or 0.0)


def codex_vals(u, rate):
    if not u:
        return None
    inp, cached, w, out = (u.get(k, 0) for k in ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
                                                  'output_tokens'))
    cost = ((inp - cached - w) * rate['normal'] + cached * rate['cached'] + w * rate['write']
            + out * rate['output']) / 1e6
    return inp, cached, out, u.get('reasoning_output_tokens', 0), cost


def load_json(p):
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}


def item_usage(key):
    """{iid: {'scored': vals or None, 'source': str, 'spent': [vals, ...]}} for one model key; vals = (input, cached,
    output, reasoning, cost)."""
    res = {}

    def slot(iid):
        return res.setdefault(iid, {'scored': None, 'source': None, 'spent': []})

    for name, k, folder, extra in CLAUDE:
        if k != key:
            continue
        m, main_dir = MCFG[k], N / 'answers' / folder
        fx = (FIXCFG.get('models') or {}).get(k, {}).get('dir')   # fixed-question answers (may be the main folder)
        fbs = [x for x in m.get('fallbacks', []) if x.get('run')]   # answers the config takes from another run
        # every usage file once, so a folder named twice (a fix folder that is the main folder) counts once
        use = {}
        for d in [main_dir] + ([cfg.ROOT / fx] if fx else []) + [N / 'answers' / e for e in extra] \
                + [cfg.ROOT / x['dir'] for x in fbs]:
            use.setdefault(d.resolve(), load_json(d / '_usage.json'))
        main, fix = use[main_dir.resolve()], use[(cfg.ROOT / fx).resolve()] if fx else {}
        for src in use.values():
            for iid, v in src.items():
                a = claude_vals(v.get('all_attempts'))
                if a:
                    slot(iid)['spent'].append(a)
        ext = m.get('ext', '.txt')
        for iid, mp in MAP.items():
            if key in mp.values():
                src, tag = (fix, 'fix') if iid in FIX else (main, 'original')
                if iid not in FIX and not (main_dir / f'{iid}{ext}').exists():
                    src, tag = next(((use[(cfg.ROOT / x['dir']).resolve()], 'fallback') for x in fbs
                                     if (not x.get('items') or iid in x['items'])
                                     and (cfg.ROOT / x['dir'] / f"{iid}{x.get('ext', ext)}").exists()), (src, tag))
                slot(iid)['scored'] = claude_vals((src.get(iid) or {}).get('answer_attempt'))
                slot(iid)['source'] = tag
        return res
    for name, k, run, r, rate in GPT:
        if k != key:
            continue
        tok = {x['prompt_id']: x for x in csv.DictReader(open(X / run / 'token_usage.csv', encoding='utf-8'))}
        cp = list(csv.DictReader(open(X / run / 'cost_per_agent.csv', encoding='utf-8')))
        col = 'total_cost_usd' if 'total_cost_usd' in cp[0] else 'equivalent_cost_usd'
        cost = {x['prompt_id']: float(x[col]) for x in cp}
        orig = {iid: (int(x['input_tokens']), int(x['cached_input_tokens']), int(x['output_tokens']),
                      int(x['reasoning_output_tokens']), cost[iid]) for iid, x in tok.items()}
        for iid, v in orig.items():
            slot(iid)['spent'].append(v)
        runs = {}
        for tag, rn in (('rerun', r), ('fix', r + '_fix1'), ('fresh', r + '_samp1'), ('fresh', r + '_redo1')):
            au = load_json(N / '_work' / 'codex_reruns' / rn / 'audit.json')
            for iid, v in (au.get('usage') or {}).items():
                a = codex_vals(v.get('all_attempts'), rate)
                if a:
                    slot(iid)['spent'].append(a)
                if iid in set(au.get('ok', [])):
                    runs.setdefault(tag, {})[iid] = codex_vals(v.get('answer_attempt'), rate)
        for iid, mp in MAP.items():
            if key not in mp.values():
                continue
            for tag in ('fix', 'fresh', 'rerun'):
                if iid in runs.get(tag, {}) and (tag != 'fix' or iid in FIX):
                    slot(iid)['scored'], slot(iid)['source'] = runs[tag][iid], tag
                    break
            else:
                slot(iid)['scored'], slot(iid)['source'] = orig.get(iid), 'original'
        return res
    raise KeyError(key)


def main():
    rows, problems = {}, []
    for name, key, *_ in CLAUDE + GPT:
        scored, spent = zero(), zero()
        for iid, s in item_usage(key).items():
            for v in s['spent']:
                add(spent, v, n=0)
            if s['source']:
                if s['scored'] is None:
                    problems.append(f'{key} {iid}: scored answer has no usage record ({s["source"]})')
                else:
                    add(scored, s['scored'])
        spent['answers'] = scored['answers']
        want = sum(key in mp.values() for mp in MAP.values())
        if scored['answers'] != want:
            problems.append(f'{key}: {scored["answers"]} scored answers with usage, {want} in the judge prompts')
        rows[name] = {'scored': scored, 'spent': spent}
    (N / 'answers' / f'token_cost_2026Q3{cfg.SUFFIX}.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')
    lines = ['# Token use and API-equivalent cost, 2026Q3 respondents', '',
             'Output includes reasoning (thinking) tokens, which are billed as output. Input includes cached input. '
             'Standard list prices. Scored = the answers in the judge prompts (fixed-question answers for the 4 fixed '
             'items; fresh isolated-session answers for GPT); spent = every try.', '']
    for scope in ('scored', 'spent'):
        lines += [f'## {scope}', '', '| model | answers | input | cached input | output (incl. reasoning) | reasoning | '
                  'total | API-equivalent USD | output per answer | USD per answer |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for name, v in rows.items():
            t = v[scope]
            n = max(t['answers'], 1)
            lines.append(f"| {name} | {t['answers']} | {t['input']:,} | {t['cached_input']:,} | {t['output']:,} | "
                         f"{t['reasoning']:,} | {t['total']:,} | ${t['cost_usd']:,.2f} | {t['output'] // n:,} | "
                         f"${t['cost_usd'] / n:.3f} |")
        lines.append('')
    (N / 'answers' / f'token_cost_2026Q3{cfg.SUFFIX}.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    print('\n'.join(lines))
    print('problems:', problems or 'none')
    return not problems


if __name__ == '__main__':
    raise SystemExit(0 if main() else 1)
