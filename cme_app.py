"""
Integritas CME Outcomes Harmonizer v6
Exchange format: single sheet, row0=meta headers, row1=section markers (PRE/POST/EVALUATION),
                 row2=question texts, row3+=respondents
Nexus format:   multi-sheet (PreNon, Pre, Post, Eval, Follow Up), ID-linked
Both vendors merged by matching question text fingerprints.
"""
import io, re, json
from collections import Counter, defaultdict
import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
import openpyxl

st.set_page_config(page_title="Integritas CME Outcomes Harmonizer", layout="wide", page_icon="🧬")

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
#MainMenu,footer,header{visibility:hidden}
.block-container{padding-top:0!important;max-width:100%!important}
section[data-testid="stSidebar"]{display:none}
body,.stApp{background:#0a0f1e!important}

/* HEADER */
.app-hdr{background:#0f172a;border-bottom:1px solid #1e3a5f;padding:10px 24px;
  display:flex;align-items:center;gap:14px}
.app-logo{font-size:18px;font-weight:700;color:#fff;white-space:nowrap}
.app-logo span{color:#22d3ee}
.pill-nx{background:#7c3aed22;border:1px solid #7c3aed;color:#a78bfa;
  padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700}
.pill-ex{background:#16a34a22;border:1px solid #16a34a;color:#4ade80;
  padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700}

/* FILTER BAR */
.fbar{background:#0f172a;border-bottom:1px solid #1e293b;padding:7px 24px;
  display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.flabel{color:#475569;font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.8px;white-space:nowrap}
.fdiv{width:1px;height:18px;background:#334155;margin:0 4px;flex-shrink:0}
.chip{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;
  border:1px solid #334155;color:#94a3b8;background:#1e293b;white-space:nowrap}
.c-all{border-color:#22d3ee!important;color:#22d3ee!important;background:#0891b220!important}
.c-nx {border-color:#a78bfa!important;color:#a78bfa!important;background:#7c3aed20!important}
.c-ex {border-color:#4ade80!important;color:#4ade80!important;background:#16a34a20!important}
.c-sp {border-color:#f59e0b!important;color:#f59e0b!important;background:#d9770620!important}

/* STAT CARDS */
.sc-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:20px}
.sc{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px 16px}
.sc-label{color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.sc-val{font-size:26px;font-weight:700;line-height:1}
.sc-sub{color:#475569;font-size:10px;margin-top:3px}

/* SECTION CARDS */
.scard{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:18px;margin-bottom:14px}
.stitle{color:#64748b;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:14px}

/* KN BARS */
.kn-q{color:#e2e8f0;font-size:13px;line-height:1.4;margin-bottom:6px}
.kn-gain{font-weight:700;float:right;margin-left:8px}
.bar-row{display:flex;align-items:center;gap:8px;margin:3px 0}
.bl{color:#475569;font-size:11px;width:38px;flex-shrink:0}
.bg{flex:1;background:#334155;border-radius:3px;height:7px}
.bf{border-radius:3px;height:7px}
.bp{color:#94a3b8;font-size:11px;width:40px;text-align:right}
.ck-lbl{color:#475569;font-size:11px;margin-top:3px}
.kn-item{padding:10px 0;border-bottom:1px solid #0f172a}
.kn-item:last-child{border-bottom:none}

/* EVAL CIRCLES */
.ev-circ-row{display:flex;gap:16px;justify-content:space-around;padding:6px 0}
.ev-c{text-align:center}
.ev-ring{width:88px;height:88px;border-radius:50%;border:6px solid;
  display:flex;align-items:center;justify-content:center;flex-direction:column;margin:0 auto 6px}
.ev-val{font-size:22px;font-weight:800;line-height:1}
.ev-name{color:#64748b;font-size:10px;text-align:center;max-width:90px;line-height:1.3}

/* SAT BARS */
.sat-row{display:flex;align-items:center;gap:10px;margin:8px 0}
.sat-lbl{color:#94a3b8;font-size:12px;flex:1;line-height:1.35}
.sat-bar{width:140px;background:#334155;border-radius:3px;height:7px;flex-shrink:0}
.sat-fill{border-radius:3px;height:7px}
.sat-val{color:#e2e8f0;font-size:12px;font-weight:600;width:38px;text-align:right;flex-shrink:0}

/* MODAL */
.modal-overlay{position:fixed;top:0;left:0;width:100%;height:100%;
  background:rgba(0,0,0,.82);z-index:99999;display:flex;align-items:center;justify-content:center}
.modal-card{background:#1a2744;border:1px solid #2a4a7f;border-radius:14px;
  width:660px;max-width:92vw;max-height:84vh;overflow-y:auto;padding:26px 30px;position:relative;
  box-shadow:0 24px 80px rgba(0,0,0,.6)}
.modal-close{position:absolute;top:14px;right:16px;color:#64748b;font-size:18px;
  cursor:pointer;background:none;border:none;padding:4px 8px;border-radius:4px}
.modal-close:hover{color:#e2e8f0;background:#334155}
.modal-qtitle{color:#e2e8f0;font-size:14px;font-weight:600;line-height:1.5;
  margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid #2a4a7f;padding-right:30px}
.ms{color:#4a7fa5;font-size:10px;text-transform:uppercase;letter-spacing:1.2px;
  font-weight:700;margin-bottom:4px;margin-top:14px}
.ms:first-of-type{margin-top:0}
.md{color:#94a3b8;font-size:13px;line-height:1.6}
.mf{background:#0d1b2e;border:1px solid #1e3a5f;border-radius:7px;
  padding:10px 14px;font-family:'Courier New',monospace;color:#4ade80;font-size:13px;line-height:1.5}
.mc{color:#e2e8f0;font-size:13px;line-height:1.7}
.mc strong{color:#22d3ee}
.mt{width:100%;border-collapse:collapse;margin-top:8px}
.mt th{color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:.7px;
  padding:6px 10px;border-bottom:1px solid #2a4a7f;text-align:left}
.mt td{color:#e2e8f0;font-size:12px;padding:8px 10px;border-bottom:1px solid #1e293b}
.mt tr:last-child td{border-bottom:none}
.bx{display:inline-block;padding:1px 7px;border-radius:3px;font-size:11px;font-weight:700}
.bx-ex{background:#16a34a22;border:1px solid #16a34a;color:#4ade80}
.bx-nx{background:#7c3aed22;border:1px solid #7c3aed;color:#a78bfa}
.bx-cb{background:#1d4ed822;border:1px solid #1d4ed8;color:#60a5fa}
.dp{color:#4ade80;font-weight:700}.dn{color:#f87171;font-weight:700}
.mv{display:flex;align-items:center;gap:8px;background:#16a34a15;border:1px solid #16a34a44;
  border-radius:5px;padding:7px 11px;margin-top:12px;color:#4ade80;font-size:12px}

/* ── FILTER FUNCTIONAL BUTTON ROW ── make them tiny pills */
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] > div[data-testid="stButton"] > button {
  padding: 2px 8px !important;
  border-radius: 20px !important;
  font-size: 10px !important;
  font-weight: 500 !important;
  height: 22px !important;
  min-height: 0 !important;
  line-height: 1.2 !important;
  white-space: nowrap !important;
}

/* ── GAIN BADGE ── */
.gain-badge {
  display: inline-block;
  padding: 2px 8px; border-radius: 4px;
  font-size: 12px; font-weight: 700;
}
.gain-pos { background: #16a34a20; border: 1px solid #16a34a; color: #4ade80; }
.gain-neg { background: #dc262620; border: 1px solid #dc2626; color: #f87171; }

/* ── CIRCLE STAT ── large colored number in a ring */
.big-ring {
  width: 90px; height: 90px; border-radius: 50%;
  border: 6px solid; display: flex; align-items: center;
  justify-content: center; flex-direction: column;
  margin: 0 auto 8px;
}
.big-ring-val { font-size: 22px; font-weight: 800; line-height: 1; }
.big-ring-sub { font-size: 9px; color: #475569; margin-top: 1px; }

/* ── IMPACT ROW ── horizontal metric strip */
.impact-strip {
  display: flex; gap: 0; border: 1px solid #334155;
  border-radius: 10px; overflow: hidden; margin-bottom: 16px;
}
.impact-cell {
  flex: 1; padding: 14px 16px; text-align: center;
  border-right: 1px solid #334155; background: #1e293b;
}
.impact-cell:last-child { border-right: none; }
.impact-val { font-size: 28px; font-weight: 700; line-height: 1; }
.impact-label { color: #64748b; font-size: 10px; text-transform: uppercase;
  letter-spacing: .5px; margin-top: 3px; }

/* ── KN VISUAL BARS ── cleaner pre/post */
.kn-pre-bar  { background: #f59e0b; }
.kn-post-bar { background: #4ade80; }

/* GENERAL */
h1,h2,h3,p,label{color:#e2e8f0!important}
.stTextInput input{background:#1e293b!important;border-color:#334155!important;color:#e2e8f0!important}
.stButton button{background:#1e293b!important;border:1px solid #334155!important;
  color:#e2e8f0!important;border-radius:6px!important}
.stButton button:hover{background:#334155!important}
.stFileUploader{background:#1e293b;border-radius:10px;padding:10px}
div[data-testid="stFileUploadDropzone"]{background:#0f172a!important;border-color:#334155!important}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
def _init():
    defs = {
        'tab': 'Overview', 'prog_name': '',
        'ex_data': None,   # parsed Exchange data
        'nx_data': None,   # parsed Nexus data
        'modal': None,
        'vendor_filter': 'All',
        'specialty_filter': 'All',
        'profession_filter': 'All',
        'api_key': '', 'ai_insights': [], 'jcehp_text': {},
    }
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v
_init()

# ══════════════════════════════════════════════════════════════════════════════
# EXCHANGE PARSER
# row0 = meta headers (Activity, Email, Last Name…, Questions/Answers)
# row1 = section markers: col0=program name, then PRE/POST/EVALUATION at start cols
# row2 = full question texts
# row3+ = one respondent per row
# ══════════════════════════════════════════════════════════════════════════════
LIKERT_ORDER = {
    'not at all familiar': 1, 'not very familiar': 2, 'neutral': 3,
    'somewhat familiar': 4, 'very familiar': 5,
    'not at all confident': 1, 'not very confident': 2,
    'somewhat confident': 4, 'very confident': 5,
    'strongly disagree': 1, 'disagree': 2, 'agree': 4, 'strongly agree': 5,
    'not at all': 1, 'slightly': 2, 'moderately': 3, 'very': 4, 'extremely': 5,
    '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
}

def to_likert(v):
    if v is None: return None
    if isinstance(v, (int, float)) and 1 <= float(v) <= 5: return float(v)
    return LIKERT_ORDER.get(str(v).strip().lower())

def norm_q(s):
    """First 8 words, lowercase, alphanum only — for question matching."""
    s = re.sub(r'[^a-zA-Z0-9\s]', ' ', str(s))
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return ' '.join(s.split()[:8])

def is_likert(vals):
    if not vals: return False
    return sum(1 for v in vals if str(v).strip().lower() in LIKERT_ORDER) / len(vals) > 0.4

def parse_exchange(file_bytes):
    wb  = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws  = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if len(all_rows) < 3:
        return None

    row0 = all_rows[0]   # meta headers
    row1 = all_rows[1]   # section markers
    row2 = all_rows[2]   # question texts

    # Find section start columns
    sections = {}  # 'PRE'/'POST'/'EVALUATION' -> start col
    for i, v in enumerate(row1):
        sv = str(v).strip().upper() if v else ''
        if sv in ('PRE', 'POST', 'EVALUATION') and sv not in sections:
            sections[sv] = i

    pre_start  = sections.get('PRE')
    post_start = sections.get('POST')
    eval_start = sections.get('EVALUATION')

    def col_section(i):
        if eval_start and i >= eval_start: return 'EVAL'
        if post_start and i >= post_start: return 'POST'
        if pre_start  and i >= pre_start:  return 'PRE'
        return 'META'

    # Build column definitions
    cols = []
    for i, q_text in enumerate(row2):
        meta_hdr = row0[i] if i < len(row0) else None
        sec = col_section(i)
        label = str(q_text).strip() if q_text and str(q_text).strip() not in ('', '\xa0') else (
                str(meta_hdr).strip() if meta_hdr and str(meta_hdr).strip() not in ('', '\xa0') else None)
        cols.append({'idx': i, 'section': sec, 'label': label})

    # Parse respondent rows
    respondents = []
    for r in all_rows[3:]:
        email = r[1] if len(r) > 1 else None
        if not email or str(email).strip() in ('', '\xa0'): continue
        rec = {'_source': 'Exchange'}
        for c in cols:
            if c['label'] is None: continue
            val = r[c['idx']] if c['idx'] < len(r) else None
            if val and str(val).strip() == '\xa0': val = None
            key = f"{c['section']}__{c['label']}"
            rec[key] = val
        # shortcuts
        rec['_specialty']  = rec.get('EVAL__Specialty:') or rec.get('META__Speciality')
        rec['_profession'] = rec.get('EVAL__I am a(n):')
        rec['_practice']   = rec.get('EVAL__Practice Type:')
        respondents.append(rec)

    # Identify PRE / POST / EVAL question lists
    pre_qs  = [c['label'] for c in cols if c['section'] == 'PRE'  and c['label']]
    post_qs = [c['label'] for c in cols if c['section'] == 'POST' and c['label']]
    eval_qs = [c['label'] for c in cols if c['section'] == 'EVAL' and c['label']]

    return {
        'respondents': respondents,
        'pre_qs': pre_qs,
        'post_qs': post_qs,
        'eval_qs': eval_qs,
        'n_pre': len(respondents),  # Exchange: all rows are pre
        'n_post': sum(1 for r in respondents if any(
            r.get(f'POST__{q}') for q in post_qs[:1])),
    }


# ══════════════════════════════════════════════════════════════════════════════
# NEXUS PARSER
# Sheets: PreNon (pre-only), Pre (pre, linked), Post (post), Eval, Follow Up
# Linked by ID column
# ══════════════════════════════════════════════════════════════════════════════
def parse_nexus(file_bytes):
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    sheet_map = {s.lower().replace(' ', '_'): s for s in wb.sheetnames}

    def read(key_variants):
        for k in key_variants:
            if k in sheet_map:
                ws = wb[sheet_map[k]]
                rows = list(ws.iter_rows(values_only=True))
                if not rows: return {}, []
                headers = [str(h).strip() if h else None for h in rows[0]]
                idx = {h: i for i, h in enumerate(headers) if h}
                return idx, rows[1:]
        return {}, []

    pre_idx,    pre_rows    = read(['pre'])
    prenon_idx, prenon_rows = read(['prenon'])
    post_idx,   post_rows   = read(['post'])
    eval_idx,   eval_rows   = read(['eval'])
    fu_idx,     fu_rows     = read(['follow_up', 'follow-up'])
    wb.close()

    def by_id(idx, rows):
        if 'ID' not in idx: return {}
        ic = idx['ID']
        return {str(r[ic]).strip(): r for r in rows if r[ic] is not None}

    post_d = by_id(post_idx, post_rows)
    eval_d = by_id(eval_idx, eval_rows)
    fu_d   = by_id(fu_idx,   fu_rows)

    def make_rec(pre_row, idx_map, is_prenon=False):
        rec = {'_source': 'Nexus'}
        id_col = idx_map.get('ID')
        rid = str(pre_row[id_col]).strip() if id_col is not None and pre_row[id_col] else None
        rec['_id'] = rid

        for h, ci in idx_map.items():
            if h == 'ID': continue
            val = pre_row[ci] if ci < len(pre_row) else None
            rec[f'PRE__{h}'] = val

        if rid and rid in post_d:
            pr = post_d[rid]
            for h, ci in post_idx.items():
                if h == 'ID': continue
                rec[f'POST__{h}'] = pr[ci] if ci < len(pr) else None

        if rid and rid in eval_d:
            er = eval_d[rid]
            for h, ci in eval_idx.items():
                if h == 'ID': continue
                rec[f'EVAL__{h}'] = er[ci] if ci < len(er) else None

        if rid and rid in fu_d:
            fr = fu_d[rid]
            for h, ci in fu_idx.items():
                if h == 'ID': continue
                rec[f'FU__{h}'] = fr[ci] if ci < len(fr) else None

        rec['_has_post'] = rid in post_d if rid else False
        rec['_has_eval'] = rid in eval_d if rid else False
        rec['_is_prenon'] = is_prenon

        # shortcuts
        ev = eval_d.get(rid, [None]*60) if rid else [None]*60
        ei = eval_idx
        rec['_profession'] = ev[ei['I am a(n):']] if 'I am a(n):' in ei and ev[ei['I am a(n):']] is not None else None
        rec['_specialty']  = ev[ei['Specialty:']] if 'Specialty:' in ei and ev[ei['Specialty:']] is not None else None
        rec['_practice']   = ev[ei['Practice Type:']] if 'Practice Type:' in ei and ev[ei['Practice Type:']] is not None else None

        return rec

    respondents = []
    for r in prenon_rows: respondents.append(make_rec(r, prenon_idx, True))
    for r in pre_rows:    respondents.append(make_rec(r, pre_idx,    False))

    pre_qs  = [h for h in pre_idx  if h != 'ID']
    post_qs = [h for h in post_idx if h != 'ID']
    eval_qs = [h for h in eval_idx if h != 'ID']

    return {
        'respondents': respondents,
        'pre_qs': pre_qs,
        'post_qs': post_qs,
        'eval_qs': eval_qs,
        'n_pre': len(respondents),
        'n_post': sum(1 for r in respondents if r.get('_has_post')),
    }


# ══════════════════════════════════════════════════════════════════════════════
# MERGE + MATCH PRE/POST PAIRS ACROSS VENDORS
# ══════════════════════════════════════════════════════════════════════════════
def match_questions(ex_data, nx_data):
    """
    Match PRE questions to POST questions across both vendors using text fingerprint.
    Returns list of dicts:
      label, correct, pre_pct, post_pct, gain, n,
      ex_pre, ex_post, ex_n, nx_pre, nx_post, nx_n,
      is_likert (bool)
    """
    def get_col_vals(respondents, section, label):
        key = f'{section}__{label}'
        return [r.get(key) for r in respondents if r.get(key) is not None]

    all_resp = []
    ex_resp  = ex_data['respondents'] if ex_data else []
    nx_resp  = nx_data['respondents'] if nx_data else []
    all_resp = ex_resp + nx_resp

    # Build fingerprint sets
    ex_pre  = ex_data['pre_qs']  if ex_data else []
    nx_pre  = nx_data['pre_qs']  if nx_data else []
    ex_post = ex_data['post_qs'] if ex_data else []
    nx_post = nx_data['post_qs'] if nx_data else []

    # Build unified pre/post question list by matching fingerprints
    def fp(q): return norm_q(q)

    # Map: fp -> canonical label (prefer longer text)
    pre_fp_map  = {}
    post_fp_map = {}

    for q in ex_pre + nx_pre:
        f = fp(q)
        if f not in pre_fp_map or len(q) > len(pre_fp_map[f]):
            pre_fp_map[f] = q

    for q in ex_post + nx_post:
        f = fp(q)
        if f not in post_fp_map or len(q) > len(post_fp_map[f]):
            post_fp_map[f] = q

    # Match pre → post by fingerprint similarity
    pairs = []
    used_post = set()

    for pre_f, pre_label in pre_fp_map.items():
        best_post = None
        best_score = 0
        pre_words = set(pre_f.split())
        for post_f, post_label in post_fp_map.items():
            if post_f in used_post: continue
            post_words = set(post_f.split())
            overlap = len(pre_words & post_words) / max(len(pre_words | post_words), 1)
            if overlap > best_score:
                best_score = overlap
                best_post = post_f

        if best_score >= 0.5 and best_post:
            used_post.add(best_post)
            post_label = post_fp_map[best_post]

            # Gather all pre values (both vendors)
            def pre_vals(src_resp, qs):
                for q in qs:
                    if fp(q) == pre_f:
                        return get_col_vals(src_resp, 'PRE', q)
                return []

            def post_vals(src_resp, qs):
                for q in qs:
                    if fp(q) == best_post:
                        return get_col_vals(src_resp, 'POST', q)
                return []

            ex_pre_v  = pre_vals(ex_resp, ex_pre)
            nx_pre_v  = pre_vals(nx_resp, nx_pre)
            ex_post_v = post_vals(ex_resp, ex_post)
            nx_post_v = post_vals(nx_resp, nx_post)

            all_pre_v  = ex_pre_v  + nx_pre_v
            all_post_v = ex_post_v + nx_post_v

            if not all_pre_v and not all_post_v: continue

            # Determine if Likert or MCQ
            sample = (all_pre_v + all_post_v)[:20]
            lk = is_likert(sample)

            if lk:
                ex_pre_nums  = [to_likert(v) for v in ex_pre_v  if to_likert(v)]
                nx_pre_nums  = [to_likert(v) for v in nx_pre_v  if to_likert(v)]
                ex_post_nums = [to_likert(v) for v in ex_post_v if to_likert(v)]
                nx_post_nums = [to_likert(v) for v in nx_post_v if to_likert(v)]
                all_pre_nums  = ex_pre_nums  + nx_pre_nums
                all_post_nums = ex_post_nums + nx_post_nums
                if not all_pre_nums or not all_post_nums: continue

                def mean(lst): return round(sum(lst)/len(lst), 2) if lst else None

                pairs.append({
                    'label':     pre_label,
                    'is_likert': True,
                    'pre_pct':   mean(all_pre_nums),
                    'post_pct':  mean(all_post_nums),
                    'gain':      round(mean(all_post_nums) - mean(all_pre_nums), 2) if all_pre_nums and all_post_nums else None,
                    'n':         len(all_pre_nums),
                    'ex_pre':    mean(ex_pre_nums),  'ex_post': mean(ex_post_nums), 'ex_n': len(ex_pre_nums),
                    'nx_pre':    mean(nx_pre_nums),  'nx_post': mean(nx_post_nums), 'nx_n': len(nx_pre_nums),
                    'unit':      '/5',
                })
            else:
                # MCQ: correct = modal post answer
                if not all_post_v: continue
                correct = Counter(str(v) for v in all_post_v).most_common(1)[0][0]

                def pct_correct(vals):
                    if not vals: return None, 0
                    n = len(vals)
                    c = sum(1 for v in vals if str(v) == correct)
                    return round(100*c/n, 1), n

                all_pre_pct,  all_pre_n  = pct_correct(all_pre_v)
                all_post_pct, all_post_n = pct_correct(all_post_v)
                ex_pre_pct,   ex_pre_n   = pct_correct(ex_pre_v)
                ex_post_pct,  ex_post_n  = pct_correct(ex_post_v)
                nx_pre_pct,   nx_pre_n   = pct_correct(nx_pre_v)
                nx_post_pct,  nx_post_n  = pct_correct(nx_post_v)

                if all_pre_n < 5 and all_post_n < 5: continue

                gain = round(all_post_pct - all_pre_pct, 1) if all_pre_pct is not None and all_post_pct is not None else None

                pairs.append({
                    'label':     pre_label,
                    'is_likert': False,
                    'correct':   correct,
                    'pre_pct':   all_pre_pct,
                    'post_pct':  all_post_pct,
                    'gain':      gain,
                    'n':         max(all_pre_n, all_post_n),
                    'pre_n':     all_pre_n,
                    'post_n':    all_post_n,
                    'ex_pre':    ex_pre_pct,  'ex_post': ex_post_pct, 'ex_n': ex_pre_n,
                    'nx_pre':    nx_pre_pct,  'nx_post': nx_post_pct, 'nx_n': nx_pre_n,
                    'unit':      '%',
                })

    # Sort: MCQ first (gains desc), then Likert
    mcq = sorted([p for p in pairs if not p['is_likert'] and p.get('gain') is not None],
                 key=lambda x: -(x['gain'] or 0))
    lk  = sorted([p for p in pairs if p['is_likert']],
                 key=lambda x: -(x['gain'] or 0))
    return mcq, lk


# ══════════════════════════════════════════════════════════════════════════════
# EVAL METRICS
# ══════════════════════════════════════════════════════════════════════════════

# Satisfaction question fingerprints (shared prefix in Nexus)
SAT_FPS = [
    'faculty for this activity were knowledgeable',
    'content presented was relevant and enhanced',
    'activity provided useful tools that will improve',
    'teaching and learning methods of this activity',
    'more confident in treating patients',
    'content provided fair and balanced',
    'intend to modify/change my clinical practice',
    'office and practice systems can accommodate',
    'patients can accommodate these changes',
    'patient access to the treatments provided will be',
]

SAT_SHORT = {
    'faculty for this activity were knowledgeable':         'Faculty knowledgeable & effective',
    'content presented was relevant and enhanced':          'Content relevant & enhanced knowledge',
    'activity provided useful tools that will improve':     'Useful tools for patient care',
    'teaching and learning methods of this activity':       'Teaching methods effective',
    'more confident in treating patients':                  'More confident treating patients',
    'content provided fair and balanced':                   'Content fair & balanced',
    'intend to modify/change my clinical practice':         'Intent to change practice',
    'office and practice systems can accommodate':          'Practice systems can accommodate',
    'patients can accommodate these changes':               'Patients can accommodate changes',
    'patient access to the treatments provided will be':    'Patient access is a barrier',
}

LO_FPS = [
    'identify shared decision-making strategies',
    'implement required laboratory testing',
    'determine clinical practice strategies to streamline',
    'describe clinical considerations for managing discontinuation',
]

def get_eval_respondents(ex_data, nx_data, spec_f='All', prof_f='All', vendor_f='All'):
    resp = []
    if ex_data and vendor_f in ('All', 'Exchange'):
        resp += ex_data['respondents']
    if nx_data and vendor_f in ('All', 'Nexus'):
        resp += [r for r in nx_data['respondents'] if r.get('_has_eval')]
    if spec_f != 'All':
        resp = [r for r in resp if str(r.get('_specialty') or '').strip() == spec_f]
    if prof_f != 'All':
        resp = [r for r in resp if str(r.get('_profession') or '').strip() == prof_f]
    return resp

def find_eval_key(resp, fp_text):
    """Find the eval key in a respondent dict whose label matches the fingerprint."""
    if not resp: return None
    sample = resp[0]
    for k in sample:
        if not k.startswith('EVAL__'): continue
        lbl = k[6:].lower()
        if fp_text.lower() in lbl:
            return k
    return None

def compute_sat_items(resp):
    items = []
    for fp in SAT_FPS:
        key = find_eval_key(resp, fp)
        if not key: continue
        vals = [to_likert(r.get(key)) for r in resp]
        vals = [v for v in vals if v is not None]
        if len(vals) < 3: continue
        ex_vals = [to_likert(r.get(key)) for r in resp if r.get('_source')=='Exchange']
        nx_vals = [to_likert(r.get(key)) for r in resp if r.get('_source')=='Nexus']
        ex_vals = [v for v in ex_vals if v is not None]
        nx_vals = [v for v in nx_vals if v is not None]
        items.append({
            'fp':    fp,
            'label': SAT_SHORT.get(fp, fp),
            'mean':  round(sum(vals)/len(vals), 2),
            'n':     len(vals),
            'ex_mean': round(sum(ex_vals)/len(ex_vals), 2) if ex_vals else None,
            'nx_mean': round(sum(nx_vals)/len(nx_vals), 2) if nx_vals else None,
            'ex_n':  len(ex_vals), 'nx_n': len(nx_vals),
        })
    return items

def yes_pct(resp, fp_text):
    key = find_eval_key(resp, fp_text)
    if not key: return None, 0
    vals = [str(r.get(key) or '').strip().lower() for r in resp if r.get(key)]
    n = len(vals)
    if n == 0: return None, 0
    yes = sum(1 for v in vals if v.startswith('yes') or v in ('agree','strongly agree'))
    return round(100*yes/n, 1), n

def compute_eval_metrics(resp):
    intent_p,  intent_n  = yes_pct(resp, 'intend to modify/change')
    rec_p,     rec_n     = yes_pct(resp, 'would you recommend this program')
    bias_p,    bias_n    = yes_pct(resp, 'free of commercial bias')

    # content new
    cn_key = find_eval_key(resp, 'percentage of the educational content')
    cn_vals = []
    if cn_key:
        for r in resp:
            v = r.get(cn_key)
            if v is None: continue
            try:
                f = float(str(v).strip())
                if f <= 1: f *= 100
                cn_vals.append(f * 100 if f <= 1 else f)
            except: pass
    cn_pct = round(sum(cn_vals)/len(cn_vals), 1) if cn_vals else None

    return {
        'intent':      {'pct': intent_p, 'n': intent_n},
        'recommend':   {'pct': rec_p,    'n': rec_n},
        'bias_free':   {'pct': bias_p,   'n': bias_n},
        'content_new': {'pct': cn_pct,   'n': len(cn_vals)},
        'n': len(resp),
    }

def compute_lo_items(resp):
    items = []
    for fp in LO_FPS:
        key = find_eval_key(resp, fp)
        if not key: continue
        vals = [to_likert(r.get(key)) for r in resp]
        vals = [v for v in vals if v is not None]
        if len(vals) < 3: continue
        items.append({
            'label': key[6:][:80],
            'mean': round(sum(vals)/len(vals), 2),
            'n': len(vals),
        })
    return items

def get_filter_options(ex_data, nx_data):
    all_resp = (ex_data['respondents'] if ex_data else []) + \
               ([r for r in nx_data['respondents'] if r.get('_has_eval')] if nx_data else [])
    specs  = sorted({str(r.get('_specialty')  or '').strip() for r in all_resp if r.get('_specialty')  and str(r.get('_specialty')).strip()})
    profs  = sorted({str(r.get('_profession') or '').strip() for r in all_resp if r.get('_profession') and str(r.get('_profession')).strip()})
    return specs, profs


# ══════════════════════════════════════════════════════════════════════════════
# MODAL BUILDER
# ══════════════════════════════════════════════════════════════════════════════
def build_modal(m):
    """
    Render modal as a pinned panel at the top of the page.
    The close button is a real Streamlit button — always visible and clickable.
    No reliance on JavaScript onclick for closing.
    """
    def fmt(v, u=''): return f'{v}{u}' if v is not None else '—'
    def dh(pre, post, u=''):
        if pre is None or post is None: return '—'
        d = round(post - pre, 1)
        sign = '+' if d >= 0 else ''
        css = 'dp' if d >= 0 else 'dn'
        return f'<span class="{css}">{sign}{d}{u}</span>'

    # ── close bar (always rendered first, always on top) ──
    close_col, _ = st.columns([1, 8])
    with close_col:
        if st.button("✕  Close details", key="modal_close", type="primary"):
            st.session_state['modal'] = None
            st.rerun()

    # ── build inner content ──
    srcs = ''
    for src, pre, post, n, u in m.get('sources', []):
        cls  = 'bx-ex' if src == 'Exchange' else ('bx-nx' if src == 'Nexus' else 'bx-cb')
        bold = ' style="font-weight:700"' if src == 'Combined' else ''
        srcs += (
            f'<tr{bold}>'
            f'<td><span class="bx {cls}">{src}</span></td>'
            f'<td>{fmt(n)}</td><td>{fmt(pre, u)}</td>'
            f'<td>{fmt(n)}</td><td>{fmt(post, u)}</td>'
            f'<td>{dh(pre, post, u)}</td>'
            f'</tr>'
        )

    table = (
        f'<div class="ms">Data Source Breakdown</div>'
        f'<table class="mt"><thead><tr>'
        f'<th>Source</th><th>n Pre</th><th>Pre {m.get("unit","")}</th>'
        f'<th>n Post</th><th>Post {m.get("unit","")}</th><th>Δ</th>'
        f'</tr></thead><tbody>{srcs}</tbody></table>'
    ) if srcs else ''

    correct = (
        f'<div style="margin-top:10px;padding:7px 11px;background:#16a34a15;'
        f'border:1px solid #16a34a44;border-radius:5px;color:#4ade80;font-size:12px">'
        f'✓ Correct answer: <strong>{m["correct"]}</strong></div>'
    ) if m.get('correct') else ''

    has_both = (
        any(s[0] == 'Exchange' for s in m.get('sources', [])) and
        any(s[0] == 'Nexus'    for s in m.get('sources', []))
    )
    verified = (
        '<div class="mv">✓ Both Exchange and Nexus data included in combined calculation</div>'
    ) if has_both else ''

    # ── render as a pinned card (not a fixed overlay — overlays get cut off by Streamlit) ──
    st.markdown(f"""
<div style="
  background:#1a2744;
  border:2px solid #22d3ee;
  border-radius:14px;
  padding:24px 28px;
  margin-bottom:20px;
  box-shadow:0 8px 40px rgba(0,0,0,.5);
">
  <div class="modal-qtitle" style="padding-right:0;margin-bottom:16px">{m.get('title', '')}</div>

  <div class="ms">What It Means</div>
  <div class="md">{m.get('definition', '')}</div>

  <div class="ms">Formula</div>
  <div class="mf">{m.get('formula', '')}</div>

  <div class="ms">Actual Calculation</div>
  <div class="mc">{m.get('calculation', '')}</div>

  {correct}
  {table}
  {verified}
</div>
""", unsafe_allow_html=True)

def kn_modal(q):
    u = q.get('unit', '%')
    ex_pre = q.get('ex_pre'); ex_post = q.get('ex_post'); ex_n = q.get('ex_n', 0)
    nx_pre = q.get('nx_pre'); nx_post = q.get('nx_post'); nx_n = q.get('nx_n', 0)
    cb_pre = q.get('pre_pct'); cb_post = q.get('post_pct'); cb_n = q.get('n', 0)
    if q['is_likert']:
        gain_str = f"{'+' if q['gain']>=0 else ''}{q['gain']}{u}"
        calc = f"Pre mean: <strong>{cb_pre}{u}</strong> → Post mean: <strong>{cb_post}{u}</strong> (Δ <strong>{gain_str}</strong>) | n={cb_n}"
        defn = 'Self-reported competence/familiarity on a 1–5 Likert scale. Measures Moore Level 4 (Competence).'
        formula = 'Mean Likert score (1–5) for matched pre/post respondents'
    else:
        gain_str = f"{'+' if (q['gain'] or 0)>=0 else ''}{q['gain']}pp"
        pre_raw  = round((cb_pre or 0)/100*(q.get('pre_n') or cb_n)) if cb_pre else '?'
        post_raw = round((cb_post or 0)/100*(q.get('post_n') or cb_n)) if cb_post else '?'
        calc = f"Pre: {pre_raw}/{q.get('pre_n','?')} = <strong>{cb_pre}%</strong> → Post: {post_raw}/{q.get('post_n','?')} = <strong>{cb_post}%</strong> (Δ <strong>{gain_str}</strong>)"
        defn = 'Knowledge assessment MCQ — measures % of learners answering correctly before vs. after the educational program. Moore Level 3 (Knowledge).'
        formula = 'Correct answers / Total responses × 100  for each time point'
    return {
        'title': q['label'], 'definition': defn, 'formula': formula,
        'calculation': calc, 'correct': q.get('correct'), 'unit': u,
        'sources': [
            ('Exchange', ex_pre, ex_post, ex_n, u),
            ('Nexus',    nx_pre, nx_post, nx_n, u),
            ('Combined', cb_pre, cb_post, cb_n, u),
        ],
    }

def sat_modal(s):
    return {
        'title': s['label'],
        'definition': 'Post-activity satisfaction rating on a 1–5 Likert scale.',
        'formula': 'Mean of all responses on 1–5 scale (post-activity evaluation only)',
        'calculation': f"Mean: <strong>{s['mean']}/5.0</strong> | n={s['n']}",
        'unit': '/5',
        'sources': [
            ('Exchange', None, s.get('ex_mean'), s.get('ex_n', 0), '/5'),
            ('Nexus',    None, s.get('nx_mean'), s.get('nx_n', 0), '/5'),
            ('Combined', None, s['mean'],         s['n'],           '/5'),
        ],
    }

def ev_modal(label, pct_v, n, definition):
    raw = round((pct_v or 0)/100*n) if pct_v and n else '?'
    return {
        'title': label, 'definition': definition,
        'formula': "Count of 'Yes' / Agree responses ÷ Total respondents × 100",
        'calculation': f"<strong>{raw}/{n} = {pct_v}%</strong>",
        'unit': '%',
        'sources': [('Combined', None, pct_v, n, '%')],
    }


# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD SCREEN
# ══════════════════════════════════════════════════════════════════════════════
def render_upload():
    st.markdown("""
<div style="padding:60px 32px;text-align:center">
  <div style="font-size:48px;margin-bottom:14px">🧬</div>
  <div style="color:#e2e8f0;font-size:24px;font-weight:700;margin-bottom:6px">Integritas CME Outcomes Harmonizer</div>
  <div style="color:#64748b;font-size:14px;margin-bottom:36px">Upload Exchange and Nexus vendor files to begin analysis</div>
</div>""", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div style="background:#1e293b;border:2px dashed #4ade80;border-radius:12px;padding:22px;text-align:center;margin-bottom:8px"><div style="font-size:30px">📊</div><div style="color:#4ade80;font-size:15px;font-weight:600;margin:6px 0">Exchange File</div><div style="color:#64748b;font-size:12px">Single-sheet .xlsx (PRE / POST / EVALUATION columns)</div></div>', unsafe_allow_html=True)
        ex_file = st.file_uploader("Exchange", type=['xlsx'], key='ex_up', label_visibility='collapsed')
    with c2:
        st.markdown('<div style="background:#1e293b;border:2px dashed #a78bfa;border-radius:12px;padding:22px;text-align:center;margin-bottom:8px"><div style="font-size:30px">📋</div><div style="color:#a78bfa;font-size:15px;font-weight:600;margin:6px 0">Nexus File</div><div style="color:#64748b;font-size:12px">Multi-sheet .xlsx (PreNon · Pre · Post · Eval · Follow Up)</div></div>', unsafe_allow_html=True)
        nx_file = st.file_uploader("Nexus", type=['xlsx'], key='nx_up', label_visibility='collapsed')
    if ex_file or nx_file:
        if st.button("🚀  Analyze Files", use_container_width=True):
            with st.spinner("Parsing and matching…"):
                if ex_file:
                    st.session_state['ex_data'] = parse_exchange(ex_file.read())
                    st.session_state['prog_name'] = ex_file.name.split('_')[0]
                if nx_file:
                    st.session_state['nx_data'] = parse_nexus(nx_file.read())
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# FILTER BAR
# ══════════════════════════════════════════════════════════════════════════════
def render_filter_bar(ex_data, nx_data):
    specs, profs = get_filter_options(ex_data, nx_data)
    sf = st.session_state.get('specialty_filter', 'All')
    pf = st.session_state.get('profession_filter', 'All')
    vf = st.session_state.get('vendor_filter', 'All')
    ex_n  = ex_data['n_pre'] if ex_data else 0
    nx_n  = nx_data['n_pre'] if nx_data else 0
    total = ex_n + nx_n

    # CSS for the filter system
    st.markdown("""
<style>
/* Active filter summary bar */
.fbar-summary {
  background: #0f172a;
  border-bottom: 1px solid #1e293b;
  padding: 7px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.fbar-label { color: #475569; font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .8px; white-space: nowrap; }
.fbar-active {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600;
}
.fbar-active.c-all { border: 1px solid #22d3ee; color: #22d3ee; background: #0891b215; }
.fbar-active.c-sp  { border: 1px solid #f59e0b; color: #f59e0b; background: #d9770615; }
.fbar-active.c-ex  { border: 1px solid #4ade80; color: #4ade80; background: #16a34a15; }
.fbar-active.c-nx  { border: 1px solid #a78bfa; color: #a78bfa; background: #7c3aed15; }
.fbar-divider { width:1px; height:14px; background:#334155; flex-shrink:0; }
/* Filter panel grid */
.fpanel {
  background: #0f172a;
  border-bottom: 2px solid #1e3a5f;
  padding: 12px 20px 16px;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
}
.fpanel-section { display: flex; flex-direction: column; gap: 6px; }
.fpanel-title { color: #475569; font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .8px; margin-bottom: 4px; }
.fpanel-pills { display: flex; flex-wrap: wrap; gap: 5px; }
.fpill {
  padding: 3px 11px; border-radius: 20px; font-size: 11px;
  border: 1px solid #334155; color: #94a3b8; background: #1e293b;
  white-space: nowrap; cursor: default;
}
/* Override Streamlit button styles inside filter panel */
div[data-testid="stButton"] button {
  padding: 3px 11px !important;
  border-radius: 20px !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  height: auto !important;
  min-height: 28px !important;
  line-height: 1.4 !important;
  white-space: nowrap !important;
}
</style>
""", unsafe_allow_html=True)

    # ── ACTIVE FILTERS SUMMARY BAR ──
    sf_label = sf if sf != 'All' else f'All ({total})'
    pf_label = pf if pf != 'All' else 'All'
    vf_label = vf if vf != 'All' else f'All ({total})'

    sf_cls = 'c-sp' if sf != 'All' else 'c-all'
    pf_cls = 'c-sp' if pf != 'All' else 'c-all'
    vf_cls = 'c-ex' if vf == 'Exchange' else ('c-nx' if vf == 'Nexus' else 'c-all')

    st.markdown(f"""
<div class="fbar-summary">
  <span class="fbar-label">Active Filters:</span>
  <span class="fbar-active {sf_cls}">Specialty: {sf_label}</span>
  <span class="fbar-divider"></span>
  <span class="fbar-active {pf_cls}">Profession: {pf_label}</span>
  <span class="fbar-divider"></span>
  <span class="fbar-active {vf_cls}">Vendor: {vf_label}</span>
</div>
""", unsafe_allow_html=True)

    # ── COLLAPSIBLE FILTER PANEL ──
    with st.expander("🔽  Change Filters", expanded=False):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown('<div class="fpanel-title">Specialty</div>', unsafe_allow_html=True)
            if st.button(f'All ({total})', key='filt_sf_all',
                         type='primary' if sf == 'All' else 'secondary',
                         use_container_width=False):
                st.session_state['specialty_filter'] = 'All'; st.rerun()
            for s in specs:
                lbl = s[:22] + ('…' if len(s) > 22 else '')
                if st.button(lbl, key=f'filt_sf_{s}', help=s,
                             type='primary' if sf == s else 'secondary',
                             use_container_width=False):
                    st.session_state['specialty_filter'] = s; st.rerun()

        with c2:
            st.markdown('<div class="fpanel-title">Profession</div>', unsafe_allow_html=True)
            if st.button('All', key='filt_pf_all',
                         type='primary' if pf == 'All' else 'secondary',
                         use_container_width=False):
                st.session_state['profession_filter'] = 'All'; st.rerun()
            for p in profs:
                lbl = p[:22] + ('…' if len(p) > 22 else '')
                if st.button(lbl, key=f'filt_pf_{p}', help=p,
                             type='primary' if pf == p else 'secondary',
                             use_container_width=False):
                    st.session_state['profession_filter'] = p; st.rerun()

        with c3:
            st.markdown('<div class="fpanel-title">Vendor</div>', unsafe_allow_html=True)
            for label, val, key in [
                (f'All ({total})', 'All',      'filt_vf_all'),
                (f'Exchange ({ex_n})', 'Exchange', 'filt_vf_ex'),
                (f'Nexus ({nx_n})',    'Nexus',    'filt_vf_nx'),
            ]:
                if st.button(label, key=key,
                             type='primary' if vf == val else 'secondary',
                             use_container_width=False):
                    st.session_state['vendor_filter'] = val; st.rerun()

            if sf != 'All' or pf != 'All' or vf != 'All':
                st.markdown('<hr style="border-color:#1e293b;margin:10px 0">', unsafe_allow_html=True)
                if st.button('✕ Clear all filters', key='filt_clear'):
                    st.session_state['specialty_filter'] = 'All'
                    st.session_state['profession_filter'] = 'All'
                    st.session_state['vendor_filter'] = 'All'
                    st.rerun()



TABS = ['Overview', 'Knowledge', 'Competence', 'Evaluation',
        'AI Insights', 'JCEHP Article', 'CIRCLE Framework', 'Kirkpatrick', 'Key Findings']


def render_tabs():
    active = st.session_state.get('tab','Overview')
    cols = st.columns(len(TABS))
    for i, t in enumerate(TABS):
        with cols[i]:
            if st.button(t, key=f'tab_{t}', use_container_width=True,
                         type='primary' if t==active else 'secondary'):
                st.session_state['tab']=t; st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB: OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
def tab_overview(ex_data, nx_data, resp):
    mcq_pairs, lk_pairs = match_questions(ex_data, nx_data)
    sat   = compute_sat_items(resp)
    ev_m  = compute_eval_metrics(resp)

    ex_n    = ex_data['n_pre']  if ex_data else 0
    nx_n    = nx_data['n_pre']  if nx_data else 0
    ex_post = ex_data['n_post'] if ex_data else 0
    nx_post = nx_data['n_post'] if nx_data else 0
    total   = ex_n + nx_n
    matched = ex_post + nx_post
    pct_match = round(100*matched/total, 1) if total else 0
    avg_gain  = round(sum(q['gain'] for q in mcq_pairs if q['gain']) / max(1, len(mcq_pairs)), 1) if mcq_pairs else 0
    cn        = ev_m.get('content_new', {})

    # ── TOP STAT CARDS (2 rows x 3 cols) ──
    st.markdown("""
<style>
.stat-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 10px; margin-bottom: 16px; }
.stat-card {
  background: #1e293b; border: 1px solid #334155; border-radius: 10px;
  padding: 14px 18px; display: flex; flex-direction: column; gap: 2px;
}
.stat-val  { font-size: 28px; font-weight: 700; line-height: 1.1; }
.stat-lbl  { color: #64748b; font-size: 10px; text-transform: uppercase;
  letter-spacing: .6px; font-weight: 600; }
.stat-sub  { color: #475569; font-size: 10px; margin-top: 1px; }
.stat-bar-wrap { height: 3px; background: #334155; border-radius: 2px; margin-top: 6px; }
.stat-bar-fill { height: 3px; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

    cards = [
        (str(total),              '#60a5fa', 'Total Pre-Test Learners',  f'Ex: {ex_n}  |  Nx: {nx_n}', None),
        (str(total - matched),    '#fb923c', 'Pre-Only (No Post/Eval)',   'Dropped off before completion', None),
        (str(matched),            '#4ade80', 'Pre/Post Matched',          f'{pct_match}% completion rate', pct_match),
        (str(len(resp)),          '#a78bfa', 'Evaluation Completers',     'Moore Levels 2-4 eligible', None),
        (f'+{avg_gain}pp',        '#22d3ee', 'Avg Knowledge Gain',        f'Across {len(mcq_pairs)} MCQ pairs', None),
        (f'{cn.get("pct","--")}%','#f59e0b', 'Content New to Learners',   f'n={cn.get("n","--")}', cn.get('pct')),
    ]

    html = '<div class="stat-grid">'
    for val, color, label, sub, bar_pct in cards:
        bar = ''
        if bar_pct is not None:
            bar = f'<div class="stat-bar-wrap"><div class="stat-bar-fill" style="width:{bar_pct}%;background:{color}"></div></div>'
        html += f"""<div class="stat-card">
  <div class="stat-lbl">{label}</div>
  <div class="stat-val" style="color:{color}">{val}</div>
  <div class="stat-sub">{sub}</div>{bar}
</div>"""
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    # ── MAIN CONTENT: Left 60% | Right 40% ──
    left, right = st.columns([6, 4], gap='medium')

    with left:
        # Knowledge gains
        st.markdown('<div class="scard">', unsafe_allow_html=True)
        st.markdown('<div class="stitle">Knowledge Gains - Pre vs Post</div>', unsafe_allow_html=True)
        for i, q in enumerate(mcq_pairs):
            gain  = q['gain'] or 0
            gc    = '#4ade80' if gain >= 0 else '#f87171'
            bg    = '#16a34a18' if gain >= 0 else '#dc262618'
            bc    = '#16a34a' if gain >= 0 else '#dc2626'
            gs    = f'+{gain}pp' if gain >= 0 else f'{gain}pp'
            pw    = min(100, int(q['pre_pct'] or 0))
            qw    = min(100, int(q['post_pct'] or 0))
            lbl   = q['label']
            short = lbl[:80] + ('...' if len(lbl) > 80 else '')
            cor   = (q.get('correct') or '')[:70]

            st.markdown(f"""
<div style="padding:12px 0;border-bottom:1px solid #0f172a">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:8px">
    <div style="color:#e2e8f0;font-size:12px;line-height:1.45;flex:1">{short}</div>
    <div style="background:{bg};border:1px solid {bc};color:{gc};padding:2px 9px;
      border-radius:5px;font-size:12px;font-weight:700;white-space:nowrap;flex-shrink:0">{gs}</div>
  </div>
  <div style="display:flex;align-items:center;gap:8px;margin:2px 0">
    <span style="color:#64748b;font-size:10px;width:30px;flex-shrink:0;font-weight:600">PRE</span>
    <div style="flex:1;background:#0f172a;border-radius:2px;height:7px">
      <div style="width:{pw}%;background:#f59e0b;border-radius:2px;height:7px"></div></div>
    <span style="color:#f59e0b;font-size:11px;font-weight:700;width:38px;text-align:right">{q['pre_pct']}%</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;margin:2px 0">
    <span style="color:#64748b;font-size:10px;width:30px;flex-shrink:0;font-weight:600">POST</span>
    <div style="flex:1;background:#0f172a;border-radius:2px;height:7px">
      <div style="width:{qw}%;background:#4ade80;border-radius:2px;height:7px"></div></div>
    <span style="color:#4ade80;font-size:11px;font-weight:700;width:38px;text-align:right">{q['post_pct']}%</span>
  </div>
  <div style="color:#334155;font-size:10px;margin-top:4px">Correct: {cor}</div>
</div>""", unsafe_allow_html=True)
            if st.button('Details', key=f'ov_kn_{i}', help='View calculation details'):
                st.session_state['modal'] = kn_modal(q); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        # Competence shifts
        if lk_pairs:
            st.markdown('<div class="scard">', unsafe_allow_html=True)
            st.markdown('<div class="stitle">Competence Shifts (Likert)</div>', unsafe_allow_html=True)
            for i, q in enumerate(lk_pairs[:4]):
                gain = q['gain'] or 0
                gc   = '#4ade80' if gain >= 0 else '#f87171'
                gs   = f'+{gain}' if gain >= 0 else str(gain)
                pre  = q['pre_pct'] or 0
                post = q['post_pct'] or 0
                pw   = min(100, int(pre / 5 * 100))
                qw   = min(100, int(post / 5 * 100))
                st.markdown(f"""
<div style="padding:8px 0;border-bottom:1px solid #0f172a">
  <div style="color:#94a3b8;font-size:11px;line-height:1.3;margin-bottom:5px">{q['label'][:55]}...</div>
  <div style="display:flex;align-items:center;gap:6px">
    <div style="text-align:center;min-width:32px">
      <div style="font-size:14px;font-weight:700;color:#a78bfa">{pre}</div>
      <div style="font-size:9px;color:#475569">PRE</div></div>
    <div style="flex:1;position:relative">
      <div style="background:#0f172a;border-radius:2px;height:6px">
        <div style="width:{qw}%;background:#22d3ee;border-radius:2px;height:6px"></div></div>
    </div>
    <div style="text-align:center;min-width:32px">
      <div style="font-size:14px;font-weight:700;color:#22d3ee">{post}</div>
      <div style="font-size:9px;color:#475569">POST</div></div>
    <div style="font-size:11px;font-weight:700;color:{gc};min-width:32px;text-align:right">{gs}</div>
  </div>
</div>""", unsafe_allow_html=True)
                if st.button('Details', key=f'ov_lk_{i}'):
                    st.session_state['modal'] = kn_modal(q); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # Eval impact - SVG donuts in 2x2
        st.markdown('<div class="scard">', unsafe_allow_html=True)
        st.markdown('<div class="stitle">Program Impact</div>', unsafe_allow_html=True)
        ev_defs = [
            ('Intent to Change',  'intent',      '#22d3ee'),
            ('Would Recommend',   'recommend',   '#4ade80'),
            ('Bias-Free',         'bias_free',   '#a78bfa'),
            ('Content New',       'content_new', '#f59e0b'),
        ]
        # 2x2 grid using st.columns
        row1 = st.columns(2)
        row2 = st.columns(2)
        grid = [row1[0], row1[1], row2[0], row2[1]]
        for idx2, (name, key, color) in enumerate(ev_defs):
            val  = ev_m.get(key, {}).get('pct')
            nn   = ev_m.get(key, {}).get('n', 0)
            vs   = f'{val}%' if val is not None else '--'
            pv   = int(val or 0)
            circ = round(2 * 3.14159 * 28, 1)
            dash = round(circ * pv / 100, 1)
            gap  = round(circ - dash, 1)
            with grid[idx2]:
                st.markdown(f"""
<div style="text-align:center;padding:6px 4px">
  <svg width="68" height="68" viewBox="0 0 68 68">
    <circle cx="34" cy="34" r="28" fill="none" stroke="#1e293b" stroke-width="7"/>
    <circle cx="34" cy="34" r="28" fill="none" stroke="{color}" stroke-width="7"
      stroke-dasharray="{dash} {gap}" stroke-linecap="round"
      transform="rotate(-90 34 34)"/>
    <text x="34" y="38" text-anchor="middle" fill="{color}"
      font-family="sans-serif" font-size="13" font-weight="700">{vs}</text>
  </svg>
  <div style="color:#94a3b8;font-size:10px;line-height:1.3;margin-top:2px">{name}</div>
  <div style="color:#334155;font-size:9px">n={nn}</div>
</div>""", unsafe_allow_html=True)
                if st.button('Detail', key=f'ov_ev_{idx2}'):
                    st.session_state['modal'] = ev_modal(name, val, nn, f'{name} metric.'); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Satisfaction - score + bar, compact
        if sat:
            st.markdown('<div class="scard">', unsafe_allow_html=True)
            st.markdown('<div class="stitle">Satisfaction (1-5)</div>', unsafe_allow_html=True)
            for i, s in enumerate(sat):
                pct   = round(s['mean'] / 5 * 100)
                color = '#22d3ee' if pct >= 80 else ('#f59e0b' if pct >= 60 else '#f87171')
                st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #0f172a">
  <div style="font-size:16px;font-weight:700;color:{color};min-width:34px;text-align:right;flex-shrink:0">{s['mean']}</div>
  <div style="flex:1;min-width:0">
    <div style="color:#94a3b8;font-size:10px;line-height:1.3;margin-bottom:3px;
      overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
      title="{s['label']}">{s['label']}</div>
    <div style="background:#0f172a;border-radius:2px;height:4px">
      <div style="width:{pct}%;background:{color};border-radius:2px;height:4px"></div></div>
  </div>
  <div style="color:#475569;font-size:9px;flex-shrink:0">/5</div>
</div>""", unsafe_allow_html=True)
                if st.button('D', key=f'ov_sat_{i}', help=s['label']):
                    st.session_state['modal'] = sat_modal(s); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


def tab_knowledge(ex_data, nx_data):
    mcq, _ = match_questions(ex_data, nx_data)
    st.markdown('<div class="scard"><div class="stitle">Knowledge Assessment — MCQ Pre/Post (Moore Level 3)</div>', unsafe_allow_html=True)
    if not mcq:
        st.markdown('<div style="color:#64748b;padding:20px">No MCQ pairs detected.</div>', unsafe_allow_html=True)
    else:
        tbl = '<table style="width:100%;border-collapse:collapse"><thead><tr>'
        for h in ['Question','Pre %','Post %','Gain','n Pre','n Post','Ex Pre','Ex Post','Nx Pre','Nx Post','Correct Answer','']:
            tbl += f'<th style="color:#475569;font-size:10px;text-transform:uppercase;padding:8px;border-bottom:1px solid #334155;text-align:left">{h}</th>'
        tbl += '</tr></thead><tbody>'
        for q in mcq:
            gc = '#4ade80' if (q['gain'] or 0)>=0 else '#f87171'
            gs = f'+{q["gain"]}pp' if (q["gain"] or 0)>=0 else f'{q["gain"]}pp'
            def f(v,u='%'): return f'{v}{u}' if v is not None else '—'
            tbl += f'''<tr style="border-bottom:1px solid #1e293b">
<td style="color:#e2e8f0;font-size:12px;padding:9px 8px" title="{q["label"]}">{q["label"][:52]}{"…" if len(q["label"])>52 else ""}</td>
<td style="color:#f59e0b;font-size:13px;font-weight:600;padding:9px 8px">{f(q["pre_pct"])}</td>
<td style="color:#4ade80;font-size:13px;font-weight:600;padding:9px 8px">{f(q["post_pct"])}</td>
<td style="color:{gc};font-size:13px;font-weight:700;padding:9px 8px">{gs}</td>
<td style="color:#64748b;font-size:11px;padding:9px 8px">{q.get("pre_n","—")}</td>
<td style="color:#64748b;font-size:11px;padding:9px 8px">{q.get("post_n","—")}</td>
<td style="color:#4ade80;font-size:11px;padding:9px 8px">{f(q.get("ex_pre"))}</td>
<td style="color:#4ade80;font-size:11px;padding:9px 8px">{f(q.get("ex_post"))}</td>
<td style="color:#a78bfa;font-size:11px;padding:9px 8px">{f(q.get("nx_pre"))}</td>
<td style="color:#a78bfa;font-size:11px;padding:9px 8px">{f(q.get("nx_post"))}</td>
<td style="color:#64748b;font-size:11px;padding:9px 8px">{(q.get("correct") or "")[:40]}</td>
<td style="padding:4px"></td>
</tr>'''
        tbl += '</tbody></table>'
        st.markdown(tbl, unsafe_allow_html=True)
        cols = st.columns(min(len(mcq),6))
        for i,q in enumerate(mcq):
            with cols[i%6]:
                if st.button(f"🔍 Q{i+1}", key=f'kn_{i}'):
                    st.session_state['modal'] = kn_modal(q); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB: COMPETENCE
# ══════════════════════════════════════════════════════════════════════════════
def tab_competence(ex_data, nx_data, resp):
    _, lk = match_questions(ex_data, nx_data)
    lo    = compute_lo_items(resp)
    st.markdown('<div class="scard"><div class="stitle">Competence — Likert Pre/Post (Moore Level 4)</div>', unsafe_allow_html=True)
    if lk:
        for i,q in enumerate(lk):
            gc = '#4ade80' if (q['gain'] or 0)>=0 else '#f87171'
            gs = f'+{q["gain"]}' if (q["gain"] or 0)>=0 else str(q["gain"])
            st.markdown(f'<div style="display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid #0f172a"><div style="color:#e2e8f0;font-size:13px;flex:1;line-height:1.35">{q["label"][:72]}</div><span style="color:#94a3b8;font-size:12px">Pre: {q["pre_pct"]}</span><span style="color:#475569;font-size:11px">→</span><span style="color:#22d3ee;font-size:12px;font-weight:600">Post: {q["post_pct"]}</span><span style="color:{gc};font-size:13px;font-weight:700;min-width:42px;text-align:right">{gs}</span></div>', unsafe_allow_html=True)
            if st.button("🔍", key=f'comp_{i}'):
                st.session_state['modal'] = kn_modal(q); st.rerun()
    if lo:
        st.markdown('<div style="margin-top:16px"><div class="stitle">Learning Objective Ratings (post-eval, 1–5)</div>', unsafe_allow_html=True)
        for i,l in enumerate(lo):
            pf = round(l['mean']/5*100)
            st.markdown(f'<div class="sat-row"><div class="sat-lbl">{l["label"][:70]}</div><div class="sat-bar"><div class="sat-fill" style="width:{pf}%;background:#a78bfa"></div></div><div class="sat-val">{l["mean"]}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB: EVALUATION
# ══════════════════════════════════════════════════════════════════════════════
def tab_evaluation(resp):
    ev_m = compute_eval_metrics(resp)
    sat  = compute_sat_items(resp)
    n    = len(resp)

    metric_defs = [
        ('Intent to Change Practice', 'intent', '#22d3ee',
         'Percentage indicating intent to change clinical practice (Moore Level 5 precursor).'),
        ('Would Recommend Program', 'recommend', '#4ade80',
         'Percentage who would recommend this program to a colleague.'),
        ('Bias-Free Content', 'bias_free', '#a78bfa',
         'Percentage rating content free of commercial bias (required ACCME metric).'),
    ]
    cols = st.columns(3)
    for i, (lbl, key, color, defn) in enumerate(metric_defs):
        m2  = ev_m.get(key,{})
        val = f"{m2.get('pct','—')}%" if m2.get('pct') is not None else '—'
        nn  = m2.get('n',0); pv = m2.get('pct')
        with cols[i]:
            st.markdown(f'<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px;margin-bottom:8px"><div style="color:#64748b;font-size:10px;text-transform:uppercase;margin-bottom:4px">{lbl}</div><div style="font-size:34px;font-weight:700;color:{color}">{val}</div><div style="color:#475569;font-size:10px">n={nn}</div></div>', unsafe_allow_html=True)
            if st.button("🔍", key=f'ev_{i}'):
                st.session_state['modal'] = ev_modal(lbl, pv, nn, defn); st.rerun()

    cn = ev_m.get('content_new',{})
    if cn.get('pct'):
        st.markdown(f'<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px;margin-bottom:14px"><div style="color:#64748b;font-size:10px;text-transform:uppercase;margin-bottom:4px">Content New to Learner</div><div style="font-size:28px;font-weight:700;color:#f59e0b">{cn["pct"]}%</div><div style="color:#475569;font-size:10px">n={cn.get("n","—")}</div></div>', unsafe_allow_html=True)

    if sat:
        st.markdown('<div class="scard"><div class="stitle">Satisfaction Ratings (1–5 Likert)</div>', unsafe_allow_html=True)
        for i,s in enumerate(sat):
            pf_v = round(s['mean']/5*100)
            color = '#22d3ee' if pf_v>=80 else ('#f59e0b' if pf_v>=60 else '#f87171')
            ex_s = f" Ex:{s['ex_mean']}" if s.get('ex_mean') else ''
            nx_s = f" Nx:{s['nx_mean']}" if s.get('nx_mean') else ''
            # Full label shown here
            st.markdown(f'<div class="sat-row"><div class="sat-lbl" style="width:400px">{s["label"]}</div><div class="sat-bar" style="width:180px"><div class="sat-fill" style="width:{pf_v}%;background:{color}"></div></div><div style="color:#e2e8f0;font-size:12px;font-weight:600;width:100px;text-align:right">{s["mean"]}/5{ex_s}{nx_s}</div></div>', unsafe_allow_html=True)
            if st.button("🔍", key=f'ev_sat_{i}'):
                st.session_state['modal'] = sat_modal(s); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# KEY FINDINGS
# ══════════════════════════════════════════════════════════════════════════════
def tab_key_findings(ex_data, nx_data, resp):
    mcq, _ = match_questions(ex_data, nx_data)
    ev_m   = compute_eval_metrics(resp)

    if mcq:
        st.markdown('<div class="scard"><div class="stitle">Knowledge Gain — Prior vs. After</div>', unsafe_allow_html=True)
        n_cols = min(4, len(mcq))
        cols = st.columns(n_cols)
        for i, q in enumerate(mcq):
            with cols[i%n_cols]:
                gc = '#4ade80' if (q['gain'] or 0)>=0 else '#f87171'
                st.markdown(f"""<div style="text-align:center;margin-bottom:10px">
<div style="display:flex;gap:6px;justify-content:center;align-items:center;margin-bottom:6px">
  <div style="width:78px;height:78px;border-radius:50%;border:5px solid #f59e0b;display:flex;align-items:center;justify-content:center;flex-direction:column">
    <div style="font-size:17px;font-weight:700;color:#f59e0b">{q['pre_pct']}%</div>
    <div style="font-size:9px;color:#475569">PRE</div>
  </div>
  <div style="font-size:12px;color:#334155">→</div>
  <div style="width:78px;height:78px;border-radius:50%;border:5px solid #4ade80;display:flex;align-items:center;justify-content:center;flex-direction:column">
    <div style="font-size:17px;font-weight:700;color:#4ade80">{q['post_pct']}%</div>
    <div style="font-size:9px;color:#475569">POST</div>
  </div>
</div>
<div style="color:{gc};font-size:12px;font-weight:700">+{q['gain']}pp gain</div>
<div style="color:#475569;font-size:10px;margin-top:3px;line-height:1.3">{q['label'][:48]}</div>
</div>""", unsafe_allow_html=True)
                if st.button("🔍", key=f'kf_{i}'):
                    st.session_state['modal'] = kn_modal(q); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    ev_defs = [
        ('Intent to Change', 'intent', '#22d3ee', 'Intent to change clinical practice.'),
        ('Would Recommend',  'recommend', '#4ade80', 'Would recommend program to colleague.'),
        ('Bias-Free',        'bias_free', '#a78bfa', 'Content free of commercial bias.'),
        ('Content New',      'content_new', '#f59e0b', 'Mean % content new to learners.'),
    ]
    st.markdown('<div class="scard"><div class="stitle">Evaluation Highlights</div>', unsafe_allow_html=True)
    circ = '<div style="display:flex;gap:20px;justify-content:center;flex-wrap:wrap;padding:8px 0">'
    for name, key, color, _ in ev_defs:
        val = ev_m.get(key,{}).get('pct'); nn = ev_m.get(key,{}).get('n',0)
        vs  = f'{val}%' if val is not None else '—'
        circ += f'<div style="text-align:center"><div style="width:96px;height:96px;border-radius:50%;border:6px solid {color};display:flex;align-items:center;justify-content:center;flex-direction:column;margin:0 auto 7px"><div style="font-size:24px;font-weight:800;color:{color}">{vs}</div></div><div style="color:#64748b;font-size:10px">{name}<br><span style="font-size:9px;color:#334155">(n={nn})</span></div></div>'
    circ += '</div>'
    st.markdown(circ, unsafe_allow_html=True)
    ev_cols = st.columns(4)
    for i, (name, key, color, defn) in enumerate(ev_defs):
        with ev_cols[i]:
            pv = ev_m.get(key,{}).get('pct'); nn = ev_m.get(key,{}).get('n',0)
            if st.button("🔍", key=f'kf_ev_{i}'):
                st.session_state['modal'] = ev_modal(name, pv, nn, defn); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# KIRKPATRICK
# ══════════════════════════════════════════════════════════════════════════════
def tab_kirkpatrick(ex_data, nx_data, resp):
    mcq, lk = match_questions(ex_data, nx_data)
    sat = compute_sat_items(resp)
    ev_m = compute_eval_metrics(resp)
    for lv, title, color, icon in [
        ('Level 1','Reaction','#22d3ee','😊'),
        ('Level 2','Learning','#4ade80','📚'),
        ('Level 3','Behavior','#a78bfa','🔄'),
        ('Level 4','Results', '#f59e0b','🎯'),
    ]:
        st.markdown(f'<div style="background:#1e293b;border-left:4px solid {color};border-radius:0 8px 8px 0;padding:16px;margin-bottom:12px">', unsafe_allow_html=True)
        st.markdown(f'<div style="color:{color};font-size:13px;font-weight:700;margin-bottom:8px">{icon} {lv}: {title}</div>', unsafe_allow_html=True)
        if lv=='Level 1':
            for i,s in enumerate(sat[:5]):
                pf=round(s['mean']/5*100)
                st.markdown(f'<div class="sat-row"><div class="sat-lbl">{s["label"]}</div><div class="sat-bar"><div class="sat-fill" style="width:{pf}%;background:{color}"></div></div><div class="sat-val">{s["mean"]}/5</div></div>', unsafe_allow_html=True)
                if st.button("🔍",key=f'k1_{i}'): st.session_state['modal']=sat_modal(s); st.rerun()
        elif lv=='Level 2':
            avg=round(sum(q['gain'] for q in mcq if q['gain'])/max(1,len(mcq)),1) if mcq else 0
            st.markdown(f'<div style="color:{color};font-size:17px;font-weight:700;margin-bottom:8px">{len(mcq)} MCQ | Avg +{avg}pp</div>', unsafe_allow_html=True)
            for i,q in enumerate(mcq):
                pf=min(100,max(0,int((q['gain'] or 0)*2)))
                st.markdown(f'<div class="sat-row"><div class="sat-lbl">{q["label"][:60]}</div><div class="sat-bar"><div class="sat-fill" style="width:{pf}%;background:{color}"></div></div><div class="sat-val" style="color:{color}">+{q["gain"]}pp</div></div>', unsafe_allow_html=True)
                if st.button("🔍",key=f'k2_{i}'): st.session_state['modal']=kn_modal(q); st.rerun()
        elif lv=='Level 3':
            ip=ev_m.get('intent',{}).get('pct'); nn=ev_m.get('intent',{}).get('n',0)
            if ip:
                st.markdown(f'<div class="sat-row"><div class="sat-lbl">Intend to change practice</div><div class="sat-bar"><div class="sat-fill" style="width:{ip}%;background:{color}"></div></div><div class="sat-val">{ip}%</div></div>', unsafe_allow_html=True)
                if st.button("🔍",key='k3_i'): st.session_state['modal']=ev_modal('Intent to Change Practice',ip,nn,'Intent to change practice.'); st.rerun()
        elif lv=='Level 4':
            st.markdown('<div style="color:#64748b;font-size:13px">Follow-up data available when Nexus Follow Up sheet is populated.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CIRCLE
# ══════════════════════════════════════════════════════════════════════════════
def tab_circle(ex_data, nx_data, resp):
    mcq, lk = match_questions(ex_data, nx_data)
    sat = compute_sat_items(resp)
    ev_m = compute_eval_metrics(resp)
    ex_n = ex_data['n_pre'] if ex_data else 0
    nx_n = nx_data['n_pre'] if nx_data else 0
    ex_post = ex_data['n_post'] if ex_data else 0
    nx_post = nx_data['n_post'] if nx_data else 0
    total = ex_n + nx_n; matched = ex_post + nx_post
    comp_pct = round(100*matched/total,1) if total else 0
    avg_gain = round(sum(q['gain'] for q in mcq if q['gain'])/max(1,len(mcq)),1) if mcq else 0
    avg_sat  = round(sum(s['mean'] for s in sat)/max(1,len(sat))/5*100,1) if sat else 0
    intent_p = ev_m.get('intent',{}).get('pct') or 0
    avg_post = round(sum(q['post_pct'] for q in mcq if q['post_pct'])/max(1,len(mcq)),1) if mcq else 0

    dims = [
        ('C','Clinician\nEngagement', f'{comp_pct}%','#22d3ee', f'completion rate (n={total})','strong' if comp_pct>=50 else 'prompt'),
        ('I','Impact on\nlearning',   f'+{avg_gain}pp','#22d3ee',f'avg knowledge gain (n={total})','strong' if avg_gain>=20 else 'moderate'),
        ('R','Relevance\nin gaps',    f'{avg_sat}%','#f59e0b',  f'prior utilization (n={len(resp)})','new insight' if avg_sat<50 else 'strong'),
        ('C','Change in\nbehavior',   f'{intent_p}%','#22d3ee', f'intent to change (n={ev_m.get("intent",{}).get("n",0)})','strong' if intent_p>=70 else 'moderate'),
        ('L','Linkage to\npatients',  f'{avg_post}%','#f59e0b', f'practice ready (n={len(resp)})','prompt' if avg_post<70 else 'strong'),
        ('E','Ecosystem\nbarriers',   str(len(resp)),'#f59e0b', f'distinct barriers (n={len(resp)})','new insight'),
    ]
    c1,c2,c3 = st.columns(3)
    for i,(letter,name,val,color,sub,badge) in enumerate(dims):
        bc = '#4ade80' if badge=='strong' else ('#f59e0b' if badge in('moderate','new insight') else '#f87171')
        with [c1,c2,c3][i%3]:
            st.markdown(f'''<div style="background:#1a2433;border:1px solid #334155;border-radius:10px;padding:18px;margin-bottom:12px;min-height:155px">
<div style="font-size:30px;font-weight:800;color:{color};text-align:center;line-height:1">{letter}</div>
<div style="color:#475569;font-size:10px;text-align:center;margin:2px 0 8px;white-space:pre-line">{name}</div>
<div style="font-size:22px;font-weight:700;color:#e2e8f0;text-align:center">{val}</div>
<div style="text-align:center;margin-top:6px">
  <span style="color:{bc};font-size:10px;text-decoration:underline">{sub}</span>
  <span style="background:{bc}22;border:1px solid {bc};color:{bc};font-size:9px;padding:1px 5px;border-radius:3px;margin-left:4px">{badge}</span>
</div></div>''', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# JCEHP + AI (lightweight)
# ══════════════════════════════════════════════════════════════════════════════
def tab_jcehp(ex_data, nx_data, resp):
    mcq, _ = match_questions(ex_data, nx_data)
    ev_m   = compute_eval_metrics(resp)
    sections = ['Abstract','Introduction','Methods','Results','Discussion','Conclusion']
    existing = st.session_state.get('jcehp_text',{})
    done = round(len([s for s in sections if existing.get(s)])/len(sections)*100)
    st.markdown(f'<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px;margin-bottom:14px"><div style="color:#e2e8f0;font-size:14px;font-weight:600;margin-bottom:6px">📝 JCEHP Article Preparation — {done}% complete</div><div style="background:#334155;border-radius:4px;height:6px"><div style="width:{done}%;background:#22d3ee;border-radius:4px;height:6px"></div></div></div>', unsafe_allow_html=True)
    kn_txt = ' '.join([f"{q['label'][:40]}: pre {q['pre_pct']}% → post {q['post_pct']}% (Δ+{q['gain']}pp)." for q in mcq])
    auto = {
        'Methods': f"Multi-vendor CME outcomes analysis. Exchange (n={ex_data['n_pre'] if ex_data else 0}) and Nexus (n={nx_data['n_pre'] if nx_data else 0}) data harmonized and matched. Pre/post matched n={( ex_data['n_post'] if ex_data else 0)+(nx_data['n_post'] if nx_data else 0)}. Evaluation n={len(resp)}.",
        'Results': f"Knowledge: {kn_txt[:280]}\n\nIntent to change: {ev_m.get('intent',{}).get('pct','N/A')}%. Would recommend: {ev_m.get('recommend',{}).get('pct','N/A')}%.",
    }
    for sec in sections:
        content = existing.get(sec, auto.get(sec,''))
        st.markdown(f'<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:14px;margin-bottom:8px"><div style="color:#a78bfa;font-size:12px;font-weight:700;margin-bottom:6px">{sec}</div>', unsafe_allow_html=True)
        new_text = st.text_area(sec, value=content, height=100, key=f'jcehp_{sec}', label_visibility='collapsed')
        if new_text != content: st.session_state.setdefault('jcehp_text',{})[sec]=new_text
        st.markdown('</div>', unsafe_allow_html=True)

def tab_ai(ex_data, nx_data, resp):
    mcq, _ = match_questions(ex_data, nx_data)
    ev_m   = compute_eval_metrics(resp)
    st.markdown('<div class="scard"><div style="color:#e2e8f0;font-size:14px;font-weight:600;margin-bottom:12px">🤖 AI Insights</div>', unsafe_allow_html=True)
    api_key = st.text_input("Anthropic API Key", type="password", value=st.session_state.get('api_key',''), placeholder="sk-ant-…")
    if api_key: st.session_state['api_key']=api_key
    if st.button("Generate Insights"):
        if not api_key: st.error("Please enter your API key.")
        else:
            with st.spinner("Generating…"):
                kn_s = "\n".join([f"- {q['label'][:55]}: pre={q['pre_pct']}% post={q['post_pct']}% gain={q['gain']}pp" for q in mcq])
                prompt = f"""CME outcomes analyst. Generate 5 actionable insights.
Ex n={ex_data['n_pre'] if ex_data else 0}, Nx n={nx_data['n_pre'] if nx_data else 0}
Knowledge:\n{kn_s}
Intent: {ev_m.get('intent',{}).get('pct','N/A')}%
Return JSON array of 5: title, moore_level, insight, recommendation"""
                try:
                    import requests as rq
                    r = rq.post("https://api.anthropic.com/v1/messages",
                        headers={"x-api-key":api_key,"anthropic-version":"2023-06-01","content-type":"application/json"},
                        json={"model":"claude-sonnet-4-20250514","max_tokens":1200,"messages":[{"role":"user","content":prompt}]},timeout=30)
                    if r.status_code==200:
                        txt=r.json()['content'][0]['text']
                        m=re.search(r'\[.*\]',txt,re.DOTALL)
                        if m: st.session_state['ai_insights']=json.loads(m.group())
                    else: st.error(f"API error {r.status_code}")
                except Exception as e: st.error(str(e))
    for ins in st.session_state.get('ai_insights',[]):
        lvl=str(ins.get('moore_level',''))
        c={'2':'#f59e0b','3':'#4ade80','4':'#22d3ee','5':'#a78bfa'}.get(lvl,'#64748b')
        st.markdown(f'<div style="background:#0f172a;border:1px solid #334155;border-radius:9px;padding:16px;margin-bottom:10px"><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px"><span style="background:{c}22;border:1px solid {c};color:{c};padding:1px 7px;border-radius:3px;font-size:10px;font-weight:700">MOORE {lvl}</span><div style="color:#e2e8f0;font-size:13px;font-weight:600">{ins.get("title","")}</div></div><div style="color:#94a3b8;font-size:12px;line-height:1.5">{ins.get("insight","")}</div><div style="color:#4ade80;font-size:11px;margin-top:6px">→ {ins.get("recommendation","")}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    ex_data = st.session_state.get('ex_data')
    nx_data = st.session_state.get('nx_data')

    # HEADER
    prog  = st.session_state.get('prog_name','')
    ex_n  = ex_data['n_pre'] if ex_data else 0
    nx_n  = nx_data['n_pre'] if nx_data else 0
    ex_pill = f'<span class="pill-ex">⬤ Exchange ({ex_n})</span>' if ex_data else ''
    nx_pill = f'<span class="pill-nx">⬤ Nexus ({nx_n})</span>'   if nx_data else ''
    st.markdown(f'''<div class="app-hdr">
  <div class="app-logo"><span>Integritas</span> CME Outcomes Harmonizer</div>
  <div style="color:#64748b;font-size:11px;flex:1">{prog}</div>
  <div style="display:flex;gap:8px">{ex_pill}{nx_pill}</div>
</div>''', unsafe_allow_html=True)

    if not ex_data and not nx_data:
        render_upload(); return

    # Tabs
    render_tabs()

    # Action row
    a1,a2,a3,_ = st.columns([1,1,1,5])
    with a1:
        if st.button("🧠 AI Insights"): st.session_state['tab']='AI Insights'; st.rerun()
    with a2:
        if st.button("✍️ Article"):     st.session_state['tab']='JCEHP Article'; st.rerun()
    with a3:
        if st.button("📁 New Upload"):
            st.session_state['ex_data']=None; st.session_state['nx_data']=None
            st.session_state['ai_insights']=[]; st.session_state['jcehp_text']={}
            st.rerun()

    # Filter bar
    vf = st.session_state.get('vendor_filter','All')
    sf = st.session_state.get('specialty_filter','All')
    pf = st.session_state.get('profession_filter','All')
    render_filter_bar(ex_data, nx_data)
    resp = get_eval_respondents(ex_data, nx_data, sf, pf, vf)

    # Modal renders here — after filters but before tab content.
    # Returns early so close button is always the first thing on screen.
    if st.session_state.get('modal'):
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
        build_modal(st.session_state['modal'])
        return

    st.divider()

    t = st.session_state.get('tab','Overview')
    if   t=='Overview':         tab_overview(ex_data, nx_data, resp)
    elif t=='Knowledge':        tab_knowledge(ex_data, nx_data)
    elif t=='Competence':       tab_competence(ex_data, nx_data, resp)
    elif t=='Evaluation':       tab_evaluation(resp)
    elif t=='Key Findings':     tab_key_findings(ex_data, nx_data, resp)
    elif t=='Kirkpatrick':      tab_kirkpatrick(ex_data, nx_data, resp)
    elif t=='CIRCLE Framework': tab_circle(ex_data, nx_data, resp)
    elif t=='JCEHP Article':    tab_jcehp(ex_data, nx_data, resp)
    elif t=='AI Insights':      tab_ai(ex_data, nx_data, resp)

    st.divider()

if __name__ == '__main__':
    main()
