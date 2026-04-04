"""
Integritas CME Outcomes Harmonizer
3-file upload: Key + Exchange + Nexus → unified analytics dashboard
"""

import io, re, math
from collections import defaultdict, Counter

import streamlit as st
import pandas as pd
import openpyxl
from scipy import stats

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — KEY FILE PARSER
# ══════════════════════════════════════════════════════════════════════════════

def parse_key_file(file_bytes):
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    questions = []
    header = rows[0]
    col_idx = {}
    for i, h in enumerate(header):
        if h:
            col_idx[str(h).strip().lower()] = i
    q_col   = col_idx.get('question text', 6)
    qn_col  = col_idx.get('questionnaire', 1)
    sc_col  = col_idx.get('score', 3)
    so_col  = col_idx.get('sort', 5)
    tp_col  = col_idx.get('type', 2)
    ans_col = col_idx.get('answers', 7)

    for row in rows[1:]:
        if not any(row):
            continue
        questionnaire = str(row[qn_col] or '').strip().lower()
        q_text = str(row[q_col] or '').strip() if row[q_col] else None
        if not q_text:
            continue

        if questionnaire.endswith('-pre'):        section = 'pre'
        elif questionnaire.endswith('-post'):     section = 'post'
        elif questionnaire.endswith('-eval'):     section = 'eval'
        elif questionnaire.endswith('-followup'): section = 'followup'
        else:                                     section = 'eval'

        score_val = str(row[sc_col] or '').strip()
        is_mcq = score_val == '1'
        q_type = str(row[tp_col] or '').strip().lower()
        is_likert = 'single' in q_type and not is_mcq

        options = []
        correct_answer = None
        for v in (row[ans_col:] if len(row) > ans_col else []):
            if v is None:
                continue
            s = str(v).strip()
            if not s:
                continue
            if s.startswith('*'):
                clean = s[1:].strip()
                correct_answer = clean
                options.append(clean)
            else:
                options.append(s)

        sort_val = int(str(row[so_col]).strip()) if row[so_col] and str(row[so_col]).strip().isdigit() else 99

        questions.append({
            'section': section, 'text': q_text,
            'correct_answer': correct_answer, 'options': options,
            'sort': sort_val, 'is_mcq': is_mcq, 'is_likert': is_likert,
        })

    questions.sort(key=lambda q: (q['section'], q['sort']))
    return questions


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — EXCHANGE DATA PARSER
# ══════════════════════════════════════════════════════════════════════════════

def parse_exchange_data(file_bytes):
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if len(all_rows) < 4:
        return []

    r0, r1, r2 = all_rows[0], all_rows[1], all_rows[2]

    pre_start = post_start = eval_start = None
    for i, v in enumerate(r1):
        sv = str(v).strip() if v else ''
        if sv == 'PRE'         and pre_start  is None: pre_start  = i
        if sv == 'POST'        and post_start is None: post_start = i
        if sv in ('EVALUATION','EVAL') and eval_start is None: eval_start = i

    meta_end = 12

    def get_section(ci):
        if ci < meta_end: return 'meta'
        if eval_start and ci >= eval_start: return 'eval'
        if post_start and ci >= post_start: return 'post'
        if pre_start  and ci >= pre_start:  return 'pre'
        return 'meta'

    records = []
    for row in all_rows[3:]:
        if not any(row): continue
        if all(str(v or '').strip() in ('', '\xa0') for v in row): continue

        def gv(idx):
            v = row[idx] if idx < len(row) else None
            return None if v in (None, '\xa0', '') else str(v).strip()

        rec = {
            '_source': 'Exchange', '_id': gv(1) or gv(10),
            '_has_post': False, '_has_eval': False, '_has_followup': False,
            'meta': {
                'email': gv(1), 'last_name': gv(2), 'first_name': gv(3),
                'zip': gv(4), 'credentials': gv(5), 'specialty': gv(6),
            },
            'pre': {}, 'post': {}, 'eval': {}, 'followup': {},
        }

        for ci in range(meta_end, len(r2)):
            q_text = str(r2[ci] or '').strip() if ci < len(r2) else ''
            if not q_text or q_text == '\xa0': continue
            val = gv(ci)
            if val is None: continue
            sec = get_section(ci)
            if sec == 'pre':
                rec['pre'][q_text] = val
            elif sec == 'post':
                rec['post'][q_text] = val
                rec['_has_post'] = True
            elif sec == 'eval':
                rec['eval'][q_text] = val
                rec['_has_eval'] = True

        records.append(rec)
    return records


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — NEXUS DATA PARSER
# ══════════════════════════════════════════════════════════════════════════════

def _sheet_to_dicts(ws):
    rows = list(ws.iter_rows(values_only=True))
    if not rows: return []
    headers = [str(h).strip() if h and str(h).strip() != '---' else None for h in rows[0]]
    result = []
    for row in rows[1:]:
        if not any(row): continue
        rec = {}
        for h, v in zip(headers, row):
            if h and v not in (None, '\xa0', ''):
                rec[h] = str(v).strip()
        if rec: result.append(rec)
    return result


def parse_nexus_data(file_bytes):
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)

    def get_sheet(*names):
        for name in names:
            for s in wb.sheetnames:
                if s.strip().lower() == name.lower():
                    return _sheet_to_dicts(wb[s])
        return []

    pre_rows  = get_sheet('Pre-Test', 'Pre')
    post_rows = get_sheet('Post')
    eval_rows = get_sheet('Eval', 'Evaluation')
    fu_rows   = get_sheet('Follow Up', 'Follow-Up', 'FollowUp')
    wb.close()

    def make_map(rows):
        m = {}
        for r in rows:
            id_val = r.get('ID') or r.get('id') or r.get('Id')
            if id_val: m[str(id_val).strip()] = r
        return m

    post_map = make_map(post_rows)
    eval_map = make_map(eval_rows)
    fu_map   = make_map(fu_rows)

    records = []
    for pre in pre_rows:
        id_val = str(pre.get('ID') or pre.get('id') or '').strip()
        post = post_map.get(id_val, {})
        ev   = eval_map.get(id_val, {})
        fu   = fu_map.get(id_val, {})
        rec = {
            '_source': 'Nexus', '_id': id_val,
            '_has_post': bool(post), '_has_eval': bool(ev), '_has_followup': bool(fu),
            'meta': {
                'specialty':    ev.get('Specialty:')    or ev.get('Specialty')    or pre.get('Specialty:'),
                'credentials':  ev.get('I am a(n):')    or pre.get('I am a(n):'),
                'practice_type':ev.get('Practice Type:') or ev.get('Practice Type'),
                'years':        ev.get('How long have you been in practice?'),
            },
            'pre':      {k: v for k, v in pre.items() if k != 'ID'},
            'post':     {k: v for k, v in post.items() if k != 'ID'},
            'eval':     {k: v for k, v in ev.items()   if k != 'ID'},
            'followup': {k: v for k, v in fu.items()   if k != 'ID'},
        }
        records.append(rec)
    return records


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — MATCHING & SCORING
# ══════════════════════════════════════════════════════════════════════════════

_STOP = {'the','a','an','of','in','to','for','and','or','is','are','was',
         'be','this','that','with','as','at','by','from','your','you','how',
         'what','which','please','following','have','has','do','will','would'}

def _norm(text):
    t = text.lower()
    t = re.sub(r'\b(are|do|will)\s+you\s+(currently|now)\b', 'are you', t)
    t = re.sub(r'\bwill you now\b', 'do you', t)
    t = re.sub(r'[^\w\s]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

def _text_sim(a, b):
    wa = set(_norm(a).split()) - _STOP
    wb = set(_norm(b).split()) - _STOP
    if not wa or not wb: return 0.0
    return len(wa & wb) / max(len(wa), len(wb))

def find_best_match(q_text, answer_dict, threshold=0.35):
    best_score, best_key = 0.0, None
    for k in answer_dict:
        s = _text_sim(q_text, k)
        if s > best_score:
            best_score, best_key = s, k
    return best_key if best_score >= threshold else None

def score_answer(val, correct):
    if not val or not correct: return None
    return 1 if val.strip().lower() == correct.strip().lower() else 0

LIKERT_MAP = {
    'never': 1, '25% of the time': 2, '50% of the time': 3,
    '75% of the time': 4, '100% of the time': 5,
    'not at all': 1, 'slightly': 2, 'somewhat': 3, 'very': 4, 'extremely': 5,
    'strongly disagree': 1, 'disagree': 2, 'neutral': 3, 'agree': 4, 'strongly agree': 5,
    'not at all confident': 1, 'not very confident': 2, 'somewhat confident': 3,
    'very confident': 4, 'extremely confident': 5,
    '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
}

def to_likert(val):
    if not val: return None
    s = str(val).strip().lower()
    if s in LIKERT_MAP: return LIKERT_MAP[s]
    try:
        f = float(s)
        if 1 <= f <= 5: return f
    except (ValueError, TypeError):
        pass
    return None


def build_unified(questions, ex_records, nx_records):
    """
    Build unified dataset. For each question in the Key:
    - Look in the matching section (pre/post/eval/followup)
    - For MCQ/Likert questions that are in 'pre' section, ALSO look in 'post'
      section to capture post-test answers (same question, different timepoint)
    - Also search eval section for Likert post questions (WILL YOU NOW)
    """
    all_records = ex_records + nx_records
    unified = []
    for rec in all_records:
        row = {
            '_source':       rec['_source'],
            '_id':           rec.get('_id'),
            '_has_post':     rec.get('_has_post', False),
            '_has_eval':     rec.get('_has_eval', False),
            '_has_followup': rec.get('_has_followup', False),
            'specialty':     rec.get('meta', {}).get('specialty'),
            'credentials':   rec.get('meta', {}).get('credentials'),
            'practice_type': rec.get('meta', {}).get('practice_type'),
            'years':         rec.get('meta', {}).get('years'),
        }
        for q in questions:
            # PRE answer
            pre_answers = rec.get('pre', {})
            pre_match = find_best_match(q['text'], pre_answers)
            pre_val = pre_answers.get(pre_match) if pre_match else None

            # Also check the section directly
            sec_answers = rec.get(q['section'], {})
            if q['section'] != 'pre':
                sec_match = find_best_match(q['text'], sec_answers)
                pre_val = sec_answers.get(sec_match) if sec_match else pre_val

            col = f"PRE_{q['text'][:80]}"
            row[col] = pre_val
            if q['is_mcq'] and pre_val is not None:
                row[f"{col}__SCORE"] = score_answer(pre_val, q['correct_answer'])
            if q['is_likert'] and pre_val is not None:
                row[f"{col}__LIKERT"] = to_likert(pre_val)

            # POST answer — look in post dict for same question
            post_answers = rec.get('post', {})
            post_match = find_best_match(q['text'], post_answers)
            post_val = post_answers.get(post_match) if post_match else None

            post_col = f"POST_{q['text'][:80]}"
            row[post_col] = post_val
            if q['is_mcq'] and post_val is not None:
                row[f"{post_col}__SCORE"] = score_answer(post_val, q['correct_answer'])
            if q['is_likert'] and post_val is not None:
                row[f"{post_col}__LIKERT"] = to_likert(post_val)

            # EVAL answer — for Likert questions also check eval (WILL YOU NOW variants)
            if q['is_likert']:
                eval_answers = rec.get('eval', {})
                # Look for "WILL YOU NOW" version of this question
                eval_match = find_best_match(q['text'], eval_answers)
                eval_val = eval_answers.get(eval_match) if eval_match else None
                eval_col = f"EVAL_{q['text'][:80]}"
                row[eval_col] = eval_val
                if eval_val is not None:
                    row[f"{eval_col}__LIKERT"] = to_likert(eval_val)

        # Store all eval answers for metric detection
        for k, v in rec.get('eval', {}).items():
            eval_col = f"EVAL_{k[:80]}"
            if eval_col not in row:
                row[eval_col] = v

        unified.append(row)
    return unified


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

def compute_mcq(df, questions):
    results = []
    for q in questions:
        if not q['is_mcq']: continue
        pre_col  = f"PRE_{q['text'][:80]}__SCORE"
        post_col = f"POST_{q['text'][:80]}__SCORE"
        if pre_col not in df.columns: continue

        def pct(col, src=None):
            d = df if src is None else df[df['_source'] == src]
            s = d[col].dropna() if col in d.columns else pd.Series([], dtype=float)
            if len(s) == 0: return None, 0
            return round(100 * s.mean(), 1), len(s)

        pre_pct, pre_n   = pct(pre_col)
        post_pct, post_n = pct(post_col)

        p_val = None
        if post_col in df.columns:
            ps = df[pre_col].dropna(); qs = df[post_col].dropna()
            if len(ps) >= 5 and len(qs) >= 5:
                try:
                    _, p_val, _, _ = stats.chi2_contingency([
                        [int(ps.sum()), len(ps)-int(ps.sum())],
                        [int(qs.sum()), len(qs)-int(qs.sum())]
                    ])
                except Exception: pass

        breakdown = {}
        for src in ('Exchange', 'Nexus'):
            pp, pn = pct(pre_col, src); qp, qn = pct(post_col, src)
            breakdown[src] = {'pre_pct': pp, 'pre_n': pn, 'post_pct': qp, 'post_n': qn}
        breakdown['Combined'] = {'pre_pct': pre_pct, 'pre_n': pre_n, 'post_pct': post_pct, 'post_n': post_n}

        results.append({
            'text': q['text'], 'correct_answer': q['correct_answer'],
            'pre_pct': pre_pct, 'post_pct': post_pct,
            'gain': round(post_pct - pre_pct, 1) if post_pct is not None and pre_pct is not None else None,
            'pre_n': pre_n, 'post_n': post_n, 'p_val': p_val, 'breakdown': breakdown,
        })
    return results


def compute_likert(df, questions):
    results = []
    for q in questions:
        if not q['is_likert']: continue
        pre_col  = f"PRE_{q['text'][:80]}__LIKERT"
        post_col = f"POST_{q['text'][:80]}__LIKERT"
        eval_col = f"EVAL_{q['text'][:80]}__LIKERT"

        pre_scores = []
        for try_col in [pre_col, eval_col]:
            if try_col in df.columns:
                pre_scores = df[try_col].dropna().tolist()
                if pre_scores: break
        if not pre_scores: continue

        post_scores = df[post_col].dropna().tolist() if post_col in df.columns else []
        pre_mean  = round(sum(pre_scores)/len(pre_scores), 2)
        post_mean = round(sum(post_scores)/len(post_scores), 2) if post_scores else None
        p_val = None
        if len(pre_scores) >= 3 and len(post_scores) >= 3:
            try: _, p_val = stats.ttest_ind(pre_scores, post_scores); p_val = round(p_val, 4)
            except Exception: pass

        results.append({
            'text': q['text'], 'pre_mean': pre_mean, 'post_mean': post_mean,
            'delta': round(post_mean - pre_mean, 2) if post_mean else None,
            'pre_n': len(pre_scores), 'post_n': len(post_scores), 'p_val': p_val,
        })
    return results


def compute_eval(df, questions):
    metrics = {}

    def find_col(*kws, exclude=None):
        exclude = exclude or []
        for col in df.columns:
            cl = col.lower()
            if all(kw.lower() in cl for kw in kws) and not any(ex in cl for ex in exclude):
                return col
        return None

    def pct_yes(col):
        if col not in df.columns: return None, 0
        nn = df[col].dropna()
        yes_vals = {'yes','y','agree','strongly agree','1','true'}
        n = sum(1 for v in nn if str(v).strip().lower() in yes_vals)
        return (round(100*n/len(nn), 1), len(nn)) if nn.size > 0 else (None, 0)

    def pct_agree(col):
        if col not in df.columns: return None, 0
        nn = df[col].dropna()
        vals = {'agree','strongly agree','4','5','yes'}
        n = sum(1 for v in nn if str(v).strip().lower() in vals)
        return (round(100*n/len(nn), 1), len(nn)) if nn.size > 0 else (None, 0)

    intent_col = find_col('intend') or find_col('as a result') or find_col('intent')
    if intent_col:
        pct, n = pct_agree(intent_col)
        metrics['intent'] = {'pct': pct, 'n': n, 'col': intent_col}

    rec_col = find_col('would you recommend') or find_col('recommend this program') or find_col('recommend', exclude=['lack of'])
    if rec_col:
        pct, n = pct_yes(rec_col)
        metrics['recommend'] = {'pct': pct, 'n': n, 'col': rec_col}

    bias_col = find_col('free of commercial') or find_col('free of bias') or find_col('commercial bias')
    if bias_col:
        pct, n = pct_yes(bias_col)
        metrics['bias_free'] = {'pct': pct, 'n': n, 'col': bias_col}

    new_col = find_col('percentage', 'content') or find_col('new to you') or find_col('percentage', 'educational')
    if new_col:
        vals = []
        for v in df[new_col].dropna():
            s = str(v).strip().rstrip('%')
            try:
                f = float(s)
                vals.append(f * 100 if f <= 1 else f)
            except ValueError: pass
        if vals: metrics['content_new'] = {'pct': round(sum(vals)/len(vals), 1), 'n': len(vals)}

    SAT_INC = ['faculty','content presented','useful tools','teaching','learning methods',
               'more confident','fair and balanced','relevant','enhanced','met the established','format']
    SAT_EXC = ['intend','modify','recommend','bias','percentage','barrier','plan to','specify','comment']
    sat_items, seen = [], set()
    for col in df.columns:
        cl = col.lower()
        if not any(i in cl for i in SAT_INC): continue
        if any(e in cl for e in SAT_EXC): continue
        pct, n = pct_agree(col)
        if pct is None or n == 0: continue
        label = re.sub(r'^(EVAL_|PRE_|POST_)', '', col)[:70]
        norm = label.lower()[:40]
        if norm in seen: continue
        seen.add(norm)
        sat_items.append({'label': label, 'pct': pct, 'n': n})
    metrics['satisfaction'] = sorted(sat_items, key=lambda x: x['pct'] or 0, reverse=True)

    bc_col = find_col('plan to change') or find_col('types of changes') or find_col('if you plan')
    if bc_col:
        counts = Counter()
        for v in df[bc_col].dropna():
            s = str(v).strip()
            if s and s.lower() != 'nan': counts[s[:70]] += 1
        metrics['behavior_change'] = dict(counts.most_common(10))

    for bt in ['patient','provider','system']:
        bc = find_col(f'{bt}-level') or find_col('barrier', bt)
        if bc:
            counts = Counter()
            for v in df[bc].dropna():
                s = str(v).strip()
                if s: counts[s[:60]] += 1
            metrics[f'barrier_{bt}'] = dict(counts.most_common(8))

    metrics['followup_n'] = int(df['_has_followup'].apply(
        lambda v: str(v).lower() in ('true','yes','1')).sum()) if '_has_followup' in df.columns else 0

    return metrics


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def pval_str(p):
    if p is None: return 'NS'
    if p < 0.001: return 'p<0.001 ✓'
    if p < 0.01:  return 'p<0.01 ✓'
    if p < 0.05:  return 'p<0.05 ✓'
    return f'p={p:.3f}'

def donut_svg(pct, color, size=90):
    if pct is None: pct = 0
    pct = min(100, max(0, pct))
    r = 32; circ = 2 * 3.14159 * r; dash = (pct/100) * circ
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 80 80">
  <circle cx="40" cy="40" r="{r}" fill="none" stroke="#1e293b" stroke-width="9"/>
  <circle cx="40" cy="40" r="{r}" fill="none" stroke="{color}" stroke-width="9"
    stroke-dasharray="{dash:.1f} {circ:.1f}" stroke-dashoffset="{circ/4:.1f}" stroke-linecap="round"/>
  <text x="40" y="45" text-anchor="middle" fill="white" font-size="15" font-weight="800">{pct}%</text>
</svg>"""

def prog_bar(pct, color='#3b82f6', label=''):
    if pct is None: pct = 0
    return f"""<div style="margin:4px 0">
  <div style="display:flex;justify-content:space-between;margin-bottom:3px">
    <span style="font-size:11px;color:#94a3b8">{label}</span>
    <span style="font-size:11px;font-weight:700;color:#f1f5f9">{pct}%</span>
  </div>
  <div style="background:#1e293b;border-radius:4px;height:8px">
    <div style="background:{color};width:{min(pct,100)}%;height:8px;border-radius:4px"></div>
  </div>
</div>"""

def stat_card(label, value, color='#3b82f6', info=''):
    return f"""<div style="background:linear-gradient(135deg,#1e293b,#0f172a);
    border:1px solid {color}33;border-radius:14px;padding:18px 14px;text-align:center">
  <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">{label}</div>
  <div style="font-size:32px;font-weight:900;color:{color}">{value}</div>
  <div style="font-size:10px;color:#475569;margin-top:4px">{info}</div>
</div>"""

def mcq_popup(r, df):
    pre  = r['pre_pct']  or 0
    post = r['post_pct'] or 0
    gain = r['gain']     or 0
    bd   = r.get('breakdown', {})
    pre_c  = int(pre  * r['pre_n']  / 100) if r['pre_n']  else 0
    post_c = int(post * r['post_n'] / 100) if r['post_n'] else 0

    with st.expander(f"📊 Details — {r['text'][:55]}..."):
        st.markdown(f"**{r['text']}**")
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**WHAT IT MEANS**")
            st.markdown("Knowledge assessment MCQ — measures the percentage of learners answering correctly before vs. after the educational program.")
            st.markdown("**FORMULA**")
            st.code("Correct answers / Total responses × 100 for each time point")
            st.markdown("**ACTUAL CALCULATION**")
            st.markdown(f"Pre: {pre_c}/{r['pre_n']} = {pre}% → Post: {post_c}/{r['post_n']} = {post}% (Δ+{gain}pp) | {pval_str(r['p_val'])}")
            if r['correct_answer']:
                st.markdown(f"✓ Correct answer: **{r['correct_answer']}**")
        with c2:
            st.markdown("**DATA SOURCE BREAKDOWN**")
            rows = []
            for src, d in bd.items():
                delta = f"+{d['post_pct']-d['pre_pct']:.1f}pp" if d.get('post_pct') and d.get('pre_pct') else '—'
                rows.append({'Source': src,
                             'n Pre':  d.get('pre_n', '—'),
                             'Pre %':  f"{d['pre_pct']}%" if d.get('pre_pct') is not None else '—',
                             'n Post': d.get('post_n', '—'),
                             'Post %': f"{d['post_pct']}%" if d.get('post_pct') is not None else '—',
                             'Δ':      delta})
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            st.success("✓ Both Exchange and Nexus data included in combined calculation")


def make_xlsx(df, questions):
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = 'Combined Data'
    cols = list(df.columns)
    for ci, col in enumerate(cols, 1): ws.cell(1, ci, col)
    for ri, row in enumerate(df.itertuples(index=False), 2):
        for ci, val in enumerate(row, 1): ws.cell(ri, ci, val)
    ws2 = wb.create_sheet('Question Key')
    ws2.append(['Section','Question Text','Correct Answer','Options','Is MCQ','Is Likert'])
    for q in questions:
        ws2.append([q['section'], q['text'], q.get('correct_answer',''),
                    ' | '.join(q.get('options',[])), q['is_mcq'], q['is_likert']])
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 7 — MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title='Integritas CME Outcomes Harmonizer',
        page_icon='📊', layout='wide',
        initial_sidebar_state='collapsed',
    )
    st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#0a0f1e}
[data-testid="stHeader"]{background:transparent}
.stTabs [data-baseweb="tab-list"]{background:#0f1e3a;padding:6px 8px;border-radius:10px;gap:4px}
.stTabs [data-baseweb="tab"]{background:transparent;border-radius:8px;padding:8px 16px;color:#64748b;font-weight:500;font-size:13px}
.stTabs [aria-selected="true"]{background:#3b82f6 !important;color:white !important}
div[data-testid="metric-container"]{background:#1e293b;border:1px solid #334155;border-radius:12px}
.stExpander{background:#0f172a;border:1px solid #1e3a5f;border-radius:10px}
label{color:#94a3b8 !important}
.stTextInput input{background:#0f1e3a !important;border:1px solid #1e3a5f !important;color:white !important}
</style>""", unsafe_allow_html=True)

    # Header
    h1, h2, h3 = st.columns([3,4,3])
    with h1:
        st.markdown("""<div style="padding:8px 0">
<span style="color:#3b82f6;font-size:22px;font-weight:900">Integritas</span>
<span style="color:white;font-size:22px;font-weight:700"> CME Outcomes Harmonizer</span>
<div style="color:#475569;font-size:11px;margin-top:2px">Nexus · ExchangeCME · Any Vendor</div>
</div>""", unsafe_allow_html=True)
    with h2:
        c1, c2 = st.columns(2)
        with c1: prog_name = st.text_input('', placeholder='Program name...', label_visibility='collapsed')
        with c2: proj_code = st.text_input('', placeholder='Project code (e.g. INT-2025-00)', label_visibility='collapsed')
    with h3:
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#1e3a5f;margin:8px 0 12px">', unsafe_allow_html=True)

    # Session state
    for k in ['questions','df','ex_n','nx_n','ai_insights','jcehp_article','jcehp_title']:
        if k not in st.session_state: st.session_state[k] = None

    # ── Upload screen ──
    if st.session_state.df is None:
        st.markdown('### Upload Your 3 Files')
        st.caption('The Question Key defines all questions and correct answers. Exchange and Nexus files contain respondent data.')
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('**📋 Question Key File**')
            st.caption('Exchange survey definition (.xlsx) — defines questions and correct answers using * marker')
            key_file = st.file_uploader('Key', type=['xlsx','xls'], label_visibility='collapsed', key='kf')
        with c2:
            st.markdown('**📊 Exchange Data File**')
            st.caption('Exchange respondent responses (.xlsx) — 3-row header with PRE/POST/EVALUATION sections')
            ex_file = st.file_uploader('Exchange', type=['xlsx','xls'], label_visibility='collapsed', key='ef')
        with c3:
            st.markdown('**📊 Nexus Data File**')
            st.caption('Nexus respondent responses (.xlsx) — multi-sheet format joined by ID')
            nx_file = st.file_uploader('Nexus', type=['xlsx','xls'], label_visibility='collapsed', key='nf')

        if key_file and ex_file and nx_file:
            if st.button('⚡ Process Files', type='primary', use_container_width=True):
                log = st.empty()
                log.info('Parsing Question Key...')
                questions = parse_key_file(key_file.read())
                st.session_state.questions = questions
                log.info(f'Key: {len(questions)} questions ({sum(1 for q in questions if q["is_mcq"])} MCQ, {sum(1 for q in questions if q["is_likert"])} Likert)')

                log.info('Parsing Exchange data...')
                ex_records = parse_exchange_data(ex_file.read())
                st.session_state.ex_n = len(ex_records)

                log.info('Parsing Nexus data...')
                nx_records = parse_nexus_data(nx_file.read())
                st.session_state.nx_n = len(nx_records)

                log.info('Matching questions and scoring...')
                unified = build_unified(questions, ex_records, nx_records)
                st.session_state.df = pd.DataFrame(unified)
                log.success(f'✅ Done — {len(unified)} respondents (Exchange: {len(ex_records)}, Nexus: {len(nx_records)})')
                st.rerun()
        return

    df = st.session_state.df
    questions = st.session_state.questions
    ex_n = st.session_state.ex_n or 0
    nx_n = st.session_state.nx_n or 0

    # ── Filter bar ──
    specs = sorted([s for s in df['specialty'].dropna().unique() if s]) if 'specialty' in df.columns else []
    f1, f2, f3 = st.columns([5,3,4])
    with f1:
        spec_sel = st.multiselect('Specialty', ['All'] + specs, default=['All'], label_visibility='collapsed')
    with f2:
        vend_sel = st.multiselect('Vendor', ['All','Exchange','Nexus'], default=['All'], label_visibility='collapsed')
    with f3:
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button('↺ New Upload'):
                for k in ['questions','df','ex_n','nx_n','ai_insights','jcehp_article','jcehp_title']:
                    st.session_state[k] = None
                st.rerun()
        with b2:
            st.download_button('⬇ XLSX', data=make_xlsx(df, questions),
                               file_name='CME_Combined.xlsx',
                               mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    df_f = df.copy()
    if 'All' not in spec_sel and spec_sel and 'specialty' in df_f.columns:
        df_f = df_f[df_f['specialty'].isin(spec_sel)]
    if 'All' not in vend_sel and vend_sel:
        df_f = df_f[df_f['_source'].isin(vend_sel)]

    ex_cnt = int((df_f['_source']=='Exchange').sum())
    nx_cnt = int((df_f['_source']=='Nexus').sum())
    st.caption(f"FILTER DATA  |  Exchange: {ex_cnt}  |  Nexus: {nx_cnt}  |  Total: {len(df_f)}")

    # Compute
    mcq    = compute_mcq(df_f, questions)
    likert = compute_likert(df_f, questions)
    ev     = compute_eval(df_f, questions)

    total_n  = len(df_f)
    has_post = int(df_f['_has_post'].apply(lambda v: str(v).lower() in ('true','yes','1')).sum())
    has_eval = int(df_f['_has_eval'].apply(lambda v: str(v).lower() in ('true','yes','1')).sum())
    has_fu   = ev.get('followup_n', 0)
    pre_only = total_n - has_post
    avg_gain = round(sum(r['gain'] or 0 for r in mcq) / max(len(mcq), 1), 1)

    # ── Tabs ──
    tabs = st.tabs(['📊 Overview','🎯 Knowledge','🧠 Competence','📋 Evaluation',
                    '🔑 Key Findings','🏆 Kirkpatrick','⭕ CIRCLE','🤖 AI Insights','📝 JCEHP'])

    # ─── OVERVIEW ─────────────────────────────────────────────────────────────
    with tabs[0]:
        cols = st.columns(6)
        for col, (lbl, val, color, info) in zip(cols, [
            ('Total Learners',   total_n,  '#3b82f6', f'{ex_cnt} Exchange + {nx_cnt} Nexus'),
            ('Pre-Only',         pre_only, '#a855f7', 'No post-test'),
            ('Pre+Post Matched', has_post, '#22c55e', f'{round(100*has_post/max(total_n,1))}% completion'),
            ('With Evaluation',  has_eval, '#f59e0b', 'Moore Levels 2-4'),
            ('Follow-Up',        has_fu,   '#06b6d4', 'Moore Level 5'),
            ('Avg % New Content', f"{ev.get('content_new',{}).get('pct','—')}%", '#ec4899', 'Content novelty'),
        ]):
            col.markdown(stat_card(lbl, val, color, info), unsafe_allow_html=True)

        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
        left, right = st.columns([6,4])

        with left:
            st.markdown('<div style="color:#94a3b8;font-size:11px;font-weight:700;letter-spacing:2px;margin-bottom:12px">KNOWLEDGE GAINS — PRE VS POST</div>', unsafe_allow_html=True)
            if not mcq:
                st.info("No scored MCQ questions found. Check your Key file — correct answers need a * prefix.")
            for r in mcq:
                pre = r['pre_pct'] or 0; post = r['post_pct'] or 0; gain = r['gain'] or 0
                ca, cb = st.columns([8,2])
                with ca:
                    st.markdown(f"**{r['text'][:70]}**")
                    st.markdown(prog_bar(pre,'#475569',f'PRE') + prog_bar(post,'#22c55e','POST'), unsafe_allow_html=True)
                    if r['correct_answer']:
                        st.markdown(f"<span style='font-size:11px;color:#22c55e'>✓ {r['correct_answer']}</span>", unsafe_allow_html=True)
                with cb:
                    c = '#22c55e' if gain > 0 else '#ef4444'
                    st.markdown(f'<div style="background:#0f172a;border:1px solid {c}44;border-radius:10px;padding:10px;text-align:center;margin-top:8px"><div style="font-size:10px;color:#475569">GAIN</div><div style="font-size:20px;font-weight:900;color:{c}">+{gain}pp</div></div>', unsafe_allow_html=True)
                st.markdown('')

        with right:
            st.markdown('<div style="color:#94a3b8;font-size:11px;font-weight:700;letter-spacing:2px;margin-bottom:12px">COMPETENCE SHIFTS</div>', unsafe_allow_html=True)
            if not likert:
                st.info("No Likert questions detected.")
            for r in likert:
                d = r['delta']
                st.markdown(f"""<div style="background:#0f172a;border:1px solid #1e3a5f;border-radius:8px;padding:10px 12px;margin-bottom:8px">
<div style="font-size:11px;color:#94a3b8;margin-bottom:4px">{r['text'][:55]}</div>
<div style="display:flex;align-items:center;gap:8px">
<span style="color:#64748b;font-size:13px">{r['pre_mean']}</span>
<span style="color:#475569">→</span>
<span style="color:#3b82f6;font-size:15px;font-weight:700">{r['post_mean'] or '—'}</span>
<span style="color:#22c55e;font-size:12px;margin-left:auto">{f'+{d}' if d else '—'}</span>
</div></div>""", unsafe_allow_html=True)

            st.markdown('<div style="color:#94a3b8;font-size:11px;font-weight:700;letter-spacing:2px;margin:12px 0 8px">SATISFACTION</div>', unsafe_allow_html=True)
            sc = st.columns(4)
            for col, (lbl, mk, color) in zip(sc, [
                ('Intent', 'intent', '#a855f7'), ('Recommend', 'recommend', '#22c55e'),
                ('Bias-Free', 'bias_free', '#3b82f6'), ('Content New', 'content_new', '#f59e0b'),
            ]):
                pct = ev.get(mk, {}).get('pct')
                col.markdown(f'<div style="text-align:center">{donut_svg(pct, color, 75)}<div style="font-size:9px;color:#64748b;margin-top:2px">{lbl}</div></div>', unsafe_allow_html=True)

    # ─── KNOWLEDGE ────────────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown('#### QUESTION-BY-QUESTION KNOWLEDGE ANALYSIS')
        st.caption('Click any question row to see definition, formula, exact calculation, and source breakdown.')
        if not mcq:
            st.warning("No scored MCQ questions detected. Ensure your Key file marks correct answers with *.")
        for r in mcq:
            pre = r['pre_pct'] or 0; post = r['post_pct'] or 0; gain = r['gain'] or 0
            st.markdown(f"**{r['text']}**")
            c1, c2 = st.columns([9,1])
            with c1:
                st.markdown(prog_bar(pre,'#475569',f'PRE  {pre}%  (n={r["pre_n"]})') + prog_bar(post,'#22c55e',f'POST  {post}%  (n={r["post_n"]})'), unsafe_allow_html=True)
                if r['correct_answer']:
                    st.markdown(f"<span style='font-size:11px;color:#22c55e'>✓ Correct answer: {r['correct_answer']}</span>", unsafe_allow_html=True)
            with c2:
                c = '#22c55e' if gain > 0 else '#ef4444'
                st.markdown(f'<div style="color:{c};font-size:18px;font-weight:900;text-align:right;padding-top:8px">+{gain}pp</div>', unsafe_allow_html=True)
            mcq_popup(r, df_f)
            st.markdown('---')

    # ─── COMPETENCE ───────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown('#### SELF-EFFICACY SHIFTS — BANDURA FRAMEWORK (LIKERT MEAN 1–5)')
        st.caption("Bandura's Self-Efficacy Theory — pre-program vs post-program confidence and frequency scores.")
        if not likert:
            st.info("No Likert/frequency questions found in the data.")
        for r in likert:
            d = r['delta']
            st.markdown(f"""<div style="background:#0f172a;border:1px solid #1e3a5f;border-radius:10px;padding:14px 16px;margin-bottom:10px">
<div style="font-size:13px;color:#e2e8f0;margin-bottom:8px">{r['text']}</div>
<div style="display:flex;align-items:center;gap:16px">
<span style="color:#64748b;font-size:12px">Pre: <b style="color:white">{r['pre_mean']}</b></span>
<span style="color:#475569">→</span>
<span style="color:#3b82f6;font-size:16px;font-weight:800">{r['post_mean'] or '—'}</span>
<span style="color:#22c55e;font-size:13px;margin-left:8px">{f'+{d}' if d else '—'}</span>
<span style="color:#475569;font-size:11px;margin-left:auto">{pval_str(r['p_val'])} | n={r['pre_n']}</span>
</div></div>""", unsafe_allow_html=True)

        bc = ev.get('behavior_change', {})
        if bc:
            st.markdown('#### INTENDED BEHAVIOR CHANGES')
            total_bc = sum(bc.values())
            html = ''
            for item, cnt in sorted(bc.items(), key=lambda x: x[1], reverse=True):
                pct = round(100*cnt/max(total_bc,1))
                html += prog_bar(pct, '#f59e0b', f"{item[:60]} ({cnt})")
            st.markdown(html, unsafe_allow_html=True)

        st.markdown('#### LEARNER DEMOGRAPHICS')
        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown('**Specialty**')
            if 'specialty' in df_f.columns:
                for k, v in df_f['specialty'].dropna().value_counts().head(10).items():
                    st.markdown(f"- {k}: **{v}** ({round(100*v/len(df_f))}%)")
        with d2:
            st.markdown('**Credentials**')
            if 'credentials' in df_f.columns:
                for k, v in df_f['credentials'].dropna().value_counts().head(8).items():
                    st.markdown(f"- {k}: **{v}**")
        with d3:
            st.markdown('**Practice Type**')
            if 'practice_type' in df_f.columns:
                for k, v in df_f['practice_type'].dropna().value_counts().head(8).items():
                    st.markdown(f"- {k}: **{v}**")

    # ─── EVALUATION ───────────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown('#### SATISFACTION AND QUALITY METRICS')
        d1, d2, d3, d4 = st.columns(4)
        for col, (lbl, mk, color) in zip([d1,d2,d3,d4], [
            ('Intent to Change','intent','#a855f7'), ('Would Recommend','recommend','#22c55e'),
            ('Bias-Free','bias_free','#3b82f6'), ('Content New','content_new','#f59e0b'),
        ]):
            m = ev.get(mk, {}); pct = m.get('pct'); n = m.get('n', 0)
            col.markdown(f"""<div style="text-align:center;padding:16px 8px;background:#0f172a;border:1px solid {color}33;border-radius:14px">
{donut_svg(pct, color, 100)}
<div style="font-size:12px;color:#94a3b8;margin-top:6px">{lbl}</div>
<div style="font-size:10px;color:#475569">n={n}</div>
</div>""", unsafe_allow_html=True)

        sat = ev.get('satisfaction', [])
        if sat:
            st.markdown('#### Satisfaction Items')
            colors = ['#3b82f6','#22c55e','#a855f7','#f59e0b','#ef4444','#06b6d4','#ec4899','#84cc16']
            html = ''
            for i, s in enumerate(sat):
                html += prog_bar(s['pct'], colors[i%len(colors)], f"{s['label'][:60]} (n={s['n']})")
            st.markdown(html, unsafe_allow_html=True)

        st.markdown('#### Vendor Mix')
        total = ex_cnt + nx_cnt
        st.markdown(
            prog_bar(round(100*ex_cnt/max(total,1)), '#22c55e', f'Exchange  {ex_cnt} ({round(100*ex_cnt/max(total,1))}%)') +
            prog_bar(round(100*nx_cnt/max(total,1)), '#3b82f6', f'Nexus  {nx_cnt} ({round(100*nx_cnt/max(total,1))}%)'),
            unsafe_allow_html=True)

        for bt, label in [('patient','Patient Barriers'),('provider','Provider Barriers'),('system','System Barriers')]:
            barriers = ev.get(f'barrier_{bt}', {})
            if barriers:
                st.markdown(f'#### {label}')
                total_b = sum(barriers.values())
                html = ''
                for item, cnt in sorted(barriers.items(), key=lambda x: x[1], reverse=True):
                    html += prog_bar(round(100*cnt/max(total_b,1)), '#ef4444', f"{item[:55]} ({cnt})")
                st.markdown(html, unsafe_allow_html=True)

    # ─── KEY FINDINGS ─────────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown('#### KEY FINDINGS — PRIOR VS. AFTER PROGRAM')
        left, right = st.columns(2)
        with left:
            st.markdown('<div style="color:#64748b;font-size:10px;letter-spacing:2px;margin-bottom:12px">PRIOR TO THE PROGRAM</div>', unsafe_allow_html=True)
            for r in mcq:
                pre = r['pre_pct'] or 0
                st.markdown(f"""<div style="display:flex;align-items:center;gap:12px;background:#0f172a;border-radius:10px;padding:12px;margin-bottom:8px">
<div style="width:56px;height:56px;border-radius:50%;background:#3b82f6;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:900;color:white;flex-shrink:0">{pre}%</div>
<div><div style="font-size:11px;color:#94a3b8">Answered correctly before the program</div>
<div style="font-size:12px;color:#e2e8f0;margin-top:3px">{r['text'][:65]}...</div>
<div style="font-size:10px;color:#475569">n={r['pre_n']} pre-test respondents</div></div></div>""", unsafe_allow_html=True)
        with right:
            st.markdown('<div style="color:#64748b;font-size:10px;letter-spacing:2px;margin-bottom:12px">AFTER PARTICIPATING IN THE PROGRAM</div>', unsafe_allow_html=True)
            for r in mcq:
                post = r['post_pct'] or 0; pre = r['pre_pct'] or 0
                rel = round((post-pre)/max(pre,1)*100) if pre > 0 else 0
                st.markdown(f"""<div style="display:flex;align-items:center;gap:12px;background:#0f172a;border-radius:10px;padding:12px;margin-bottom:8px">
<div style="position:relative;flex-shrink:0">
<div style="width:56px;height:56px;border-radius:50%;background:#22c55e;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:900;color:white">{post}%</div>
<div style="position:absolute;bottom:-4px;right:-4px;background:#f59e0b;border-radius:8px;padding:1px 5px;font-size:9px;font-weight:700;color:#000">+{rel}%</div>
</div>
<div><div style="font-size:11px;color:#94a3b8">Answered correctly — <b style="color:#22c55e">{rel}% relative increase</b></div>
<div style="font-size:12px;color:#e2e8f0;margin-top:3px">{r['text'][:65]}...</div>
<div style="font-size:10px;color:#475569">n={r['post_n']} matched pre/post</div></div></div>""", unsafe_allow_html=True)

        st.markdown('---')
        st.markdown('#### EDUCATIONAL IMPACT')
        ei1, ei2 = st.columns([3,2])
        with ei1:
            intent_m = ev.get('intent', {})
            st.markdown(f"""<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
{donut_svg(intent_m.get('pct'), '#a855f7', 70)}
<div><div style="font-size:16px;font-weight:700;color:white">Intend to change practice</div>
<div style="font-size:12px;color:#64748b">n={intent_m.get('n',0)} evaluators</div></div></div>""", unsafe_allow_html=True)
            bc = ev.get('behavior_change', {})
            if bc:
                total_bc = sum(bc.values())
                html = ''
                for item, cnt in list(sorted(bc.items(), key=lambda x: x[1], reverse=True))[:5]:
                    html += prog_bar(round(100*cnt/max(total_bc,1)), '#f59e0b', item[:50])
                st.markdown(html, unsafe_allow_html=True)
        with ei2:
            bias_m = ev.get('bias_free', {}); new_m = ev.get('content_new', {})
            st.markdown(f"""<div style="display:flex;gap:12px;flex-wrap:wrap">
<div style="text-align:center">{donut_svg(bias_m.get('pct'), '#3b82f6', 80)}<div style="font-size:10px;color:#64748b">Bias-free</div></div>
<div style="text-align:center">{donut_svg(new_m.get('pct'), '#f59e0b', 80)}<div style="font-size:10px;color:#64748b">New to learners</div></div>
</div>
<div style="text-align:center;margin-top:16px;background:#0f172a;border-radius:10px;padding:16px">
<div style="font-size:36px;font-weight:900;color:#22c55e">+{avg_gain}pp</div>
<div style="font-size:12px;color:#64748b">Average knowledge gain across {len(mcq)} questions</div>
</div>""", unsafe_allow_html=True)

    # ─── KIRKPATRICK ──────────────────────────────────────────────────────────
    with tabs[5]:
        st.markdown('#### Kirkpatrick Four-Level Evaluation Model')
        st.caption('Maps your program outcomes to the most widely recognized CE evaluation framework.')

        with st.expander('**1 — Reaction** | Did participants find the program engaging and relevant?', expanded=True):
            kc = st.columns(4)
            for col, (lbl, mk, color) in zip(kc, [
                ('Would Recommend','recommend','#22c55e'), ('Bias-Free','bias_free','#3b82f6'),
                ('Content New','content_new','#f59e0b'), ('Eval Completion',None,'#a855f7'),
            ]):
                pct = ev.get(mk, {}).get('pct') if mk else round(100*has_eval/max(total_n,1))
                col.markdown(f'<div style="text-align:center">{donut_svg(pct, color, 80)}<div style="font-size:10px;color:#64748b;margin-top:4px">{lbl}</div></div>', unsafe_allow_html=True)
            st.info('💡 High recommendation rate and low bias scores establish the credibility floor that makes Levels 2–4 findings defensible to pharma reviewers.')

        with st.expander('**2 — Learning** | Did participants acquire knowledge and skills?', expanded=True):
            st.markdown('**Knowledge acquisition — % correct responses pre vs post**')
            for r in mcq:
                st.markdown(f"**{r['text'][:70]}**")
                st.markdown(prog_bar(r['pre_pct'] or 0,'#475569',f'PRE  {r["pre_pct"]}%') + prog_bar(r['post_pct'] or 0,'#22c55e',f'POST  {r["post_pct"]}%  +{r["gain"]}pp'), unsafe_allow_html=True)
                if r['correct_answer']: st.caption(f'✓ {r["correct_answer"]}')
            if likert:
                st.markdown('**Competence shifts — Likert mean 1–5**')
                for r in likert:
                    st.markdown(f"**{r['text'][:55]}** — {r['pre_mean']} → {r['post_mean'] or '—'} (+{r['delta'] or '—'})")

        with st.expander('**3 — Behavior** | Did participants intend to apply what they learned?', expanded=True):
            kc3 = st.columns([1,3])
            with kc3[0]:
                intent_m = ev.get('intent', {})
                st.markdown(donut_svg(intent_m.get('pct'), '#a855f7', 90), unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center;font-size:12px;color:#94a3b8'>Intent to Change<br>n={intent_m.get('n',0)}</div>", unsafe_allow_html=True)
            with kc3[1]:
                bc = ev.get('behavior_change', {})
                if bc:
                    st.markdown('**Planned behavior changes:**')
                    total_bc = sum(bc.values())
                    for item, cnt in sorted(bc.items(), key=lambda x: x[1], reverse=True)[:5]:
                        st.markdown(prog_bar(round(100*cnt/max(total_bc,1)), '#f59e0b', f"{item[:55]}"), unsafe_allow_html=True)

        with st.expander('**4 — Results** | Did learners actually change their practice?', expanded=True):
            if has_fu > 0:
                st.metric('Follow-Up Respondents', has_fu)
                st.success('Follow-up data collected — reflects actual practice change.')
            else:
                st.info('No follow-up data available for this program.')

    # ─── CIRCLE ───────────────────────────────────────────────────────────────
    with tabs[6]:
        st.markdown('#### CIRCLE Framework for CE/CPD Outcomes')
        st.caption('ACEhp Almanac · 6 dimensions mapped from your existing data')
        barrier_count = len(ev.get('barrier_patient',{})) + len(ev.get('barrier_provider',{})) + len(ev.get('barrier_system',{}))
        circle_dims = [
            ('C','Clinician engagement', f"{round(100*has_eval/max(total_n,1))}%", 'completion rate', '#3b82f6'),
            ('I','Impact on learning',   f"+{avg_gain}pp", 'avg knowledge gain', '#22c55e'),
            ('R','Relevance to gaps',    f"{ev.get('content_new',{}).get('pct','—')}%", 'content was new', '#f59e0b'),
            ('C','Change in behavior',   f"{ev.get('intent',{}).get('pct','—')}%", 'intent to change', '#a855f7'),
            ('L','Linkage to patients',  f"{round(100*has_post/max(total_n,1))}%", 'practice ready', '#06b6d4'),
            ('E','Ecosystem factors',    str(barrier_count), 'distinct barriers identified', '#ec4899'),
        ]
        r1c = st.columns(3); r2c = st.columns(3)
        for col, (letter, name, val, sub, color) in zip(r1c+r2c, circle_dims):
            col.markdown(f"""<div style="background:#0f172a;border:1px solid {color}33;border-radius:14px;padding:20px 16px;text-align:center;margin-bottom:8px">
<div style="font-size:32px;font-weight:900;color:{color};margin-bottom:4px">{letter}</div>
<div style="font-size:11px;color:#64748b;margin-bottom:8px">{name}</div>
<div style="font-size:24px;font-weight:800;color:white;margin-bottom:4px">{val}</div>
<div style="font-size:10px;color:#475569">{sub}</div></div>""", unsafe_allow_html=True)

    # ─── AI INSIGHTS ──────────────────────────────────────────────────────────
    with tabs[7]:
        st.markdown('#### AI-Generated Outcomes Analysis')
        st.caption('Powered by Claude — generates grant-ready narrative from your data')
        api_key = st.text_input('Anthropic API Key', type='password', placeholder='sk-ant-...', help='Get at console.anthropic.com')

        def build_data():
            lines = [f"Program: {prog_name or 'CME Program'}", f"Total: {total_n} (Exchange: {ex_cnt}, Nexus: {nx_cnt})", f"Pre+Post: {has_post}", f"With Eval: {has_eval}"]
            for r in mcq: lines.append(f"MCQ: '{r['text'][:55]}' Pre={r['pre_pct']}% Post={r['post_pct']}% +{r['gain']}pp {pval_str(r['p_val'])}")
            for r in likert: lines.append(f"Likert: '{r['text'][:55]}' Pre={r['pre_mean']} Post={r['post_mean']} Δ={r['delta']}")
            lines += [f"Intent: {ev.get('intent',{}).get('pct')}%", f"Recommend: {ev.get('recommend',{}).get('pct')}%", f"Bias-Free: {ev.get('bias_free',{}).get('pct')}%", f"Content New: {ev.get('content_new',{}).get('pct')}%"]
            return '\n'.join(lines)

        if st.button('🤖 Generate Deep Insights', type='primary', disabled=not api_key):
            with st.spinner('Analyzing...'):
                try:
                    import requests
                    resp = requests.post('https://api.anthropic.com/v1/messages',
                        headers={'Content-Type':'application/json','x-api-key':api_key,'anthropic-version':'2023-06-01'},
                        json={'model':'claude-sonnet-4-20250514','max_tokens':2000,
                              'messages':[{'role':'user','content':f"Analyze this CME outcomes data and write a grant-ready narrative with sections: Executive Summary, Knowledge Outcomes, Competence Outcomes, Practice Impact, Program Quality, Recommendations.\n\nDATA:\n{build_data()}"}]},
                        timeout=90)
                    result = resp.json()
                    if 'content' in result: st.session_state.ai_insights = result['content'][0]['text']
                    else: st.error(f"API error: {result.get('error',{}).get('message','Unknown')}")
                except Exception as e: st.error(f"Error: {e}")

        if st.session_state.ai_insights:
            st.markdown(st.session_state.ai_insights)
            st.download_button('⬇ Download', st.session_state.ai_insights, 'CME_Insights.txt', 'text/plain')
        elif not api_key:
            st.info('Enter your Anthropic API key above to enable AI Insights.')

    # ─── JCEHP ────────────────────────────────────────────────────────────────
    with tabs[8]:
        st.markdown('#### JCEHP Article Writer')
        st.caption('Researches submission criteria, auto-generates title, writes publication-ready manuscript')
        api_key_j = st.text_input('Anthropic API Key', type='password', placeholder='sk-ant-...', key='jk')
        therapeutic_area = st.text_input('Therapeutic area', placeholder='e.g. Chronic Rhinosinusitis with Nasal Polyps (CRSwNP)')

        if st.button('📝 Research & Write JCEHP Article', type='primary', disabled=not api_key_j):
            with st.spinner('Researching JCEHP criteria...'):
                try:
                    import requests
                    def api(prompt, max_tokens=800, tools=None):
                        body = {'model':'claude-sonnet-4-20250514','max_tokens':max_tokens,'messages':[{'role':'user','content':prompt}]}
                        if tools: body['tools'] = tools
                        r = requests.post('https://api.anthropic.com/v1/messages',
                            headers={'Content-Type':'application/json','x-api-key':api_key_j,'anthropic-version':'2023-06-01'},
                            json=body, timeout=120)
                        result = r.json()
                        return ' '.join(b.get('text','') for b in result.get('content',[]) if b.get('type')=='text')

                    crit = api('Search for current JCEHP submission guidelines word limits required sections abstract format', 800, [{'type':'web_search_20250305','name':'web_search'}])
                    st.session_state.jcehp_title = api(f"Generate a 15-20 word JCEHP manuscript title for a CME program on {therapeutic_area} with knowledge gains averaging +{avg_gain}pp. Return ONLY the title.", 80)
                    st.session_state.jcehp_article = api(f"""Write a JCEHP manuscript. Title: {st.session_state.jcehp_title}
Criteria: {crit[:400]}
Data: {build_data()}
Sections: STRUCTURED ABSTRACT (250 words) | INTRODUCTION | METHODS | RESULTS | DISCUSSION | CONCLUSIONS | DISCLOSURES | REFERENCES (3 AMA references)""", 3000)
                except Exception as e: st.error(f"Error: {e}")

        if st.session_state.jcehp_title:
            st.markdown(f"**Generated Title:** {st.session_state.jcehp_title}")
        if st.session_state.jcehp_article:
            st.markdown(st.session_state.jcehp_article)
            st.download_button('⬇ Download Article', st.session_state.jcehp_article, 'JCEHP_Draft.txt', 'text/plain')
        elif not api_key_j:
            st.info('Enter your API key and therapeutic area, then click **Research & Write JCEHP Article**.')


if __name__ == '__main__':
    main()
