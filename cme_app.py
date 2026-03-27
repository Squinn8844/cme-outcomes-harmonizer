"""
Integritas CME Outcomes Harmonizer v5
- Fixed satisfaction labels (full question text, not truncated prefix)
- Full filter bar: Specialty + Profession + Vendor (All / Nexus / Exchange)
- Layout matching reference screenshots
- Modal popup on every data point
- Direct parse of Combined_Pre-Post and Combined_Eval structure
"""
import io, re, json
from collections import Counter, defaultdict
import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
import openpyxl

st.set_page_config(
    page_title="Integritas CME Outcomes Harmonizer",
    layout="wide", page_icon="🧬"
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
#MainMenu,footer,header{visibility:hidden}
.block-container{padding-top:0!important;max-width:100%!important}
section[data-testid="stSidebar"]{display:none}
body,.stApp{background:#0a0f1e!important}

/* ── HEADER ── */
.app-hdr{
  background:#0f172a;border-bottom:1px solid #1e3a5f;
  padding:10px 24px;display:flex;align-items:center;gap:14px;
}
.app-logo{font-size:18px;font-weight:700;color:#fff;white-space:nowrap}
.app-logo span{color:#22d3ee}
.hdr-meta{color:#64748b;font-size:11px;white-space:nowrap}
.hdr-pill-nx{background:#7c3aed22;border:1px solid #7c3aed;color:#a78bfa;
  padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap}
.hdr-pill-ex{background:#16a34a22;border:1px solid #16a34a;color:#4ade80;
  padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap}

/* ── FILTER BAR ── */
.fbar{
  background:#0f172a;border-bottom:1px solid #1e293b;
  padding:6px 24px;display:flex;gap:6px;flex-wrap:wrap;align-items:center;
}
.flabel{color:#475569;font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.8px;white-space:nowrap}
.chip{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;
  cursor:pointer;border:1px solid #334155;color:#94a3b8;background:#1e293b;white-space:nowrap}
.chip-active-all{border-color:#22d3ee!important;color:#22d3ee!important;background:#0891b220!important}
.chip-active-nx {border-color:#a78bfa!important;color:#a78bfa!important;background:#7c3aed20!important}
.chip-active-ex {border-color:#4ade80!important;color:#4ade80!important;background:#16a34a20!important}
.chip-active-sp {border-color:#f59e0b!important;color:#f59e0b!important;background:#d9770620!important}
.divider-v{width:1px;height:20px;background:#334155;margin:0 4px}

/* ── STAT CARDS ── */
.sc-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:20px}
.sc{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px 16px;cursor:pointer;transition:.15s}
.sc:hover{border-color:#22d3ee}
.sc-label{color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.sc-val{font-size:26px;font-weight:700;line-height:1}
.sc-sub{color:#475569;font-size:10px;margin-top:3px}

/* ── SECTION CARD ── */
.scard{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:18px;margin-bottom:14px}
.scard-title{color:#94a3b8;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:14px}

/* ── KN BARS ── */
.kn-item{padding:10px 0;border-bottom:1px solid #1e293b}
.kn-item:last-child{border-bottom:none}
.kn-q{color:#e2e8f0;font-size:13px;margin-bottom:6px;line-height:1.4}
.kn-gain{font-size:14px;font-weight:700;float:right}
.bar-row{display:flex;align-items:center;gap:8px;margin:3px 0}
.bar-lbl{color:#475569;font-size:11px;width:36px;flex-shrink:0}
.bar-bg{flex:1;background:#1e293b;border-radius:3px;height:7px}
.bar-fill{border-radius:3px;height:7px}
.bar-pct{color:#94a3b8;font-size:11px;width:38px;text-align:right}
.correct-lbl{color:#475569;font-size:11px;margin-top:2px}

/* ── COMPETENCE ── */
.comp-item{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #1e293b}
.comp-item:last-child{border-bottom:none}
.comp-q{color:#94a3b8;font-size:12px;flex:1;line-height:1.4}
.comp-pre{color:#a78bfa;font-size:13px;font-weight:600;min-width:34px}
.comp-arrow{color:#475569;font-size:12px}
.comp-post{color:#22d3ee;font-size:13px;font-weight:600;min-width:34px}
.comp-delta{font-size:13px;font-weight:700;min-width:44px;text-align:right}

/* ── SAT CIRCLES ── */
.sat-circles{display:flex;gap:24px;flex-wrap:wrap;justify-content:center;padding:8px 0}
.sat-circle{text-align:center;cursor:pointer}
.sat-ring{width:80px;height:80px;border-radius:50%;border:5px solid;
  display:flex;align-items:center;justify-content:center;
  flex-direction:column;margin:0 auto 6px;cursor:pointer;
  transition:transform .15s,filter .15s}
.sat-ring:hover{transform:scale(1.06);filter:brightness(1.15)}
.sat-val{font-size:18px;font-weight:700;line-height:1}
.sat-name{color:#64748b;font-size:10px;text-align:center;max-width:80px;line-height:1.3}

/* ── EVAL CIRCLES ── */
.ev-circles{display:flex;gap:20px;justify-content:space-around;padding:8px 0}
.ev-circle{text-align:center;cursor:pointer}
.ev-ring{width:90px;height:90px;border-radius:50%;border:6px solid;
  display:flex;align-items:center;justify-content:center;flex-direction:column;
  margin:0 auto 8px;cursor:pointer;transition:transform .15s,filter .15s}
.ev-ring:hover{transform:scale(1.06)}
.ev-val{font-size:22px;font-weight:800;line-height:1}
.ev-name{color:#64748b;font-size:10px;text-align:center;max-width:90px;line-height:1.3}

/* ── MODAL ── */
.modal-overlay{
  position:fixed;top:0;left:0;width:100%;height:100%;
  background:rgba(0,0,0,.82);z-index:99999;
  display:flex;align-items:center;justify-content:center;
}
.modal-card{
  background:#1a2744;border:1px solid #2a4a7f;border-radius:14px;
  width:660px;max-width:90vw;max-height:82vh;overflow-y:auto;
  padding:26px 30px;position:relative;
  box-shadow:0 24px 80px rgba(0,0,0,.6);
}
.modal-close{
  position:absolute;top:14px;right:16px;
  color:#64748b;font-size:18px;cursor:pointer;
  background:none;border:none;padding:4px 8px;border-radius:4px;
}
.modal-close:hover{color:#e2e8f0;background:#334155}
.modal-qtitle{
  color:#e2e8f0;font-size:14px;font-weight:600;line-height:1.5;
  margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid #2a4a7f;
  padding-right:30px;
}
.modal-sec{color:#4a7fa5;font-size:10px;text-transform:uppercase;
  letter-spacing:1.2px;font-weight:700;margin-bottom:4px;margin-top:14px}
.modal-sec:first-of-type{margin-top:0}
.modal-def{color:#94a3b8;font-size:13px;line-height:1.6}
.modal-formula{background:#0d1b2e;border:1px solid #1e3a5f;border-radius:7px;
  padding:10px 14px;font-family:'Courier New',monospace;color:#4ade80;font-size:13px;line-height:1.5}
.modal-calc{color:#e2e8f0;font-size:13px;line-height:1.7}
.modal-calc strong{color:#22d3ee}
.modal-table{width:100%;border-collapse:collapse;margin-top:8px}
.modal-table th{color:#64748b;font-size:10px;text-transform:uppercase;
  letter-spacing:.7px;padding:6px 10px;border-bottom:1px solid #2a4a7f;text-align:left}
.modal-table td{color:#e2e8f0;font-size:12px;padding:8px 10px;border-bottom:1px solid #1e293b}
.modal-table tr:last-child td{border-bottom:none}
.src-ex{display:inline-block;background:#7c3aed22;border:1px solid #7c3aed;color:#a78bfa;
  padding:1px 7px;border-radius:3px;font-size:11px;font-weight:700}
.src-nx{display:inline-block;background:#16a34a22;border:1px solid #16a34a;color:#4ade80;
  padding:1px 7px;border-radius:3px;font-size:11px;font-weight:700}
.src-cb{display:inline-block;background:#1d4ed822;border:1px solid #1d4ed8;color:#60a5fa;
  padding:1px 7px;border-radius:3px;font-size:11px;font-weight:700}
.d-pos{color:#4ade80;font-weight:700}
.d-neg{color:#f87171;font-weight:700}
.modal-verified{display:flex;align-items:center;gap:8px;
  background:#16a34a15;border:1px solid #16a34a44;border-radius:5px;
  padding:7px 11px;margin-top:12px;color:#4ade80;font-size:12px}

/* ── GENERAL ── */
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
        'tab': 'Overview',
        'prog_name': '', 'proj_code': '',
        'prepost_rows': [],   # parsed from Combined_Pre-Post
        'eval_rows': [],      # parsed from Combined_Eval (one dict per respondent)
        'eval_headers': {},   # col_index -> full header text
        'modal': None,
        'vendor_filter': 'All',
        'specialty_filter': 'All',
        'profession_filter': 'All',
        'api_key': '',
        'ai_insights': [],
        'jcehp_text': {},
    }
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v
_init()

# ══════════════════════════════════════════════════════════════════════════════
# PARSERS
# ══════════════════════════════════════════════════════════════════════════════

def parse_prepost(file_bytes):
    """Parse Combined_Pre-Post.xlsx into structured question blocks."""
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    # col layout: 0=Q#, 1=choice#, 2=correct_flag, 3=text, 4=pre_n, 5=post_n, 6=total_n, 7=pct
    questions = []
    i = 0
    while i < len(rows):
        r = rows[i]
        if r[0] and str(r[0]).strip().isdigit() and r[3]:
            section_label = str(r[3])  # e.g. "Pretest Question 3"
            q_text = str(r[4]) if r[4] else ''
            qnum = int(str(r[0]).strip())
            choices = []
            j = i + 1
            while j < len(rows):
                cr = rows[j]
                # stop when next question starts
                if cr[0] and str(cr[0]).strip().isdigit():
                    break
                if cr[1] is not None and cr[3] and str(cr[3]) not in ('Number of Votes', 'Right Answers'):
                    pre_n  = int(cr[4]) if cr[4] is not None else 0
                    post_n = int(cr[5]) if cr[5] is not None else 0
                    total  = int(cr[6]) if cr[6] is not None else 0
                    pct_v  = float(cr[7]) if cr[7] is not None else 0.0
                    choices.append({
                        'num': cr[1],
                        'text': str(cr[3]),
                        'pre_n': pre_n,
                        'post_n': post_n,
                        'total_n': total,
                        'pct': pct_v,
                        'correct_flag': cr[2],  # non-None if marked correct
                    })
                j += 1

            # determine totals
            pre_total  = sum(c['pre_n']  for c in choices)
            post_total = sum(c['post_n'] for c in choices)
            # correct answer: highest combined total (most common = correct for MCQ)
            correct_choice = max(choices, key=lambda c: c['total_n']) if choices else None

            # classify section
            sl = section_label.lower()
            if 'pretest' in sl:
                section = 'pretest'
            elif 'posttest' in sl:
                section = 'posttest'
            elif 'checkpoint' in sl:
                section = 'checkpoint'
            else:
                section = 'other'

            questions.append({
                'qnum': qnum,
                'section': section,
                'section_label': section_label,
                'text': q_text,
                'choices': choices,
                'pre_total': pre_total,
                'post_total': post_total,
                'correct': correct_choice,
            })
            i = j
        else:
            i += 1

    return questions


def parse_eval(file_bytes):
    """Parse Combined_Eval.xlsx -> list of respondent dicts + header map."""
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not all_rows:
        return [], {}

    raw_headers = all_rows[0]
    header_map = {}  # col_idx -> full text
    for i, v in enumerate(raw_headers):
        if v and str(v).strip():
            header_map[i] = str(v).strip()

    respondents = []
    for r in all_rows[1:]:
        # skip summary/aggregate rows — require email-like value in col 1
        email = r[1] if len(r) > 1 else None
        if not email or '@' not in str(email):
            continue
        rec = {}
        for ci, label in header_map.items():
            val = r[ci] if ci < len(r) else None
            rec[label] = val
        # convenience shortcuts
        rec['_profession'] = r[8]  if len(r) > 8  else None
        rec['_specialty']  = r[10] if len(r) > 10 else None
        rec['_practice']   = r[12] if len(r) > 12 else None
        rec['_source']     = 'Eval'  # single source for now
        respondents.append(rec)

    return respondents, header_map


# ══════════════════════════════════════════════════════════════════════════════
# DERIVED METRICS
# ══════════════════════════════════════════════════════════════════════════════

# Full labels for satisfaction questions
SAT_SHORT = {
    'This activity met the established learning objectives': 'Met learning objectives',
    'The faculty for this activity was knowledgeable and effective.': 'Faculty knowledgeable & effective',
    'The content presented was relevant and enhanced my knowledge base.': 'Content relevant & enhanced knowledge',
    'The activity provided useful tools that will improve patient care and enhance my professional practice': 'Useful tools for patient care',
    'The teaching and learning methods were effective': 'Teaching methods effective',
    'As a result of this activity, I intend to change my practice within the next 6 months.': 'Intent to change practice',
    'I am more confident in treating patients in my practice after participating in this activity.': 'More confident in treating patients',
    'The format of this activity helped learners achieve the objectives.': 'Format helped achieve objectives',
    'The content provided a fair and balanced coverage of the topic': 'Fair & balanced coverage',
}

SAT_KEYS = list(SAT_SHORT.keys())

def to_num(v):
    if v is None: return None
    try:
        f = float(str(v).strip())
        if 1 <= f <= 5: return f
    except: pass
    return None

def pct(n, d):
    return round(100*n/d, 1) if d else 0.0

def compute_sat(respondents):
    """Returns list of {label, short, mean, n, vals}"""
    results = []
    for key in SAT_KEYS:
        vals = [to_num(r.get(key)) for r in respondents]
        vals = [v for v in vals if v is not None]
        if vals:
            results.append({
                'label': key,
                'short': SAT_SHORT.get(key, key[:50]),
                'mean': round(sum(vals)/len(vals), 2),
                'n': len(vals),
                'vals': vals,
            })
    return results

def compute_knowledge_pairs(prepost_rows):
    """Match pretest Qs to posttest Qs by question order."""
    pre_qs  = [q for q in prepost_rows if q['section'] == 'pretest'  and q['choices']]
    post_qs = [q for q in prepost_rows if q['section'] == 'posttest' and q['choices']]
    checkpoints = [q for q in prepost_rows if q['section'] == 'checkpoint' and q['choices']]

    pairs = []
    for i, pq in enumerate(pre_qs):
        # match by index to same-indexed posttest question
        postq = post_qs[i] if i < len(post_qs) else None

        # correct answer = most common choice (highest total_n)
        correct = pq['correct']
        if correct is None: continue

        pre_correct  = correct['pre_n']
        pre_total    = pq['pre_total']
        pre_pct      = pct(pre_correct, pre_total)

        if postq:
            # find matching answer in post
            post_correct_choice = next(
                (c for c in postq['choices'] if c['text'] == correct['text']),
                None
            )
            post_n     = post_correct_choice['post_n'] if post_correct_choice else 0
            post_total = postq['post_total']
            post_pct   = pct(post_n, post_total)
        else:
            post_n = correct['post_n']
            post_total = pq['post_total']
            post_pct   = pct(post_n, post_total)

        gain = round(post_pct - pre_pct, 1)

        pairs.append({
            'label': pq['text'] or pq['section_label'],
            'correct_text': correct['text'],
            'pre_pct': pre_pct,
            'post_pct': post_pct,
            'pre_n': pre_total,
            'post_n': post_total,
            'gain': gain,
            'pre_raw': pre_correct,
            'post_raw': post_n,
        })

    # also include checkpoints
    for q in checkpoints:
        if not q['correct']: continue
        c = q['correct']
        post_pct = pct(c['post_n'], q['post_total']) if q['post_total'] else 0
        pre_pct  = pct(c['pre_n'],  q['pre_total'])  if q['pre_total']  else 0
        pairs.append({
            'label': q['text'] or q['section_label'],
            'correct_text': c['text'],
            'pre_pct': pre_pct,
            'post_pct': post_pct,
            'pre_n': q['pre_total'],
            'post_n': q['post_total'],
            'gain': round(post_pct - pre_pct, 1),
            'pre_raw': c['pre_n'],
            'post_raw': c['post_n'],
            'is_checkpoint': True,
        })

    return pairs

def compute_eval_metrics(respondents):
    """Compute intent, recommend, bias-free, content-new from eval respondents."""
    n = len(respondents)
    if n == 0:
        return {}

    def yes_pct(key):
        vals = [str(r.get(key, '') or '').strip().lower() for r in respondents]
        yes  = sum(1 for v in vals if v.startswith('yes'))
        return pct(yes, len(vals)), len(vals)

    intent_key   = 'As a result of this activity, I intend to change my practice within the next 6 months.'
    recommend_key = 'Would you recommend this program to a colleague?'
    bias_key      = 'Overall, was the content of this activity free of commercial bias?'
    new_key       = 'What percentage of the educational content presented was NEW to you?'

    def new_pct_mean():
        vals = []
        for r in respondents:
            v = r.get(new_key)
            if v is None: continue
            try:
                f = float(str(v).strip())
                if f <= 1: f *= 100
                vals.append(f)
            except: pass
        return round(sum(vals)/len(vals)*100, 1) if vals else None, len(vals)

    intent_p, intent_n   = yes_pct(intent_key)
    rec_p,    rec_n      = yes_pct(recommend_key)
    bias_p,   bias_n     = yes_pct(bias_key)
    new_p,    new_n      = new_pct_mean()

    # confidence
    conf_key = 'How confident are you that you will be able to make these intended changes?'
    conf_vals = [str(r.get(conf_key,'')).strip().lower() for r in respondents if r.get(conf_key)]
    conf_map = {'not at all confident':1,'not very confident':2,'neutral':3,'somewhat confident':4,'very confident':5}
    conf_nums = [conf_map[v] for v in conf_vals if v in conf_map]
    conf_mean = round(sum(conf_nums)/len(conf_nums),2) if conf_nums else None

    return {
        'intent':    {'pct': intent_p, 'n': intent_n},
        'recommend': {'pct': rec_p,    'n': rec_n},
        'bias_free': {'pct': bias_p,   'n': bias_n},
        'content_new': {'pct': new_p,  'n': new_n},
        'confidence': {'mean': conf_mean, 'n': len(conf_nums)},
        'n_total': n,
    }

def get_filter_options(respondents):
    specs  = sorted(set(str(r['_specialty']  or '').strip() for r in respondents if r.get('_specialty')  and str(r['_specialty']).strip()))
    profs  = sorted(set(str(r['_profession'] or '').strip() for r in respondents if r.get('_profession') and str(r['_profession']).strip()))
    return specs, profs

def apply_eval_filters(respondents):
    sf = st.session_state.get('specialty_filter', 'All')
    pf = st.session_state.get('profession_filter', 'All')
    out = respondents
    if sf != 'All':
        out = [r for r in out if str(r.get('_specialty') or '').strip() == sf]
    if pf != 'All':
        out = [r for r in out if str(r.get('_profession') or '').strip() == pf]
    return out

# ══════════════════════════════════════════════════════════════════════════════
# MODAL
# ══════════════════════════════════════════════════════════════════════════════
def render_modal():
    m = st.session_state.get('modal')
    if not m: return

    def fmt(v, u=''):
        return f'{v}{u}' if v is not None else '—'

    def delta_html(pre, post, u=''):
        if pre is None or post is None: return '—'
        d = round(post - pre, 1)
        sign = '+' if d >= 0 else ''
        css  = 'd-pos' if d >= 0 else 'd-neg'
        return f'<span class="{css}">{sign}{d}{u}</span>'

    # source table
    rows_html = ''
    for src, badge, pre, post, n, u in m.get('sources', []):
        cls = 'src-ex' if src=='Exchange' else ('src-nx' if src=='Nexus' else 'src-cb')
        bold = ' style="font-weight:700"' if src=='Combined' else ''
        rows_html += f'''<tr{bold}>
          <td><span class="{cls}">{src}</span></td>
          <td>{fmt(n)}</td>
          <td>{fmt(pre,u)}</td>
          <td>{fmt(n)}</td>
          <td>{fmt(post,u)}</td>
          <td>{delta_html(pre,post,u)}</td>
        </tr>'''

    table_html = f'''
    <div class="modal-sec">Data Source Breakdown</div>
    <table class="modal-table">
      <thead><tr>
        <th>Source</th><th>n Pre</th><th>Pre{m.get("unit","")}</th>
        <th>n Post</th><th>Post{m.get("unit","")}</th><th>Δ</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>''' if rows_html else ''

    correct_html = ''
    if m.get('correct'):
        correct_html = f'<div style="margin-top:10px;padding:7px 11px;background:#16a34a15;border:1px solid #16a34a44;border-radius:5px;color:#4ade80;font-size:12px">✓ Correct answer: <strong>{m["correct"]}</strong></div>'

    verified = ''
    sources = m.get('sources', [])
    has_both = any(s[0]=='Exchange' for s in sources) and any(s[0]=='Nexus' for s in sources)
    if has_both:
        verified = '<div class="modal-verified">✓ Both Exchange and Nexus data included in combined calculation</div>'

    st.markdown(f"""
<div class="modal-overlay" onclick="if(event.target===this)this.remove()">
  <div class="modal-card" onclick="event.stopPropagation()">
    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</button>
    <div class="modal-qtitle">{m.get('title','')}</div>
    <div class="modal-sec">What It Means</div>
    <div class="modal-def">{m.get('definition','')}</div>
    <div class="modal-sec">Formula</div>
    <div class="modal-formula">{m.get('formula','')}</div>
    <div class="modal-sec">Actual Calculation</div>
    <div class="modal-calc">{m.get('calculation','')}</div>
    {correct_html}
    {table_html}
    {verified}
  </div>
</div>""", unsafe_allow_html=True)

    if st.button("✕ Close", key="modal_close_btn"):
        st.session_state['modal'] = None
        st.rerun()


def open_modal(data):
    st.session_state['modal'] = data
    st.rerun()

def kn_modal(q):
    pre_pct  = q['pre_pct']; post_pct = q['post_pct']
    pre_n    = q['pre_n'];   post_n   = q['post_n']
    gain     = q['gain']
    pre_raw  = q.get('pre_raw', 0); post_raw = q.get('post_raw', 0)
    return {
        'title': q['label'],
        'definition': 'Knowledge assessment MCQ — measures % of learners answering correctly before vs. after the educational program.',
        'formula': 'Correct answers / Total responses × 100  for each time point',
        'calculation': f"Pre: {pre_raw}/{pre_n} = <strong>{pre_pct}%</strong> → Post: {post_raw}/{post_n} = <strong>{post_pct}%</strong> (Δ <strong>{'+' if gain>=0 else ''}{gain}pp</strong>)",
        'correct': q.get('correct_text'),
        'unit': '%',
        'sources': [
            ('Combined', 'cb', pre_pct, post_pct, pre_n, '%'),
        ],
    }

def sat_modal(s):
    return {
        'title': s['label'],
        'definition': 'Post-activity satisfaction rating — learners rate this item on a 1–5 Likert scale after the program.',
        'formula': 'Mean of all responses on 1–5 scale (post-activity evaluation only)',
        'calculation': f"Mean rating: <strong>{s['mean']}/5.0</strong> ({round(s['mean']/5*100)}th percentile of scale) | n={s['n']}",
        'unit': '/5',
        'sources': [
            ('Combined', 'cb', None, s['mean'], s['n'], '/5'),
        ],
    }

def ev_modal(label, pct_v, n, definition):
    raw = round(pct_v/100*n) if pct_v and n else '?'
    return {
        'title': label,
        'definition': definition,
        'formula': "Count of 'Yes' / Agree responses ÷ Total respondents × 100",
        'calculation': f"<strong>{raw}/{n} = {pct_v}%</strong>",
        'unit': '%',
        'sources': [
            ('Combined', 'cb', None, pct_v, n, '%'),
        ],
    }

# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD SCREEN
# ══════════════════════════════════════════════════════════════════════════════
def render_upload():
    st.markdown("""
<div style="padding:60px 32px;text-align:center">
  <div style="font-size:52px;margin-bottom:14px">🧬</div>
  <div style="color:#e2e8f0;font-size:24px;font-weight:700;margin-bottom:6px">Integritas CME Outcomes Harmonizer</div>
  <div style="color:#64748b;font-size:14px;margin-bottom:36px">Upload your Pre/Post and Evaluation files to begin analysis</div>
</div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div style="background:#1e293b;border:2px dashed #a78bfa;border-radius:12px;padding:22px;text-align:center;margin-bottom:8px"><div style="font-size:30px">📊</div><div style="color:#a78bfa;font-size:15px;font-weight:600;margin:6px 0">Pre/Post File</div><div style="color:#64748b;font-size:12px">Combined_Pre-Post.xlsx</div></div>', unsafe_allow_html=True)
        pp_file = st.file_uploader("Pre/Post", type=['xlsx'], key='pp_upload', label_visibility='collapsed')
    with c2:
        st.markdown('<div style="background:#1e293b;border:2px dashed #4ade80;border-radius:12px;padding:22px;text-align:center;margin-bottom:8px"><div style="font-size:30px">📋</div><div style="color:#4ade80;font-size:15px;font-weight:600;margin:6px 0">Evaluation File</div><div style="color:#64748b;font-size:12px">Combined_Eval.xlsx</div></div>', unsafe_allow_html=True)
        ev_file = st.file_uploader("Evaluation", type=['xlsx'], key='ev_upload', label_visibility='collapsed')

    if pp_file or ev_file:
        if st.button("🚀  Analyze", use_container_width=True):
            with st.spinner("Parsing…"):
                if pp_file:
                    st.session_state['prepost_rows'] = parse_prepost(pp_file.read())
                    st.session_state['prog_name']    = pp_file.name.rsplit('.',1)[0]
                if ev_file:
                    rows, hdrs = parse_eval(ev_file.read())
                    st.session_state['eval_rows']    = rows
                    st.session_state['eval_headers'] = hdrs
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# FILTER BAR
# ══════════════════════════════════════════════════════════════════════════════
def render_filter_bar(respondents):
    specs, profs = get_filter_options(respondents)
    sf  = st.session_state.get('specialty_filter', 'All')
    pf  = st.session_state.get('profession_filter', 'All')
    vf  = st.session_state.get('vendor_filter', 'All')
    n   = len(respondents)

    # Build HTML for display
    spec_chips = ''
    for sp in specs:
        cnt = sum(1 for r in respondents if str(r.get('_specialty') or '').strip() == sp)
        active = 'chip-active-sp' if sf==sp else ''
        spec_chips += f'<span class="chip {active}" title="{sp}">{sp[:20]} ({cnt})</span> '

    prof_chips = ''
    for pr in profs:
        cnt = sum(1 for r in respondents if str(r.get('_profession') or '').strip() == pr)
        active = 'chip-active-sp' if pf==pr else ''
        prof_chips += f'<span class="chip {active}">{pr} ({cnt})</span> '

    st.markdown(f"""
<div class="fbar">
  <span class="flabel">Specialty:</span>
  <span class="chip {'chip-active-all' if sf=='All' else ''}">All ({n})</span>
  {spec_chips}
  <span class="divider-v"></span>
  <span class="flabel">Profession:</span>
  <span class="chip {'chip-active-all' if pf=='All' else ''}">All</span>
  {prof_chips}
  <span class="divider-v"></span>
  <span class="flabel">Vendor:</span>
  <span class="chip {'chip-active-all' if vf=='All' else ''}">All</span>
  <span class="chip {'chip-active-nx' if vf=='Nexus' else ''}">Nexus</span>
  <span class="chip {'chip-active-ex' if vf=='Exchange' else ''}">Exchange</span>
</div>""", unsafe_allow_html=True)

    # Actual filter buttons (invisible, but functional)
    with st.expander("🔽 Click to filter", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write("**Specialty**")
            if st.button("All specialties", key='sf_all'):
                st.session_state['specialty_filter'] = 'All'; st.rerun()
            for sp in specs:
                if st.button(sp, key=f'sf_{sp}'):
                    st.session_state['specialty_filter'] = sp; st.rerun()
        with c2:
            st.write("**Profession**")
            if st.button("All professions", key='pf_all'):
                st.session_state['profession_filter'] = 'All'; st.rerun()
            for pr in profs:
                if st.button(pr, key=f'pf_{pr}'):
                    st.session_state['profession_filter'] = pr; st.rerun()
        with c3:
            st.write("**Vendor**")
            if st.button("All vendors", key='vf_all'):
                st.session_state['vendor_filter'] = 'All'; st.rerun()
            if st.button("Nexus", key='vf_nx'):
                st.session_state['vendor_filter'] = 'Nexus'; st.rerun()
            if st.button("Exchange", key='vf_ex'):
                st.session_state['vendor_filter'] = 'Exchange'; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
TABS = ['Overview','Knowledge','Competence','Evaluation',
        'AI Insights','JCEHP Article','CIRCLE Framework','Kirkpatrick','Key Findings']

def render_tabs():
    active = st.session_state.get('tab', 'Overview')
    cols = st.columns(len(TABS))
    for i, t in enumerate(TABS):
        with cols[i]:
            if st.button(t, key=f'tab_{t}', use_container_width=True,
                         type='primary' if t==active else 'secondary'):
                st.session_state['tab'] = t
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW TAB
# ══════════════════════════════════════════════════════════════════════════════
def tab_overview(prepost, respondents):
    kn_pairs  = compute_knowledge_pairs(prepost)
    sat_items = compute_sat(respondents)
    ev_m      = compute_eval_metrics(respondents)

    n_eval    = len(respondents)
    n_pre     = sum(q['pre_total'] for q in prepost if q['section']=='pretest' and q['text'])
    # use the first pretest Q for total pre count
    first_pre = next((q for q in prepost if q['section']=='pretest'), None)
    n_pre_total = first_pre['pre_total'] if first_pre else 0
    n_post_total = first_pre['post_total'] if first_pre else 0

    avg_gain = round(sum(q['gain'] for q in kn_pairs if not q.get('is_checkpoint'))/
               max(1, len([q for q in kn_pairs if not q.get('is_checkpoint')])), 1) if kn_pairs else 0

    # ── STAT CARDS ──
    sc_data = [
        ('Total Pre-Test',    n_pre_total,  '#60a5fa', 'all pre-test starters'),
        ('Pre-Only Learners', n_pre_total - n_post_total, '#fb923c', 'no post/eval'),
        ('Pre/Post Matched',  n_post_total, '#4ade80', f'{pct(n_post_total,n_pre_total)}% of pre-test starters'),
        ('With Evaluation',   n_eval,       '#a78bfa', f'Moore Levels 2–4'),
        ('Avg Knowledge Gain',f'+{avg_gain}pp', '#22d3ee', f'{len(kn_pairs)} question pairs'),
        ('Avg % New Content', f'{ev_m.get("content_new",{}).get("pct") or "—"}%', '#f59e0b', f'n={ev_m.get("content_new",{}).get("n","—")}'),
    ]
    html = '<div class="sc-grid">'
    for lbl, val, color, sub in sc_data:
        html += f'''<div class="sc">
  <div class="sc-label">{lbl}</div>
  <div class="sc-val" style="color:{color}">{val}</div>
  <div class="sc-sub">{sub}</div>
</div>'''
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    # ── TWO COLUMNS ──
    left, right = st.columns([6, 4])

    with left:
        st.markdown('<div class="scard">', unsafe_allow_html=True)
        st.markdown('<div class="scard-title">Knowledge Gains — Pre vs Post</div>', unsafe_allow_html=True)
        for q in [x for x in kn_pairs if not x.get('is_checkpoint')]:
            gc    = '#4ade80' if q['gain'] >= 0 else '#f87171'
            gs    = f'+{q["gain"]}pp' if q['gain'] >= 0 else f'{q["gain"]}pp'
            pre_w = min(100, int(q['pre_pct']))
            post_w= min(100, int(q['post_pct']))
            st.markdown(f"""
<div class="kn-item">
  <div class="kn-q">{q['label'][:90]}… <span class="kn-gain" style="color:{gc}">{gs}</span></div>
  <div class="bar-row">
    <span class="bar-lbl">PRE</span>
    <div class="bar-bg"><div class="bar-fill" style="width:{pre_w}%;background:#f59e0b"></div></div>
    <span class="bar-pct">{q['pre_pct']}%</span>
  </div>
  <div class="bar-row">
    <span class="bar-lbl">POST</span>
    <div class="bar-bg"><div class="bar-fill" style="width:{post_w}%;background:#4ade80"></div></div>
    <span class="bar-pct">{q['post_pct']}%</span>
  </div>
  <div class="correct-lbl">✓ {q['correct_text'][:80]}</div>
</div>""", unsafe_allow_html=True)
            if st.button("🔍", key=f'ov_kn_{q["label"][:20]}'):
                open_modal(kn_modal(q))
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        # Competence shift (single item if available)
        comp_q = next((q for q in prepost if q['section']=='pretest' and 'currently' in q['text'].lower()), None)
        if comp_q:
            st.markdown('<div class="scard">', unsafe_allow_html=True)
            st.markdown('<div class="scard-title">Competence Shifts</div>', unsafe_allow_html=True)
            c = comp_q['correct']
            if c:
                pre_pct_c  = pct(c['pre_n'],  comp_q['pre_total'])
                post_pct_c = pct(c['post_n'], comp_q['post_total'])
                st.markdown(f"""
<div class="comp-item">
  <div class="comp-q">{comp_q['text'][:80]}</div>
  <div class="comp-pre">{pre_pct_c}%</div>
  <div class="comp-arrow">→</div>
  <div class="comp-post">{post_pct_c}%</div>
  <div class="comp-delta" style="color:#4ade80">+{round(post_pct_c-pre_pct_c,1)}pp</div>
</div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Satisfaction
        st.markdown('<div class="scard">', unsafe_allow_html=True)
        st.markdown('<div class="scard-title">Satisfaction</div>', unsafe_allow_html=True)

        ev_circle_data = [
            ('Intent to\nChange', ev_m.get('intent',{}).get('pct'), f"(n={ev_m.get('intent',{}).get('n',0)})", '#22d3ee', 'intent'),
            ('Would\nRecommend', ev_m.get('recommend',{}).get('pct'), f"(n={ev_m.get('recommend',{}).get('n',0)})", '#4ade80', 'recommend'),
            ('Bias-\nFree',      ev_m.get('bias_free',{}).get('pct'), f"(n={ev_m.get('bias_free',{}).get('n',0)})", '#a78bfa', 'bias_free'),
            ('Content\nNew',     ev_m.get('content_new',{}).get('pct'), f"(n={ev_m.get('content_new',{}).get('n',0)})", '#f59e0b', 'content_new'),
        ]
        circ_html = '<div class="ev-circles">'
        for name, val, sub, color, key in ev_circle_data:
            vs = f'{val}%' if val is not None else '—'
            pf_deg = int(val * 3.6) if val else 0
            circ_html += f'''
<div class="ev-circle">
  <div class="ev-ring" style="border-color:{color}">
    <div class="ev-val" style="color:{color}">{vs}</div>
  </div>
  <div class="ev-name">{name}<br><span style="color:#475569;font-size:9px">{sub}</span></div>
</div>'''
        circ_html += '</div>'
        st.markdown(circ_html, unsafe_allow_html=True)

        # Sat circles - using full labels
        if sat_items:
            circ2 = '<div class="sat-circles">'
            for s in sat_items:
                pf_v = round(s['mean']/5*100)
                color = '#22d3ee' if pf_v >= 80 else ('#f59e0b' if pf_v >= 60 else '#f87171')
                circ2 += f'''
<div class="sat-circle">
  <div class="sat-ring" style="border-color:{color}">
    <div class="sat-val" style="color:{color}">{s['mean']}</div>
    <div style="font-size:9px;color:#475569">/5</div>
  </div>
  <div class="sat-name">{s['short']}</div>
</div>'''
                if st.button("🔍", key=f'ov_sat_{s["short"][:15]}'):
                    open_modal(sat_modal(s))
            circ2 += '</div>'
            st.markdown(circ2, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE TAB
# ══════════════════════════════════════════════════════════════════════════════
def tab_knowledge(prepost):
    kn_pairs = compute_knowledge_pairs(prepost)
    st.markdown('<div class="scard">', unsafe_allow_html=True)
    st.markdown('<div class="scard-title">Knowledge Assessment — MCQ Pre/Post (Moore Level 3)</div>', unsafe_allow_html=True)

    if not kn_pairs:
        st.markdown('<div style="color:#64748b;padding:20px">No matched question pairs detected.</div>', unsafe_allow_html=True)
    else:
        # Table header
        tbl = '''<table style="width:100%;border-collapse:collapse">
<thead><tr>'''
        for h in ['Question','Pre %','Post %','Gain','Pre n','Post n','Correct Answer','']:
            tbl += f'<th style="color:#475569;font-size:10px;text-transform:uppercase;padding:8px 8px;border-bottom:1px solid #334155;text-align:left">{h}</th>'
        tbl += '</tr></thead><tbody>'

        for i, q in enumerate(kn_pairs):
            gc = '#4ade80' if q['gain'] >= 0 else '#f87171'
            gs = f'+{q["gain"]}pp' if q['gain'] >= 0 else f'{q["gain"]}pp'
            ck = '🏁 ' if q.get('is_checkpoint') else ''
            tbl += f'''<tr style="border-bottom:1px solid #1e293b">
  <td style="color:#e2e8f0;font-size:12px;padding:9px 8px" title="{q['label']}">{ck}{q['label'][:55]}{'…' if len(q['label'])>55 else ''}</td>
  <td style="color:#f59e0b;font-size:13px;font-weight:600;padding:9px 8px">{q['pre_pct']}%</td>
  <td style="color:#4ade80;font-size:13px;font-weight:600;padding:9px 8px">{q['post_pct']}%</td>
  <td style="color:{gc};font-size:13px;font-weight:700;padding:9px 8px">{gs}</td>
  <td style="color:#64748b;font-size:12px;padding:9px 8px">{q['pre_n']}</td>
  <td style="color:#64748b;font-size:12px;padding:9px 8px">{q['post_n']}</td>
  <td style="color:#94a3b8;font-size:11px;padding:9px 8px">{q['correct_text'][:50]}</td>
  <td style="padding:4px"></td>
</tr>'''
        tbl += '</tbody></table>'
        st.markdown(tbl, unsafe_allow_html=True)

        btn_cols = st.columns(min(len(kn_pairs), 8))
        for i, q in enumerate(kn_pairs):
            with btn_cols[i % len(btn_cols)]:
                if st.button(f"🔍 Q{i+1}", key=f'kn_tab_{i}'):
                    open_modal(kn_modal(q))
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# EVALUATION TAB
# ══════════════════════════════════════════════════════════════════════════════
def tab_evaluation(respondents):
    ev_m      = compute_eval_metrics(respondents)
    sat_items = compute_sat(respondents)
    n         = len(respondents)

    # Big metric cards
    metric_defs = [
        ('Intent to Change Practice', 'intent', '#22d3ee',
         'Percentage indicating intent to change clinical practice (Moore Level 5 precursor).'),
        ('Would Recommend Program',   'recommend', '#4ade80',
         'Percentage who would recommend this program to a colleague.'),
        ('Bias-Free Content',         'bias_free', '#a78bfa',
         'Percentage rating content free of commercial bias (required ACCME metric).'),
    ]
    cols = st.columns(3)
    for i, (lbl, key, color, defn) in enumerate(metric_defs):
        m2  = ev_m.get(key, {})
        val = f"{m2.get('pct','—')}%" if m2.get('pct') is not None else '—'
        nn  = m2.get('n', 0)
        pv  = m2.get('pct')
        with cols[i]:
            st.markdown(f'''<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px;margin-bottom:8px">
  <div style="color:#64748b;font-size:10px;text-transform:uppercase;margin-bottom:4px">{lbl}</div>
  <div style="font-size:34px;font-weight:700;color:{color}">{val}</div>
  <div style="color:#475569;font-size:10px">n={nn}</div>
</div>''', unsafe_allow_html=True)
            if st.button("🔍", key=f'ev_card_{i}'):
                open_modal(ev_modal(lbl, pv, nn, defn))

    cn = ev_m.get('content_new', {})
    if cn.get('pct'):
        st.markdown(f'''<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px;margin-bottom:14px">
  <div style="color:#64748b;font-size:10px;text-transform:uppercase;margin-bottom:4px">Content New to Learner</div>
  <div style="font-size:28px;font-weight:700;color:#f59e0b">{cn["pct"]}%</div>
  <div style="color:#475569;font-size:10px">n={cn.get("n","—")}</div>
</div>''', unsafe_allow_html=True)

    # Satisfaction — FULL labels
    if sat_items:
        st.markdown('<div class="scard">', unsafe_allow_html=True)
        st.markdown('<div class="scard-title">Satisfaction Ratings (1–5 Likert)</div>', unsafe_allow_html=True)
        for s in sat_items:
            pf_v = round(s['mean']/5*100)
            color = '#22d3ee' if pf_v >= 80 else ('#f59e0b' if pf_v >= 60 else '#f87171')
            # Show FULL label here
            st.markdown(f'''<div style="display:flex;align-items:center;gap:10px;margin:9px 0">
  <div style="color:#94a3b8;font-size:12px;width:380px;flex-shrink:0;line-height:1.35" title="{s['label']}">{s['label']}</div>
  <div style="flex:1;background:#334155;border-radius:3px;height:8px">
    <div style="width:{pf_v}%;background:{color};border-radius:3px;height:8px"></div>
  </div>
  <div style="color:#e2e8f0;font-size:13px;font-weight:600;width:44px;text-align:right">{s['mean']}</div>
</div>''', unsafe_allow_html=True)
            if st.button("🔍", key=f'ev_sat_{s["short"][:12]}'):
                open_modal(sat_modal(s))
        st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# KEY FINDINGS TAB
# ══════════════════════════════════════════════════════════════════════════════
def tab_key_findings(prepost, respondents):
    kn_pairs  = compute_knowledge_pairs(prepost)
    ev_m      = compute_eval_metrics(respondents)

    # Knowledge circles
    if kn_pairs:
        st.markdown('<div class="scard">', unsafe_allow_html=True)
        st.markdown('<div class="scard-title">Knowledge Gain — Prior vs. After</div>', unsafe_allow_html=True)
        n_cols = min(4, len(kn_pairs))
        cols   = st.columns(n_cols)
        for i, q in enumerate([x for x in kn_pairs if not x.get('is_checkpoint')]):
            with cols[i % n_cols]:
                st.markdown(f"""
<div style="text-align:center;margin-bottom:12px">
  <div style="display:flex;gap:6px;justify-content:center;align-items:center;margin-bottom:8px">
    <div style="width:80px;height:80px;border-radius:50%;border:5px solid #f59e0b;display:flex;align-items:center;justify-content:center;flex-direction:column">
      <div style="font-size:18px;font-weight:700;color:#f59e0b">{q['pre_pct']}%</div>
      <div style="font-size:9px;color:#64748b">PRE</div>
    </div>
    <div style="font-size:14px;color:#334155">→</div>
    <div style="width:80px;height:80px;border-radius:50%;border:5px solid #4ade80;display:flex;align-items:center;justify-content:center;flex-direction:column">
      <div style="font-size:18px;font-weight:700;color:#4ade80">{q['post_pct']}%</div>
      <div style="font-size:9px;color:#64748b">POST</div>
    </div>
  </div>
  <div style="color:#4ade80;font-size:12px;font-weight:700">+{q['gain']}pp gain</div>
  <div style="color:#64748b;font-size:10px;margin-top:3px;line-height:1.3">{q['label'][:50]}</div>
</div>""", unsafe_allow_html=True)
                if st.button("🔍", key=f'kf_kn_{i}'):
                    open_modal(kn_modal(q))
        st.markdown('</div>', unsafe_allow_html=True)

    # Eval circles
    st.markdown('<div class="scard">', unsafe_allow_html=True)
    st.markdown('<div class="scard-title">Evaluation Highlights</div>', unsafe_allow_html=True)
    ev_defs = [
        ('Intent to Change', 'intent', '#22d3ee', 'Intent to change clinical practice (Moore Level 5 precursor).'),
        ('Would Recommend',  'recommend', '#4ade80', 'Would recommend program to colleague.'),
        ('Bias-Free',        'bias_free', '#a78bfa', 'Content rated free of commercial bias.'),
        ('Content New',      'content_new', '#f59e0b', 'Mean % of content new to learners.'),
    ]
    circ = '<div style="display:flex;gap:24px;justify-content:center;flex-wrap:wrap;padding:8px 0">'
    for name, key, color, defn in ev_defs:
        val = ev_m.get(key, {}).get('pct')
        nn  = ev_m.get(key, {}).get('n', 0)
        vs  = f'{val}%' if val is not None else '—'
        circ += f'''
<div style="text-align:center">
  <div style="width:100px;height:100px;border-radius:50%;border:6px solid {color};display:flex;align-items:center;justify-content:center;flex-direction:column;margin:0 auto 8px;cursor:pointer">
    <div style="font-size:26px;font-weight:800;color:{color}">{vs}</div>
  </div>
  <div style="color:#64748b;font-size:11px">{name}<br><span style="font-size:10px;color:#334155">(n={nn})</span></div>
</div>'''
    circ += '</div>'
    st.markdown(circ, unsafe_allow_html=True)
    ev_cols = st.columns(4)
    for i, (name, key, color, defn) in enumerate(ev_defs):
        with ev_cols[i]:
            pv = ev_m.get(key,{}).get('pct'); nn = ev_m.get(key,{}).get('n',0)
            if st.button("🔍", key=f'kf_ev_{i}'):
                open_modal(ev_modal(name, pv, nn, defn))
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# KIRKPATRICK TAB
# ══════════════════════════════════════════════════════════════════════════════
def tab_kirkpatrick(prepost, respondents):
    kn_pairs  = compute_knowledge_pairs(prepost)
    sat_items = compute_sat(respondents)
    ev_m      = compute_eval_metrics(respondents)

    levels = [
        ('Level 1', 'Reaction', '#22d3ee', '😊'),
        ('Level 2', 'Learning', '#4ade80', '📚'),
        ('Level 3', 'Behavior', '#a78bfa', '🔄'),
        ('Level 4', 'Results',  '#f59e0b', '🎯'),
    ]
    for lv, title, color, icon in levels:
        st.markdown(f'<div style="background:#1e293b;border-left:4px solid {color};border-radius:0 8px 8px 0;padding:16px;margin-bottom:12px">', unsafe_allow_html=True)
        st.markdown(f'<div style="color:{color};font-size:13px;font-weight:700;margin-bottom:8px">{icon} {lv}: {title}</div>', unsafe_allow_html=True)
        if lv == 'Level 1':
            for s in sat_items[:5]:
                pf = round(s['mean']/5*100)
                st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin:5px 0"><div style="color:#94a3b8;font-size:12px;flex:1">{s["label"][:60]}</div><div style="width:180px;background:#334155;border-radius:3px;height:7px"><div style="width:{pf}%;background:{color};border-radius:3px;height:7px"></div></div><div style="color:#e2e8f0;font-size:12px;width:44px;text-align:right">{s["mean"]}/5</div></div>', unsafe_allow_html=True)
                if st.button("🔍", key=f'kirk_l1_{s["short"][:10]}'):
                    open_modal(sat_modal(s))
        elif lv == 'Level 2':
            avg = round(sum(q['gain'] for q in kn_pairs)/max(1,len(kn_pairs)),1) if kn_pairs else 0
            st.markdown(f'<div style="color:{color};font-size:18px;font-weight:700;margin-bottom:8px">{len(kn_pairs)} Questions | Avg +{avg}pp</div>', unsafe_allow_html=True)
            for i, q in enumerate(kn_pairs):
                pf = min(100,max(0,int(q['gain']*2)))
                st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin:5px 0"><div style="color:#94a3b8;font-size:12px;flex:1">{q["label"][:55]}</div><div style="width:180px;background:#334155;border-radius:3px;height:7px"><div style="width:{pf}%;background:{color};border-radius:3px;height:7px"></div></div><div style="color:#e2e8f0;font-size:12px;width:44px;text-align:right">+{q["gain"]}pp</div></div>', unsafe_allow_html=True)
                if st.button("🔍", key=f'kirk_l2_{i}'):
                    open_modal(kn_modal(q))
        elif lv == 'Level 3':
            ip = ev_m.get('intent',{}).get('pct'); nn = ev_m.get('intent',{}).get('n',0)
            if ip:
                st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin:5px 0"><div style="color:#94a3b8;font-size:12px;flex:1">Intend to change practice</div><div style="width:200px;background:#334155;border-radius:3px;height:8px"><div style="width:{ip}%;background:{color};border-radius:3px;height:8px"></div></div><div style="color:#e2e8f0;font-size:13px;font-weight:600;width:44px;text-align:right">{ip}%</div></div>', unsafe_allow_html=True)
                if st.button("🔍", key='kirk_l3'):
                    open_modal(ev_modal('Intent to Change Practice', ip, nn, 'Percentage indicating intent to change practice.'))
        elif lv == 'Level 4':
            st.markdown('<div style="color:#64748b;font-size:13px">Follow-up data collection needed for Level 4 (Results) analysis.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CIRCLE TAB
# ══════════════════════════════════════════════════════════════════════════════
def tab_circle(prepost, respondents):
    kn_pairs  = compute_knowledge_pairs(prepost)
    sat_items = compute_sat(respondents)
    ev_m      = compute_eval_metrics(respondents)

    avg_post_kn = round(sum(q['post_pct'] for q in kn_pairs)/max(1,len(kn_pairs)),1) if kn_pairs else 0
    avg_gain    = round(sum(q['gain'] for q in kn_pairs)/max(1,len(kn_pairs)),1) if kn_pairs else 0
    avg_sat     = round(sum(s['mean'] for s in sat_items)/max(1,len(sat_items))/5*100,1) if sat_items else 0
    intent_p    = ev_m.get('intent',{}).get('pct') or 0
    rec_p       = ev_m.get('recommend',{}).get('pct') or 0
    n_pre       = next((q['pre_total'] for q in prepost if q['section']=='pretest'), 0)
    n_post      = next((q['post_total'] for q in prepost if q['section']=='pretest'), 0)
    completion  = pct(n_post, n_pre)

    dims = [
        ('C', 'Clinician\nEngagement',  f'{completion}%',  '#22d3ee',  f'completion rate (n={n_pre})', 'strong' if completion>=50 else 'prompt',
         'Pre/post completion rate — percentage of pre-test starters who completed the post-test.',
         'Pre/post matched ÷ Total pre-test starters × 100',
         f'{n_post}/{n_pre} = {completion}%'),
        ('I', 'Impact on\nlearning',    f'+{avg_gain}pp', '#22d3ee', f'avg knowledge gain (n={n_pre})', 'strong' if avg_gain>=20 else 'moderate',
         'Average knowledge gain (pp) across all MCQ pairs.',
         'Mean(Post% − Pre%) across all matched question pairs',
         f'Mean gain across {len(kn_pairs)} questions = +{avg_gain}pp'),
        ('R', 'Relevance\nin gaps',     f'{avg_sat}%', '#f87171', f'prior utilization (n={len(respondents)})', 'strong' if avg_sat>=80 else 'new insight',
         'Average satisfaction rating as % of 5-pt maximum.',
         'Mean(all satisfaction Likert ratings) ÷ 5 × 100',
         f'Mean sat: {avg_sat}% of max'),
        ('C', 'Change in\nbehavior',    f'{intent_p}%', '#22d3ee', f'intent to change (n={ev_m.get("intent",{}).get("n",0)})', 'strong' if intent_p>=70 else 'moderate',
         'Percentage of learners intending to change practice.',
         'Count(intent Yes) ÷ Total eval respondents × 100',
         f'{intent_p}% intent to change'),
        ('L', 'Linkage to\npatients',   f'{avg_post_kn}%', '#f59e0b', f'practice ready (n={len(respondents)})', 'prompt' if avg_post_kn<70 else 'strong',
         'Mean post-test accuracy across all MCQ questions.',
         'Mean(Post% correct) across all MCQ pairs',
         f'Mean post accuracy: {avg_post_kn}%'),
        ('E', 'Ecosystem\nbarriers',    str(len(respondents)), '#f59e0b', f'distinct barriers (n={len(respondents)})', 'new insight',
         'Number of unique barrier types identified by learners.',
         'Count(distinct barrier responses across patient/provider/system categories)',
         f'{len(respondents)} evaluators reporting barriers'),
    ]

    # 2x3 grid
    c1, c2, c3 = st.columns(3)
    for i, (letter, name, val, color, sub, badge, defn, formula, calc) in enumerate(dims):
        col = [c1, c2, c3][i % 3]
        badge_color = '#4ade80' if badge=='strong' else ('#f59e0b' if badge in ('moderate','new insight') else '#f87171')
        with col:
            st.markdown(f'''<div style="background:#1a2433;border:1px solid #334155;border-radius:10px;padding:18px;margin-bottom:12px;min-height:160px">
  <div style="font-size:32px;font-weight:800;color:{color};text-align:center;line-height:1">{letter}</div>
  <div style="color:#64748b;font-size:10px;text-align:center;margin:2px 0 8px;white-space:pre-line">{name}</div>
  <div style="font-size:22px;font-weight:700;color:#e2e8f0;text-align:center">{val}</div>
  <div style="text-align:center;margin-top:6px">
    <a style="color:{badge_color};font-size:10px;text-decoration:underline">{sub}</a>
    <span style="background:{badge_color}22;border:1px solid {badge_color};color:{badge_color};font-size:9px;padding:1px 6px;border-radius:3px;margin-left:4px">{badge}</span>
  </div>
</div>''', unsafe_allow_html=True)
            if st.button("🔍", key=f'circle_{i}'):
                open_modal({
                    'title': f'CIRCLE — {letter}: {name.replace(chr(10)," ")}',
                    'definition': defn,
                    'formula': formula,
                    'calculation': calc,
                    'unit': '%',
                    'sources': [('Combined','cb',None,None,len(respondents),'')],
                })


# ══════════════════════════════════════════════════════════════════════════════
# JCEHP / AI tabs (abbreviated, same as before)
# ══════════════════════════════════════════════════════════════════════════════
def tab_jcehp(prepost, respondents):
    kn_pairs = compute_knowledge_pairs(prepost)
    ev_m     = compute_eval_metrics(respondents)
    sections = ['Abstract','Introduction','Methods','Results','Discussion','Conclusion']
    existing = st.session_state.get('jcehp_text',{})
    filled   = [s for s in sections if existing.get(s)]
    done     = round(len(filled)/len(sections)*100)

    n_total = next((q['pre_total'] for q in prepost if q['section']=='pretest'), 0)
    kn_txt  = ' '.join([f"Knowledge of {q['label'][:50]}: pre {q['pre_pct']}% → post {q['post_pct']}% (Δ={q['gain']}pp)." for q in kn_pairs])
    auto = {
        'Methods': f"This outcomes analysis included learners across combined vendor data (N_pre={n_total}). Pre/post matched analysis included {next((q['post_total'] for q in prepost if q['section']=='pretest'),0)} learners. Evaluation survey data was available for {len(respondents)} participants.",
        'Results': f"Knowledge outcomes: {kn_txt[:300]}\n\nEvaluation: {ev_m.get('intent',{}).get('pct','N/A')}% indicated intent to change practice. {ev_m.get('recommend',{}).get('pct','N/A')}% would recommend this program.",
    }
    st.markdown(f'<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px;margin-bottom:14px"><div style="color:#e2e8f0;font-size:14px;font-weight:600;margin-bottom:6px">📝 JCEHP Article Preparation</div><div style="color:#64748b;font-size:11px;margin-bottom:6px">{done}% complete ({len(filled)}/{len(sections)} sections)</div><div style="background:#334155;border-radius:4px;height:6px"><div style="width:{done}%;background:#22d3ee;border-radius:4px;height:6px"></div></div></div>', unsafe_allow_html=True)
    for sec in sections:
        content = existing.get(sec, auto.get(sec,''))
        st.markdown(f'<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:14px;margin-bottom:8px"><div style="color:#a78bfa;font-size:12px;font-weight:700;margin-bottom:6px">{sec}</div>', unsafe_allow_html=True)
        new_text = st.text_area(sec, value=content, height=100, key=f'jcehp_{sec}', label_visibility='collapsed')
        if new_text != content:
            st.session_state.setdefault('jcehp_text',{})[sec] = new_text
        st.markdown('</div>', unsafe_allow_html=True)

def tab_ai_insights(prepost, respondents):
    kn_pairs = compute_knowledge_pairs(prepost)
    ev_m     = compute_eval_metrics(respondents)
    st.markdown('<div class="scard">', unsafe_allow_html=True)
    st.markdown('<div style="color:#e2e8f0;font-size:14px;font-weight:600;margin-bottom:12px">🤖 AI Insights</div>', unsafe_allow_html=True)
    api_key = st.text_input("Anthropic API Key", type="password",
                            value=st.session_state.get('api_key',''), placeholder="sk-ant-…")
    if api_key: st.session_state['api_key'] = api_key
    if st.button("Generate Insights"):
        if not api_key:
            st.error("Please enter your API key.")
        else:
            with st.spinner("Generating…"):
                kn_s = "\n".join([f"- {q['label'][:60]}: pre={q['pre_pct']}% post={q['post_pct']}% gain={q['gain']}pp" for q in kn_pairs]) or "No data"
                prompt = f"""CME outcomes analyst. Generate 5 actionable insights.
Knowledge:\n{kn_s}
Intent to change: {ev_m.get('intent',{}).get('pct','N/A')}%
Would recommend: {ev_m.get('recommend',{}).get('pct','N/A')}%
Return JSON array of 5: title, moore_level, insight, recommendation"""
                try:
                    import requests as rq
                    r = rq.post("https://api.anthropic.com/v1/messages",
                        headers={"x-api-key":api_key,"anthropic-version":"2023-06-01","content-type":"application/json"},
                        json={"model":"claude-sonnet-4-20250514","max_tokens":1200,
                              "messages":[{"role":"user","content":prompt}]},timeout=30)
                    if r.status_code==200:
                        txt = r.json()['content'][0]['text']
                        m = re.search(r'\[.*\]', txt, re.DOTALL)
                        if m: st.session_state['ai_insights'] = json.loads(m.group())
                    else: st.error(f"API error {r.status_code}")
                except Exception as e: st.error(str(e))
    for ins in st.session_state.get('ai_insights',[]):
        lvl = str(ins.get('moore_level',''))
        c = {'2':'#f59e0b','3':'#4ade80','4':'#22d3ee','5':'#a78bfa'}.get(lvl,'#64748b')
        st.markdown(f'<div style="background:#0f172a;border:1px solid #334155;border-radius:9px;padding:16px;margin-bottom:10px"><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px"><span style="background:{c}22;border:1px solid {c};color:{c};padding:1px 7px;border-radius:3px;font-size:10px;font-weight:700">MOORE {lvl}</span><div style="color:#e2e8f0;font-size:13px;font-weight:600">{ins.get("title","")}</div></div><div style="color:#94a3b8;font-size:12px;line-height:1.5">{ins.get("insight","")}</div><div style="color:#4ade80;font-size:11px;margin-top:6px">→ {ins.get("recommendation","")}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    prepost_rows = st.session_state.get('prepost_rows', [])
    eval_rows    = st.session_state.get('eval_rows', [])

    # ── HEADER ──
    prog = st.session_state.get('prog_name', '')
    pp_n = sum(q['pre_total'] for q in prepost_rows[:1]) if prepost_rows else 0
    ev_n = len(eval_rows)

    st.markdown(f"""
<div class="app-hdr">
  <div class="app-logo"><span>Integritas</span> CME Outcomes Harmonizer</div>
  <div class="hdr-meta">{prog}</div>
  <div style="flex:1"></div>
  {'<span class="hdr-pill-nx">Pre/Post (' + str(pp_n) + ')</span>' if prepost_rows else ''}
  {'<span class="hdr-pill-ex">Eval (' + str(ev_n) + ')</span>' if eval_rows else ''}
</div>""", unsafe_allow_html=True)

    if not prepost_rows and not eval_rows:
        render_upload()
        return

    # ── MODAL ──
    render_modal()

    # ── TABS ──
    render_tabs()

    # ── ACTION ROW ──
    a1,a2,a3,_sp = st.columns([1,1,1,5])
    with a1:
        if st.button("🧠 Deep Insights"): st.session_state['tab']='AI Insights'; st.rerun()
    with a2:
        if st.button("✍️ Write Article"): st.session_state['tab']='JCEHP Article'; st.rerun()
    with a3:
        if st.button("📁 New Upload"):
            for k in ['prepost_rows','eval_rows','ai_insights']:
                st.session_state[k] = []
            st.session_state['jcehp_text'] = {}
            st.rerun()

    # ── FILTER BAR ──
    filtered_eval = apply_eval_filters(eval_rows)
    render_filter_bar(eval_rows)

    st.divider()

    # ── RENDER TAB ──
    t = st.session_state.get('tab', 'Overview')
    if   t == 'Overview':         tab_overview(prepost_rows, filtered_eval)
    elif t == 'Knowledge':        tab_knowledge(prepost_rows)
    elif t == 'Competence':       tab_knowledge(prepost_rows)  # reuse
    elif t == 'Evaluation':       tab_evaluation(filtered_eval)
    elif t == 'Key Findings':     tab_key_findings(prepost_rows, filtered_eval)
    elif t == 'Kirkpatrick':      tab_kirkpatrick(prepost_rows, filtered_eval)
    elif t == 'CIRCLE Framework': tab_circle(prepost_rows, filtered_eval)
    elif t == 'JCEHP Article':    tab_jcehp(prepost_rows, filtered_eval)
    elif t == 'AI Insights':      tab_ai_insights(prepost_rows, filtered_eval)

    st.divider()


if __name__ == '__main__':
    main()
