"""
Integritas CME Outcomes Harmonizer
Two-tab Streamlit app:
  Tab 1 — Merger: upload Exchange + Nexus → download combined Excel
  Tab 2 — Analyzer: upload combined Excel → full analytics dashboard

MCQ FIX: write_combined_excel() deduplicates column headers by appending
_PRE / _POST / _EVAL suffix when two columns share the same truncated display
name.  classify_cols() detects section by suffix rather than position.
"""

import io
import re
import math
from collections import defaultdict

import streamlit as st
import pandas as pd
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter
from scipy import stats

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — EXCHANGE PARSER
# ══════════════════════════════════════════════════════════════════════════════

def parse_exchange(file_bytes):
    """
    Exchange format:
      Row 0: section banner (PRE / POST / EVALUATION in merged cells)
      Row 1: sub-header (sometimes blank)
      Row 2: column labels (actual question text)
      Row 3+: data
    Returns list of dicts, each with keys  META_* / PRE_* / POST_* / EVAL_*
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if len(all_rows) < 4:
        return []

    r0 = all_rows[0]   # section banners
    r1 = all_rows[1]   # sub-headers
    r2 = all_rows[2]   # column labels

    # ── Find section boundaries from row 0 ──
    pre_start = post_start = eval_start = None
    for i, v in enumerate(r0):
        sv = str(v).strip().upper() if v else ''
        if sv == 'PRE'  and pre_start  is None: pre_start  = i
        if sv == 'POST' and post_start is None: post_start = i
        if sv in ('EVALUATION', 'EVAL') and eval_start is None: eval_start = i

    # Fallback: scan row 1 for section markers
    if pre_start is None:
        for i, v in enumerate(r1):
            sv = str(v).strip().upper() if v else ''
            if sv == 'PRE'  and pre_start  is None: pre_start  = i
            if sv == 'POST' and post_start is None: post_start = i
            if sv in ('EVALUATION', 'EVAL') and eval_start is None: eval_start = i

    # Hard fallbacks
    if pre_start  is None: pre_start  = 12
    if post_start is None: post_start = pre_start + 8
    if eval_start is None: eval_start = post_start + 8

    # ── Build column map ──
    cols = []
    n = max(len(r0), len(r2))
    for i in range(n):
        meta_hdr = str(r0[i]).strip() if i < len(r0) and r0[i] else ''
        col_lbl  = str(r2[i]).strip() if i < len(r2) and r2[i] else ''
        header   = col_lbl if col_lbl and col_lbl not in ('\xa0', 'Questions/Answers') else (
                   meta_hdr if meta_hdr and meta_hdr not in ('\xa0',) else None)
        if not header:
            continue

        sec = 'meta'
        if   i >= eval_start:  sec = 'eval'
        elif i >= post_start:  sec = 'post'
        elif i >= pre_start:   sec = 'pre'
        cols.append({'header': header, 'section': sec, 'idx': i})

    # ── Build records ──
    records = []
    for row in all_rows[3:]:
        if not any(row):
            continue
        rec = {
            '_source':      'Exchange',
            '_has_post':    False,
            '_has_eval':    False,
            '_has_followup': False,
        }
        for col in cols:
            i = col['idx']
            val = row[i] if i < len(row) else None
            if val == '\xa0': val = None
            sec = col['section']
            key = f"{sec.upper()}_{col['header']}"
            rec[key] = val
            if sec == 'post' and val is not None: rec['_has_post'] = True
            if sec == 'eval' and val is not None: rec['_has_eval'] = True
        records.append(rec)

    return records


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — NEXUS PARSER
# ══════════════════════════════════════════════════════════════════════════════

def _nexus_sheet_to_dicts(ws):
    if ws is None:
        return []
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip() if h else '' for h in rows[0]]
    result = []
    for row in rows[1:]:
        if not any(row):
            continue
        rec = {}
        for h, v in zip(headers, row):
            if h:
                rec[h] = v if v != '\xa0' else None
        result.append(rec)
    return result


def _nexus_find_key(rows, *keyword_groups):
    """Find the first column key that contains ALL keywords in any group."""
    if not rows:
        return None
    for group in keyword_groups:
        for k in rows[0]:
            kl = k.lower()
            if all(w.lower() in kl for w in group):
                return k
    return None


def parse_nexus(file_bytes):
    """
    Nexus multi-sheet format:
      PreNon — pre-only respondents (no post)
      Pre    — matched pre rows
      Post   — matched post rows  (same respondents as Pre, same order)
      Eval   — evaluation rows
      Follow Up — follow-up rows
    Returns list of dicts with keys META_* / PRE_* / POST_* / EVAL_* / FOLLOWUP_*
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)

    def sheet(name):
        for s in wb.sheetnames:
            if s.strip().lower() == name.lower():
                return _nexus_sheet_to_dicts(wb[s])
        return []

    pre_non  = sheet('PreNon')
    pre_rows = sheet('Pre')
    post_rows= sheet('Post')
    eval_rows= sheet('Eval')
    fu_rows  = sheet('Follow Up')
    wb.close()

    # ── Email key ──
    email_key = (_nexus_find_key(pre_rows, ['email']) or
                 _nexus_find_key(pre_non,  ['email']))

    # ── Build email→eval map ──
    eval_map = {}
    if eval_rows and email_key:
        ek = _nexus_find_key(eval_rows, ['email'])
        for r in eval_rows:
            e = str(r.get(ek, '') or '').strip().lower()
            if e:
                eval_map[e] = r

    # ── Build email→fu map ──
    fu_map = {}
    if fu_rows and email_key:
        ek = _nexus_find_key(fu_rows, ['email'])
        for r in fu_rows:
            e = str(r.get(ek, '') or '').strip().lower()
            if e:
                fu_map[e] = r

    # Helper to prefix keys
    def prefixed(row_dict, prefix, exclude_keys=None):
        out = {}
        for k, v in row_dict.items():
            if exclude_keys and k in exclude_keys:
                continue
            out[f"{prefix}_{k}"] = v
        return out

    records = []

    # ── Pre-only respondents (no post) ──
    for pre in pre_non:
        email = str(pre.get(email_key, '') or '').strip().lower() if email_key else ''
        rec = {
            '_source':      'Nexus',
            '_has_post':    False,
            '_has_eval':    False,
            '_has_followup': False,
        }
        rec.update(prefixed(pre, 'META'))
        ev = eval_map.get(email)
        if ev:
            rec.update(prefixed(ev, 'EVAL'))
            rec['_has_eval'] = True
        fu = fu_map.get(email)
        if fu:
            rec.update(prefixed(fu, 'FOLLOWUP'))
            rec['_has_followup'] = True
        records.append(rec)

    # ── Matched pre/post respondents ──
    for i, pre in enumerate(pre_rows):
        email = str(pre.get(email_key, '') or '').strip().lower() if email_key else ''
        post  = post_rows[i] if i < len(post_rows) else {}
        rec = {
            '_source':      'Nexus',
            '_has_post':    bool(post),
            '_has_eval':    False,
            '_has_followup': False,
        }
        rec.update(prefixed(pre, 'META'))
        if post:
            rec.update(prefixed(post, 'POST'))
        ev = eval_map.get(email)
        if ev:
            rec.update(prefixed(ev, 'EVAL'))
            rec['_has_eval'] = True
        fu = fu_map.get(email)
        if fu:
            rec.update(prefixed(fu, 'FOLLOWUP'))
            rec['_has_followup'] = True
        records.append(rec)

    # ── Follow-up-only rows not already captured ──
    matched_emails = set()
    if email_key:
        for r in pre_rows + pre_non:
            e = str(r.get(email_key, '') or '').strip().lower()
            if e:
                matched_emails.add(e)
    for fu in fu_rows:
        ek = _nexus_find_key(fu_rows, ['email'])
        e  = str(fu.get(ek, '') or '').strip().lower() if ek else ''
        if e and e in matched_emails:
            continue
        rec = {
            '_source':      'Nexus',
            '_has_post':    False,
            '_has_eval':    False,
            '_has_followup': True,
        }
        rec.update(prefixed(fu, 'FOLLOWUP'))
        records.append(rec)

    return records


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — COMBINED EXCEL WRITER  (with MCQ dedup fix)
# ══════════════════════════════════════════════════════════════════════════════

SECTION_ORDER = ['meta', 'pre', 'post', 'eval', 'followup']

SECTION_FILLS = {
    'meta':     PatternFill('solid', fgColor='2D3142'),
    'pre':      PatternFill('solid', fgColor='1A3A5C'),
    'post':     PatternFill('solid', fgColor='1A4A2E'),
    'eval':     PatternFill('solid', fgColor='3D1A5C'),
    'followup': PatternFill('solid', fgColor='5C3A1A'),
}
SOURCE_FILLS = {
    'Exchange': PatternFill('solid', fgColor='1E1030'),
    'Nexus':    PatternFill('solid', fgColor='0E2010'),
    'Nexus_FU': PatternFill('solid', fgColor='2A1A0E'),
}
WHITE_FONT  = Font(color='FFFFFF', bold=True, size=9)
BOLD_FONT   = Font(bold=True)
NORMAL_FONT = Font(size=9)
CENTER_ALIGN = Alignment(horizontal='center', vertical='center', wrap_text=True)
LEFT_ALIGN   = Alignment(horizontal='left',   vertical='top',    wrap_text=True)


def _section_of_key(key: str) -> str:
    k = key.upper()
    for sec in ('FOLLOWUP', 'EVAL', 'POST', 'PRE', 'META'):
        if k.startswith(sec + '_'):
            return sec.lower()
    if key.startswith('_'):
        return 'meta'
    return 'meta'


def _display_of_key(key: str) -> str:
    """Strip the section prefix to get a human-readable column name."""
    for sec in ('FOLLOWUP_', 'EVAL_', 'POST_', 'PRE_', 'META_'):
        if key.upper().startswith(sec):
            return key[len(sec):]
    return key.lstrip('_')


def write_combined_excel(ex_records, nx_records) -> bytes:
    """
    Build the combined Excel workbook and return as bytes.

    MCQ DEDUP FIX:
    When two columns have the same display name but come from different
    sections (e.g. PRE and POST carry the same truncated MCQ question text),
    we append   __PRE / __POST / __EVAL  to the output column header so that
    every header in the sheet is unique.  The section suffix is also stored
    as part of the column definition so the Analyzer can detect section by
    suffix rather than by position.
    """
    all_records = ex_records + nx_records

    # ── Collect all keys in section order ──
    seen_keys = set()
    ordered_keys = []
    # System keys first
    for sk in ('_source', '_has_post', '_has_eval', '_has_followup'):
        seen_keys.add(sk)
        ordered_keys.append(sk)

    sec_buckets = defaultdict(list)
    for rec in all_records:
        for k in rec:
            if k not in seen_keys:
                seen_keys.add(k)
                sec_buckets[_section_of_key(k)].append(k)

    for sec in SECTION_ORDER:
        for k in sec_buckets[sec]:
            ordered_keys.append(k)

    # ── Build display headers with dedup suffix ──
    # display_name → list of (key, section)
    display_count = defaultdict(list)
    for k in ordered_keys:
        if k.startswith('_'):
            continue
        disp = _display_of_key(k)
        trunc = disp[:60]   # same truncation threshold used in pandas read
        display_count[trunc].append(k)

    # Keys whose display names collide across sections
    collision_keys = set()
    for trunc, keys in display_count.items():
        if len(keys) > 1:
            # Only flag if they come from different sections
            secs = {_section_of_key(k) for k in keys}
            if len(secs) > 1:
                for k in keys:
                    collision_keys.add(k)

    def col_header(key):
        if key.startswith('_'):
            return key
        disp = _display_of_key(key)
        if key in collision_keys:
            sec = _section_of_key(key).upper()
            return f"{disp}__{sec}"
        return disp

    headers = [col_header(k) for k in ordered_keys]

    # ── Write workbook ──
    wb = openpyxl.Workbook()
    ws_data    = wb.active
    ws_data.title = 'Combined Data'
    ws_summary = wb.create_sheet('Summary')
    ws_colmap  = wb.create_sheet('Column Map')

    # — Header row with section color bands —
    for ci, (key, hdr) in enumerate(zip(ordered_keys, headers), start=1):
        sec = _section_of_key(key)
        cell = ws_data.cell(row=1, column=ci, value=hdr)
        cell.fill  = SECTION_FILLS.get(sec, SECTION_FILLS['meta'])
        cell.font  = WHITE_FONT
        cell.alignment = CENTER_ALIGN
        ws_data.column_dimensions[get_column_letter(ci)].width = max(12, min(40, len(hdr) * 0.8 + 4))

    ws_data.row_dimensions[1].height = 40
    ws_data.freeze_panes = 'A2'

    # — Data rows —
    for ri, rec in enumerate(all_records, start=2):
        src = rec.get('_source', 'Nexus')
        is_fu = rec.get('_has_followup') and not rec.get('_has_post') and not rec.get('_has_eval')
        row_fill = SOURCE_FILLS.get('Nexus_FU' if is_fu else src, None)

        for ci, key in enumerate(ordered_keys, start=1):
            val = rec.get(key)
            cell = ws_data.cell(row=ri, column=ci, value=val)
            cell.font = NORMAL_FONT
            if row_fill:
                cell.fill = row_fill

    # — Summary sheet —
    ex_n  = len(ex_records)
    nx_n  = sum(1 for r in nx_records if not r.get('_has_followup'))
    fu_n  = sum(1 for r in nx_records if r.get('_has_followup') and
                                          not r.get('_has_post') and
                                          not r.get('_has_eval'))
    total = len(all_records)

    ws_summary['A1'] = 'Source';    ws_summary['A1'].font = BOLD_FONT
    ws_summary['B1'] = 'Records';   ws_summary['B1'].font = BOLD_FONT
    rows_s = [('Exchange', ex_n), ('Nexus (pre/post/eval)', nx_n),
              ('Nexus (follow-up only)', fu_n), ('TOTAL', total)]
    for i, (lbl, cnt) in enumerate(rows_s, start=2):
        ws_summary.cell(row=i, column=1, value=lbl)
        ws_summary.cell(row=i, column=2, value=cnt)

    # — Column map sheet —
    ws_colmap['A1'] = 'Column Header'; ws_colmap['A1'].font = BOLD_FONT
    ws_colmap['B1'] = 'Section';       ws_colmap['B1'].font = BOLD_FONT
    ws_colmap['C1'] = 'Original Key';  ws_colmap['C1'].font = BOLD_FONT
    ws_colmap['D1'] = 'Deduped';       ws_colmap['D1'].font = BOLD_FONT
    for i, (key, hdr) in enumerate(zip(ordered_keys, headers), start=2):
        ws_colmap.cell(row=i, column=1, value=hdr)
        ws_colmap.cell(row=i, column=2, value=_section_of_key(key))
        ws_colmap.cell(row=i, column=3, value=key)
        ws_colmap.cell(row=i, column=4, value='yes' if key in collision_keys else '')

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — ANALYZER: load combined Excel
# ══════════════════════════════════════════════════════════════════════════════

def load_combined(file_bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name='Combined Data', header=0)
    return df


def classify_cols(df: pd.DataFrame):
    """
    Classify columns into sections.
    MCQ FIX: columns deduplicated by write_combined_excel() carry __PRE/__POST/__EVAL suffix.
    """
    pre_cols  = []
    post_cols = []
    eval_cols = []
    meta_cols = []

    for col in df.columns:
        cu = col.upper()
        if cu.endswith('__PRE'):
            pre_cols.append(col); continue
        if cu.endswith('__POST'):
            post_cols.append(col); continue
        if cu.endswith('__EVAL'):
            eval_cols.append(col); continue
        if cu.startswith('PRE_'):
            pre_cols.append(col)
        elif cu.startswith('POST_'):
            post_cols.append(col)
        elif cu.startswith('EVAL_'):
            eval_cols.append(col)
        elif cu.startswith('FOLLOWUP_'):
            eval_cols.append(col)
        else:
            meta_cols.append(col)

    return pre_cols, post_cols, eval_cols, meta_cols


# ── Likert scorer ──
LIKERT_MAP = {
    "not at all familiar": 1, "not very familiar": 2, "neutral": 3,
    "somewhat familiar": 4, "very familiar": 5,
    "not at all confident": 1, "not very confident": 2,
    "somewhat confident": 3, "very confident": 4,
    "never": 1, "25% of the time": 2, "50% of the time": 3,
    "75% of the time": 4, "100% of the time": 5,
    "strongly disagree": 1, "disagree": 2, "agree": 4, "strongly agree": 5,
    "not at all": 1, "slightly": 2, "somewhat": 3, "very": 4, "extremely": 5,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
}

def to_likert(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    s = str(val).strip().lower()
    if s in LIKERT_MAP:
        return LIKERT_MAP[s]
    try:
        f = float(s)
        if 1.0 <= f <= 5.0:
            return f
    except (ValueError, TypeError):
        pass
    return None


def is_mcq_col(col_name, series):
    """Heuristic: column looks like a multiple-choice question answer."""
    cn = col_name.lower()
    # Skip obvious non-MCQ columns
    skip_patterns = [
        'email', 'name', 'zip', 'credential', 'specialty', 'practice',
        'source', 'activity', 'certificate', 'date', 'time',
        'satisfied', 'satisfaction', 'recommend', 'bias', 'new',
        'commercial', 'faculty', 'objectives', 'barrier', 'change',
        'intend', 'will you', 'are you', 'aware', 'important',
        'confident', 'familiar', 'agree', 'disagree',
    ]
    for pat in skip_patterns:
        if pat in cn:
            return False
    # Must have question-like text (>20 chars)
    if len(col_name) < 20:
        return False
    # Values should be mostly text answers (not numbers, not pure Likert)
    non_null = series.dropna()
    if len(non_null) == 0:
        return False
    likert_count = sum(1 for v in non_null if to_likert(v) is not None)
    if likert_count / len(non_null) > 0.8:
        return False
    return True


CORRECT_ANSWERS = {
    # LAI PrEP program answers — extend as needed
    "shared decision": "Ask the patient what factors matter most to them.",
    "jordan": "Syphilis, gonorrhea, and chlamydia screening",
    "cab lai": "CAB LAI requires cold-chain storage",
    "post-discontinuation": "HIV-1 RNA assay every 3 months for 12 months",
}

def get_correct_answer(col_name):
    cn = col_name.lower()
    for kw, ans in CORRECT_ANSWERS.items():
        if kw in cn:
            return ans
    return None


def pct_correct(series, correct_answer):
    if correct_answer is None:
        return None
    non_null = series.dropna()
    if len(non_null) == 0:
        return None
    n_correct = sum(1 for v in non_null
                    if str(v).strip().lower() == correct_answer.strip().lower())
    return round(100 * n_correct / len(non_null), 1), len(non_null)


def chi_square_pvalue(pre_series, post_series, correct_answer):
    if correct_answer is None:
        return None
    pre_c  = sum(1 for v in pre_series.dropna()
                 if str(v).strip().lower() == correct_answer.strip().lower())
    post_c = sum(1 for v in post_series.dropna()
                 if str(v).strip().lower() == correct_answer.strip().lower())
    pre_n  = len(pre_series.dropna())
    post_n = len(post_series.dropna())
    if pre_n == 0 or post_n == 0:
        return None
    contingency = [[pre_c,  pre_n  - pre_c],
                   [post_c, post_n - post_c]]
    try:
        _, p, _, _ = stats.chi2_contingency(contingency)
        return p
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — ANALYZER METRICS
# ══════════════════════════════════════════════════════════════════════════════

def find_col(df, *keywords, exclude=None):
    """Return first column whose name contains ALL keywords (case-insensitive)."""
    exclude = exclude or []
    for col in df.columns:
        cl = col.lower()
        if all(kw.lower() in cl for kw in keywords):
            if not any(ex.lower() in cl for ex in exclude):
                return col
    return None


def pct_yes(series):
    nn = series.dropna()
    if len(nn) == 0:
        return None, 0
    yes_vals = {'yes', 'y', '1', 'true', 'strongly agree', 'agree', 'very', 'extremely'}
    n_yes = sum(1 for v in nn if str(v).strip().lower() in yes_vals)
    return round(100 * n_yes / len(nn), 1), len(nn)


def pct_agree(series):
    nn = series.dropna()
    if len(nn) == 0:
        return None, 0
    agree_vals = {'agree', 'strongly agree', '4', '5', 'yes', 'y', 'true',
                  'very', 'extremely', '1'}
    n_agree = sum(1 for v in nn if str(v).strip().lower() in agree_vals)
    return round(100 * n_agree / len(nn), 1), len(nn)


def avg_pct_new(series):
    vals = []
    for v in series.dropna():
        s = str(v).strip().rstrip('%')
        try:
            f = float(s)
            if 0 <= f <= 100:
                vals.append(f)
            elif 0 <= f <= 1:
                vals.append(f * 100)
        except ValueError:
            pass
    if not vals:
        return None, 0
    return round(sum(vals) / len(vals), 1), len(vals)


def compute_knowledge(df, pre_cols, post_cols):
    """Match PRE and POST MCQ column pairs and compute gains."""
    # Build display-name → col lookup for post columns
    def disp(col):
        # Strip __PRE / __POST suffix and section prefix
        c = col
        for sfx in ('__PRE', '__POST', '__EVAL'):
            if c.upper().endswith(sfx):
                c = c[:-len(sfx)]
                break
        return _display_of_key(c).strip()

    post_by_disp = {}
    for col in post_cols:
        d = disp(col)
        post_by_disp[d] = col

    results = []
    for pre_col in pre_cols:
        if not is_mcq_col(pre_col, df[pre_col]):
            continue
        d = disp(pre_col)
        post_col = post_by_disp.get(d)
        if post_col is None:
            # Try fuzzy: look for a post col whose display name shares ≥60% of words
            pre_words = set(d.lower().split())
            for pd_disp, pc in post_by_disp.items():
                pc_words = set(pd_disp.lower().split())
                overlap = len(pre_words & pc_words) / max(len(pre_words), 1)
                if overlap >= 0.6:
                    post_col = pc
                    break

        correct = get_correct_answer(pre_col)
        pre_result  = pct_correct(df[pre_col],  correct)
        post_result = pct_correct(df[post_col], correct) if post_col else None

        if pre_result is None:
            continue

        pre_pct, pre_n = pre_result
        post_pct = post_n = None
        if post_result:
            post_pct, post_n = post_result

        p_val = None
        if post_col and correct:
            p_val = chi_square_pvalue(df[pre_col], df[post_col], correct)

        label = d[:80] if len(d) > 80 else d
        results.append({
            'label':    label,
            'pre_pct':  pre_pct,
            'post_pct': post_pct,
            'gain':     round(post_pct - pre_pct, 1) if post_pct is not None else None,
            'pre_n':    pre_n,
            'post_n':   post_n,
            'p_val':    p_val,
            'correct':  correct,
            'pre_col':  pre_col,
            'post_col': post_col,
        })
    return results


def compute_competence(df, pre_cols, post_cols):
    """Match PRE/POST Likert column pairs and compute mean shifts."""
    def disp(col):
        c = col
        for sfx in ('__PRE', '__POST', '__EVAL'):
            if c.upper().endswith(sfx):
                c = c[:-len(sfx)]
                break
        return _display_of_key(c).strip()

    post_by_disp = {}
    for col in post_cols:
        d = disp(col)
        post_by_disp[d] = col

    results = []
    for pre_col in pre_cols:
        scores = [to_likert(v) for v in df[pre_col] if to_likert(v) is not None]
        if len(scores) < 5:
            continue
        d = disp(pre_col)
        post_col = post_by_disp.get(d)

        pre_scores  = [s for s in scores if s is not None]
        post_scores = []
        if post_col:
            post_scores = [to_likert(v) for v in df[post_col] if to_likert(v) is not None]

        if not pre_scores:
            continue

        pre_mean  = round(sum(pre_scores)  / len(pre_scores),  2)
        post_mean = round(sum(post_scores) / len(post_scores), 2) if post_scores else None
        pre_pct4  = round(100 * sum(1 for s in pre_scores  if s >= 4) / len(pre_scores),  1)
        post_pct4 = round(100 * sum(1 for s in post_scores if s >= 4) / len(post_scores), 1) if post_scores else None

        p_val = None
        if post_scores and len(pre_scores) >= 3 and len(post_scores) >= 3:
            try:
                _, p_val = stats.ttest_ind(pre_scores, post_scores)
                p_val = round(p_val, 4)
            except Exception:
                pass

        label = d[:80] if len(d) > 80 else d
        results.append({
            'label':    label,
            'pre_mean': pre_mean,
            'post_mean': post_mean,
            'delta_mean': round(post_mean - pre_mean, 2) if post_mean else None,
            'pre_pct4': pre_pct4,
            'post_pct4': post_pct4,
            'delta_pct4': round(post_pct4 - pre_pct4, 1) if post_pct4 is not None else None,
            'pre_n':   len(pre_scores),
            'post_n':  len(post_scores),
            'p_val':   p_val,
            'pre_col': pre_col,
            'post_col': post_col,
        })
    return results


def compute_evaluation(df, eval_cols):
    """Compute evaluation metrics from eval columns."""
    metrics = {}

    # Intent to change
    intent_col = find_col(df, 'intend', exclude=['barrier']) or \
                 find_col(df, 'modify', 'practice') or \
                 find_col(df, 'intent') or \
                 find_col(df, 'change', 'practice', exclude=['barrier'])
    if intent_col:
        pct, n = pct_yes(df[intent_col])
        metrics['intent'] = {'pct': pct, 'n': n, 'col': intent_col}

    # Would recommend
    rec_col = find_col(df, 'recommend')
    if rec_col:
        pct, n = pct_yes(df[rec_col])
        metrics['recommend'] = {'pct': pct, 'n': n, 'col': rec_col}

    # Bias-free
    bias_col = find_col(df, 'free', 'commercial') or \
               find_col(df, 'free', 'bias') or \
               find_col(df, 'bias')
    if bias_col:
        pct, n = pct_yes(df[bias_col])
        metrics['bias_free'] = {'pct': pct, 'n': n, 'col': bias_col}

    # Content was new
    new_col = find_col(df, 'new', exclude=['renew', 'knew']) or \
              find_col(df, 'percentage', 'content') or \
              find_col(df, 'content', 'new')
    if new_col:
        pct, n = avg_pct_new(df[new_col])
        metrics['content_new'] = {'pct': pct, 'n': n, 'col': new_col}

    # Satisfaction items (faculty, objectives, etc.)
    sat_keywords = [
        ('faculty', ['faculty', 'knowledgeable', 'effective']),
        ('objectives', ['objectives', 'objective']),
        ('overall', ['overall', 'satisfaction']),
    ]
    satisfaction = []
    for sat_key, kws in sat_keywords:
        for kw_set in [kws]:
            for col in eval_cols:
                if all(kw in col.lower() for kw in kw_set[:1]):
                    pct, n = pct_agree(df[col])
                    if pct is not None:
                        # Strip long prefixes for display
                        label = col
                        for pfx in ['Please indicate the extent of your agreement with the following statements:>> ',
                                    'EVAL_', 'META_', 'PRE_', 'POST_']:
                            label = label.replace(pfx, '')
                        label = label[:70]
                        satisfaction.append({'label': label, 'pct': pct, 'n': n, 'col': col})
                        break

    metrics['satisfaction'] = satisfaction

    # Behavior change checkboxes
    behavior_col = find_col(df, 'behavior', 'change') or find_col(df, 'plan to')
    if behavior_col:
        counts = df[behavior_col].dropna().value_counts().head(10).to_dict()
        metrics['behavior_change'] = counts

    # Barriers
    for barrier_type in ['patient', 'provider', 'system']:
        bc = find_col(df, 'barrier', barrier_type)
        if bc:
            counts = df[bc].dropna().value_counts().head(10).to_dict()
            metrics[f'barrier_{barrier_type}'] = counts

    # Follow-up
    fu_cols = [c for c in df.columns if 'FOLLOWUP' in c.upper() or c.upper().endswith('__FOLLOWUP')]
    metrics['followup_n'] = int(df['_has_followup'].apply(
        lambda v: str(v).strip().lower() in ('true', 'yes', '1')
    ).sum()) if '_has_followup' in df.columns else 0

    return metrics


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — STREAMLIT UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def metric_card(label, value, delta=None, info=None):
    delta_html = ''
    if delta is not None:
        color = '#22c55e' if delta >= 0 else '#ef4444'
        sign  = '+' if delta >= 0 else ''
        delta_html = f'<span style="color:{color};font-size:14px">{sign}{delta}</span>'
    info_html = f'<span title="{info}" style="cursor:help;color:#94a3b8;font-size:11px"> ℹ</span>' if info else ''
    st.markdown(f"""
<div style="background:#1c2130;border:1px solid #252b38;border-radius:10px;
            padding:16px 20px;text-align:center;margin-bottom:8px">
  <div style="font-size:12px;color:#94a3b8;margin-bottom:6px">{label}{info_html}</div>
  <div style="font-size:28px;font-weight:700;color:#e2e8f0">{value}</div>
  {delta_html}
</div>
""", unsafe_allow_html=True)


def pval_badge(p):
    if p is None:
        return '<span style="color:#64748b">NS</span>'
    if p < 0.001:
        return '<span style="color:#22c55e;font-weight:700">p&lt;0.001 ✓</span>'
    if p < 0.01:
        return '<span style="color:#22c55e">p&lt;0.01 ✓</span>'
    if p < 0.05:
        return '<span style="color:#86efac">p&lt;0.05 ✓</span>'
    if p < 0.10:
        return '<span style="color:#fbbf24">p&lt;0.10 ~</span>'
    return f'<span style="color:#64748b">p={p:.3f}</span>'


def bar_html(pct, color='#3b82f6', max_width=200):
    if pct is None:
        return ''
    w = int(max_width * pct / 100)
    return (f'<div style="display:inline-block;background:{color};'
            f'height:10px;width:{w}px;border-radius:3px;vertical-align:middle"></div> '
            f'<span style="font-size:12px">{pct}%</span>')


def source_breakdown(df, col, compute_fn):
    """Return {Exchange: val, Nexus: val, Combined: val} for any metric fn."""
    out = {}
    for src in ('Exchange', 'Nexus', 'Combined'):
        if src == 'Combined':
            subset = df
        else:
            subset = df[df['_source'] == src] if '_source' in df.columns else df
        if len(subset) == 0:
            out[src] = (None, 0)
            continue
        out[src] = compute_fn(subset[col])
    return out


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 7 — TAB 1: MERGER
# ══════════════════════════════════════════════════════════════════════════════

def render_merger():
    st.subheader("Step 1 — Upload Source Files")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Exchange File**")
        ex_file = st.file_uploader("Upload Exchange .xlsx", type=['xlsx', 'xls'],
                                    key='ex_upload', label_visibility='collapsed')
    with col2:
        st.markdown("**Nexus File**")
        nx_file = st.file_uploader("Upload Nexus .xlsx", type=['xlsx', 'xls'],
                                    key='nx_upload', label_visibility='collapsed')

    if ex_file and nx_file:
        with st.spinner("Parsing Exchange file…"):
            ex_records = parse_exchange(ex_file.read())
        with st.spinner("Parsing Nexus file…"):
            nx_records = parse_nexus(nx_file.read())

        st.success(f"✅ Exchange: {len(ex_records)} records  |  "
                   f"Nexus: {len(nx_records)} records  |  "
                   f"Combined: {len(ex_records) + len(nx_records)} records")

        with st.spinner("Building combined Excel…"):
            combined_bytes = write_combined_excel(ex_records, nx_records)

        st.download_button(
            label     = "⬇  Download CME_Combined_Data.xlsx",
            data      = combined_bytes,
            file_name = "CME_Combined_Data.xlsx",
            mime      = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # Quick preview
        df_preview = pd.read_excel(io.BytesIO(combined_bytes), sheet_name='Combined Data',
                                    header=0, nrows=20)
        with st.expander("Preview first 20 rows", expanded=False):
            st.dataframe(df_preview, use_container_width=True)

        with st.expander("Column Map", expanded=False):
            df_colmap = pd.read_excel(io.BytesIO(combined_bytes), sheet_name='Column Map', header=0)
            st.dataframe(df_colmap, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 8 — TAB 2: ANALYZER
# ══════════════════════════════════════════════════════════════════════════════

def render_analyzer():
    st.subheader("Upload Combined Data")
    combo_file = st.file_uploader("Upload CME_Combined_Data.xlsx", type=['xlsx', 'xls'],
                                   key='combo_upload', label_visibility='collapsed')
    if not combo_file:
        st.info("Upload the combined Excel file produced by the Merger tab to begin.")
        return

    with st.spinner("Loading data…"):
        df = load_combined(combo_file.read())

    pre_cols, post_cols, eval_cols, meta_cols = classify_cols(df)

    # ── Overview cards ──
    total_n   = len(df)
    has_post  = int(df['_has_post'].apply(lambda v: str(v).strip().lower() in ('true', 'yes', '1')).sum()) \
                if '_has_post' in df.columns else 0
    has_eval  = int(df['_has_eval'].apply(lambda v: str(v).strip().lower() in ('true', 'yes', '1')).sum()) \
                if '_has_eval' in df.columns else 0
    has_fu    = int(df['_has_followup'].apply(lambda v: str(v).strip().lower() in ('true', 'yes', '1')).sum()) \
                if '_has_followup' in df.columns else 0
    pre_only  = total_n - has_post

    ex_n = int((df['_source'] == 'Exchange').sum()) if '_source' in df.columns else 0
    nx_n = int((df['_source'] == 'Nexus').sum())    if '_source' in df.columns else 0

    st.markdown("### Overview")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: metric_card("Total Learners",     total_n,
                          info="All records across Exchange and Nexus")
    with c2: metric_card("Pre-Only",           pre_only,
                          info="Completed pre-test but no post-test")
    with c3: metric_card("Pre+Post Matched",   has_post,
                          info="Completed both pre- and post-test")
    with c4: metric_card("With Evaluation",    has_eval,
                          info="Completed evaluation survey")
    with c5: metric_card("Follow-Up",          has_fu,
                          info="Completed follow-up survey")

    st.caption(f"Exchange: {ex_n}  |  Nexus: {nx_n}  |  "
               f"Pre cols: {len(pre_cols)}  |  Post cols: {len(post_cols)}  |  "
               f"Eval cols: {len(eval_cols)}")

    # ── Tabs ──
    tabs = st.tabs(["📊 Knowledge", "🎯 Competence", "📋 Evaluation",
                    "📈 Satisfaction", "🔄 Behavior / Barriers"])

    # ─── Knowledge tab ───────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("#### Knowledge Gain (MCQ % Correct)")
        kn_results = compute_knowledge(df, pre_cols, post_cols)

        if not kn_results:
            st.warning(
                "No MCQ questions detected. \n\n"
                "**Debug info:**\n"
                f"- PRE cols found: {len(pre_cols)}\n"
                f"- POST cols found: {len(post_cols)}\n"
                f"- PRE col names: {[c[:60] for c in pre_cols[:5]]}\n"
                f"- POST col names: {[c[:60] for c in post_cols[:5]]}"
            )
        else:
            for r in sorted(kn_results, key=lambda x: (x['gain'] or -999), reverse=True):
                post_str = f"{r['post_pct']}%" if r['post_pct'] is not None else "—"
                p = r['p_val']
                p_str = "p<0.001 ✓" if p and p < 0.001 else (f"p<0.05 ✓" if p and p < 0.05 else (f"p={p:.3f}" if p else "NS"))
                with st.expander(f"{r['label'][:70]} — Pre: {r['pre_pct']}%  →  Post: {post_str}  ({p_str})"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Pre % Correct",  f"{r['pre_pct']}%",   f"n={r['pre_n']}")
                    c2.metric("Post % Correct", f"{r['post_pct']}%" if r['post_pct'] else "—",
                               f"n={r['post_n']}")
                    c3.metric("Gain", f"{r['gain']:+.1f}pp" if r['gain'] is not None else "—")

                    st.markdown("**Definition:** % of respondents selecting the correct answer")
                    st.markdown(f"**Correct answer:** `{r['correct']}`")
                    st.markdown(f"**Formula:** (# correct) ÷ (# answered) × 100")
                    st.markdown(f"**p-value:** {pval_badge(r['p_val'])}", unsafe_allow_html=True)

                    # Source breakdown
                    if '_source' in df.columns and r['pre_col']:
                        st.markdown("**Source breakdown:**")
                        cols_bd = st.columns(3)
                        for si, src in enumerate(['Exchange', 'Nexus', 'Combined']):
                            sub = df if src == 'Combined' else df[df['_source'] == src]
                            res_pre  = pct_correct(sub[r['pre_col']], r['correct']) if r['pre_col'] else None
                            res_post = pct_correct(sub[r['post_col']], r['correct']) \
                                       if r['post_col'] and r['post_col'] in sub.columns else None
                            with cols_bd[si]:
                                st.markdown(f"**{src}** (n={len(sub)})")
                                if res_pre:
                                    st.write(f"Pre: {res_pre[0]}%")
                                if res_post:
                                    st.write(f"Post: {res_post[0]}%")

    # ─── Competence tab ──────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("#### Competence / Confidence Shifts (Likert)")
        comp_results = compute_competence(df, pre_cols, post_cols)

        if not comp_results:
            st.warning("No Likert questions detected in PRE/POST columns.")
        else:
            for r in sorted(comp_results,
                             key=lambda x: (x['delta_pct4'] or -999), reverse=True):
                p = r['p_val']
                p_str = "p<0.001" if p and p < 0.001 else (f"p<0.05" if p and p < 0.05 else (f"p={p:.3f}" if p else "NS"))
                post_mean_str = str(r['post_mean']) if r['post_mean'] is not None else "—"
                with st.expander(f"{r['label'][:70]} — Pre: {r['pre_mean']}  → Post: {post_mean_str}  ({p_str}):"):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Pre Mean",  r['pre_mean'])
                    c2.metric("Post Mean", r['post_mean'] or "—")
                    c3.metric("Δ Mean",    f"{r['delta_mean']:+.2f}" if r['delta_mean'] else "—")
                    c4.metric("Post % ≥4", f"{r['post_pct4']}%" if r['post_pct4'] is not None else "—",
                               delta=f"{r['delta_pct4']:+.1f}pp" if r['delta_pct4'] is not None else None)

                    st.markdown("**Definition:** Mean score on 5-point Likert scale (1=lowest, 5=highest)")
                    st.markdown("**% ≥4 formula:** COUNT(scores ≥ 4) ÷ COUNT(non-null) × 100")
                    st.markdown(f"**p-value (t-test):** {pval_badge(r['p_val'])}", unsafe_allow_html=True)

                    # Source breakdown
                    if '_source' in df.columns and r['pre_col']:
                        st.markdown("**Source breakdown:**")
                        bcols = st.columns(3)
                        for si, src in enumerate(['Exchange', 'Nexus', 'Combined']):
                            sub = df if src == 'Combined' else df[df['_source'] == src]
                            ps = [to_likert(v) for v in sub[r['pre_col']].dropna() if to_likert(v)]
                            with bcols[si]:
                                st.markdown(f"**{src}** (n={len(sub)})")
                                if ps:
                                    st.write(f"Pre mean: {round(sum(ps)/len(ps),2)}")

    # ─── Evaluation tab ──────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("#### Evaluation Metrics")
        ev = compute_evaluation(df, eval_cols)

        cols_ev = st.columns(4)
        defs = {
            'intent':      ("Intent to Change",  "% selecting Yes/Strongly Agree to intending to modify practice"),
            'recommend':   ("Would Recommend",   "% who would recommend this program to a colleague"),
            'bias_free':   ("Bias-Free",          "% rating the content as free of commercial bias"),
            'content_new': ("Content New",        "Avg % of content rated as new to the respondent"),
        }
        for ci, (mk, (label, defn)) in enumerate(defs.items()):
            m = ev.get(mk, {})
            val = f"{m.get('pct')}%" if m.get('pct') is not None else "—"
            with cols_ev[ci]:
                with st.expander(f"**{label}**: {val}"):
                    st.markdown(f"**Definition:** {defn}")
                    st.markdown(f"**n:** {m.get('n', 0)}")
                    if m.get('col'):
                        st.markdown(f"**Column:** `{m['col'][:60]}`")
                        # Source breakdown
                        for src in ['Exchange', 'Nexus', 'Combined']:
                            sub = df if src == 'Combined' else df[df['_source'] == src] if '_source' in df.columns else df
                            if mk == 'content_new':
                                pct, n = avg_pct_new(sub[m['col']])
                            else:
                                pct, n = pct_yes(sub[m['col']])
                            st.write(f"{src}: {pct}% (n={n})" if pct is not None else f"{src}: — (n={n})")

    # ─── Satisfaction tab ────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("#### Satisfaction (% Agree / Strongly Agree)")
        ev = compute_evaluation(df, eval_cols)
        sat_items = ev.get('satisfaction', [])

        if not sat_items:
            # Show all eval cols for debugging
            st.info("No satisfaction items detected via keyword matching.")
            with st.expander("All EVAL columns (debug)"):
                for ec in eval_cols:
                    st.code(ec)
        else:
            for item in sorted(sat_items, key=lambda x: x['pct'] or 0, reverse=True):
                st.markdown(
                    f"**{item['label']}** — "
                    f"{bar_html(item['pct'])} "
                    f"<span style='color:#94a3b8;font-size:11px'>(n={item['n']})</span>",
                    unsafe_allow_html=True
                )

    # ─── Behavior / Barriers tab ─────────────────────────────────────────────
    with tabs[4]:
        ev = compute_evaluation(df, eval_cols)

        col_beh, col_bar = st.columns(2)
        with col_beh:
            st.markdown("#### Behavior Change")
            bc = ev.get('behavior_change', {})
            if bc:
                for item, cnt in sorted(bc.items(), key=lambda x: x[1], reverse=True):
                    st.markdown(f"**{cnt}** — {str(item)[:80]}")
            else:
                st.info("No behavior change data found.")

        with col_bar:
            st.markdown("#### Barriers")
            for btype in ['patient', 'provider', 'system']:
                barriers = ev.get(f'barrier_{btype}', {})
                if barriers:
                    st.markdown(f"**{btype.title()} barriers:**")
                    for item, cnt in sorted(barriers.items(), key=lambda x: x[1], reverse=True)[:5]:
                        st.markdown(f"  {cnt} — {str(item)[:60]}")

        st.markdown("#### Follow-Up")
        metric_card("Follow-Up Respondents", ev.get('followup_n', 0),
                     info="Completed follow-up survey")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 9 — MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title  = "Integritas CME Outcomes Harmonizer",
        page_icon   = "📊",
        layout      = "wide",
        initial_sidebar_state = "collapsed",
    )
    st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0d1117; }
  [data-testid="stHeader"] { background: transparent; }
  .stTabs [data-baseweb="tab-list"] { gap: 8px; }
  .stTabs [data-baseweb="tab"] {
      background: #1c2130; border-radius: 8px 8px 0 0;
      padding: 8px 20px; color: #94a3b8;
  }
  .stTabs [aria-selected="true"] { background: #243046; color: #e2e8f0; }
  div[data-testid="metric-container"] {
      background: #1c2130; border: 1px solid #252b38;
      border-radius: 10px; padding: 10px;
  }
</style>
""", unsafe_allow_html=True)

    st.title("📊 Integritas CME Outcomes Harmonizer")
    st.caption("Tab 1: Merge Exchange + Nexus → combined Excel  |  "
               "Tab 2: Analyze combined Excel → outcomes dashboard")

    tab_merge, tab_analyze = st.tabs(["🔀  Merger", "📈  Analyzer"])

    with tab_merge:
        render_merger()

    with tab_analyze:
        render_analyzer()


if __name__ == "__main__":
    main()
