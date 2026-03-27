"""
Integritas CME Outcomes Harmonizer v3
DocuParse-style UI: dark header, horizontal tabs, filter chips, metric modals
All parser/analytics logic rebuilt and bug-fixed.
"""
import io, re, math, json, textwrap
from collections import defaultdict
import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="Integritas CME Outcomes Harmonizer", layout="wide", page_icon="🧬")

# ══════════════════════════════════════════════════════════════════════════════
# STYLES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* Hide default Streamlit chrome */
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 0 !important; max-width: 100% !important;}
section[data-testid="stSidebar"] {display: none;}

/* ── APP HEADER ── */
.app-header {
  background: #0f172a;
  border-bottom: 1px solid #1e3a5f;
  padding: 14px 32px;
  display: flex;
  align-items: center;
  gap: 20px;
  position: sticky;
  top: 0;
  z-index: 1000;
}
.app-logo {
  font-size: 20px;
  font-weight: 700;
  color: #ffffff;
  white-space: nowrap;
}
.app-logo span {color: #22d3ee;}
.header-inputs {display: flex; gap: 10px; flex: 1;}
.header-inputs input {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 6px 12px;
  color: #e2e8f0;
  font-size: 13px;
  width: 200px;
}
.badge-ex {
  background: #7c3aed22;
  border: 1px solid #7c3aed;
  color: #a78bfa;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
.badge-nx {
  background: #16a34a22;
  border: 1px solid #16a34a;
  color: #4ade80;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

/* ── TAB BAR ── */
.tab-bar {
  background: #0f172a;
  border-bottom: 1px solid #1e293b;
  padding: 0 32px;
  display: flex;
  gap: 0;
  overflow-x: auto;
}
.tab-btn {
  padding: 12px 18px;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
  background: none;
  border-top: none;
  border-left: none;
  border-right: none;
  transition: all 0.15s;
}
.tab-btn:hover {color: #e2e8f0;}
.tab-btn.active {color: #22d3ee; border-bottom-color: #22d3ee;}

/* ── ACTION ROW ── */
.action-row {
  background: #0f172a;
  border-bottom: 1px solid #1e293b;
  padding: 8px 32px;
  display: flex;
  gap: 10px;
  align-items: center;
}
.action-btn {
  background: #1e293b;
  border: 1px solid #334155;
  color: #e2e8f0;
  padding: 5px 14px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}
.action-btn:hover {background: #334155;}

/* ── FILTER CHIPS ── */
.filter-bar {
  background: #0f172a;
  border-bottom: 1px solid #1e293b;
  padding: 8px 32px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.filter-label {color: #64748b; font-size: 11px; font-weight: 600; text-transform: uppercase;}
.chip {
  padding: 3px 12px;
  border-radius: 20px;
  font-size: 12px;
  cursor: pointer;
  border: 1px solid #334155;
  color: #94a3b8;
  background: #1e293b;
}
.chip.active-all  {border-color: #22d3ee; color: #22d3ee; background: #0891b220;}
.chip.active-ex   {border-color: #a78bfa; color: #a78bfa; background: #7c3aed20;}
.chip.active-nx   {border-color: #4ade80; color: #4ade80; background: #16a34a20;}
.chip.active-spec {border-color: #f59e0b; color: #f59e0b; background: #d9770620;}

/* ── CONTENT AREA ── */
.content {padding: 24px 32px; background: #0f172a; min-height: calc(100vh - 160px);}

/* ── STAT CARDS ── */
.stat-grid {display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px; margin-bottom: 24px;}
.stat-card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.stat-card:hover {border-color: #22d3ee;}
.stat-label {color: #94a3b8; font-size: 11px; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px;}
.stat-value {font-size: 28px; font-weight: 700; color: #e2e8f0; line-height: 1;}
.stat-sub {color: #64748b; font-size: 11px; margin-top: 4px;}
.stat-blue {color: #60a5fa;}
.stat-orange {color: #fb923c;}
.stat-green {color: #4ade80;}
.stat-purple {color: #a78bfa;}
.stat-teal {color: #22d3ee;}

/* ── TWO-COL LAYOUT ── */
.two-col {display: grid; grid-template-columns: 1fr 1fr; gap: 20px;}
.three-col {display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px;}

/* ── SECTION CARD ── */
.section-card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 16px;
}
.section-title {color: #e2e8f0; font-size: 15px; font-weight: 600; margin-bottom: 14px;}

/* ── DATA TABLE ── */
.data-table {width: 100%; border-collapse: collapse;}
.data-table th {
  color: #94a3b8; font-size: 11px; text-transform: uppercase;
  padding: 8px 10px; border-bottom: 1px solid #334155; text-align: left;
}
.data-table td {
  color: #e2e8f0; font-size: 13px;
  padding: 10px 10px; border-bottom: 1px solid #1e293b; cursor: pointer;
}
.data-table tr:hover td {background: #334155;}
.gain-pos {color: #4ade80; font-weight: 600;}
.gain-neg {color: #f87171; font-weight: 600;}
.pval {color: #94a3b8; font-size: 11px;}

/* ── PROGRESS BAR ── */
.prog-wrap {display: flex; align-items: center; gap: 10px; margin: 6px 0;}
.prog-label {color: #94a3b8; font-size: 12px; width: 320px; flex-shrink: 0;}
.prog-bar-bg {flex: 1; background: #334155; border-radius: 4px; height: 8px; cursor: pointer;}
.prog-bar-fill {border-radius: 4px; height: 8px;}
.prog-pct {color: #e2e8f0; font-size: 12px; width: 50px; text-align: right;}

/* ── BIG CIRCLE ── */
.circle-wrap {display: flex; flex-direction: column; align-items: center; gap: 8px; cursor: pointer;}
.circle-ring {
  width: 90px; height: 90px; border-radius: 50%; display: flex;
  align-items: center; justify-content: center; flex-direction: column;
  border: 5px solid;
}
.circle-val {font-size: 22px; font-weight: 700; line-height: 1;}
.circle-lbl {font-size: 10px; color: #94a3b8; text-align: center; max-width: 90px;}

/* ── MODAL OVERLAY ── */
.modal-overlay {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.75); z-index: 9999;
  display: flex; align-items: center; justify-content: center;
}
.modal-card {
  background: #1e293b; border: 1px solid #334155; border-radius: 12px;
  width: 640px; max-height: 80vh; overflow-y: auto; padding: 28px;
  position: relative;
}
.modal-title {color: #22d3ee; font-size: 16px; font-weight: 700; margin-bottom: 16px;}
.modal-section {margin-bottom: 14px;}
.modal-section-label {
  color: #64748b; font-size: 10px; text-transform: uppercase;
  letter-spacing: 1px; margin-bottom: 4px;
}
.modal-section-value {color: #e2e8f0; font-size: 13px; line-height: 1.5;}
.modal-table {width: 100%; border-collapse: collapse; margin-top: 10px;}
.modal-table th {
  color: #94a3b8; font-size: 11px; padding: 6px 10px;
  border-bottom: 1px solid #334155; text-align: left;
}
.modal-table td {color: #e2e8f0; font-size: 12px; padding: 8px 10px; border-bottom: 1px solid #1e293b;}
.src-ex {
  display: inline-flex; align-items: center; gap: 4px;
  background: #7c3aed22; border: 1px solid #7c3aed; color: #a78bfa;
  padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
}
.src-nx {
  display: inline-flex; align-items: center; gap: 4px;
  background: #16a34a22; border: 1px solid #16a34a; color: #4ade80;
  padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
}
.src-cb {
  display: inline-flex; align-items: center; gap: 4px;
  background: #1d4ed822; border: 1px solid #1d4ed8; color: #60a5fa;
  padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;
}

/* ── KEY FINDINGS CIRCLES ── */
.kf-circle {
  width: 140px; height: 140px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-direction: column; cursor: pointer; border: 6px solid;
  margin: 0 auto 10px;
}
.kf-val {font-size: 36px; font-weight: 800; line-height: 1;}
.kf-lbl {font-size: 11px; text-align: center; margin-top: 2px; padding: 0 8px;}
.kf-increase {color: #4ade80; font-size: 13px; font-weight: 700; text-align: center;}

/* ── UPLOAD ZONE ── */
.upload-zone {
  background: #1e293b; border: 2px dashed #334155; border-radius: 12px;
  padding: 40px; text-align: center; cursor: pointer;
  transition: border-color 0.15s;
}
.upload-zone:hover {border-color: #22d3ee;}
.upload-icon {font-size: 40px; margin-bottom: 12px;}
.upload-title {color: #e2e8f0; font-size: 16px; font-weight: 600; margin-bottom: 6px;}
.upload-sub {color: #64748b; font-size: 13px;}

/* ── JCEHP ── */
.checklist-bar {
  background: #334155; border-radius: 6px; height: 10px;
  margin-bottom: 16px; overflow: hidden;
}
.checklist-fill {background: #22d3ee; height: 100%; border-radius: 6px;}
.jcehp-section {
  background: #1e293b; border: 1px solid #334155; border-radius: 8px;
  padding: 16px; margin-bottom: 12px;
}
.jcehp-section-title {color: #a78bfa; font-size: 13px; font-weight: 700; margin-bottom: 8px;}
.jcehp-content {color: #cbd5e1; font-size: 13px; line-height: 1.6; white-space: pre-wrap;}

/* ── KIRKPATRICK ── */
.kirk-level {
  background: #1e293b; border-left: 4px solid;
  border-radius: 0 8px 8px 0; padding: 16px; margin-bottom: 12px;
}
.kirk-level-title {font-size: 13px; font-weight: 700; margin-bottom: 10px;}

/* ── AI INSIGHTS ── */
.insight-card {
  background: #1e293b; border: 1px solid #334155; border-radius: 10px;
  padding: 18px; margin-bottom: 12px;
}
.insight-header {display: flex; align-items: center; gap: 10px; margin-bottom: 8px;}
.insight-badge {
  padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .5px;
}
.insight-title {color: #e2e8f0; font-size: 14px; font-weight: 600;}
.insight-body {color: #94a3b8; font-size: 13px; line-height: 1.5;}
.insight-rec {color: #4ade80; font-size: 12px; margin-top: 8px;}

/* ── GENERAL ── */
body, .stApp {background: #0a0f1e !important;}
h1, h2, h3, p, label {color: #e2e8f0 !important;}
.stTextInput input, .stSelectbox select {
  background: #1e293b !important;
  border-color: #334155 !important;
  color: #e2e8f0 !important;
}
.stButton button {
  background: #1e293b !important;
  border: 1px solid #334155 !important;
  color: #e2e8f0 !important;
  border-radius: 6px !important;
}
.stButton button:hover {background: #334155 !important;}
.stFileUploader {background: #1e293b; border-radius: 10px; padding: 10px;}
div[data-testid="stFileUploadDropzone"] {background: #0f172a !important; border-color: #334155 !important;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
def _init():
    defaults = {
        'tab': 'Overview',
        'prog_name': '',
        'proj_code': '',
        'ex_records': [],
        'nx_records': [],
        'all_records': [],
        'vendor_filter': 'All',
        'specialty_filter': 'All',
        'modal': None,
        'api_key': '',
        'ai_insights': [],
        'jcehp_text': {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

# ══════════════════════════════════════════════════════════════════════════════
# PARSE EXCHANGE (single-sheet: META | EVAL | PRE | POST in columns)
# ══════════════════════════════════════════════════════════════════════════════
def parse_exchange(file_bytes):
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if len(all_rows) < 3:
        return []

    r1 = all_rows[1]   # section row: 'EVALUATION', 'PRE', 'POST'
    r2 = all_rows[2]   # column label row

    # Find section start columns
    eval_s = pre_s = post_s = None
    for i, v in enumerate(r1):
        sv = str(v).strip().upper() if v else ''
        if sv == 'EVALUATION' and eval_s is None: eval_s = i
        if sv == 'PRE' and pre_s is None:         pre_s  = i
        if sv == 'POST' and post_s is None:        post_s = i

    if pre_s is None:
        return []

    total_cols = len(r2)

    def section_of(i):
        # Check in reverse so POST wins over PRE over EVAL
        if post_s is not None and i >= post_s: return 'POST'
        if pre_s  is not None and i >= pre_s:  return 'PRE'
        if eval_s is not None and i >= eval_s: return 'EVAL'
        return 'META'

    # Build column map
    col_map = []  # list of (section, label)
    for i, v in enumerate(r2):
        lbl = str(v).strip() if v and str(v).strip() not in ['', '\xa0'] else None
        col_map.append((section_of(i), lbl))

    records = []
    for row in all_rows[3:]:
        rec = {'_source': 'Exchange'}
        for i, val in enumerate(row):
            if i >= len(col_map): break
            sec, lbl = col_map[i]
            if lbl is None: continue
            key = f"{sec}__{lbl}"
            # Handle specialty specifically for META
            if sec == 'META':
                key = f"META__{lbl}"
            rec[key] = val
        records.append(rec)

    return records

# ══════════════════════════════════════════════════════════════════════════════
# PARSE NEXUS (multi-sheet: PreNon, Pre, Post, Eval, Follow-Up)
# ══════════════════════════════════════════════════════════════════════════════
def parse_nexus(file_bytes):
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    sheets = {s.upper(): s for s in wb.sheetnames}

    def read_sheet(key_variants):
        for k in key_variants:
            if k.upper() in sheets:
                ws = wb[sheets[k.upper()]]
                rows = list(ws.iter_rows(values_only=True))
                if not rows: return {}, []
                headers = [str(h).strip() if h else None for h in rows[0]]
                return {h: i for i, h in enumerate(headers) if h}, rows[1:]
        return {}, []

    pre_idx,    pre_rows    = read_sheet(['Pre'])
    prenon_idx, prenon_rows = read_sheet(['PreNon'])
    post_idx,   post_rows   = read_sheet(['Post'])
    eval_idx,   eval_rows   = read_sheet(['Eval'])
    fu_idx,     fu_rows     = read_sheet(['Follow-Up', 'Follow Up'])
    wb.close()

    # Index post/eval/fu by ID
    def index_by_id(idx, rows):
        d = {}
        if 'ID' not in idx: return d
        id_col = idx['ID']
        for r in rows:
            rid = str(r[id_col]).strip() if r[id_col] is not None else None
            if rid: d[rid] = r
        return d

    post_by_id = index_by_id(post_idx, post_rows)
    eval_by_id = index_by_id(eval_idx, eval_rows)
    fu_by_id   = index_by_id(fu_idx,   fu_rows)

    def make_record(pre_row, pre_idx_map, is_prenon=False):
        rec = {'_source': 'Nexus'}
        id_col = pre_idx_map.get('ID')
        rid = str(pre_row[id_col]).strip() if id_col is not None and pre_row[id_col] is not None else None
        rec['_id'] = rid

        # PRE columns
        for h, ci in pre_idx_map.items():
            if h == 'ID': continue
            val = pre_row[ci] if ci < len(pre_row) else None
            rec[f'PRE__{h}'] = val

        # POST
        if rid and rid in post_by_id:
            post_row = post_by_id[rid]
            for h, ci in post_idx.items():
                if h == 'ID': continue
                val = post_row[ci] if ci < len(post_row) else None
                rec[f'POST__{h}'] = val

        # EVAL
        if rid and rid in eval_by_id:
            ev_row = eval_by_id[rid]
            for h, ci in eval_idx.items():
                if h == 'ID': continue
                val = ev_row[ci] if ci < len(ev_row) else None
                rec[f'EVAL__{h}'] = val

        # Follow-Up
        if rid and rid in fu_by_id:
            fu_row = fu_by_id[rid]
            for h, ci in fu_idx.items():
                if h == 'ID': continue
                val = fu_row[ci] if ci < len(fu_row) else None
                rec[f'FU__{h}'] = val

        rec['_is_prenon'] = is_prenon
        rec['_has_post']  = rid in post_by_id if rid else False
        rec['_has_eval']  = rid in eval_by_id if rid else False
        return rec

    records = []
    for row in prenon_rows:
        records.append(make_record(row, prenon_idx, is_prenon=True))
    for row in pre_rows:
        records.append(make_record(row, pre_idx, is_prenon=False))

    return records

# ══════════════════════════════════════════════════════════════════════════════
# COMBINE INTO DATAFRAME
# ══════════════════════════════════════════════════════════════════════════════
def combine_records(ex_records, nx_records):
    all_records = ex_records + nx_records
    if not all_records:
        return pd.DataFrame()
    df = pd.DataFrame(all_records)

    # Detect which cols are MCQ (PRE__ and POST__ with matching question text)
    # Build short-label map to deduplicate PRE/POST collision
    pre_cols  = [c for c in df.columns if c.startswith('PRE__')]
    post_cols = [c for c in df.columns if c.startswith('POST__')]

    # Build label fingerprint for deduplication display
    # (columns already have unique full-text keys — no truncation issue)
    return df

# ══════════════════════════════════════════════════════════════════════════════
# CLASSIFY COLUMNS
# ══════════════════════════════════════════════════════════════════════════════
def classify_cols(df):
    pre_cols  = sorted([c for c in df.columns if c.startswith('PRE__')])
    post_cols = sorted([c for c in df.columns if c.startswith('POST__')])
    eval_cols = sorted([c for c in df.columns if c.startswith('EVAL__')])
    fu_cols   = sorted([c for c in df.columns if c.startswith('FU__')])
    meta_cols = sorted([c for c in df.columns if c.startswith('META__')
                        or c in ('_source','_id','_is_prenon','_has_post','_has_eval')])
    return pre_cols, post_cols, eval_cols, fu_cols, meta_cols

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def pct(n, d):
    if not d: return None
    return round(100 * n / d, 1)

def short(s, n=55):
    s = str(s)
    return s[:n] + '…' if len(s) > n else s

def strip_prefix(col):
    return re.sub(r'^(PRE__|POST__|EVAL__|FU__|META__)', '', col)

def is_mcq_col(series):
    """Returns True if column looks like MCQ (text answers, high cardinality of text)."""
    vals = series.dropna().astype(str)
    if len(vals) < 5: return False
    # If most values are long text (>10 chars) and there are few unique — MCQ answer choices
    avg_len = vals.str.len().mean()
    n_unique = vals.nunique()
    if avg_len > 8 and n_unique <= 20: return True
    return False

def is_likert_col(series):
    """Returns True if column has Likert-like scale values."""
    vals = series.dropna()
    if len(vals) < 5: return False
    str_vals = vals.astype(str)
    likert_patterns = [
        r'^(Not at all|Slightly|Moderately|Very|Extremely)',
        r'^(Strongly (agree|disagree)|Agree|Disagree|Neutral)',
        r'^(Not at all|Not very|Somewhat|Very|Extremely)',
        r'^(1|2|3|4|5)$',
        r'^(Poor|Fair|Good|Very Good|Excellent)',
        r'^(Never|Rarely|Sometimes|Often|Always)',
        r'^(Not at all familiar|Not very familiar|Neutral|Somewhat familiar|Very familiar)',
        r'^(Not at all confident|Not very confident|Neutral|Somewhat confident|Very confident)',
    ]
    for pat in likert_patterns:
        if str_vals.str.match(pat, case=False, na=False).mean() > 0.3:
            return True
    return False

LIKERT_MAP = {
    # 5-point familiarity/confidence
    'not at all familiar': 1, 'not very familiar': 2, 'neutral': 3,
    'somewhat familiar': 4, 'very familiar': 5,
    'not at all confident': 1, 'not very confident': 2,
    'somewhat confident': 4, 'very confident': 5,
    # Generic 5-point
    'not at all': 1, 'slightly': 2, 'moderately': 3, 'very': 4, 'extremely': 5,
    'strongly disagree': 1, 'disagree': 2, 'agree': 4, 'strongly agree': 5,
    'poor': 1, 'fair': 2, 'good': 3, 'very good': 4, 'excellent': 5,
    'never': 1, 'rarely': 2, 'sometimes': 3, 'often': 4, 'always': 5,
    # Satisfaction specific
    'very poor': 1, 'below average': 2, 'average': 3, 'above average': 4,
    # Numeric strings
    '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
}

def to_likert(val):
    if val is None: return None
    if isinstance(val, (int, float)):
        v = float(val)
        if 1 <= v <= 5: return v
        return None
    s = str(val).strip().lower()
    return LIKERT_MAP.get(s)

# ══════════════════════════════════════════════════════════════════════════════
# MATCH PRE / POST QUESTION PAIRS
# ══════════════════════════════════════════════════════════════════════════════
def norm_q(s):
    """Normalize question text: strip HTML/entities/non-ASCII, first 9 words."""
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'&[a-zA-Z0-9#]+;', ' ', s)
    s = s.encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return ' '.join(s.split()[:9])

def norm_answer(v):
    """Normalize a single answer string for comparison."""
    if v is None: return ''
    s = str(v).strip()
    s = re.sub(r'<[^>]+>', ' ', s)
    s = s.encode('ascii', 'ignore').decode('ascii')
    s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip().lower()[:40]

def answer_fingerprint(series):
    """Return frozenset of normalized top answer values (top 5 by frequency)."""
    vals = series.dropna().astype(str)
    if len(vals) == 0: return frozenset()
    top = vals.value_counts().head(5).index.tolist()
    return frozenset(norm_answer(v) for v in top if norm_answer(v))

def answer_overlap(fp_a, fp_b):
    """Overlap ratio between two answer fingerprints."""
    if not fp_a or not fp_b: return 0.0
    return len(fp_a & fp_b) / max(len(fp_a), len(fp_b))

def match_pre_post(df, pre_cols, post_cols):
    """
    Match pre/post column groups using answer-set overlap as primary signal.

    Returns list of dicts, each representing ONE semantic question:
        {
          'pre_cols':  [list of all matching PRE columns (may be Ex + Nx versions)],
          'post_cols': [list of all matching POST columns],
          'label':     best question label (longest / most complete),
        }
    This allows computing combined stats across both vendors even when
    Exchange and Nexus encode the same question with slightly different text.
    """
    # Pre-compute answer fingerprints
    pre_fps  = {c: answer_fingerprint(df[c]) for c in pre_cols}
    post_fps = {c: answer_fingerprint(df[c]) for c in post_cols}

    # Score all pre/post combinations
    scored = []
    for pc in pre_cols:
        for qc in post_cols:
            a_sc = answer_overlap(pre_fps[pc], post_fps[qc])
            pq = norm_q(pc); qq = norm_q(qc)
            pw = set(pq.split()); qw = set(qq.split())
            q_sc = len(pw & qw) / max(len(pw), len(qw)) if pw and qw else 0
            combined = a_sc * 0.7 + q_sc * 0.3
            if combined >= 0.45:
                scored.append((combined, pc, qc))

    scored.sort(key=lambda x: -x[0])

    # Cluster into semantic groups
    # Each group: all (pre_col, post_col) pairs that share answer fingerprints
    groups = []   # list of {'pre_cols': set, 'post_cols': set, 'fp': answer_fp}

    def find_group(pc, qc):
        """Find existing group that matches this pair's answer fingerprint."""
        pc_fp = pre_fps[pc]
        qc_fp = post_fps[qc]
        for g in groups:
            # Check overlap with any existing member
            g_pre_fp  = next(iter(g['pre_fps']))
            g_post_fp = next(iter(g['post_fps']))
            if answer_overlap(pc_fp, g_pre_fp) >= 0.65 and answer_overlap(qc_fp, g_post_fp) >= 0.65:
                return g
        return None

    for score, pc, qc in scored:
        g = find_group(pc, qc)
        if g is None:
            groups.append({
                'pre_cols':  {pc},
                'post_cols': {qc},
                'pre_fps':   {pre_fps[pc]},
                'post_fps':  {post_fps[qc]},
                'best_pre':  pc,   # longest label
                'best_post': qc,
            })
        else:
            g['pre_cols'].add(pc)
            g['post_cols'].add(qc)
            g['pre_fps'].add(pre_fps[pc])
            g['post_fps'].add(post_fps[qc])
            # Keep the label with the longer text as 'best'
            if len(pc) > len(g['best_pre']): g['best_pre'] = pc
            if len(qc) > len(g['best_post']): g['best_post'] = qc

    # Convert to list of (pre_col_list, post_col_list) tuples
    result = []
    for g in groups:
        result.append((sorted(g['pre_cols']), sorted(g['post_cols'])))

    return result



# ══════════════════════════════════════════════════════════════════════════════
# COMPUTE KNOWLEDGE (MCQ)
# ══════════════════════════════════════════════════════════════════════════════
def compute_knowledge(df, pre_cols, post_cols):
    """
    For each matched group of pre/post MCQ columns, compute % correct.
    Groups may contain multiple columns (Exchange + Nexus versions) for the
    same semantic question — all are merged into a single combined result.
    """
    groups = match_pre_post(df, pre_cols, post_cols)
    results = []

    for pre_group, post_group in groups:
        # Merge all pre versions into one series (first non-null wins per row)
        pre_ser  = df[pre_group].bfill(axis=1).iloc[:, 0]
        post_ser = df[post_group].bfill(axis=1).iloc[:, 0]

        pre_vals  = pre_ser.dropna().astype(str)
        post_vals = post_ser.dropna().astype(str)

        if len(post_vals) < 5: continue
        n_unique = post_vals.nunique()
        if n_unique > 30 or n_unique < 2: continue
        if is_likert_col(post_ser): continue

        # Skip if only one vendor has data and gain is trivially small (likely a behavior/frequency item)
        both_vendor_mask = pre_ser.notna() & post_ser.notna()
        ex_has = (df.loc[both_vendor_mask, '_source'] == 'Exchange').sum() if '_source' in df.columns else 0
        nx_has = (df.loc[both_vendor_mask, '_source'] == 'Nexus').sum()    if '_source' in df.columns else 0
        if nx_has == 0 and ex_has < 100:
            # Only Exchange data and small n — likely a non-MCQ item, skip
            continue

        # Correct answer = modal answer in POST
        mode_series = post_vals.value_counts()
        if mode_series.empty: continue
        correct = mode_series.index[0]

        # Matched pairs only
        both_mask = pre_ser.notna() & post_ser.notna()
        matched = df[both_mask]
        if len(matched) < 5: continue

        pre_m  = pre_ser[both_mask].astype(str)
        post_m = post_ser[both_mask].astype(str)
        n      = len(matched)

        pre_correct  = (pre_m  == correct).sum()
        post_correct = (post_m == correct).sum()
        pre_pct  = pct(pre_correct, n)
        post_pct = pct(post_correct, n)
        gain     = round(post_pct - pre_pct, 1) if pre_pct is not None and post_pct is not None else None

        # Chi-square
        try:
            ct = pd.crosstab(
                pd.concat([pd.Series(['pre']*n), pd.Series(['post']*n)]),
                pd.concat([(pre_m == correct).astype(int), (post_m == correct).astype(int)])
            )
            _, p_val, _, _ = stats.chi2_contingency(ct)
            p_val = round(p_val, 4)
        except:
            p_val = None

        # Per-vendor stats: use each vendor's own pre/post series
        def vendor_stats(src):
            vdf = matched[matched['_source'] == src]
            vn  = len(vdf)
            if vn == 0: return None, None, None, 0
            # Find best non-null PRE col for this vendor
            v_pre  = df.loc[vdf.index, pre_group].bfill(axis=1).iloc[:, 0]
            v_post = df.loc[vdf.index, post_group].bfill(axis=1).iloc[:, 0]
            v_both = v_pre.notna() & v_post.notna()
            v_pre_m  = v_pre[v_both].astype(str)
            v_post_m = v_post[v_both].astype(str)
            vn2 = len(v_pre_m)
            if vn2 == 0: return None, None, None, 0
            vp_pre  = pct((v_pre_m  == correct).sum(), vn2)
            vp_post = pct((v_post_m == correct).sum(), vn2)
            vg = round(vp_post - vp_pre, 1) if vp_pre is not None and vp_post is not None else None
            return vp_pre, vp_post, vg, vn2

        ex_pre, ex_post, ex_gain, ex_n = vendor_stats('Exchange')
        nx_pre, nx_post, nx_gain, nx_n = vendor_stats('Nexus')

        # Best label: prefer the longer / more complete text
        label = strip_prefix(max(pre_group, key=len))

        results.append({
            'label':    label,
            'pre_cols': pre_group,
            'post_cols':post_group,
            'correct':  correct,
            'pre_pct':  pre_pct,
            'post_pct': post_pct,
            'gain':     gain,
            'n':        n,
            'p_val':    p_val,
            'ex_pre': ex_pre, 'ex_post': ex_post, 'ex_gain': ex_gain, 'ex_n': ex_n,
            'nx_pre': nx_pre, 'nx_post': nx_post, 'nx_gain': nx_gain, 'nx_n': nx_n,
        })

    return results

def compute_competence(df, pre_cols, post_cols):
    """
    Match Likert-scale pre/post pairs (grouped across vendors).
    """
    groups = match_pre_post(df, pre_cols, post_cols)
    results = []

    for pre_group, post_group in groups:
        pre_ser  = df[pre_group].bfill(axis=1).iloc[:, 0]
        post_ser = df[post_group].bfill(axis=1).iloc[:, 0]

        if not is_likert_col(pre_ser) and not is_likert_col(post_ser):
            continue

        both_mask = pre_ser.apply(to_likert).notna() & post_ser.apply(to_likert).notna()
        matched = df[both_mask]
        if len(matched) < 5: continue

        mp = pre_ser[both_mask].apply(to_likert)
        mq = post_ser[both_mask].apply(to_likert)
        pre_mean  = round(float(mp.mean()), 2)
        post_mean = round(float(mq.mean()), 2)
        change    = round(post_mean - pre_mean, 2)
        n         = len(matched)

        try:
            _, p_val = stats.ttest_rel(mp, mq)
            p_val = round(p_val, 4)
        except:
            p_val = None

        def vendor_likert(src):
            vdf = matched[matched['_source'] == src]
            if len(vdf) < 3: return None, None, None, 0
            vp = df.loc[vdf.index, pre_group].bfill(axis=1).iloc[:, 0].apply(to_likert)
            vq = df.loc[vdf.index, post_group].bfill(axis=1).iloc[:, 0].apply(to_likert)
            vn = int(vp.notna().sum())
            return (round(float(vp.mean()), 2) if vn > 0 else None,
                    round(float(vq.mean()), 2) if vn > 0 else None,
                    round(float(vq.mean()-vp.mean()), 2) if vn > 0 else None, vn)

        ex_pre, ex_post, ex_chg, ex_n = vendor_likert('Exchange')
        nx_pre, nx_post, nx_chg, nx_n = vendor_likert('Nexus')

        label = strip_prefix(max(pre_group, key=len))
        results.append({
            'label':     label,
            'pre_cols':  pre_group,
            'post_cols': post_group,
            'pre_mean':  pre_mean,
            'post_mean': post_mean,
            'change':    change,
            'n':         n,
            'p_val':     p_val,
            'ex_pre': ex_pre, 'ex_post': ex_post, 'ex_chg': ex_chg, 'ex_n': ex_n,
            'nx_pre': nx_pre, 'nx_post': nx_post, 'nx_chg': nx_chg, 'nx_n': nx_n,
        })

    return results


# ══════════════════════════════════════════════════════════════════════════════
# COMPUTE EVALUATION
# ══════════════════════════════════════════════════════════════════════════════
INTENT_KEYWORDS      = ['intend to', 'plan to change', 'modify', 'change my practice']
RECOMMEND_KEYWORDS   = ['recommend this program', 'recommend this activity']
BIAS_KEYWORDS        = ['free of commercial bias', 'free of bias', 'balanced coverage']
CONTENT_NEW_KEYWORDS = ['content.*new', 'percentage.*new', 'new.*content', 'how much.*new']
SAT_KEYWORDS         = ['knowledgeable', 'relevant', 'useful tools', 'teaching.*method',
                        'faculty', 'learning method', 'enhanced my knowledge',
                        'improve patient', 'effective', 'learning objectives']
BARRIER_KEYWORDS     = ['significant barrier', 'significant challenge', 'obstacle']
BEHAVIOR_KEYWORDS    = ['intend to incorporate', 'plan to incorporate', 'change your practice behavior',
                        'types of change', 'will you now']
EVAL_COMPETENCE_KEYWORDS = [
    'incorporate', 'create comprehensive', 'review patient selection',
    'participants will be able', 'upon completion',
    'identify', 'implement', 'determine', 'describe',
]

def find_eval_col(df, eval_cols, keywords):
    for kw in keywords:
        for c in eval_cols:
            lbl = strip_prefix(c).lower()
            if re.search(kw, lbl, re.I):
                return c
    return None

def eval_yes_pct(df, col):
    if col is None: return None, None
    vals = df[col].dropna().astype(str).str.strip()
    if len(vals) == 0: return None, None
    n = len(vals)
    lvals = vals.str.lower()
    yes_mask = lvals.str.match(r'^yes', na=False)
    if yes_mask.sum() / n > 0.05:
        return pct(yes_mask.sum(), n), int(n)
    agree_mask = lvals.str.match(r'^(strongly agree|agree)$', na=False)
    if agree_mask.sum() > 0:
        return pct(agree_mask.sum(), n), int(n)
    pos_mask = lvals.str.match(r'^(4|5|very|extremely|always|often)', na=False)
    if pos_mask.sum() / n > 0.05:
        return pct(pos_mask.sum(), n), int(n)
    return None, None

def eval_pct_from_content_new(series):
    def parse_one(v):
        if v is None: return None
        if isinstance(v, (int, float)):
            f = float(v)
            if f <= 1: return f * 100
            if f <= 100: return f
            return None
        s = str(v).strip()
        m = re.search(r'(\d+)\s*-\s*(\d+)', s)
        if m: return (int(m.group(1)) + int(m.group(2))) / 2
        m2 = re.search(r'(\d+(?:\.\d+)?)', s)
        if m2:
            f = float(m2.group(1))
            if f <= 1: return f * 100
            return f
        return None
    parsed = series.apply(parse_one).dropna()
    return round(float(parsed.mean()), 1) if len(parsed) > 0 else None

def _vendor_yes(df, col, src):
    if '_source' not in df.columns or col is None: return None
    vdf = df[df['_source'] == src]
    if len(vdf) == 0: return None
    vals = vdf[col].dropna().astype(str).str.strip()
    if len(vals) == 0: return None
    lvals = vals.str.lower()
    n = len(lvals)
    yes_mask = lvals.str.match(r'^yes', na=False)
    if yes_mask.sum() / n > 0.05:
        return pct(yes_mask.sum(), n)
    agree_mask = lvals.str.match(r'^(strongly agree|agree)$', na=False)
    if agree_mask.sum() > 0:
        return pct(agree_mask.sum(), n)
    pos_mask = lvals.str.match(r'^(4|5|very|extremely|always|often)', na=False)
    return pct(pos_mask.sum(), n)

def compute_evaluation(df, eval_cols):
    import pandas as pd
    result = {}

    ic = find_eval_col(df, eval_cols, INTENT_KEYWORDS)
    if ic:
        p, n = eval_yes_pct(df, ic)
        result['intent'] = {'col': ic, 'pct': p, 'n': n,
            'ex_pct': _vendor_yes(df, ic, 'Exchange'),
            'nx_pct': _vendor_yes(df, ic, 'Nexus'),
            'ex_n': int((df['_source']=='Exchange').sum()) if '_source' in df.columns else 0,
            'nx_n': int((df['_source']=='Nexus').sum()) if '_source' in df.columns else 0,
        }

    rc = find_eval_col(df, eval_cols, RECOMMEND_KEYWORDS)
    if rc:
        p, n = eval_yes_pct(df, rc)
        result['recommend'] = {'col': rc, 'pct': p, 'n': n,
            'ex_pct': _vendor_yes(df, rc, 'Exchange'),
            'nx_pct': _vendor_yes(df, rc, 'Nexus'),
        }

    bc = find_eval_col(df, eval_cols, BIAS_KEYWORDS)
    if bc:
        p, n = eval_yes_pct(df, bc)
        result['bias_free'] = {'col': bc, 'pct': p, 'n': n,
            'ex_pct': _vendor_yes(df, bc, 'Exchange'),
            'nx_pct': _vendor_yes(df, bc, 'Nexus'),
        }

    nc = find_eval_col(df, eval_cols, CONTENT_NEW_KEYWORDS)
    if nc:
        p = eval_pct_from_content_new(df[nc])
        n = int(df[nc].notna().sum())
        result['content_new'] = {'col': nc, 'pct': p, 'n': n,
            'ex_pct': eval_pct_from_content_new(df[df['_source']=='Exchange'][nc]) if '_source' in df.columns else None,
            'nx_pct': eval_pct_from_content_new(df[df['_source']=='Nexus'][nc]) if '_source' in df.columns else None,
        }

    sat_items = []
    for c in eval_cols:
        lbl = strip_prefix(c).lower()
        if any(re.search(kw, lbl, re.I) for kw in SAT_KEYWORDS):
            lv = df[c].apply(to_likert).dropna()
            if len(lv) < 5: continue
            m  = round(float(lv.mean()), 2)
            n  = int(len(lv))
            ex_lv = df[df['_source']=='Exchange'][c].apply(to_likert).dropna() if '_source' in df.columns else pd.Series(dtype=float)
            nx_lv = df[df['_source']=='Nexus'][c].apply(to_likert).dropna()    if '_source' in df.columns else pd.Series(dtype=float)
            sat_items.append({
                'col': c, 'label': strip_prefix(c), 'mean': m, 'n': n,
                'ex_mean': round(float(ex_lv.mean()), 2) if len(ex_lv) > 0 else None,
                'nx_mean': round(float(nx_lv.mean()), 2) if len(nx_lv) > 0 else None,
                'ex_n': int(len(ex_lv)), 'nx_n': int(len(nx_lv)),
            })
    result['satisfaction'] = sat_items

    behavior_items = []
    barrier_items  = []
    for c in eval_cols:
        lbl = strip_prefix(c).lower()
        if any(re.search(kw, lbl, re.I) for kw in BEHAVIOR_KEYWORDS):
            vc = df[c].dropna()
            if len(vc) > 3:
                behavior_items.append({'col': c, 'label': strip_prefix(c), 'vals': vc.tolist()})
        if any(re.search(kw, lbl, re.I) for kw in BARRIER_KEYWORDS):
            vc = df[c].dropna()
            if len(vc) > 3:
                barrier_items.append({'col': c, 'label': strip_prefix(c), 'vals': vc.tolist()})

    result['behavior'] = behavior_items
    result['barriers'] = barrier_items

    eval_comp_items = []
    for c in eval_cols:
        lbl = strip_prefix(c).lower()
        if any(re.search(kw, lbl, re.I) for kw in EVAL_COMPETENCE_KEYWORDS):
            lv = df[c].apply(to_likert).dropna()
            if len(lv) < 5: continue
            m  = round(float(lv.mean()), 2)
            n  = int(len(lv))
            ex_lv = df[df['_source']=='Exchange'][c].apply(to_likert).dropna() if '_source' in df.columns else pd.Series(dtype=float)
            nx_lv = df[df['_source']=='Nexus'][c].apply(to_likert).dropna()    if '_source' in df.columns else pd.Series(dtype=float)
            eval_comp_items.append({
                'col': c, 'label': strip_prefix(c), 'mean': m, 'n': n,
                'ex_mean': round(float(ex_lv.mean()), 2) if len(ex_lv) > 0 else None,
                'nx_mean': round(float(nx_lv.mean()), 2) if len(nx_lv) > 0 else None,
                'ex_n': int(len(ex_lv)), 'nx_n': int(len(nx_lv)),
            })
    result['eval_competence'] = eval_comp_items

    return result

# ══════════════════════════════════════════════════════════════════════════════
# COMPUTE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
def compute_summary(df):
    import pandas as pd
    if df.empty: return {}
    ex_df = df[df['_source']=='Exchange'] if '_source' in df.columns else pd.DataFrame()
    nx_df = df[df['_source']=='Nexus']    if '_source' in df.columns else pd.DataFrame()

    has_post   = df['_has_post'].fillna(False).astype(bool)  if '_has_post'  in df.columns else pd.Series(False, index=df.index)
    has_eval_s = df['_has_eval'].fillna(False).astype(bool)  if '_has_eval'  in df.columns else pd.Series(False, index=df.index)

    total      = len(df)
    nx_matched = int(has_post.sum())
    post_cols_present = [c for c in df.columns if c.startswith('POST__')]
    ex_matched = int(ex_df[post_cols_present[0]].notna().sum()) if post_cols_present and len(ex_df) > 0 else 0
    matched    = ex_matched + nx_matched

    nx_eval  = int(has_eval_s.sum())
    eval_cols_ex = [c for c in df.columns if c.startswith('EVAL__')]
    ex_eval  = int(ex_df[eval_cols_ex[0]].notna().sum()) if eval_cols_ex and len(ex_df) > 0 else 0
    with_eval = ex_eval + nx_eval

    return {
        'total':      total,
        'ex_total':   len(ex_df),
        'nx_total':   len(nx_df),
        'matched':    matched,
        'ex_matched': ex_matched,
        'nx_matched': nx_matched,
        'with_eval':  with_eval,
        'pre_only':   total - matched,
        'match_pct':  pct(matched, total),
    }

# ══════════════════════════════════════════════════════════════════════════════
# FILTER DATAFRAME
# ══════════════════════════════════════════════════════════════════════════════
def apply_filters(df):
    if df.empty: return df
    filt = df.copy()
    vf = st.session_state.get('vendor_filter', 'All')
    if vf == 'Exchange': filt = filt[filt['_source'] == 'Exchange']
    elif vf == 'Nexus':  filt = filt[filt['_source'] == 'Nexus']
    sf = st.session_state.get('specialty_filter', 'All')
    if sf != 'All':
        spec_col = next((c for c in filt.columns if 'specialty' in c.lower()
                         and 'eval' not in c.lower()), None)
        if spec_col:
            filt = filt[filt[spec_col].astype(str).str.lower() == sf.lower()]
    return filt

def get_specialties(df):
    spec_col = next((c for c in df.columns if 'specialty' in c.lower()
                     and 'eval' not in c.lower()), None)
    if spec_col is None: return []
    return sorted(df[spec_col].dropna().astype(str).unique().tolist())

# ══════════════════════════════════════════════════════════════════════════════
# XLSX EXPORT
# ══════════════════════════════════════════════════════════════════════════════
def export_xlsx(df, kn, comp, ev, summary):
    import pandas as pd
    buf = io.BytesIO()
    wb = openpyxl.Workbook()
    hdr_fill = PatternFill('solid', fgColor='0F172A')
    hdr_font = Font(color='22D3EE', bold=True)

    def write_sheet(ws, headers, rows):
        ws.append(headers)
        for cell in ws[1]:
            cell.fill = hdr_fill
            cell.font = hdr_font
        for row in rows:
            ws.append(row)

    ws1 = wb.active; ws1.title = 'Summary'
    write_sheet(ws1, ['Metric', 'Value'], [
        ['Total Learners',    summary.get('total', 0)],
        ['Exchange Learners', summary.get('ex_total', 0)],
        ['Nexus Learners',    summary.get('nx_total', 0)],
        ['Pre/Post Matched',  summary.get('matched', 0)],
        ['Match Rate',        f"{summary.get('match_pct', '—')}%"],
        ['With Evaluation',   summary.get('with_eval', 0)],
    ])

    ws2 = wb.create_sheet('Knowledge')
    write_sheet(ws2, ['Question','N','Pre%','Post%','Gain(pp)','p-value',
                      'Ex Pre%','Ex Post%','Nx Pre%','Nx Post%'],
        [[r['label'], r['n'], r['pre_pct'], r['post_pct'], r['gain'], r['p_val'],
          r.get('ex_pre'), r.get('ex_post'), r.get('nx_pre'), r.get('nx_post')] for r in kn])

    ws3 = wb.create_sheet('Competence')
    write_sheet(ws3, ['Item','N','Pre Mean','Post Mean','Change','p-value',
                      'Ex Pre','Ex Post','Nx Pre','Nx Post'],
        [[r['label'], r['n'], r['pre_mean'], r['post_mean'], r['change'], r['p_val'],
          r.get('ex_pre'), r.get('ex_post'), r.get('nx_pre'), r.get('nx_post')] for r in comp])

    ws4 = wb.create_sheet('Evaluation')
    write_sheet(ws4, ['Metric','Combined%','N','Exchange%','Nexus%'],
        [[k, ev.get(k,{}).get('pct'), ev.get(k,{}).get('n'),
          ev.get(k,{}).get('ex_pct'), ev.get(k,{}).get('nx_pct')]
         for k in ['intent','recommend','bias_free','content_new']])

    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()

# ══════════════════════════════════════════════════════════════════════════════
# TAB RENDERERS
# ══════════════════════════════════════════════════════════════════════════════
TABS = ['Overview', 'Knowledge', 'Competence', 'Evaluation',
        'AI Insights', 'JCEHP Article', 'CIRCLE Framework',
        'Kirkpatrick', 'Key Findings']

def tab_overview(df, summary, ev, kn, comp):
    m = summary
    avg_kn_gain = round(sum(r['gain'] for r in kn if r['gain']) / max(1, len(kn)), 1) if kn else None
    avg_comp_chg = round(sum(r['change'] for r in comp if r['change']) / max(1, len(comp)), 2) if comp else None

    cards = [
        ('Total Learners',    m.get('total', 0),   '#60a5fa',
         f"Ex: {m.get('ex_total',0)} | Nx: {m.get('nx_total',0)}"),
        ('Pre-Only',          m.get('pre_only', 0),'#fb923c', 'Pre-test only'),
        ('Pre/Post Matched',  m.get('matched', 0), '#4ade80',
         f"{m.get('match_pct','—')}% match rate"),
        ('With Evaluation',   m.get('with_eval',0),'#a78bfa', 'Completed eval'),
        ('Avg Knowledge Gain',
         f"+{avg_kn_gain}pp" if avg_kn_gain else '—', '#22d3ee',
         f"{len(kn)} questions"),
        ('Avg Competence Gain',
         f"+{avg_comp_chg}" if avg_comp_chg else '—', '#22d3ee',
         f"{len(comp)} Likert items"),
    ]
    html = '<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:14px;margin-bottom:24px">'
    for lbl, val, color, sub in cards:
        html += f"""
<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px;cursor:pointer">
  <div style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">{lbl}</div>
  <div style="font-size:28px;font-weight:700;color:{color};line-height:1">{val}</div>
  <div style="color:#64748b;font-size:11px;margin-top:4px">{sub}</div>
</div>"""
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px">', unsafe_allow_html=True)
        st.markdown('<div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:14px">📚 Knowledge (Moore Level 3)</div>', unsafe_allow_html=True)
        if kn:
            tbl = '<table style="width:100%;border-collapse:collapse"><thead><tr>'
            for h in ['Question', 'Pre', 'Post', 'Gain', 'p']:
                tbl += f'<th style="color:#94a3b8;font-size:11px;text-transform:uppercase;padding:8px 6px;border-bottom:1px solid #334155;text-align:left">{h}</th>'
            tbl += '</tr></thead><tbody>'
            for r in kn:
                gain_color = '#4ade80' if r['gain'] and r['gain'] > 0 else '#f87171'
                gain_str = f"+{r['gain']}pp" if r['gain'] and r['gain'] > 0 else f"{r['gain']}pp"
                p_str = '<0.001' if r['p_val'] and r['p_val'] < 0.001 else (str(r['p_val']) if r['p_val'] else '—')
                tbl += f'''<tr>
  <td style="color:#e2e8f0;font-size:12px;padding:9px 6px;border-bottom:1px solid #1e293b" title="{r["label"]}">{short(r["label"],42)}</td>
  <td style="color:#e2e8f0;font-size:12px;padding:9px 6px;border-bottom:1px solid #1e293b">{r["pre_pct"]}%</td>
  <td style="color:#e2e8f0;font-size:12px;padding:9px 6px;border-bottom:1px solid #1e293b">{r["post_pct"]}%</td>
  <td style="color:{gain_color};font-size:12px;font-weight:600;padding:9px 6px;border-bottom:1px solid #1e293b">{gain_str}</td>
  <td style="color:#94a3b8;font-size:11px;padding:9px 6px;border-bottom:1px solid #1e293b">{p_str}</td>
</tr>'''
            tbl += '</tbody></table>'
            st.markdown(tbl, unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#64748b;font-size:13px">No MCQ pairs detected.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        # Competence
        st.markdown('<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px;margin-bottom:14px">', unsafe_allow_html=True)
        st.markdown('<div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:14px">🎯 Competence (Moore Level 4)</div>', unsafe_allow_html=True)
        comp_to_show = comp if comp else ev.get('eval_competence', [])
        if comp_to_show:
            tbl = '<table style="width:100%;border-collapse:collapse"><thead><tr>'
            if comp:
                for h in ['Item','Pre','Post','Δ']:
                    tbl += f'<th style="color:#94a3b8;font-size:11px;text-transform:uppercase;padding:8px 6px;border-bottom:1px solid #334155;text-align:left">{h}</th>'
                tbl += '</tr></thead><tbody>'
                for r in comp:
                    chg_color = '#4ade80' if r['change'] > 0 else '#f87171'
                    chg_str = f"+{r['change']}" if r['change'] > 0 else str(r['change'])
                    tbl += f'<tr><td style="color:#e2e8f0;font-size:12px;padding:9px 6px;border-bottom:1px solid #1e293b" title="{r["label"]}">{short(r["label"],38)}</td><td style="color:#e2e8f0;font-size:12px;padding:9px 6px;border-bottom:1px solid #1e293b">{r["pre_mean"]}</td><td style="color:#e2e8f0;font-size:12px;padding:9px 6px;border-bottom:1px solid #1e293b">{r["post_mean"]}</td><td style="color:{chg_color};font-weight:600;font-size:12px;padding:9px 6px;border-bottom:1px solid #1e293b">{chg_str}</td></tr>'
            else:
                for h in ['Learning Objective','Mean','N']:
                    tbl += f'<th style="color:#94a3b8;font-size:11px;text-transform:uppercase;padding:8px 6px;border-bottom:1px solid #334155;text-align:left">{h}</th>'
                tbl += '</tr></thead><tbody>'
                for r in [x for x in comp_to_show if 'participants will be able' not in x['label'].lower()][:5]:
                    tbl += f'<tr><td style="color:#e2e8f0;font-size:12px;padding:9px 6px;border-bottom:1px solid #1e293b" title="{r["label"]}">{short(r["label"],38)}</td><td style="color:#22d3ee;font-size:12px;padding:9px 6px;border-bottom:1px solid #1e293b">{r["mean"]}/5.0</td><td style="color:#94a3b8;font-size:12px;padding:9px 6px;border-bottom:1px solid #1e293b">{r["n"]}</td></tr>'
            tbl += '</tbody></table>'
            st.markdown(tbl, unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#64748b;font-size:13px">No Likert items detected.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Satisfaction
        sats = ev.get('satisfaction', [])
        if sats:
            st.markdown('<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px">', unsafe_allow_html=True)
            st.markdown('<div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:14px">⭐ Satisfaction (1–5)</div>', unsafe_allow_html=True)
            for s in sats[:5]:
                pf = round((s['mean'] / 5) * 100)
                st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin:6px 0">
  <div style="color:#94a3b8;font-size:12px;width:220px;flex-shrink:0" title="{s['label']}">{short(s['label'],35)}</div>
  <div style="flex:1;background:#334155;border-radius:4px;height:8px">
    <div style="width:{pf}%;background:#22d3ee;border-radius:4px;height:8px"></div>
  </div>
  <div style="color:#e2e8f0;font-size:12px;width:40px;text-align:right">{s['mean']}</div>
</div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)


def tab_knowledge(df, kn):
    st.markdown('<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px;margin-bottom:16px">', unsafe_allow_html=True)
    st.markdown('<div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:14px">📚 Knowledge Assessment — MCQ Pre/Post (Moore Level 3)</div>', unsafe_allow_html=True)
    if not kn:
        st.markdown('<div style="color:#64748b;padding:20px">No MCQ pre/post pairs detected.</div>', unsafe_allow_html=True)
    else:
        tbl = '<table style="width:100%;border-collapse:collapse"><thead><tr>'
        for h in ['Question','N','Pre %','Post %','Gain','p-value','Ex Pre','Ex Post','Nx Pre','Nx Post']:
            tbl += f'<th style="color:#94a3b8;font-size:11px;text-transform:uppercase;padding:8px 10px;border-bottom:1px solid #334155;text-align:left">{h}</th>'
        tbl += '</tr></thead><tbody>'
        for r in kn:
            gc = '#4ade80' if r['gain'] and r['gain'] > 0 else '#f87171'
            gs = f"+{r['gain']}pp" if r['gain'] and r['gain'] > 0 else f"{r['gain']}pp"
            ps = '<0.001' if r['p_val'] and r['p_val'] < 0.001 else (str(r['p_val']) if r['p_val'] else '—')
            def f(v): return f"{v}%" if v is not None else '—'
            tbl += f'<tr style="cursor:pointer" onmouseover="this.style.background=\'#334155\'" onmouseout="this.style.background=\'\'"><td style="color:#e2e8f0;font-size:13px;padding:10px" title="{r["label"]}">{short(r["label"],48)}</td><td style="color:#e2e8f0;font-size:13px;padding:10px">{r["n"]}</td><td style="color:#e2e8f0;font-size:13px;padding:10px">{f(r["pre_pct"])}</td><td style="color:#e2e8f0;font-size:13px;padding:10px">{f(r["post_pct"])}</td><td style="color:{gc};font-weight:600;font-size:13px;padding:10px">{gs}</td><td style="color:#94a3b8;font-size:12px;padding:10px">{ps}</td><td style="color:#a78bfa;font-size:12px;padding:10px">{f(r.get("ex_pre"))}</td><td style="color:#a78bfa;font-size:12px;padding:10px">{f(r.get("ex_post"))}</td><td style="color:#4ade80;font-size:12px;padding:10px">{f(r.get("nx_pre"))}</td><td style="color:#4ade80;font-size:12px;padding:10px">{f(r.get("nx_post"))}</td></tr>'
        tbl += '</tbody></table>'
        st.markdown(tbl, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def tab_competence(df, comp, ev):
    st.markdown('<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px;margin-bottom:16px">', unsafe_allow_html=True)
    st.markdown('<div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:14px">🎯 Competence — Likert Pre/Post (Moore Level 4)</div>', unsafe_allow_html=True)
    if comp:
        tbl = '<table style="width:100%;border-collapse:collapse"><thead><tr>'
        for h in ['Item','N','Pre Mean','Post Mean','Change','p-value','Ex Pre','Ex Post','Nx Pre','Nx Post']:
            tbl += f'<th style="color:#94a3b8;font-size:11px;text-transform:uppercase;padding:8px 10px;border-bottom:1px solid #334155;text-align:left">{h}</th>'
        tbl += '</tr></thead><tbody>'
        for r in comp:
            cc = '#4ade80' if r['change'] > 0 else '#f87171'
            cs = f"+{r['change']}" if r['change'] > 0 else str(r['change'])
            ps = '<0.001' if r['p_val'] and r['p_val'] < 0.001 else (str(r['p_val']) if r['p_val'] else '—')
            def fm(v): return str(v) if v is not None else '—'
            tbl += f'<tr><td style="color:#e2e8f0;font-size:13px;padding:10px" title="{r["label"]}">{short(r["label"],48)}</td><td style="color:#e2e8f0;font-size:13px;padding:10px">{r["n"]}</td><td style="color:#e2e8f0;font-size:13px;padding:10px">{r["pre_mean"]}</td><td style="color:#e2e8f0;font-size:13px;padding:10px">{r["post_mean"]}</td><td style="color:{cc};font-weight:600;font-size:13px;padding:10px">{cs}</td><td style="color:#94a3b8;font-size:12px;padding:10px">{ps}</td><td style="color:#a78bfa;font-size:12px;padding:10px">{fm(r.get("ex_pre"))}</td><td style="color:#a78bfa;font-size:12px;padding:10px">{fm(r.get("ex_post"))}</td><td style="color:#4ade80;font-size:12px;padding:10px">{fm(r.get("nx_pre"))}</td><td style="color:#4ade80;font-size:12px;padding:10px">{fm(r.get("nx_post"))}</td></tr>'
        tbl += '</tbody></table>'
        st.markdown(tbl, unsafe_allow_html=True)
    else:
        # Show EVAL competence items instead
        ec = [x for x in ev.get('eval_competence',[]) if 'participants will be able' not in x['label'].lower()]
        if ec:
            st.markdown('<div style="color:#94a3b8;font-size:12px;margin-bottom:10px">Post-activity learning objective ratings (1–5 Likert)</div>', unsafe_allow_html=True)
            for s in ec:
                pf = round((s['mean'] / 5) * 100)
                ex_s = f" | Ex: {s['ex_mean']}" if s['ex_mean'] else ''
                nx_s = f" | Nx: {s['nx_mean']}" if s['nx_mean'] else ''
                st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin:8px 0">
  <div style="color:#94a3b8;font-size:12px;width:360px;flex-shrink:0" title="{s['label']}">{short(s['label'],58)}</div>
  <div style="flex:1;background:#334155;border-radius:4px;height:8px">
    <div style="width:{pf}%;background:#a78bfa;border-radius:4px;height:8px"></div>
  </div>
  <div style="color:#e2e8f0;font-size:12px;width:100px;text-align:right">{s['mean']}/5.0{ex_s}{nx_s}</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#64748b">No Likert competence data detected.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def tab_evaluation(df, ev):
    metrics_html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:20px">'
    for lbl, key, color in [
        ('Intent to Change Practice','intent','#22d3ee'),
        ('Would Recommend Program','recommend','#4ade80'),
        ('Bias-Free Content','bias_free','#a78bfa'),
    ]:
        m = ev.get(key, {})
        val = f"{m.get('pct','—')}%" if m.get('pct') is not None else '—'
        n   = m.get('n','—')
        ex  = f"{m.get('ex_pct','—')}%" if m.get('ex_pct') is not None else '—'
        nx  = f"{m.get('nx_pct','—')}%" if m.get('nx_pct') is not None else '—'
        metrics_html += f"""
<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px;cursor:pointer">
  <div style="color:#94a3b8;font-size:11px;text-transform:uppercase;margin-bottom:6px">{lbl}</div>
  <div style="font-size:36px;font-weight:700;color:{color}">{val}</div>
  <div style="color:#64748b;font-size:11px;margin-top:4px">n={n} | Ex: {ex} | Nx: {nx}</div>
</div>"""
    metrics_html += '</div>'
    st.markdown(metrics_html, unsafe_allow_html=True)

    cn = ev.get('content_new', {})
    if cn.get('pct') is not None:
        st.markdown(f'<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px;margin-bottom:16px"><div style="color:#94a3b8;font-size:11px;text-transform:uppercase;margin-bottom:4px">Content New to Learner</div><div style="font-size:30px;font-weight:700;color:#f59e0b">{cn["pct"]}%</div><div style="color:#64748b;font-size:11px">n={cn.get("n","—")} | Ex: {cn.get("ex_pct","—")}% | Nx: {cn.get("nx_pct","—")}%</div></div>', unsafe_allow_html=True)

    if ev.get('satisfaction'):
        st.markdown('<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px;margin-bottom:16px">', unsafe_allow_html=True)
        st.markdown('<div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:14px">⭐ Satisfaction Ratings (1–5)</div>', unsafe_allow_html=True)
        for s in ev['satisfaction']:
            pf = round((s['mean'] / 5) * 100)
            ex_s = f" Ex:{s['ex_mean']}" if s['ex_mean'] else ''
            nx_s = f" Nx:{s['nx_mean']}" if s['nx_mean'] else ''
            st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin:8px 0">
  <div style="color:#94a3b8;font-size:12px;width:320px;flex-shrink:0" title="{s['label']}">{short(s['label'],52)}</div>
  <div style="flex:1;background:#334155;border-radius:4px;height:8px">
    <div style="width:{pf}%;background:#22d3ee;border-radius:4px;height:8px"></div>
  </div>
  <div style="color:#e2e8f0;font-size:12px;width:120px;text-align:right">{s['mean']}/5.0{ex_s}{nx_s}</div>
</div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def tab_key_findings(df, kn, comp, ev, summary):
    st.markdown('<div style="color:#e2e8f0;font-size:18px;font-weight:700;margin-bottom:20px">Key Findings Summary</div>', unsafe_allow_html=True)

    if kn:
        st.markdown('<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px;margin-bottom:16px">', unsafe_allow_html=True)
        st.markdown('<div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:16px">Knowledge Gain — Prior vs. After</div>', unsafe_allow_html=True)
        html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:20px">'
        for r in kn:
            pre  = r['pre_pct'] or 0
            post = r['post_pct'] or 0
            gain = r['gain'] or 0
            html += f"""
<div style="text-align:center">
  <div style="display:flex;gap:10px;justify-content:center;align-items:center;margin-bottom:8px">
    <div style="width:90px;height:90px;border-radius:50%;border:5px solid #f59e0b;display:flex;align-items:center;justify-content:center;flex-direction:column">
      <div style="font-size:22px;font-weight:700;color:#f59e0b">{pre}%</div>
      <div style="font-size:9px;color:#94a3b8">PRE</div>
    </div>
    <div style="font-size:18px;color:#64748b">→</div>
    <div style="width:90px;height:90px;border-radius:50%;border:5px solid #4ade80;display:flex;align-items:center;justify-content:center;flex-direction:column">
      <div style="font-size:22px;font-weight:700;color:#4ade80">{post}%</div>
      <div style="font-size:9px;color:#94a3b8">POST</div>
    </div>
  </div>
  <div style="color:#4ade80;font-size:13px;font-weight:700">+{gain}pp gain</div>
  <div style="color:#94a3b8;font-size:11px;margin-top:4px">{short(r["label"],55)}</div>
</div>"""
        st.markdown(html + '</div></div>', unsafe_allow_html=True)

    comp_show = comp if comp else [x for x in ev.get('eval_competence',[]) if 'participants will be able' not in x['label'].lower()]
    if comp_show:
        st.markdown('<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px;margin-bottom:16px">', unsafe_allow_html=True)
        st.markdown('<div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:16px">Competence Shift</div>', unsafe_allow_html=True)
        html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:20px">'
        for r in comp_show[:6]:
            if 'pre_mean' in r:
                pre_v, post_v = r['pre_mean'], r['post_mean']
                chg_txt = f"+{r['change']}" if r['change'] >= 0 else str(r['change'])
                html += f"""
<div style="text-align:center">
  <div style="display:flex;gap:10px;justify-content:center;align-items:center;margin-bottom:8px">
    <div style="width:80px;height:80px;border-radius:50%;border:4px solid #a78bfa;display:flex;align-items:center;justify-content:center;flex-direction:column">
      <div style="font-size:20px;font-weight:700;color:#a78bfa">{pre_v}</div>
      <div style="font-size:9px;color:#94a3b8">PRE</div>
    </div>
    <div style="font-size:14px;color:#64748b">→</div>
    <div style="width:80px;height:80px;border-radius:50%;border:4px solid #22d3ee;display:flex;align-items:center;justify-content:center;flex-direction:column">
      <div style="font-size:20px;font-weight:700;color:#22d3ee">{post_v}</div>
      <div style="font-size:9px;color:#94a3b8">POST</div>
    </div>
  </div>
  <div style="color:#22d3ee;font-size:13px;font-weight:700">{chg_txt} Likert pts</div>
  <div style="color:#94a3b8;font-size:11px;margin-top:4px">{short(r["label"],55)}</div>
</div>"""
            else:
                pf = round((r['mean']/5)*100)
                html += f"""
<div style="text-align:center">
  <div style="width:100px;height:100px;border-radius:50%;border:5px solid #a78bfa;display:flex;align-items:center;justify-content:center;flex-direction:column;margin:0 auto 8px">
    <div style="font-size:24px;font-weight:700;color:#a78bfa">{r["mean"]}</div>
    <div style="font-size:9px;color:#94a3b8">/5.0</div>
  </div>
  <div style="color:#94a3b8;font-size:11px">{short(r["label"],55)}</div>
</div>"""
        html += '</div></div>'
        st.markdown(html, unsafe_allow_html=True)

    html = '<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px;margin-bottom:16px"><div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:16px">Evaluation Highlights</div><div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px">'
    for lbl, key, color in [('Intent to Change','intent','#22d3ee'),('Would Recommend','recommend','#4ade80'),('Bias-Free','bias_free','#a78bfa')]:
        val = ev.get(key,{}).get('pct')
        vs  = f"{val}%" if val is not None else '—'
        html += f"""
<div style="text-align:center">
  <div style="width:110px;height:110px;border-radius:50%;border:6px solid {color};display:flex;align-items:center;justify-content:center;flex-direction:column;margin:0 auto 8px">
    <div style="font-size:28px;font-weight:800;color:{color}">{vs}</div>
  </div>
  <div style="color:#94a3b8;font-size:12px">{lbl}</div>
</div>"""
    html += '</div></div>'
    st.markdown(html, unsafe_allow_html=True)


def tab_kirkpatrick(df, kn, comp, ev, summary):
    levels = [
        ('Level 1','Reaction','#22d3ee','😊','Did learners find the activity relevant?'),
        ('Level 2','Learning','#4ade80','📚','Did learners gain knowledge/competence?'),
        ('Level 3','Behavior','#a78bfa','🔄','Did learners intend to change practice?'),
        ('Level 4','Results', '#f59e0b','🎯','Did the activity impact patient care?'),
    ]
    for lv, title, color, icon, desc in levels:
        st.markdown(f'<div style="background:#1e293b;border-left:4px solid {color};border-radius:0 8px 8px 0;padding:16px;margin-bottom:12px">', unsafe_allow_html=True)
        st.markdown(f'<div style="color:{color};font-size:13px;font-weight:700;margin-bottom:6px">{icon} {lv}: {title}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#94a3b8;font-size:12px;margin-bottom:10px">{desc}</div>', unsafe_allow_html=True)
        if lv == 'Level 1':
            for s in ev.get('satisfaction',[])[:5]:
                pf = round((s['mean']/5)*100)
                st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin:5px 0"><div style="color:#94a3b8;font-size:12px;width:300px;flex-shrink:0">{short(s["label"],48)}</div><div style="flex:1;background:#334155;border-radius:4px;height:8px"><div style="width:{pf}%;background:{color};border-radius:4px;height:8px"></div></div><div style="color:#e2e8f0;font-size:12px;width:50px;text-align:right">{s["mean"]}/5</div></div>', unsafe_allow_html=True)
        elif lv == 'Level 2':
            avg = round(sum(r['gain'] for r in kn if r['gain'])/max(1,len(kn)),1) if kn else 0
            st.markdown(f'<div style="color:{color};font-size:20px;font-weight:700;margin-bottom:8px">{len(kn)} MCQ Questions | Avg +{avg}pp gain</div>', unsafe_allow_html=True)
            for r in kn:
                pf = min(100, max(0, int((r['gain'] or 0) * 2)))
                st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin:5px 0"><div style="color:#94a3b8;font-size:12px;width:300px;flex-shrink:0">{short(r["label"],48)}</div><div style="flex:1;background:#334155;border-radius:4px;height:8px"><div style="width:{pf}%;background:{color};border-radius:4px;height:8px"></div></div><div style="color:#e2e8f0;font-size:12px;width:60px;text-align:right">+{r["gain"]}pp</div></div>', unsafe_allow_html=True)
        elif lv == 'Level 3':
            ip = ev.get('intent',{}).get('pct')
            if ip:
                st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin:5px 0"><div style="color:#94a3b8;font-size:12px;width:300px;flex-shrink:0">Intend to change practice</div><div style="flex:1;background:#334155;border-radius:4px;height:8px"><div style="width:{ip}%;background:{color};border-radius:4px;height:8px"></div></div><div style="color:#e2e8f0;font-size:12px;width:50px;text-align:right">{ip}%</div></div>', unsafe_allow_html=True)
        elif lv == 'Level 4':
            fu_cols = [c for c in df.columns if c.startswith('FU__')]
            if fu_cols:
                did = next((c for c in fu_cols if 'change' in c.lower()), None)
                if did:
                    vals = df[did].dropna().astype(str)
                    yp = pct(vals.str.lower().str.startswith('yes').sum(), len(vals))
                    st.markdown(f'<div style="color:{color};font-size:18px;font-weight:700">Confirmed Practice Change: {yp}% (n={len(vals)})</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#64748b;font-size:13px">Follow-up data not available in this dataset.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def tab_circle(df, kn, comp, ev, summary):
    st.markdown('<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px;margin-bottom:16px">', unsafe_allow_html=True)
    st.markdown('<div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:6px">CIRCLE Framework — CE/CPD Outcomes</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#94a3b8;font-size:12px;margin-bottom:16px">Competence · Impact · Relevance · Change · Learning · Engagement</div>', unsafe_allow_html=True)

    comp_show = comp if comp else ev.get('eval_competence', [])
    c_val = round(float(sum(r.get('post_mean', r.get('mean',0)) for r in comp_show) / max(1,len(comp_show)) / 5 * 100), 1) if comp_show else 0
    i_val = ev.get('intent',{}).get('pct') or 0
    sats  = ev.get('satisfaction',[])
    r_val = round(float(sum(s['mean'] for s in sats)/max(1,len(sats))/5*100),1) if sats else 0
    ch_val = ev.get('recommend',{}).get('pct') or 0
    l_val  = round(float(sum(r['post_pct'] for r in kn if r['post_pct'])/max(1,len(kn))),1) if kn else 0
    e_val  = summary.get('match_pct') or 0

    for lbl, val, color, desc in [
        ('C — Competence', c_val, '#22d3ee', f"Post-training competence across {len(comp_show)} items"),
        ('I — Impact',     i_val, '#4ade80', 'Intent to change clinical practice'),
        ('R — Relevance',  r_val, '#a78bfa', f"Activity satisfaction ({len(sats)} items, 1–5 scale)"),
        ('C — Change',     ch_val,'#f59e0b', 'Would recommend program to colleague'),
        ('L — Learning',   l_val, '#60a5fa', f"Post-test knowledge accuracy ({len(kn)} MCQ questions)"),
        ('E — Engagement', e_val, '#fb923c', 'Pre/post completion rate'),
    ]:
        pf = min(100, max(0, int(val)))
        st.markdown(f"""
<div style="margin-bottom:14px">
  <div style="display:flex;justify-content:space-between;margin-bottom:4px">
    <div style="color:#e2e8f0;font-size:13px;font-weight:600">{lbl}</div>
    <div style="color:{color};font-size:13px;font-weight:700">{val}%</div>
  </div>
  <div style="background:#334155;border-radius:4px;height:10px">
    <div style="width:{pf}%;background:{color};border-radius:4px;height:10px"></div>
  </div>
  <div style="color:#64748b;font-size:11px;margin-top:3px">{desc}</div>
</div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def tab_jcehp(df, kn, comp, ev, summary, prog_name):
    sections = ['Abstract','Introduction','Methods','Results','Discussion','Conclusion']
    existing = st.session_state.get('jcehp_text', {})
    filled = [s for s in sections if existing.get(s)]
    pct_done = round(len(filled)/len(sections)*100)

    st.markdown(f'<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px;margin-bottom:16px"><div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:8px">📝 JCEHP Article Preparation</div><div style="color:#94a3b8;font-size:12px;margin-bottom:8px">{pct_done}% complete ({len(filled)}/{len(sections)} sections)</div><div style="background:#334155;border-radius:6px;height:8px"><div style="width:{pct_done}%;background:#22d3ee;border-radius:6px;height:8px"></div></div></div>', unsafe_allow_html=True)

    kn_txt = ' '.join([f"Knowledge of {short(r['label'],50)}: pre {r['pre_pct']}% vs post {r['post_pct']}% (Δ={r['gain']}pp)." for r in kn])
    intent = ev.get('intent',{}).get('pct')
    rec    = ev.get('recommend',{}).get('pct')

    auto = {
        'Abstract':  f"Background: Educational programming addressing {prog_name or 'clinical practice gaps'} is needed to support clinician competence. Methods: A multi-vendor CME activity (Exchange + Nexus, N={summary.get('total',0)}) was analyzed for outcomes. Results: {kn_txt[:200]} Discussion: Findings support meaningful educational impact.",
        'Methods':   f"This outcomes analysis included {summary.get('total',0)} learners across Exchange (n={summary.get('ex_total',0)}) and Nexus (n={summary.get('nx_total',0)}) vendors. Pre/post matched analysis included {summary.get('matched',0)} learners ({summary.get('match_pct',0)}% completion). Evaluation survey data was available for {summary.get('with_eval',0)} participants.",
        'Results':   f"Knowledge outcomes: {kn_txt}\n\nEvaluation: {f'{intent}% of respondents indicated intent to change practice. ' if intent else ''}{f'{rec}% would recommend this program.' if rec else ''}",
    }

    for sec in sections:
        content = existing.get(sec, auto.get(sec, ''))
        st.markdown(f'<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;margin-bottom:10px"><div style="color:#a78bfa;font-size:13px;font-weight:700;margin-bottom:8px">{sec}</div>', unsafe_allow_html=True)
        new_text = st.text_area(sec, value=content, height=110, key=f'jcehp_{sec}', label_visibility='collapsed')
        if new_text != content:
            st.session_state.setdefault('jcehp_text', {})[sec] = new_text
        st.markdown('</div>', unsafe_allow_html=True)


def tab_ai_insights(df, kn, comp, ev, summary):
    st.markdown('<div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px">', unsafe_allow_html=True)
    st.markdown('<div style="color:#e2e8f0;font-size:15px;font-weight:600;margin-bottom:14px">🤖 AI Insights</div>', unsafe_allow_html=True)

    api_key = st.text_input("Anthropic API Key", type="password",
                            value=st.session_state.get('api_key',''),
                            placeholder="sk-ant-...")
    if api_key: st.session_state['api_key'] = api_key

    if st.button("Generate AI Insights"):
        if not api_key:
            st.error("Please enter your Anthropic API key.")
        else:
            with st.spinner("Generating insights…"):
                kn_s   = "\n".join([f"- {r['label'][:60]}: pre={r['pre_pct']}% post={r['post_pct']}% gain={r['gain']}pp" for r in kn]) or "No MCQ data"
                comp_s = "\n".join([f"- {r['label'][:60]}: pre={r['pre_mean']} post={r['post_mean']} chg={r['change']}" for r in comp]) or "No Likert data"
                prompt = f"""You are a CME outcomes analyst. Generate 5 actionable insights for medical education QI.

Program: {st.session_state.get('prog_name','CME Activity')}
Learners: {summary.get('total',0)} (Exchange:{summary.get('ex_total',0)}, Nexus:{summary.get('nx_total',0)})
Matched: {summary.get('matched',0)} ({summary.get('match_pct','—')}%)

KNOWLEDGE:\n{kn_s}
COMPETENCE:\n{comp_s}
Intent to change: {ev.get('intent',{}).get('pct','N/A')}%
Would recommend: {ev.get('recommend',{}).get('pct','N/A')}%

Return JSON array of 5 objects: title, moore_level (2/3/4/5), insight, recommendation"""
                try:
                    import requests as _req
                    resp = _req.post("https://api.anthropic.com/v1/messages",
                        headers={"x-api-key": api_key, "anthropic-version":"2023-06-01","content-type":"application/json"},
                        json={"model":"claude-sonnet-4-20250514","max_tokens":1500,
                              "messages":[{"role":"user","content":prompt}]}, timeout=30)
                    if resp.status_code == 200:
                        text = resp.json()['content'][0]['text']
                        m = re.search(r'\[.*\]', text, re.DOTALL)
                        if m: st.session_state['ai_insights'] = json.loads(m.group())
                    else:
                        st.error(f"API error {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    st.error(f"Error: {e}")

    for ins in st.session_state.get('ai_insights',[]):
        lvl = str(ins.get('moore_level',''))
        colors = {'2':'#f59e0b','3':'#4ade80','4':'#22d3ee','5':'#a78bfa'}
        c = colors.get(lvl,'#64748b')
        st.markdown(f'<div style="background:#0f172a;border:1px solid #334155;border-radius:10px;padding:18px;margin-bottom:12px"><div style="display:flex;align-items:center;gap:10px;margin-bottom:8px"><span style="background:{c}22;border:1px solid {c};color:{c};padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700">MOORE LEVEL {lvl}</span><div style="color:#e2e8f0;font-size:14px;font-weight:600">{ins.get("title","")}</div></div><div style="color:#94a3b8;font-size:13px;line-height:1.5">{ins.get("insight","")}</div><div style="color:#4ade80;font-size:12px;margin-top:8px">→ {ins.get("recommendation","")}</div></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD SCREEN
# ══════════════════════════════════════════════════════════════════════════════
def render_upload_screen():
    st.markdown("""
<div style="padding:60px 32px;text-align:center">
  <div style="font-size:52px;margin-bottom:16px">🧬</div>
  <div style="color:#e2e8f0;font-size:26px;font-weight:700;margin-bottom:8px">Integritas CME Outcomes Harmonizer</div>
  <div style="color:#64748b;font-size:15px;margin-bottom:40px">Upload Exchange and Nexus vendor files to begin analysis</div>
</div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div style="background:#1e293b;border:2px dashed #7c3aed;border-radius:12px;padding:24px;text-align:center;margin-bottom:8px"><div style="font-size:32px">📊</div><div style="color:#a78bfa;font-size:16px;font-weight:600;margin:8px 0">Exchange File</div><div style="color:#64748b;font-size:12px">Single-sheet .xlsx (PRE/POST/EVAL columns)</div></div>', unsafe_allow_html=True)
        ex_file = st.file_uploader("Exchange", type=['xlsx'], key='ex_upload', label_visibility='collapsed')
    with col2:
        st.markdown('<div style="background:#1e293b;border:2px dashed #16a34a;border-radius:12px;padding:24px;text-align:center;margin-bottom:8px"><div style="font-size:32px">📋</div><div style="color:#4ade80;font-size:16px;font-weight:600;margin:8px 0">Nexus File</div><div style="color:#64748b;font-size:12px">Multi-sheet .xlsx (Pre, Post, Eval sheets)</div></div>', unsafe_allow_html=True)
        nx_file = st.file_uploader("Nexus", type=['xlsx'], key='nx_upload', label_visibility='collapsed')

    if ex_file or nx_file:
        if st.button("🚀  Analyze Files", use_container_width=True):
            with st.spinner("Parsing files…"):
                ex_rec = parse_exchange(ex_file.read()) if ex_file else []
                nx_rec = parse_nexus(nx_file.read())   if nx_file else []
                if ex_file: st.session_state['prog_name'] = ex_file.name.rsplit('.',1)[0]
                st.session_state['ex_records']  = ex_rec
                st.session_state['nx_records']  = nx_rec
                st.session_state['all_records'] = ex_rec + nx_rec
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    ex_records  = st.session_state.get('ex_records', [])
    nx_records  = st.session_state.get('nx_records', [])
    all_records = st.session_state.get('all_records', [])

    # ── HEADER ──
    prog = st.session_state.get('prog_name','')
    ex_badge = f'<span style="background:#7c3aed22;border:1px solid #7c3aed;color:#a78bfa;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600">⬤ Exchange ({len(ex_records)})</span>' if ex_records else ''
    nx_badge = f'<span style="background:#16a34a22;border:1px solid #16a34a;color:#4ade80;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600">⬤ Nexus ({len(nx_records)})</span>'  if nx_records else ''
    st.markdown(f"""
<div style="background:#0f172a;border-bottom:1px solid #1e3a5f;padding:14px 32px;display:flex;align-items:center;gap:20px">
  <div style="font-size:20px;font-weight:700;color:#fff;white-space:nowrap">
    <span style="color:#22d3ee">Integritas</span> CME Outcomes Harmonizer
  </div>
  <div style="flex:1;color:#94a3b8;font-size:13px">{prog}</div>
  <div style="display:flex;gap:8px;align-items:center">{ex_badge}{nx_badge}</div>
</div>""", unsafe_allow_html=True)

    if not all_records:
        render_upload_screen()
        return

    # ── BUILD DATA ──
    raw_df      = combine_records(ex_records, nx_records)
    filtered_df = apply_filters(raw_df)
    pre_c, post_c, eval_c, fu_c, meta_c = classify_cols(filtered_df)
    kn   = compute_knowledge(filtered_df, pre_c, post_c)
    comp = compute_competence(filtered_df, pre_c, post_c)
    ev   = compute_evaluation(filtered_df, eval_c)
    summ = compute_summary(filtered_df)

    # ── TAB BAR ──
    active = st.session_state.get('tab','Overview')
    tab_cols = st.columns(len(TABS))
    for i, t in enumerate(TABS):
        with tab_cols[i]:
            if st.button(t, key=f'tab_{t}', use_container_width=True,
                         type='primary' if t == active else 'secondary'):
                st.session_state['tab'] = t
                st.rerun()

    # ── ACTION ROW ──
    a1, a2, a3, a4, _sp = st.columns([1,1,1,1,3])
    with a1:
        if st.button("🧠 Deep Insights"): st.session_state['tab']='AI Insights'; st.rerun()
    with a2:
        if st.button("✍️ Write Article"): st.session_state['tab']='JCEHP Article'; st.rerun()
    with a3:
        st.button("📄 PDF Report")
    with a4:
        xlsx_data = export_xlsx(filtered_df, kn, comp, ev, summ)
        st.download_button("📊 XLSX", data=xlsx_data, file_name="cme_outcomes.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ── VENDOR FILTER ──
    vf = st.session_state.get('vendor_filter','All')
    ex_n = int((raw_df['_source']=='Exchange').sum()) if '_source' in raw_df.columns else 0
    nx_n = int((raw_df['_source']=='Nexus').sum())    if '_source' in raw_df.columns else 0
    vc1, vc2, vc3, _vsp = st.columns([1,1,1,5])
    with vc1:
        if st.button(f"All ({len(raw_df)})", key='vf_all',
                     type='primary' if vf=='All' else 'secondary'):
            st.session_state['vendor_filter']='All'; st.rerun()
    with vc2:
        if st.button(f"⬤ Exchange ({ex_n})", key='vf_ex',
                     type='primary' if vf=='Exchange' else 'secondary'):
            st.session_state['vendor_filter']='Exchange'; st.rerun()
    with vc3:
        if st.button(f"⬤ Nexus ({nx_n})", key='vf_nx',
                     type='primary' if vf=='Nexus' else 'secondary'):
            st.session_state['vendor_filter']='Nexus'; st.rerun()

    st.divider()

    # ── RENDER ACTIVE TAB ──
    t = st.session_state.get('tab','Overview')
    pn = st.session_state.get('prog_name','')
    if   t == 'Overview':         tab_overview(filtered_df, summ, ev, kn, comp)
    elif t == 'Knowledge':        tab_knowledge(filtered_df, kn)
    elif t == 'Competence':       tab_competence(filtered_df, comp, ev)
    elif t == 'Evaluation':       tab_evaluation(filtered_df, ev)
    elif t == 'Key Findings':     tab_key_findings(filtered_df, kn, comp, ev, summ)
    elif t == 'Kirkpatrick':      tab_kirkpatrick(filtered_df, kn, comp, ev, summ)
    elif t == 'CIRCLE Framework': tab_circle(filtered_df, kn, comp, ev, summ)
    elif t == 'JCEHP Article':    tab_jcehp(filtered_df, kn, comp, ev, summ, pn)
    elif t == 'AI Insights':      tab_ai_insights(filtered_df, kn, comp, ev, summ)

    st.divider()
    if st.button("📁 Upload New Files"):
        for k in ['ex_records','nx_records','all_records','ai_insights']:
            st.session_state[k] = []
        st.session_state['jcehp_text'] = {}
        st.rerun()


if __name__ == '__main__':
    main()
