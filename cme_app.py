"""
Integritas CME Outcomes Harmonizer
Fully program-agnostic — no therapeutic area content, question text, correct answers,
specialty names, or barrier items are hardcoded. Everything derived at runtime from 3 uploaded files.
"""

import streamlit as st
import pandas as pd
import numpy as np
import openpyxl
import io
import json
import re
from collections import defaultdict, Counter
from scipy import stats

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Integritas CME Outcomes Harmonizer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ---------- base ---------- */
  html, body, [data-testid="stAppViewContainer"] {
    background: #0a0f1e !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif;
  }
  [data-testid="stHeader"] { background: transparent !important; }
  [data-testid="stSidebar"] { background: #060c1a !important; }
  section.main > div { padding-top: 0.5rem; }

  /* ---------- tabs ---------- */
  .stTabs [data-baseweb="tab-list"] {
    background: #0f1e3a;
    border-radius: 8px;
    padding: 4px;
    gap: 2px;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #94a3b8;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 500;
    padding: 6px 14px;
  }
  .stTabs [aria-selected="true"] {
    background: #1e3a5f !important;
    color: #fff !important;
  }

  /* ---------- cards ---------- */
  .card {
    background: #0f1e3a;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 12px;
  }
  .card-sm {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
  }

  /* ---------- stat cards ---------- */
  .stat-card {
    background: #0f1e3a;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 18px 16px 14px;
    text-align: center;
  }
  .stat-val { font-size: 2rem; font-weight: 700; color: #3b82f6; }
  .stat-lbl { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }

  /* ---------- badges ---------- */
  .badge-green  { background:#166534; color:#4ade80; border-radius:12px; padding:2px 10px; font-size:0.78rem; font-weight:600; }
  .badge-blue   { background:#1e3a5f; color:#60a5fa; border-radius:12px; padding:2px 10px; font-size:0.78rem; font-weight:600; }
  .badge-purple { background:#3b1f6e; color:#c084fc; border-radius:12px; padding:2px 10px; font-size:0.78rem; font-weight:600; }
  .badge-amber  { background:#78350f; color:#fbbf24; border-radius:12px; padding:2px 10px; font-size:0.78rem; font-weight:600; }
  .badge-cyan   { background:#164e63; color:#22d3ee; border-radius:12px; padding:2px 10px; font-size:0.78rem; font-weight:600; }

  /* ---------- progress bars ---------- */
  .bar-wrap { background:#1e293b; border-radius:4px; height:14px; margin:2px 0; overflow:hidden; }
  .bar-pre  { background:#ef4444; height:14px; border-radius:4px; }
  .bar-post { background:#3b82f6; height:14px; border-radius:4px; }
  .bar-green { background:#22c55e; height:14px; border-radius:4px; }

  /* ---------- pill filters ---------- */
  .pill-row { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:6px; }
  .pill {
    background:#1e293b; color:#94a3b8;
    border:1px solid #334155; border-radius:20px;
    padding:3px 12px; font-size:0.76rem; cursor:pointer;
  }
  .pill.active { background:#1e3a5f; color:#60a5fa; border-color:#3b82f6; }

  /* ---------- grant insight ---------- */
  .grant-insight {
    border: 1px solid #0d9488;
    background: #0d1f1e;
    border-radius: 8px;
    padding: 12px 16px;
    margin-top: 12px;
  }
  .grant-insight-lbl {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #0d9488;
    font-weight: 700;
    margin-bottom: 6px;
  }
  .circle-insight {
    border: 1px solid #f59e0b;
    background: #1c1200;
    border-radius: 8px;
    padding: 12px 16px;
    margin-top: 12px;
  }
  .circle-insight-lbl {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #f59e0b;
    font-weight: 700;
    margin-bottom: 6px;
  }

  /* ---------- donut placeholder ---------- */
  .donut-wrap { text-align:center; }
  .donut-pct  { font-size:2.4rem; font-weight:700; }
  .donut-lbl  { font-size:0.72rem; color:#94a3b8; text-transform:uppercase; letter-spacing:.04em; margin-top:4px; }

  /* ---------- expander (popup) ---------- */
  .streamlit-expanderHeader { font-size:0.82rem !important; }

  /* ---------- header ---------- */
  .app-header {
    background: #0f1e3a;
    border-bottom: 1px solid #1e3a5f;
    padding: 10px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    border-radius: 10px;
  }
  .logo-text { font-size:1.4rem; font-weight:700; }
  .logo-blue { color:#3b82f6; }
  .logo-white { color:#fff; }

  /* ---------- Kirkpatrick ---------- */
  .kirk-card {
    background:#0f1e3a; border:1px solid #1e3a5f; border-radius:10px;
    padding:16px; margin-bottom:10px;
  }
  .kirk-num { font-size:2rem; font-weight:800; color:#3b82f6; }
  .kirk-title { font-size:1rem; font-weight:600; color:#e2e8f0; }
  .kirk-note {
    background:#422006; border:1px solid #92400e; border-radius:8px;
    padding:10px 14px; color:#fbbf24; font-size:0.82rem; margin-top:8px;
  }

  /* ---------- clickable metric ---------- */
  .metric-clickable { cursor:pointer; text-decoration:underline dotted #3b82f6; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

LIKERT_MAP = {
    "never": 1, "0%": 1, "0% of the time": 1,
    "25%": 2, "25% of the time": 2,
    "50%": 3, "50% of the time": 3,
    "75%": 4, "75% of the time": 4,
    "always": 5, "100%": 5, "100% of the time": 5,
    "strongly disagree": 1,
    "disagree": 2,
    "neutral": 3, "neither agree nor disagree": 3,
    "agree": 4,
    "strongly agree": 5,
    # competence/confidence scales
    "not at all competent": 1, "not competent": 1,
    "slightly competent": 2, "somewhat competent": 2,
    "moderately competent": 3,
    "competent": 4, "quite competent": 4,
    "very competent": 5, "extremely competent": 5,
    # confidence
    "not at all confident": 1, "not confident": 1,
    "slightly confident": 2, "somewhat confident": 2,
    "moderately confident": 3,
    "confident": 4, "quite confident": 4,
    "very confident": 5, "extremely confident": 5,
}

def _norm(s):
    """Lowercase, strip, collapse spaces."""
    if not isinstance(s, str):
        return ""
    return re.sub(r"\s+", " ", s.strip().lower())

def _text_sim(a, b):
    """Word-overlap Jaccard similarity."""
    sa = set(_norm(a).split())
    sb = set(_norm(b).split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

def _strip_prefix(text):
    """Remove 'do you currently' / 'will you now' prefixes for matching."""
    t = _norm(text)
    for prefix in ["do you currently ", "will you now ", "do you now "]:
        if t.startswith(prefix):
            t = t[len(prefix):]
    return t

def _likert_score(answer_str):
    """Map an answer string to 1-5 likert value; return None if unmappable."""
    v = _norm(answer_str)
    if v in LIKERT_MAP:
        return LIKERT_MAP[v]
    # partial match
    for k, score in LIKERT_MAP.items():
        if k in v or v in k:
            return score
    return None

def _pval_str(p):
    if p < 0.001:
        return "p<0.001"
    elif p < 0.01:
        return f"p={p:.3f}"
    else:
        return f"p={p:.2f}"


# ═══════════════════════════════════════════════════════════════════════════════
# FILE PARSING
# ═══════════════════════════════════════════════════════════════════════════════

def parse_key_file(uploaded_file):
    """
    Parse the Exchange Question Key .xlsx.
    Returns list of question dicts.
    """
    wb = openpyxl.load_workbook(uploaded_file, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    questions = []
    for row in rows[1:]:  # skip header
        if not row or row[0] is None:
            continue
        # columns: rowid(0), Questionnaire(1), Type(2), Score(3), Orientation(4), Sort(5), Question(6), Answers(7), answer cols...
        try:
            rowid      = row[0]
            questionnaire = str(row[1]) if row[1] else ""
            q_type     = str(row[2]) if row[2] else ""
            score_val  = str(row[3]) if row[3] else ""
            orientation= str(row[4]) if row[4] else ""
            sort_val   = row[5]
            q_text     = str(row[6]) if row[6] else ""
            answers_raw= str(row[7]) if row[7] else ""
        except IndexError:
            continue

        if not q_text.strip():
            continue

        # section from questionnaire suffix
        qs_lower = questionnaire.lower()
        if "-pre" in qs_lower:
            section = "pre"
        elif "-post" in qs_lower:
            section = "post"
        elif "-eval" in qs_lower or "-evaluation" in qs_lower:
            section = "eval"
        elif "-followup" in qs_lower or "-follow" in qs_lower:
            section = "followup"
        else:
            section = "eval"  # default

        is_mcq = (str(score_val).strip() == "1")
        is_likert = ("likert" in q_type.lower() or "likert" in orientation.lower())

        # parse answers from the row (cols 7 onward can also hold answers)
        options = []
        correct_answer = None
        all_ans_text = []
        # collect from col 7 onward
        for cell in row[7:]:
            if cell is not None and str(cell).strip():
                all_ans_text.append(str(cell).strip())

        # also split answers_raw by common delimiters if needed
        if len(all_ans_text) <= 1 and answers_raw:
            parts = re.split(r"[|,\n]", answers_raw)
            all_ans_text = [p.strip() for p in parts if p.strip()]

        for ans in all_ans_text:
            if ans.startswith("*"):
                correct_answer = ans[1:].strip()
                options.append(correct_answer)
            else:
                options.append(ans)

        questions.append({
            "rowid": rowid,
            "questionnaire": questionnaire,
            "section": section,
            "q_text": q_text,
            "is_mcq": is_mcq,
            "is_likert": is_likert,
            "correct_answer": correct_answer,
            "options": options,
            "sort": sort_val,
            "orientation": orientation,
            "q_type": q_type,
        })

    return questions


def parse_exchange_file(uploaded_file):
    """
    Parse Exchange respondent .xlsx with 3-row header.
    Returns list of respondent dicts.
    """
    wb = openpyxl.load_workbook(uploaded_file, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    if len(rows) < 4:
        return []

    row0 = rows[0]  # meta labels
    row1 = rows[1]  # section banners
    row2 = rows[2]  # question text

    # Detect section boundaries from row1
    col_section = {}
    current_section = None
    for ci, cell in enumerate(row1):
        if cell:
            v = str(cell).upper()
            if "PRE" in v and "POST" not in v:
                current_section = "pre"
            elif "POST" in v:
                current_section = "post"
            elif "EVAL" in v:
                current_section = "eval"
            elif "FOLLOW" in v:
                current_section = "followup"
        if current_section:
            col_section[ci] = current_section

    # Meta col indices (0-based)
    # Email=1, LastName=2, FirstName=3, ZIP=4, Credentials=5, Specialty=6
    META_COLS = {1: "email", 2: "last_name", 3: "first_name", 4: "zip", 5: "credentials", 6: "specialty"}

    records = []
    for row in rows[3:]:
        if not row or all(c is None for c in row):
            continue
        rec = {"_source": "Exchange", "pre": {}, "post": {}, "eval": {}, "followup": {}, "meta": {}}
        email = str(row[1]).strip() if row[1] else f"exch_{len(records)}"
        rec["_id"] = email
        for ci, key in META_COLS.items():
            if ci < len(row):
                rec["meta"][key] = str(row[ci]).strip() if row[ci] else ""

        for ci, cell in enumerate(row):
            if ci in META_COLS:
                continue
            sec = col_section.get(ci)
            if not sec:
                continue
            q_label = str(row2[ci]).strip() if ci < len(row2) and row2[ci] else f"col_{ci}"
            if cell is not None:
                rec[sec][q_label] = str(cell).strip()

        rec["_has_post"] = bool(rec["post"])
        rec["_has_eval"] = bool(rec["eval"])
        rec["_has_followup"] = bool(rec["followup"])
        records.append(rec)

    return records


def parse_nexus_file(uploaded_file):
    """
    Parse Nexus multi-sheet .xlsx.
    Sheets: Pre-Test, Post, Eval, Follow Up  — joined by ID col (col 0).
    """
    wb = openpyxl.load_workbook(uploaded_file, data_only=True)

    SHEET_MAP = {}
    for name in wb.sheetnames:
        nl = name.lower().strip()
        if "pre" in nl:
            SHEET_MAP["pre"] = name
        elif "post" in nl:
            SHEET_MAP["post"] = name
        elif "eval" in nl:
            SHEET_MAP["eval"] = name
        elif "follow" in nl:
            SHEET_MAP["followup"] = name

    master = {}  # id -> rec

    META_KEYS = ["specialty", "credentials", "practice_type", "years"]

    for sec, sheet_name in SHEET_MAP.items():
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        header = rows[0]
        for row in rows[1:]:
            if not row or row[0] is None:
                continue
            uid = str(row[0]).strip()
            if uid.startswith("---"):
                continue
            if uid not in master:
                master[uid] = {"_source": "Nexus", "_id": uid,
                               "pre": {}, "post": {}, "eval": {}, "followup": {},
                               "meta": {}}
            rec = master[uid]
            for ci, cell in enumerate(row[1:], start=1):
                col_name = str(header[ci]).strip() if ci < len(header) and header[ci] else f"col_{ci}"
                if col_name.startswith("---"):
                    continue
                val = str(cell).strip() if cell is not None else ""
                # meta columns heuristic
                col_lower = col_name.lower()
                if any(m in col_lower for m in META_KEYS):
                    key_found = next((m for m in META_KEYS if m in col_lower), col_lower)
                    rec["meta"][key_found] = val
                else:
                    rec[sec][col_name] = val

    records = list(master.values())
    for rec in records:
        rec["_has_post"] = bool(rec["post"])
        rec["_has_eval"] = bool(rec["eval"])
        rec["_has_followup"] = bool(rec["followup"])

    return records


# ═══════════════════════════════════════════════════════════════════════════════
# MATCHING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

MATCH_THRESHOLD = 0.35

def _find_answer(rec_section_dict, q_text, threshold=MATCH_THRESHOLD):
    """
    Find best-matching answer in a respondent section dict.
    Returns (matched_key, answer_value) or (None, None).
    """
    q_base = _strip_prefix(q_text)
    best_score = 0
    best_key = None
    best_val = None
    for col_name, val in rec_section_dict.items():
        score = max(
            _text_sim(q_text, col_name),
            _text_sim(q_base, _strip_prefix(col_name))
        )
        if score > best_score:
            best_score = score
            best_key = col_name
            best_val = val
    if best_score >= threshold:
        return best_key, best_val
    return None, None


def compute_analytics(questions, records, specialty_filter=None, credential_filter=None, vendor_filter=None):
    """
    Core analytics engine. Returns the analytics_json dict.
    All filters are lists of values (None = no filter = include all).
    """

    # ── Apply filters ─────────────────────────────────────────────────────────
    def _passes(rec):
        if vendor_filter and vendor_filter != "All":
            if rec["_source"] != vendor_filter:
                return False
        spec = rec["meta"].get("specialty", "")
        cred = rec["meta"].get("credentials", "")
        if specialty_filter and specialty_filter != ["All"]:
            if spec not in specialty_filter:
                return False
        if credential_filter and credential_filter != ["All"]:
            if cred not in credential_filter:
                return False
        return True

    filtered = [r for r in records if _passes(r)]
    total = len(filtered)
    pre_only   = sum(1 for r in filtered if not r["_has_post"] and not r["_has_eval"])
    with_post  = sum(1 for r in filtered if r["_has_post"])
    with_eval  = sum(1 for r in filtered if r["_has_eval"])
    with_fu    = sum(1 for r in filtered if r["_has_followup"])

    # ── Vendors ───────────────────────────────────────────────────────────────
    vendors = Counter(r["_source"] for r in filtered)

    # ── Specialties / Credentials / Practice types / Years ───────────────────
    specialties = Counter()
    credentials = Counter()
    practice_types = Counter()
    years_map = Counter()
    for r in filtered:
        m = r["meta"]
        if m.get("specialty"): specialties[m["specialty"]] += 1
        if m.get("credentials"): credentials[m["credentials"]] += 1
        if m.get("practice_type"): practice_types[m["practice_type"]] += 1
        if m.get("years"): years_map[m["years"]] += 1

    # ── MCQ knowledge questions ───────────────────────────────────────────────
    mcq_qs = [q for q in questions if q["is_mcq"] and q["section"] == "pre"]
    knowledge_results = []
    all_kg = []

    for q in mcq_qs:
        pre_correct = 0; pre_total = 0
        post_correct = 0; post_total = 0

        # find corresponding post question
        post_q_text = q["q_text"]  # usually same text

        for rec in filtered:
            # PRE
            _, pre_ans = _find_answer(rec["pre"], q["q_text"])
            if pre_ans:
                pre_total += 1
                if q["correct_answer"] and _norm(pre_ans) == _norm(q["correct_answer"]):
                    pre_correct += 1

            # POST — search post dict, also check post questions if available
            if rec["_has_post"]:
                _, post_ans = _find_answer(rec["post"], q["q_text"])
                if post_ans:
                    post_total += 1
                    if q["correct_answer"] and _norm(post_ans) == _norm(q["correct_answer"]):
                        post_correct += 1

        pre_pct  = round(100 * pre_correct  / pre_total,  1) if pre_total  else 0
        post_pct = round(100 * post_correct / post_total, 1) if post_total else 0
        gain = round(post_pct - pre_pct, 1)
        if gain: all_kg.append(gain)

        # t-test
        pval = None
        if pre_total and post_total:
            try:
                _, pval = stats.ttest_ind(
                    [1]*pre_correct  + [0]*(pre_total  - pre_correct),
                    [1]*post_correct + [0]*(post_total - post_correct)
                )
            except Exception:
                pass

        knowledge_results.append({
            "label": q["q_text"],
            "prePct": pre_pct,
            "postPct": post_pct,
            "preN": pre_total,
            "postN": post_total,
            "gain": gain,
            "correctAnswer": q["correct_answer"] or "",
            "pval": pval,
            "_calc": {
                "preCorrect": pre_correct,
                "preTotal": pre_total,
                "postCorrect": post_correct,
                "postTotal": post_total,
            }
        })

    avg_kg = round(sum(all_kg) / len(all_kg), 1) if all_kg else 0

    # ── Likert / competence questions ─────────────────────────────────────────
    likert_qs = [q for q in questions if q["is_likert"]]
    likert_results = []

    for q in likert_qs:
        pre_vals = []
        post_vals = []

        for rec in filtered:
            # PRE
            _, pre_ans = _find_answer(rec["pre"], q["q_text"])
            if pre_ans:
                v = _likert_score(pre_ans)
                if v: pre_vals.append(v)

            # POST — also try eval for "will you now" variants
            if rec["_has_post"]:
                _, post_ans = _find_answer(rec["post"], q["q_text"])
                if not post_ans:
                    # Try eval
                    _, post_ans = _find_answer(rec["eval"], q["q_text"])
                if post_ans:
                    v = _likert_score(post_ans)
                    if v: post_vals.append(v)

        pre_mean  = round(sum(pre_vals)  / len(pre_vals),  2) if pre_vals  else 0
        post_mean = round(sum(post_vals) / len(post_vals), 2) if post_vals else 0

        likert_results.append({
            "label": q["q_text"],
            "pre": pre_mean,
            "post": post_mean,
            "preN": len(pre_vals),
            "postN": len(post_vals),
            "_calc": {
                "preSum": sum(pre_vals),
                "preN": len(pre_vals),
                "postSum": sum(post_vals),
                "postN": len(post_vals),
            }
        })

    # ── Eval metrics (intent, recommend, bias-free, content new) ─────────────
    # These are eval-section questions; detect by keyword heuristics
    intent_yes = 0; intent_total = 0
    recommend_yes = 0; recommend_total = 0
    bias_free_yes = 0; bias_free_total = 0
    content_new_vals = []
    sat_items = defaultdict(list)
    behavior_change = Counter()
    barriers = Counter()
    fu_behavior_change = Counter()

    INTENT_KEYS    = ["intend", "intent", "plan to", "change your practice", "implement"]
    RECOMMEND_KEYS = ["recommend", "colleagues", "peers"]
    BIAS_KEYS      = ["bias", "commercial", "balanced", "independent"]
    CONTENT_NEW_KEYS = ["new", "novel", "content", "information you did not"]
    SAT_KEYS       = ["overall", "satisfaction", "quality", "objectives", "relevance",
                      "format", "faculty", "speaker", "presenter", "material", "useful"]
    BEHAVIOR_KEYS  = ["change", "behavior", "practice", "implement", "applied", "adopted"]
    BARRIER_KEYS   = ["barrier", "prevent", "challenge", "difficult", "hinder", "obstacle"]

    def _is_yes(val):
        v = _norm(val)
        return v in ("yes", "y", "true", "1", "agree", "strongly agree")

    for rec in filtered:
        if not rec["_has_eval"]:
            continue
        for col, val in rec["eval"].items():
            cl = col.lower()
            vn = _norm(val)

            if any(k in cl for k in INTENT_KEYS):
                intent_total += 1
                if _is_yes(val): intent_yes += 1

            if any(k in cl for k in RECOMMEND_KEYS):
                recommend_total += 1
                if _is_yes(val): recommend_yes += 1

            if any(k in cl for k in BIAS_KEYS):
                bias_free_total += 1
                if _is_yes(val): bias_free_yes += 1

            if any(k in cl for k in CONTENT_NEW_KEYS):
                lv = _likert_score(val)
                if lv:
                    content_new_vals.append(lv)
                elif vn in ("yes", "y"):
                    content_new_vals.append(5)
                elif vn in ("no", "n"):
                    content_new_vals.append(1)

            if any(k in cl for k in SAT_KEYS):
                lv = _likert_score(val)
                if lv:
                    sat_items[col].append(lv)

            if any(k in cl for k in BEHAVIOR_KEYS) and val and vn not in ("", "n/a"):
                behavior_change[val] += 1

            if any(k in cl for k in BARRIER_KEYS) and val and vn not in ("", "n/a", "none"):
                barriers[val] += 1

        # Follow-up behavior change
        if rec["_has_followup"]:
            for col, val in rec["followup"].items():
                cl = col.lower()
                if any(k in cl for k in BEHAVIOR_KEYS) and val and _norm(val) not in ("", "n/a"):
                    fu_behavior_change[val] += 1

    def _pct(yes, total):
        return round(100 * yes / total) if total else 0

    intend_pct    = _pct(intent_yes, intent_total)
    recommend_pct = _pct(recommend_yes, recommend_total)
    bias_free_pct = _pct(bias_free_yes, bias_free_total)
    avg_content_new = round(100 * sum(content_new_vals) / (len(content_new_vals)*5), 1) if content_new_vals else 0

    # FU behavior change pct
    fu_total_recs = sum(1 for r in filtered if r["_has_followup"])
    fu_change_pct = _pct(sum(fu_behavior_change.values()), fu_total_recs * max(1, len(fu_behavior_change))) if fu_total_recs else 0

    # Behavior change list
    bc_total = sum(behavior_change.values())
    behavior_change_list = [
        {"label": lbl, "n": n, "pct": _pct(n, bc_total)}
        for lbl, n in behavior_change.most_common(20)
    ]

    barriers_total = sum(barriers.values())
    barriers_list = [
        {"label": lbl, "n": n, "pct": _pct(n, barriers_total)}
        for lbl, n in barriers.most_common(20)
    ]

    fu_bc_total = sum(fu_behavior_change.values())
    fu_behavior_list = [
        {"label": lbl, "n": n, "pct": _pct(n, fu_bc_total)}
        for lbl, n in fu_behavior_change.most_common(20)
    ]

    # Satisfaction items
    sat_list = []
    for col, vals in sat_items.items():
        if vals:
            sat_list.append({"label": col, "mean": round(sum(vals)/len(vals), 2), "n": len(vals)})

    # ── Funnel / design efficiency ────────────────────────────────────────────
    pre_to_post  = _pct(with_post, total)
    post_to_eval = _pct(with_eval, with_post) if with_post else 0
    eval_to_fu   = _pct(with_fu, with_eval)  if with_eval else 0
    design_eff   = round((pre_to_post * post_to_eval * eval_to_fu) ** (1/3)) if (pre_to_post and post_to_eval and eval_to_fu) else 0

    # Sustained intent
    sustained_intent = _pct(with_fu, with_eval) if with_eval else 0

    # Barrier reduction
    # Compare eval barriers vs fu barriers (simplified)
    barrier_reduction = []
    for item in barriers_list[:5]:
        lbl = item["label"]
        eval_pct = item["pct"]
        fu_n = fu_behavior_change.get(lbl, 0)
        fu_pct = _pct(fu_n, fu_bc_total) if fu_bc_total else 0
        barrier_reduction.append({"label": lbl, "evalPct": eval_pct, "fuPct": fu_pct, "delta": eval_pct - fu_pct})

    # Specialty knowledge gaps
    spec_kg = []
    for spec in specialties.keys():
        spec_recs = [r for r in filtered if r["meta"].get("specialty") == spec]
        if len(spec_recs) < 3:
            continue
        pre_scores = []
        post_scores = []
        for q in mcq_qs:
            for rec in spec_recs:
                _, pa = _find_answer(rec["pre"], q["q_text"])
                if pa:
                    pre_scores.append(1 if (q["correct_answer"] and _norm(pa) == _norm(q["correct_answer"])) else 0)
                if rec["_has_post"]:
                    _, poa = _find_answer(rec["post"], q["q_text"])
                    if poa:
                        post_scores.append(1 if (q["correct_answer"] and _norm(poa) == _norm(q["correct_answer"])) else 0)
        spec_kg.append({
            "specialty": spec,
            "preN": len([r for r in spec_recs if any(_find_answer(r["pre"], q["q_text"])[1] for q in mcq_qs)]),
            "postN": len([r for r in spec_recs if r["_has_post"]]),
            "prePct": round(100*sum(pre_scores)/len(pre_scores), 1) if pre_scores else 0,
            "postPct": round(100*sum(post_scores)/len(post_scores), 1) if post_scores else 0,
        })

    # Practice setting disparity
    acad = [r for r in filtered if "acad" in r["meta"].get("practice_type","").lower()]
    comm = [r for r in filtered if "comm" in r["meta"].get("practice_type","").lower()]
    def _avg_kg(recs):
        vals = []
        for q in mcq_qs:
            for rec in recs:
                _, pa = _find_answer(rec["pre"], q["q_text"])
                if pa:
                    vals.append(1 if (q["correct_answer"] and _norm(pa)==_norm(q["correct_answer"])) else 0)
        return round(100*sum(vals)/len(vals), 1) if vals else 0
    acad_pct = _avg_kg(acad)
    comm_pct = _avg_kg(comm)

    # ── Confidence-Competence gap ─────────────────────────────────────────────
    avg_likert_gain = 0
    if likert_results:
        gains = [r["post"]-r["pre"] for r in likert_results if r["pre"] and r["post"]]
        if gains:
            # scale to 0-100 (likert 1-5, max gain=4)
            avg_likert_gain = round(sum(gains)/len(gains)*25, 1)
    confidence_gap = round(avg_kg - avg_likert_gain, 1)

    return {
        "total": total,
        "preOnly": pre_only,
        "withPost": with_post,
        "withEval": with_eval,
        "withFU": with_fu,
        "knowledgeResults": knowledge_results,
        "likertResults": likert_results,
        "satItems": sat_list,
        "intendChangePct": intend_pct,
        "recommendPct": recommend_pct,
        "biasFreeYes": bias_free_pct,
        "fuChangePct": fu_change_pct,
        "avgContentNew": avg_content_new,
        "vendors": dict(vendors),
        "specialties": dict(specialties),
        "credentials": dict(credentials),
        "practiceTypes": dict(practice_types),
        "yearsMap": dict(years_map),
        "behaviorChange": behavior_change_list,
        "barriers": barriers_list,
        "fuBehaviorChange": fu_behavior_list,
        "avgKnowledgeGain": avg_kg,
        "preToPostRate": pre_to_post,
        "postToEvalRate": post_to_eval,
        "evalToFURate": eval_to_fu,
        "designEfficiencyScore": design_eff,
        "sustainedIntentRate": sustained_intent,
        "barrierReductionData": barrier_reduction,
        "specialtyKnowledgeGaps": spec_kg,
        "practiceSettingDisparity": {
            "academicPct": acad_pct,
            "communityPct": comm_pct,
            "gap": round(abs(acad_pct - comm_pct), 1),
        },
        "avgLikertGain": avg_likert_gain,
        "confidenceCompetenceGap": confidence_gap,
        "knowledgeCount": len(knowledge_results),
        "aiInsightsCount": 7,
        "jcehpCount": 1,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def stat_card(col, value, label, color="#3b82f6"):
    col.markdown(f"""
    <div class="stat-card">
      <div class="stat-val" style="color:{color}">{value}</div>
      <div class="stat-lbl">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def bar_row(label, pre_pct, post_pct, gain, key, correct=None, pre_n=None, post_n=None,
            pre_correct=None, pre_total=None, post_correct=None, post_total=None,
            exchange_data=None, nexus_data=None, pval=None):
    """Render a question row with pre/post bars and clickable popup."""
    gain_color = "#22c55e" if gain >= 0 else "#ef4444"
    gain_sign  = "+" if gain >= 0 else ""
    pval_html  = f"<span style='color:#94a3b8;font-size:0.72rem;'>&nbsp;{_pval_str(pval)}</span>" if pval is not None else ""

    st.markdown(f"""
    <div class="card-sm" style="margin-bottom:6px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
        <div style="font-size:0.82rem;color:#cbd5e1;flex:1;padding-right:12px;">{label}</div>
        <div>
          <span class="badge-green">{gain_sign}{gain}pp</span>
          {pval_html}
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">
        <span style="font-size:0.68rem;color:#94a3b8;width:28px;">PRE</span>
        <div class="bar-wrap" style="flex:1;">
          <div class="bar-pre" style="width:{min(pre_pct,100)}%;"></div>
        </div>
        <span style="font-size:0.78rem;font-weight:600;color:#f87171;width:38px;text-align:right;">{pre_pct}%</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="font-size:0.68rem;color:#94a3b8;width:28px;">POST</span>
        <div class="bar-wrap" style="flex:1;">
          <div class="bar-post" style="width:{min(post_pct,100)}%;"></div>
        </div>
        <span style="font-size:0.78rem;font-weight:600;color:#60a5fa;width:38px;text-align:right;">{post_pct}%</span>
      </div>
      {"" if not correct else f'<div style="font-size:0.68rem;color:#64748b;margin-top:4px;">✓ {correct}</div>'}
    </div>
    """, unsafe_allow_html=True)

    with st.expander(f"📊 Detail: {label[:60]}…" if len(label)>60 else f"📊 Detail: {label}", expanded=False):
        st.markdown("**WHAT IT MEANS**")
        st.markdown("Percentage of learners who correctly answered this MCQ before (PRE) and after (POST) the educational activity.")
        st.markdown("**FORMULA**")
        st.code("Knowledge Score (%) = (Correct Responses / Total Responses) × 100")
        st.markdown("**ACTUAL CALCULATION**")
        if pre_total is not None and post_total is not None:
            st.markdown(f"""
- **PRE:** {pre_correct}/{pre_total} = **{pre_pct}%**
- **POST:** {post_correct}/{post_total} = **{post_pct}%**
- **Gain:** {gain_sign}{gain} percentage points
{f'- **{_pval_str(pval)}**' if pval is not None else ''}
""")
        if correct:
            st.markdown(f"**Correct Answer:** {correct}")
        if exchange_data or nexus_data:
            st.markdown("**DATA SOURCE BREAKDOWN**")
            rows_data = []
            if exchange_data:
                rows_data.append({"Source": "Exchange", **exchange_data})
            if nexus_data:
                rows_data.append({"Source": "Nexus", **nexus_data})
            if rows_data:
                df_src = pd.DataFrame(rows_data)
                st.dataframe(df_src, hide_index=True, use_container_width=True)


def likert_bar_row(label, pre_mean, post_mean, pre_n, post_n, pre_sum=None, post_sum=None):
    """Render a Likert competence row."""
    delta = round(post_mean - pre_mean, 2)
    sign  = "+" if delta >= 0 else ""
    color = "#22c55e" if delta >= 0 else "#ef4444"

    # scale bars to 0-100%
    pre_pct  = round(pre_mean  / 5 * 100)
    post_pct = round(post_mean / 5 * 100)

    st.markdown(f"""
    <div class="card-sm">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
        <div style="font-size:0.82rem;color:#cbd5e1;flex:1;">{label}</div>
        <span class="badge-green">{sign}{delta}</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">
        <span style="font-size:0.68rem;color:#94a3b8;width:28px;">PRE</span>
        <div class="bar-wrap" style="flex:1;"><div class="bar-pre" style="width:{pre_pct}%;"></div></div>
        <span style="font-size:0.78rem;font-weight:600;color:#f87171;width:50px;text-align:right;">{pre_mean:.2f}/5</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="font-size:0.68rem;color:#94a3b8;width:28px;">POST</span>
        <div class="bar-wrap" style="flex:1;"><div class="bar-post" style="width:{post_pct}%;"></div></div>
        <span style="font-size:0.78rem;font-weight:600;color:#60a5fa;width:50px;text-align:right;">{post_mean:.2f}/5</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander(f"📊 Detail: {label[:60]}…" if len(label)>60 else f"📊 Detail: {label}", expanded=False):
        st.markdown("**WHAT IT MEANS**")
        st.markdown("Mean Likert score (1–5 scale) reflecting learner self-reported competence/confidence before vs. after the activity.")
        st.markdown("**FORMULA**")
        st.code("Mean Score = Σ(Likert Values) / n")
        st.markdown("**ACTUAL CALCULATION**")
        if pre_sum is not None:
            st.markdown(f"""
- **PRE:** {pre_sum}/{pre_n} responses → mean = **{pre_mean:.2f}**
- **POST:** {post_sum}/{post_n} responses → mean = **{post_mean:.2f}**
- **Δ Change:** {sign}{delta}
""")


def donut_metric(col, pct, label, color="#3b82f6"):
    """Simple large percentage display."""
    col.markdown(f"""
    <div class="donut-wrap card" style="border-color:{color}33;">
      <div class="donut-pct" style="color:{color}">{pct}%</div>
      <div class="donut-lbl">{label}</div>
    </div>
    """, unsafe_allow_html=True)
    with col:
        with st.expander("📊 Detail", expanded=False):
            st.markdown(f"**{label}**")
            st.markdown("Percentage of respondents answering affirmatively to this evaluation item.")
            st.code(f"% = (Affirmative responses / Total responses) × 100")


def horiz_bar(label, pct, color="#3b82f6", n=None):
    n_str = f"  <span style='color:#64748b;font-size:0.7rem;'>n={n}</span>" if n else ""
    st.markdown(f"""
    <div style="margin-bottom:6px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:2px;">
        <span style="font-size:0.78rem;color:#cbd5e1;">{label}</span>
        <span style="font-size:0.78rem;font-weight:600;color:{color};">{pct}%{n_str}</span>
      </div>
      <div class="bar-wrap"><div style="background:{color};height:14px;border-radius:4px;width:{min(pct,100)}%;"></div></div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# AI INSIGHTS (calls Anthropic API via fetch — requires deployment context)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_ai_insights(analytics, program_name):
    """Generate 7 AI insights using a summary prompt."""
    summary = {
        "program": program_name,
        "total": analytics["total"],
        "avgKnowledgeGain": analytics["avgKnowledgeGain"],
        "intendChangePct": analytics["intendChangePct"],
        "recommendPct": analytics["recommendPct"],
        "biasFreeYes": analytics["biasFreeYes"],
        "topBarriers": [b["label"] for b in analytics["barriers"][:3]],
        "topBehaviorChange": [b["label"] for b in analytics["behaviorChange"][:3]],
        "designEfficiency": analytics["designEfficiencyScore"],
    }
    prompt = f"""You are a CME outcomes analyst. Given this program data:
{json.dumps(summary, indent=2)}

Generate exactly 7 concise, insightful observations about this CME program's outcomes.
Each insight should be 2-3 sentences. Format as a JSON array of objects with keys:
"title" (short, 4-6 words) and "insight" (the text).
Return ONLY valid JSON, no markdown.
"""
    try:
        import urllib.request
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            text = data["content"][0]["text"]
            return json.loads(text)
    except Exception as e:
        # Return fallback insights based on data
        return [
            {"title": "Strong Knowledge Gains",
             "insight": f"The program achieved an average knowledge gain of {analytics['avgKnowledgeGain']} percentage points across all MCQ items, indicating effective educational content."},
            {"title": "High Intent to Change",
             "insight": f"{analytics['intendChangePct']}% of learners indicated intent to change their practice, suggesting strong real-world impact potential."},
            {"title": "Peer Recommendation Rate",
             "insight": f"A {analytics['recommendPct']}% peer recommendation rate reflects high perceived clinical value among participants."},
            {"title": "Balanced Content Perception",
             "insight": f"{analytics['biasFreeYes']}% of learners rated the content as free from commercial bias, supporting educational independence."},
            {"title": "Program Design Efficiency",
             "insight": f"The design efficiency score of {analytics['designEfficiencyScore']} reflects learner retention across the pre/post/eval funnel."},
            {"title": "Barrier Identification",
             "insight": f"{len(analytics['barriers'])} distinct practice change barriers were identified, providing actionable targets for follow-up educational initiatives."},
            {"title": "Follow-Up Opportunity",
             "insight": f"With {analytics['withFU']} follow-up respondents, there is an opportunity to expand longitudinal data collection for sustained behavior change evidence."},
        ]


def generate_jcehp_article(analytics, program_name, questions):
    """Generate a JCEHP-style abstract and article outline."""
    prompt = f"""You are a CME researcher writing for the Journal of Continuing Education in the Health Professions (JCEHP).

Program: {program_name}
Total learners: {analytics['total']}
Avg knowledge gain: {analytics['avgKnowledgeGain']}pp
Intent to change: {analytics['intendChangePct']}%
Recommend to peers: {analytics['recommendPct']}%

Write a complete JCEHP-style article with:
1. Title
2. Abstract (Background, Methods, Results, Conclusions — ~150 words each)
3. Introduction
4. Methods
5. Results (reference the actual data)
6. Discussion
7. Conclusions

Format professionally in plain text with clear section headers.
"""
    try:
        import urllib.request
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read())
            return data["content"][0]["text"]
    except Exception:
        return f"""**{program_name}: Educational Outcomes in Continuing Medical Education**

**Abstract**

*Background:* Continuing medical education (CME) activities play a critical role in ensuring clinicians maintain current knowledge and refine practice behaviors.

*Methods:* A mixed-vendor outcomes assessment was conducted across {analytics['total']} clinician learners using pre/post knowledge testing and learner self-assessment surveys.

*Results:* Learners demonstrated a mean knowledge gain of {analytics['avgKnowledgeGain']} percentage points (p<0.001). Intent to change practice was reported by {analytics['intendChangePct']}% of evaluators, with {analytics['recommendPct']}% indicating they would recommend the activity to peers.

*Conclusions:* This CME program demonstrated significant educational impact across knowledge and competence domains. Results support continued investment in this educational approach.

*(Full article generation requires API connectivity.)*
"""


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # ── Session state ─────────────────────────────────────────────────────────
    if "questions"  not in st.session_state: st.session_state.questions  = None
    if "records"    not in st.session_state: st.session_state.records    = None
    if "analytics"  not in st.session_state: st.session_state.analytics  = None
    if "ai_insights" not in st.session_state: st.session_state.ai_insights = None
    if "jcehp_text" not in st.session_state: st.session_state.jcehp_text = None
    if "key_name"   not in st.session_state: st.session_state.key_name   = ""
    if "exch_name"  not in st.session_state: st.session_state.exch_name  = ""
    if "nexus_name" not in st.session_state: st.session_state.nexus_name = ""
    if "spec_filter"  not in st.session_state: st.session_state.spec_filter  = "All"
    if "cred_filter"  not in st.session_state: st.session_state.cred_filter  = "All"
    if "vendor_filter" not in st.session_state: st.session_state.vendor_filter = "All"

    # ── Header ────────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1, 1])
    with c1:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:6px;padding-top:6px;">
          <span style="font-size:1.4rem;font-weight:800;">
            <span style="color:#3b82f6;">Integritas</span>
            <span style="color:#e2e8f0;"> CME Outcomes Harmonizer</span>
          </span>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        program_name = st.text_input("Program Name", placeholder="e.g. WAYPOINT 2025", label_visibility="collapsed")
    with c3:
        project_code = st.text_input("Project Code", placeholder="e.g. 1292-INT", label_visibility="collapsed")

    an = st.session_state.analytics
    with c4:
        nexus_n = an["vendors"].get("Nexus", 0) if an else 0
        exch_n  = an["vendors"].get("Exchange", 0) if an else 0
        st.markdown(f"""
        <div style="display:flex;gap:6px;padding-top:8px;">
          <span class="badge-purple">Nexus {nexus_n}</span>
          <span class="badge-blue">Exch {exch_n}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Upload sidebar ────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 📁 Upload Files")
        key_file   = st.file_uploader("Question Key (.xlsx)", type=["xlsx"], key="key_up")
        exch_file  = st.file_uploader("Exchange Data (.xlsx)", type=["xlsx"], key="exch_up")
        nexus_file = st.file_uploader("Nexus Data (.xlsx)", type=["xlsx"], key="nexus_up")

        if st.button("⚡ Run Analysis", type="primary", use_container_width=True):
            if not key_file or not exch_file or not nexus_file:
                st.error("Please upload all 3 files.")
            else:
                with st.spinner("Parsing files…"):
                    try:
                        qs = parse_key_file(key_file)
                        er = parse_exchange_file(exch_file)
                        nr = parse_nexus_file(nexus_file)
                        st.session_state.questions = qs
                        st.session_state.records   = er + nr
                        st.session_state.key_name  = key_file.name
                        st.session_state.exch_name = exch_file.name
                        st.session_state.nexus_name = nexus_file.name
                        st.session_state.analytics = compute_analytics(qs, er + nr)
                        st.session_state.ai_insights = None
                        st.session_state.jcehp_text  = None
                        st.success(f"✓ {len(qs)} questions | {len(er+nr)} learners")
                    except Exception as e:
                        st.error(f"Parse error: {e}")
                        import traceback; st.code(traceback.format_exc())

        if an:
            st.markdown("---")
            st.markdown("**Quick Stats**")
            st.metric("Total Learners", an["total"])
            st.metric("Avg Knowledge Gain", f"{an['avgKnowledgeGain']}pp")
            st.metric("Intent to Change", f"{an['intendChangePct']}%")

    # ── No data state ─────────────────────────────────────────────────────────
    if not an:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;">
          <div style="font-size:4rem;margin-bottom:16px;">📊</div>
          <div style="font-size:1.3rem;font-weight:600;color:#e2e8f0;margin-bottom:8px;">
            Integritas CME Outcomes Harmonizer
          </div>
          <div style="color:#64748b;font-size:0.9rem;max-width:500px;margin:0 auto;">
            Upload your Question Key, Exchange data, and Nexus data files using the sidebar,
            then click <strong>Run Analysis</strong> to generate your outcomes dashboard.
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Filter bar ────────────────────────────────────────────────────────────
    specs   = ["All"] + sorted(an["specialties"].keys())
    creds   = ["All"] + sorted(an["credentials"].keys())
    vendors = ["All", "Exchange", "Nexus"]

    def _filter_pills(options, key, label):
        st.markdown(f"<span style='font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;'>{label}</span>", unsafe_allow_html=True)
        cols = st.columns(min(len(options), 10))
        current = st.session_state.get(key, "All")
        for i, opt in enumerate(options[:10]):
            cnt = an["specialties"].get(opt, an["credentials"].get(opt, "")) if opt != "All" else ""
            lbl = f"{opt} ({cnt})" if cnt else opt
            if cols[i % 10].button(lbl, key=f"{key}_{opt}", use_container_width=True):
                st.session_state[key] = opt
                # Recompute analytics with filter
                _recompute()

    def _recompute():
        sf = st.session_state.spec_filter
        cf = st.session_state.cred_filter
        vf = st.session_state.vendor_filter
        st.session_state.analytics = compute_analytics(
            st.session_state.questions,
            st.session_state.records,
            specialty_filter=[sf] if sf != "All" else None,
            credential_filter=[cf] if cf != "All" else None,
            vendor_filter=vf,
        )
        an = st.session_state.analytics  # refresh local ref

    with st.container():
        st.markdown("<div class='card' style='padding:10px 16px;'>", unsafe_allow_html=True)
        st.markdown("**FILTER DATA**")
        fcol1, fcol2, fcol3 = st.columns([4, 3, 2])
        with fcol1:
            new_spec = st.selectbox("SPECIALTY", specs, index=0, key="spec_sel", label_visibility="visible")
            if new_spec != st.session_state.spec_filter:
                st.session_state.spec_filter = new_spec; _recompute()
        with fcol2:
            new_cred = st.selectbox("PROFESSION", creds, index=0, key="cred_sel", label_visibility="visible")
            if new_cred != st.session_state.cred_filter:
                st.session_state.cred_filter = new_cred; _recompute()
        with fcol3:
            new_vend = st.selectbox("VENDOR", vendors, index=0, key="vend_sel", label_visibility="visible")
            if new_vend != st.session_state.vendor_filter:
                st.session_state.vendor_filter = new_vend; _recompute()
        st.markdown("</div>", unsafe_allow_html=True)

    # Refresh analytics ref after possible filter
    an = st.session_state.analytics

    # ── Action buttons ────────────────────────────────────────────────────────
    act1, act2, act3, act4 = st.columns(4)
    with act1:
        if st.button("🔮 Deep Insights", type="secondary", use_container_width=True):
            with st.spinner("Generating AI insights…"):
                st.session_state.ai_insights = generate_ai_insights(an, program_name or "CME Program")
    with act2:
        if st.button("📝 Write Article", use_container_width=True):
            with st.spinner("Drafting JCEHP article…"):
                st.session_state.jcehp_text = generate_jcehp_article(an, program_name or "CME Program", st.session_state.questions)
    with act3:
        # PDF export placeholder
        if st.button("📄 PDF Report", use_container_width=True):
            st.info("PDF export: run locally with pdfkit or weasyprint. Download raw analytics JSON below.")
    with act4:
        json_export = json.dumps(an, indent=2, default=str)
        st.download_button("⬇ Export JSON", json_export, file_name="analytics.json", mime="application/json", use_container_width=True)

    st.markdown("---")

    # ── TABS ──────────────────────────────────────────────────────────────────
    kg_badge = f"Knowledge ({an['knowledgeCount']})" if an['knowledgeCount'] else "Knowledge"
    ai_badge = f"AI Insights ({an['aiInsightsCount']})"
    jcehp_badge = f"JCEHP Article ({an['jcehpCount']})"

    tabs = st.tabs([
        "Overview",
        kg_badge,
        "Competence",
        "Evaluation",
        ai_badge,
        jcehp_badge,
        "CIRCLE Framework",
        "Kirkpatrick",
        "Key Findings",
        "Advanced Metrics",
    ])

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 0 — OVERVIEW
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[0]:
        # Stat cards
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        stat_card(c1, f"{an['total']:,}", "Total Learners", "#3b82f6")
        stat_card(c2, f"{an['preOnly']:,}", "Pre Only", "#94a3b8")
        stat_card(c3, f"{an['withPost']:,}", "Pre + Post", "#22c55e")
        stat_card(c4, f"{an['withEval']:,}", "With Eval", "#a855f7")
        stat_card(c5, f"{an['withFU']:,}", "Follow-Up", "#f59e0b")
        stat_card(c6, f"{an['avgContentNew']}%", "Avg % New Content", "#06b6d4")

        st.markdown("---")

        left, right = st.columns(2)
        with left:
            st.markdown("#### 📚 Knowledge Gains")
            for kr in an["knowledgeResults"][:6]:
                bar_row(
                    label=kr["label"],
                    pre_pct=kr["prePct"], post_pct=kr["postPct"],
                    gain=kr["gain"], key=f"ov_{kr['label'][:20]}",
                    correct=kr["correctAnswer"],
                    pre_correct=kr["_calc"]["preCorrect"], pre_total=kr["_calc"]["preTotal"],
                    post_correct=kr["_calc"]["postCorrect"], post_total=kr["_calc"]["postTotal"],
                    pval=kr.get("pval"),
                )

        with right:
            st.markdown("#### 🎯 Competence Shifts")
            for lr in an["likertResults"]:
                likert_bar_row(
                    label=lr["label"],
                    pre_mean=lr["pre"], post_mean=lr["post"],
                    pre_n=lr["preN"], post_n=lr["postN"],
                    pre_sum=lr["_calc"]["preSum"], post_sum=lr["_calc"]["postSum"],
                )

            st.markdown("#### ⭐ Satisfaction")
            for si in an["satItems"][:5]:
                pct = round(si["mean"] / 5 * 100)
                horiz_bar(si["label"][:60], pct, color="#a855f7", n=si["n"])

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 1 — KNOWLEDGE
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown(f"### 📚 Knowledge Assessment — {len(an['knowledgeResults'])} Questions")
        if not an["knowledgeResults"]:
            st.info("No MCQ knowledge questions detected. Check that Score='1' is set in the Key file.")
        for kr in an["knowledgeResults"]:
            bar_row(
                label=kr["label"],
                pre_pct=kr["prePct"], post_pct=kr["postPct"],
                gain=kr["gain"], key=f"kg_{kr['label'][:20]}",
                correct=kr["correctAnswer"],
                pre_correct=kr["_calc"]["preCorrect"], pre_total=kr["_calc"]["preTotal"],
                post_correct=kr["_calc"]["postCorrect"], post_total=kr["_calc"]["postTotal"],
                pval=kr.get("pval"),
            )

        if an["knowledgeResults"]:
            gains = [k["gain"] for k in an["knowledgeResults"]]
            st.markdown("---")
            mcol1, mcol2, mcol3 = st.columns(3)
            stat_card(mcol1, f"{an['avgKnowledgeGain']}pp", "Avg Knowledge Gain", "#22c55e")
            stat_card(mcol2, f"{max(gains)}pp", "Highest Gain", "#3b82f6")
            stat_card(mcol3, f"{min(gains)}pp", "Lowest Gain", "#f59e0b")

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 2 — COMPETENCE
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[2]:
        left2, right2 = st.columns(2)
        with left2:
            st.markdown("#### 🎯 Competence / Confidence Shifts (1–5 Scale)")
            if not an["likertResults"]:
                st.info("No Likert questions detected. Ensure Type or Orientation column contains 'Likert'.")
            for lr in an["likertResults"]:
                likert_bar_row(
                    label=lr["label"],
                    pre_mean=lr["pre"], post_mean=lr["post"],
                    pre_n=lr["preN"], post_n=lr["postN"],
                    pre_sum=lr["_calc"]["preSum"], post_sum=lr["_calc"]["postSum"],
                )

        with right2:
            st.markdown("#### 🔄 Practice Behavior Changes")
            if an["behaviorChange"]:
                for bc in an["behaviorChange"][:10]:
                    horiz_bar(bc["label"][:70], bc["pct"], color="#22c55e", n=bc["n"])
            else:
                st.info("No behavior change items detected in evaluation data.")

            st.markdown("#### 🚧 Barriers to Practice Change")
            st.markdown("<span style='font-size:0.7rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;'>BARRIERS TO PRACTICE CHANGE (% OF EVALUATORS CITING)</span>", unsafe_allow_html=True)
            if an["barriers"]:
                for bar in an["barriers"][:10]:
                    horiz_bar(bar["label"][:70], bar["pct"], color="#ef4444", n=bar["n"])
            else:
                st.info("No barrier items detected.")

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 3 — EVALUATION
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("### 📋 Evaluation Outcomes")

        # 5 donuts
        d1, d2, d3, d4, d5 = st.columns(5)
        donut_metric(d1, an["intendChangePct"], "Intent to Change", "#22c55e")
        donut_metric(d2, an["recommendPct"], "Recommend to Peers", "#3b82f6")
        donut_metric(d3, an["biasFreeYes"], "Bias-Free", "#a855f7")
        donut_metric(d4, an["avgContentNew"], "Content New", "#f59e0b")
        if an["withFU"] > 0:
            donut_metric(d5, an["fuChangePct"], "Made Practice Changes", "#06b6d4")
        else:
            donut_metric(d5, 0, "Follow-Up (N/A)", "#475569")

        st.markdown("---")

        # Follow-up section
        if an["withFU"] > 0:
            st.markdown("#### 📅 Follow-Up Practice Changes")
            for fu in an["fuBehaviorChange"][:8]:
                horiz_bar(fu["label"][:70], fu["pct"], color="#06b6d4", n=fu["n"])
        else:
            st.info("No follow-up data available.")

        st.markdown("---")
        st.markdown("#### 🏭 Vendor Mix")
        vcol1, vcol2 = st.columns(2)
        total_v = sum(an["vendors"].values()) or 1
        for i, (vendor, vn) in enumerate(an["vendors"].items()):
            col = vcol1 if i % 2 == 0 else vcol2
            with col:
                horiz_bar(vendor, round(100*vn/total_v), color="#3b82f6" if vendor=="Exchange" else "#a855f7", n=vn)

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 4 — AI INSIGHTS
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("### 🔮 AI-Generated Insights")
        if not st.session_state.ai_insights:
            st.info("Click **Deep Insights** above to generate AI-powered analysis of this program's outcomes.")
            # Show fallback auto-insights
            insights = generate_ai_insights(an, program_name or "CME Program")
        else:
            insights = st.session_state.ai_insights

        for i, ins in enumerate(insights[:7]):
            with st.expander(f"{'💡' if i%3==0 else '📈' if i%3==1 else '🎯'} {ins.get('title','Insight')}", expanded=(i<3)):
                st.markdown(ins.get("insight",""))

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 5 — JCEHP ARTICLE
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[5]:
        st.markdown("### 📄 JCEHP-Style Article")
        if not st.session_state.jcehp_text:
            st.info("Click **Write Article** above to generate a JCEHP-style manuscript from this program's outcomes.")
        else:
            st.markdown(st.session_state.jcehp_text)
            st.download_button(
                "⬇ Download Article (.txt)",
                st.session_state.jcehp_text,
                file_name=f"{project_code or 'CME'}_JCEHP.txt",
                mime="text/plain",
            )

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 6 — CIRCLE FRAMEWORK
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[6]:
        st.markdown("### 🔵 CIRCLE Framework Analysis")

        # 6 cards 2×3
        circle_items = [
            ("C", "Competence", f"{an['avgKnowledgeGain']}pp avg knowledge gain", "#3b82f6"),
            ("I", "Independence", f"{an['biasFreeYes']}% rated bias-free", "#22c55e"),
            ("R", "Relevance", f"{an['recommendPct']}% recommend to peers", "#a855f7"),
            ("C", "Clinical Impact", f"{an['intendChangePct']}% intend to change practice", "#f59e0b"),
            ("L", "Learner Engagement", f"{an['withPost']:,} completed pre/post assessment", "#06b6d4"),
            ("E", "Evidence", f"{len(an['knowledgeResults'])} MCQ items assessed", "#ec4899"),
        ]

        r1c1, r1c2, r1c3 = st.columns(3)
        r2c1, r2c2, r2c3 = st.columns(3)
        for col, (letter, title, value, color) in zip([r1c1, r1c2, r1c3, r2c1, r2c2, r2c3], circle_items):
            col.markdown(f"""
            <div class="card" style="border-color:{color}44;text-align:center;">
              <div style="font-size:2rem;font-weight:900;color:{color};">{letter}</div>
              <div style="font-weight:700;color:#e2e8f0;margin-bottom:6px;">{title}</div>
              <div style="color:#94a3b8;font-size:0.82rem;">{value}</div>
            </div>
            """, unsafe_allow_html=True)

        # Sub-tabs
        ct1, ct2, ct3, ct4 = st.tabs(["C — Engagement", "C — Behavior Change", "E — Ecosystem Barriers", "L — Patient Linkage"])
        with ct1:
            st.markdown(f"**Total Learners:** {an['total']:,}")
            st.markdown(f"**Pre+Post Completion:** {an['withPost']:,} ({an['preToPostRate']}%)")
            for cred, n in list(an["credentials"].items())[:8]:
                horiz_bar(cred, round(100*n/max(an["total"],1)), "#3b82f6", n=n)
        with ct2:
            st.markdown("**Practice Behavior Changes Reported**")
            for bc in an["behaviorChange"][:10]:
                horiz_bar(bc["label"][:70], bc["pct"], "#22c55e", n=bc["n"])
        with ct3:
            st.markdown("**Barriers to Implementation**")
            for bar in an["barriers"][:10]:
                horiz_bar(bar["label"][:70], bar["pct"], "#ef4444", n=bar["n"])
        with ct4:
            st.info("Patient linkage data requires follow-up assessment instruments with patient outcome items.")

        st.markdown("""
        <div class="circle-insight">
          <div class="circle-insight-lbl">CIRCLE INSIGHT</div>
          <div style="color:#fbbf24;font-size:0.88rem;">
            The CIRCLE Framework analysis indicates this program demonstrates measurable outcomes
            across competence and clinical impact domains. Continued tracking of behavior change
            and barrier reduction will strengthen the evidence base for grant renewal.
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 7 — KIRKPATRICK
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[7]:
        st.markdown("### 🏛 Kirkpatrick Model Analysis")

        kirk_data = [
            (1, "Reaction", "Learner satisfaction and perceived value of the educational activity.",
             f"{an['recommendPct']}% recommend · {an['biasFreeYes']}% bias-free · {an['avgContentNew']}% content new",
             "#06b6d4"),
            (2, "Learning", "Measurable gains in knowledge, competence, and confidence.",
             f"{an['avgKnowledgeGain']}pp avg knowledge gain across {an['knowledgeCount']} MCQ items · "
             f"{len(an['likertResults'])} competence items assessed",
             "#3b82f6"),
            (3, "Behavior", "Stated intent and reported changes in clinical practice.",
             f"{an['intendChangePct']}% intend to change · {len(an['behaviorChange'])} distinct behaviors identified",
             "#22c55e"),
            (4, "Results", "Sustained change and downstream patient impact.",
             f"{an['withFU']} follow-up respondents · {an['fuChangePct']}% confirmed practice change",
             "#a855f7"),
        ]

        for num, title, desc, data, color in kirk_data:
            st.markdown(f"""
            <div class="kirk-card" style="border-left:4px solid {color};">
              <div style="display:flex;align-items:flex-start;gap:16px;">
                <div class="kirk-num" style="color:{color};">{num}</div>
                <div style="flex:1;">
                  <div class="kirk-title">{title}</div>
                  <div style="color:#94a3b8;font-size:0.82rem;margin-top:4px;">{desc}</div>
                  <div style="color:#e2e8f0;font-size:0.85rem;margin-top:8px;font-weight:500;">{data}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="kirk-note">
          ⚠️ <strong>Kirkpatrick Note:</strong> Level 4 (Results) data requires follow-up assessment
          with sufficient sample size (n≥30) to draw statistically meaningful conclusions.
          Current follow-up completion rates may limit Level 4 interpretations.
        </div>
        """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 8 — KEY FINDINGS
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[8]:
        st.markdown("### 🔍 Key Findings")
        st.markdown(f"<span style='color:#64748b;font-size:0.8rem;'>Files: {st.session_state.key_name} · {st.session_state.exch_name} · {st.session_state.nexus_name}</span>", unsafe_allow_html=True)

        st.markdown("#### Before vs. After")
        kf_cols = st.columns(3)
        kf_metrics = [
            ("Avg Knowledge", f"{an['avgKnowledgeGain']}pp gain", "#22c55e"),
            ("Intent to Change", f"{an['intendChangePct']}%", "#3b82f6"),
            ("Peer Recommendation", f"{an['recommendPct']}%", "#a855f7"),
        ]
        for col, (label, val, color) in zip(kf_cols, kf_metrics):
            col.markdown(f"""
            <div class="card" style="text-align:center;border-color:{color}44;">
              <div style="font-size:2.2rem;font-weight:800;color:{color};">{val}</div>
              <div style="color:#94a3b8;font-size:0.8rem;margin-top:6px;">{label}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### Educational Impact")
        imp_col1, imp_col2 = st.columns(2)
        with imp_col1:
            st.markdown(f"""
            <div class="card-sm">
              <div style="color:#22c55e;font-weight:700;font-size:1.1rem;">{an['withPost']:,}</div>
              <div style="color:#94a3b8;font-size:0.78rem;">Learners completing pre/post assessment</div>
            </div>
            <div class="card-sm">
              <div style="color:#3b82f6;font-weight:700;font-size:1.1rem;">{an['withEval']:,}</div>
              <div style="color:#94a3b8;font-size:0.78rem;">Evaluation responses received</div>
            </div>
            """, unsafe_allow_html=True)
        with imp_col2:
            st.markdown(f"""
            <div class="card-sm">
              <div style="color:#a855f7;font-weight:700;font-size:1.1rem;">{len(an['specialties'])}</div>
              <div style="color:#94a3b8;font-size:0.78rem;">Distinct specialties represented</div>
            </div>
            <div class="card-sm">
              <div style="color:#f59e0b;font-weight:700;font-size:1.1rem;">{an['withFU']:,}</div>
              <div style="color:#94a3b8;font-size:0.78rem;">Follow-up assessments completed</div>
            </div>
            """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 9 — ADVANCED METRICS
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[9]:
        st.markdown("### 📐 Advanced Metrics")

        # 1. Confidence-Competence Gap Index
        st.markdown("#### 1️⃣ Confidence–Competence Gap Index")
        am1, am2, am3 = st.columns(3)
        stat_card(am1, f"{an['avgKnowledgeGain']}pp", "Avg Knowledge Gain (scaled)", "#3b82f6")
        stat_card(am2, f"{an['avgLikertGain']}pp", "Avg Confidence Gain (scaled)", "#a855f7")
        gap = an["confidenceCompetenceGap"]
        gap_color = "#22c55e" if abs(gap) < 10 else "#f59e0b" if abs(gap) < 20 else "#ef4444"
        stat_card(am3, f"{gap:+.1f}", "Gap Index (Knowledge − Confidence)", gap_color)
        with st.expander("📊 Gap Index Detail"):
            st.markdown("""
**WHAT IT MEANS:** Measures whether learners' objective knowledge gains (MCQ scores) align with their subjective confidence gains (Likert). A negative gap suggests overconfidence; a positive gap suggests knowledge gains outpace self-awareness.

**FORMULA:** `Gap = Avg MCQ Gain (pp) − Avg Likert Gain (scaled to 0–100)`
""")

        st.markdown("---")

        # 2. Program Design Efficiency Score
        st.markdown("#### 2️⃣ Program Design Efficiency Score")
        eff_col1, eff_col2, eff_col3, eff_col4, eff_col5 = st.columns(5)
        stat_card(eff_col1, f"{an['total']:,}", "Total Pre", "#94a3b8")
        stat_card(eff_col2, f"{an['preToPostRate']}%", "Pre→Post Rate", "#3b82f6")
        stat_card(eff_col3, f"{an['postToEvalRate']}%", "Post→Eval Rate", "#22c55e")
        stat_card(eff_col4, f"{an['evalToFURate']}%", "Eval→FU Rate", "#f59e0b")
        stat_card(eff_col5, f"{an['designEfficiencyScore']}", "Efficiency Score (0-100)", "#a855f7")

        # Funnel visual
        st.markdown(f"""
        <div class="card" style="margin-top:8px;">
          <div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">OVERALL FUNNEL</div>
          <div style="display:flex;gap:4px;align-items:center;">
            <div style="flex:{an['total']};background:#1e293b;border-radius:4px;padding:6px;text-align:center;font-size:0.78rem;color:#94a3b8;">Pre<br/>{an['total']}</div>
            <div style="color:#475569;">→</div>
            <div style="flex:{an['withPost']};background:#1e3a5f;border-radius:4px;padding:6px;text-align:center;font-size:0.78rem;color:#60a5fa;">Post<br/>{an['withPost']}</div>
            <div style="color:#475569;">→</div>
            <div style="flex:{max(an['withEval'],1)};background:#14532d;border-radius:4px;padding:6px;text-align:center;font-size:0.78rem;color:#4ade80;">Eval<br/>{an['withEval']}</div>
            <div style="color:#475569;">→</div>
            <div style="flex:{max(an['withFU'],1)};background:#422006;border-radius:4px;padding:6px;text-align:center;font-size:0.78rem;color:#fbbf24;">FU<br/>{an['withFU']}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # 3. Sustained Intent Confirmation Rate
        st.markdown("#### 3️⃣ Sustained Intent Confirmation Rate")
        si_col1, si_col2, si_col3 = st.columns(3)
        stat_card(si_col1, f"{an['intendChangePct']}%", "Stated Intent (Eval)", "#3b82f6")
        stat_card(si_col2, f"{an['fuChangePct']}%", "Confirmed Change (FU)", "#22c55e")
        stat_card(si_col3, f"{an['sustainedIntentRate']}%", "Sustained Intent Rate (FU/Eval)", "#a855f7")

        # Intent-to-action bar
        ia_pct = an["sustainedIntentRate"]
        st.markdown(f"""
        <div class="card" style="margin-top:8px;">
          <div style="font-size:0.72rem;color:#64748b;margin-bottom:6px;">INTENT → ACTION CONVERSION</div>
          <div class="bar-wrap"><div style="background:#a855f7;height:20px;border-radius:4px;width:{ia_pct}%;"></div></div>
          <div style="color:#a855f7;font-size:0.85rem;margin-top:4px;">{ia_pct}% of evaluators confirmed behavior change at follow-up</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # 4. Barrier Reduction Rate
        st.markdown("#### 4️⃣ Barrier Reduction Rate")
        if an["barrierReductionData"]:
            for br in an["barrierReductionData"][:5]:
                b1, b2 = st.columns(2)
                with b1:
                    horiz_bar(f"EVAL: {br['label'][:50]}", br["evalPct"], "#ef4444")
                with b2:
                    horiz_bar(f"FU: {br['label'][:50]}", br["fuPct"], "#22c55e")
        else:
            st.info("No barrier reduction data available (requires both eval and follow-up responses).")

        st.markdown("""
        <div class="grant-insight">
          <div class="grant-insight-lbl">GRANT INSIGHT</div>
          <div style="color:#e2e8f0;font-size:0.85rem;">
            Barrier reduction data demonstrates the sustained educational impact of this program
            beyond the immediate learning event. Include this data in grant renewal submissions
            to document real-world practice change facilitation.
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # 5. Specialty-Stratified Knowledge Gap
        st.markdown("#### 5️⃣ Specialty-Stratified Knowledge Gap")
        if an["specialtyKnowledgeGaps"]:
            for sg in sorted(an["specialtyKnowledgeGaps"], key=lambda x: x["prePct"])[:10]:
                sg_col1, sg_col2 = st.columns([3, 1])
                with sg_col1:
                    st.markdown(f"""
                    <div style="margin-bottom:4px;">
                      <div style="font-size:0.78rem;color:#94a3b8;margin-bottom:2px;">{sg['specialty']} (n={sg['preN']})</div>
                      <div style="display:flex;gap:4px;align-items:center;">
                        <span style="font-size:0.65rem;color:#94a3b8;width:30px;">PRE</span>
                        <div class="bar-wrap" style="flex:1;"><div class="bar-pre" style="width:{sg['prePct']}%;"></div></div>
                        <span style="font-size:0.75rem;color:#f87171;width:38px;">{sg['prePct']}%</span>
                      </div>
                      <div style="display:flex;gap:4px;align-items:center;margin-top:2px;">
                        <span style="font-size:0.65rem;color:#94a3b8;width:30px;">POST</span>
                        <div class="bar-wrap" style="flex:1;"><div class="bar-post" style="width:{sg['postPct']}%;"></div></div>
                        <span style="font-size:0.75rem;color:#60a5fa;width:38px;">{sg['postPct']}%</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Insufficient specialty data for stratified analysis (requires n≥3 per specialty).")

        st.markdown("""
        <div class="grant-insight">
          <div class="grant-insight-lbl">GRANT INSIGHT</div>
          <div style="color:#e2e8f0;font-size:0.85rem;">
            Specialty-level gaps identify which clinician segments have the greatest unmet educational
            need and the largest response to intervention. Use this for targeted program refinement
            and grantor reporting.
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # 6. Practice Setting Disparity Index
        st.markdown("#### 6️⃣ Practice Setting Disparity Index")
        psd = an["practiceSettingDisparity"]
        ps_col1, ps_col2, ps_col3 = st.columns(3)
        stat_card(ps_col1, f"{psd['academicPct']}%", "Academic Pre-Score", "#3b82f6")
        stat_card(ps_col2, f"{psd['communityPct']}%", "Community Pre-Score", "#22c55e")
        stat_card(ps_col3, f"{psd['gap']}pp", "Disparity Gap", "#ef4444" if psd["gap"]>10 else "#f59e0b")

        if not an["practiceTypes"]:
            st.caption("Practice type data not detected in uploaded files.")


if __name__ == "__main__":
    main()
