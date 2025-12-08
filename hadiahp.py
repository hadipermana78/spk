# app_ahp_cloud_part1.py
"""
Streamlit AHP Multi-User — Cloud-ready (Part 1/3)

This part contains:
- imports
- core config (criteria/subcriteria)
- Excel helper (openpyxl)
- AHP core functions
- PDF generator (reportlab)
- Supabase integration helpers (register/auth/save/fetch)
- PBKDF2 password hashing helpers

Usage:
- Put SUPABASE_URL and SUPABASE_KEY in Streamlit Secrets (or env)
- Then append Part 2 and Part 3 (request them)
"""

# ------------------------------
# Imports
# ------------------------------

import json
import itertools
import numpy as np
import pandas as pd
from io import BytesIO
from datetime import datetime
import hashlib
import os
import streamlit as st
from supabase import create_client

SUPABASE_URL = st.secrets["https://eokdvkmsixasrozhcknq.supabase.co"]
SUPABASE_KEY = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVva2R2a21zaXhhc3Jvemhja25xIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUxNzIyNjEsImV4cCI6MjA4MDc0ODI2MX0.MyOe1JJNf0_byEDDdV_4FEmoNhbm4po4jra5H7jyJss"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
import traceback
import streamlit as st
import sys
from io import StringIO

# ==== INTERNAL LOG VIEWER ====
log_buffer = StringIO()
sys.stdout = log_buffer
sys.stderr = log_buffer

def show_internal_logs():
    st.subheader("🧪 INTERNAL DEBUG LOGS (Auto)")
    logs = log_buffer.getvalue()
    if logs.strip() == "":
        st.info("Tidak ada error atau log output.")
    else:
        st.code(logs, language="text")

# Supabase client
try:
    from supabase import create_client, Client
except Exception:
    create_client = None
    Client = None

# PDF & Excel libraries
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
except Exception:
    canvas = None
    A4 = None
    mm = None

from openpyxl import Workbook

# ------------------------------
# Utility: Excel writer (openpyxl, no pandas.ExcelWriter)
# ------------------------------
def to_excel_bytes(df_dict):
    """
    df_dict: {"SheetName": dataframe or dict/list, ...}
    Return BytesIO Excel file using openpyxl (no pandas.ExcelWriter)
    """
    wb = Workbook()
    # remove default sheet
    default = wb.active
    wb.remove(default)

    for sheet_name, df in df_dict.items():
        if not isinstance(df, pd.DataFrame):
            try:
                df = pd.DataFrame(df)
            except Exception:
                df = pd.DataFrame([df])
        ws = wb.create_sheet(sheet_name[:31])
        # header
        ws.append(list(df.columns))
        # rows
        for row in df.itertuples(index=False, name=None):
            ws.append(list(row))

    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out

# ------------------------------
# Config: Criteria & Subcriteria
# ------------------------------
CRITERIA = [
    "A. Penataan Area Drop-off, Pick-up, dan Manajemen Moda",
    "B. Penataan Sirkulasi Kendaraan dan Pengendalian Kemacetan",
    "C. Keamanan dan Keselamatan Ruang Publik",
    "D. Kenyamanan Ruang Publik dan Lingkungan",
    "E. Kebersihan dan Pemeliharaan Fasilitas",
    "F. Aksesibilitas dan Konektivitas",
    "G. Aktivitas dan Fasilitas Pendukung"
]

SUBCRITERIA = {
    "A. Penataan Area Drop-off, Pick-up, dan Manajemen Moda": [
        "A1. Sediakan zona drop-off/pick-up resmi yang tertata",
        "A2. Bangun zona khusus drop-off untuk ojek online",
        "A3. Sediakan ruang drop-off terpisah untuk taksi dan mobil pribadi",
        "A4. Perbesar kapasitas ruang drop-off sesuai volume kendaraan",
        "A5. Pisahkan zona antarmoda secara tegas",
        "A6. Sediakan tempat mangkal resmi untuk ojek online dan ojek pangkalan",
        "A7. Tata alur sirkulasi kendaraan dengan pola yang terarah",
        "A8. Integrasikan manajemen transit dalam satu sistem zonasi",
        "A9. Kendalikan aktivitas moda pada jam sibuk",
        "A10. Sediakan area parkir resmi yang teratur dan mudah diakses"
    ],
    "B. Penataan Sirkulasi Kendaraan dan Pengendalian Kemacetan": [
        "B1. Susun sirkulasi kendaraan agar tidak bergantung pada satu koridor",
        "B2. Hilangkan titik parkir liar melalui desain fisik dan pengawasan",
        "B3. Tambahkan kapasitas sirkulasi untuk moda kecil dan ojol",
        "B4. Atur perilaku lalu lintas melalui desain preventif",
        "B5. Pisahkan jalur kendaraan dari area pejalan kaki"
    ],
    "C. Keamanan dan Keselamatan Ruang Publik": [
        "C1. Sediakan titik penyeberangan aman dan terlindungi",
        "C2. Kurangi titik konflik kendaraan–pejalan kaki melalui pemisahan fisik",
        "C3. Sediakan penerangan merata di seluruh koridor",
        "C4. Tingkatkan keamanan dengan CCTV, patroli, dan desain yang aktif"
    ],
    "D. Kenyamanan Ruang Publik dan Lingkungan": [
        "D1. Sediakan area teduh dan pelindung cuaca pada jalur pejalan kaki",
        "D2. Tambahkan ruang terbuka hijau dan vegetasi",
        "D3. Lebarkan area pejalan kaki agar terasa lapang",
        "D4. Sediakan tempat duduk di titik beristirahat strategis",
        "D5. Bangun ruang tunggu yang luas, teduh, dan nyaman",
        "D6. Tingkatkan kualitas estetika kawasan",
        "D7. Kendalikan kebisingan melalui buffer fisik atau vegetasi"
    ],
    "E. Kebersihan dan Pemeliharaan Fasilitas": [
        "E1. Tingkatkan standar kebersihan toilet, lantai, dan fasilitas dasar",
        "E2. Sediakan sistem pengelolaan sampah yang memadai",
        "E3. Lakukan pemeliharaan fasilitas secara berkala"
    ],
    "F. Aksesibilitas dan Konektivitas": [
        "F1. Sediakan jalur akses yang dekat dan tidak melelahkan",
        "F2. Bangun ramp dan fasilitas akses ramah difabel",
        "F3. Pastikan eskalator dan lift berfungsi baik setiap saat",
        "F4. Tingkatkan konektivitas antarmoda melalui jalur direct link",
        "F5. Sediakan jalur pejalan kaki yang aman, rata, dan tidak licin",
        "F6. Sediakan parkir sepeda yang aman dan memadai"
    ],
    "G. Aktivitas dan Fasilitas Pendukung": [
        "G1. Sediakan fasilitas komersial dasar yang mudah dijangkau",
        "G2. Sediakan fasilitas makan dan minum yang layak dan terjangkau",
        "G3. Sediakan ruang istirahat dan fasilitas transit yang memadai",
        "G4. Tata zona aktivitas agar tidak mengganggu sirkulasi utama",
        "G5. Sediakan sistem informasi dan signage yang jelas dan konsisten"
    ]
}

# Random Index for CI/CR
RI_DICT = {1:0.0,2:0.0,3:0.58,4:0.90,5:1.12,6:1.24,7:1.32,8:1.41,9:1.45,10:1.49}

# ------------------------------
# AHP core functions
# ------------------------------
def build_matrix_from_pairs(items, pair_values):
    n = len(items)
    M = np.ones((n, n), dtype=float)
    idx = {it: i for i, it in enumerate(items)}
    for (a, b), val in pair_values.items():
        if a not in idx or b not in idx:
            # allow stored string keys "A ||| B"
            continue
        i = idx[a]; j = idx[b]
        try:
            M[i, j] = float(val)
            if float(val) != 0:
                M[j, i] = 1.0 / float(val)
        except Exception:
            continue
    return M

def geometric_mean_weights(mat):
    n = mat.shape[0]
    gm = np.prod(mat, axis=1) ** (1.0 / n)
    w = gm / np.sum(gm)
    return w

def consistency_metrics(mat, weights):
    n = mat.shape[0]
    Aw = mat.dot(weights)
    lambda_max = float(np.mean(Aw / weights))
    CI = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    RI = RI_DICT.get(n, 1.49)
    CR = CI / RI if RI != 0 else 0.0
    return {"lambda_max": lambda_max, "CI": CI, "CR": CR}

# ------------------------------
# PDF generator (reportlab)
# ------------------------------
def generate_pdf_bytes(submission_row):
    if canvas is None:
        raise RuntimeError("reportlab tidak terinstall. Tambahkan 'reportlab' ke requirements.")
    bio = BytesIO()
    c = canvas.Canvas(bio, pagesize=A4)
    width, height = A4
    margin = 18 * mm
    x = margin; y = height - margin

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, "Laporan Hasil AHP — Penataan Ruang Publik")
    y -= 8 * mm
    c.setFont("Helvetica", 9)
    c.drawString(x, y, f"User / Group: {submission_row.get('username','')}")
    y -= 5 * mm
    c.drawString(x, y, f"Waktu: {submission_row.get('timestamp','')}")
    y -= 8 * mm

    res = submission_row.get("result", {})
    main = res.get("main", {})
    keys = main.get("keys", [])
    weights = main.get("weights", [])
    cons = main.get("cons", {})

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Bobot Kriteria Utama:")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    for k, w in zip(keys, weights):
        if y < margin + 30 * mm:
            c.showPage(); y = height - margin
        c.drawString(x + 2 * mm, y, f"{k} — {w:.4f}")
        y -= 5 * mm

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Bobot Global (Top):")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    gw = pd.DataFrame(res.get("global", []))
    if not gw.empty:
        gw_sorted = gw.sort_values("GlobalWeight", ascending=False).head(25)
        for _, row in gw_sorted.iterrows():
            if y < margin + 20 * mm:
                c.showPage(); y = height - margin
            text = f"{row.get('SubKriteria','')} ({row.get('Kriteria','')}) — {row.get('GlobalWeight',0):.6f}"
            c.drawString(x + 2 * mm, y, text if len(text) < 120 else text[:117] + "...")
            y -= 5 * mm

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Ringkasan Konsistensi (CI / CR):")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    c.drawString(x + 2 * mm, y, f"Kriteria Utama — CI: {cons.get('CI',0):.4f} , CR: {cons.get('CR',0):.4f}")
    y -= 6 * mm

    local = res.get("local", {})
    for grp, info in local.items():
        grp_cons = info.get("cons", {})
        if grp_cons.get("CR", 0) > 0.1:
            if y < margin + 15 * mm:
                c.showPage(); y = height - margin
            c.drawString(x + 2 * mm, y, f"Perhatian: CR>0.1 pada {grp} (CR={grp_cons.get('CR'):.3f})")
            y -= 5 * mm

    c.showPage()
    c.save()
    bio.seek(0)
    return bio

# ------------------------------
# Supabase integration helpers
# ------------------------------
# Read credentials from st.secrets or environment variables
SUPABASE_URL = None
SUPABASE_KEY = None
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    # We'll not stop here; main app will check and show helpful error when needed.
    supabase = None
else:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------------------
# Auth & DB functions using Supabase
# ------------------------------
def register_user(username, password, is_admin=0):
    if not supabase:
        return False, "Supabase belum dikonfigurasi."
    if not username or not password:
        return False, "Username dan password wajib diisi."
    # check existing
    r = supabase.table("users").select("id").eq("username", username).execute()
    if r.data and len(r.data) > 0:
        return False, "Username sudah terdaftar."
    salt, pw_hash = hash_password(password)
    payload = {"username": username, "pw_salt": salt, "pw_hash": pw_hash, "is_admin": bool(is_admin)}
    res = supabase.table("users").insert(payload).execute()
    if res.status_code in (200, 201):
        return True, "Registrasi berhasil."
    return False, f"Gagal registrasi: {getattr(res,'status_code', 'unknown')}"

def authenticate_user(username, password):
    if not supabase:
        return False, "Supabase belum dikonfigurasi."
    r = supabase.table("users").select("*").eq("username", username).limit(1).execute()
    if not r.data or len(r.data) == 0:
        return False, "User tidak ditemukan."
    user = r.data[0]
    if verify_password(password, user["pw_salt"], user["pw_hash"]):
        return True, {"id": int(user["id"]), "username": user["username"], "is_admin": bool(user["is_admin"])}
    return False, "Password salah."

def delete_submission(submission_id):
    if not supabase:
        raise RuntimeError("Supabase belum dikonfigurasi.")
    supabase.table("submissions").delete().eq("id", int(submission_id)).execute()

def save_submission(user_id, main_pairs_dict, sub_pairs_dict, result_dict):
    if not supabase:
        raise RuntimeError("Supabase belum dikonfigurasi.")
    payload = {
        "user_id": int(user_id),
        "main_pairs": json.dumps(main_pairs_dict),
        "sub_pairs": json.dumps(sub_pairs_dict),
        "result_json": json.dumps(result_dict)
    }
    res = supabase.table("submissions").insert(payload).execute()
    return res

def get_submissions_by_user(user_id):
    if not supabase:
        return []
    r = supabase.table("submissions").select("*").eq("user_id", int(user_id)).order("id", {"ascending": False}).execute()
    return r.data or []

def get_submission_by_id(submission_id):
    if not supabase:
        return None
    r = supabase.table("submissions").select("*").eq("id", int(submission_id)).limit(1).execute()
    return (r.data[0] if r.data and len(r.data) > 0 else None)

def get_all_submissions():
    if not supabase:
        return []
    r = supabase.table("submissions").select("*").order("id", {"ascending": False}).execute()
    return r.data or []

def get_latest_submission_per_user():
    """
    Return list of tuples: (username, result_json, main_pairs_json)
    Implementation: fetch all users, then get latest submission per user
    """
    if not supabase:
        return []
    users = supabase.table("users").select("id,username").order("username").execute()
    out = []
    for u in users.data or []:
        s = supabase.table("submissions").select("*").eq("user_id", u["id"]).order("id", {"ascending": False}).limit(1).execute()
        if s.data and len(s.data) > 0:
            out.append((u["username"], s.data[0].get("result_json"), s.data[0].get("main_pairs")))
    return out

# ------------------------------
# PBKDF2 hashing helpers (same as local)
# ------------------------------
def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)
    else:
        salt = bytes.fromhex(salt)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 200000)
    return salt.hex(), dk.hex()

def verify_password(password, salt_hex, hash_hex):
    try:
        salt = bytes.fromhex(salt_hex)
    except Exception:
        return False
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 200000)
    return dk.hex() == hash_hex

# End of Part 1
# Next: Part 2 will include Streamlit UI routing, pairwise inputs, Isi Kuesioner and My Submissions.
# Ask: "lanjutkan part 2"
# ------------------------------
# Part 2/3 — UI: Auth, Routing, Pairwise Input, Kuesioner, My Submissions
# ------------------------------

# Page config (can be set once)
st.set_page_config(page_title="AHP Multi-User (Cloud)", layout="wide")

# ------------------------------
# Authentication UI & flow
# ------------------------------
st.sidebar.title("Akses Aplikasi")
auth_mode = st.sidebar.selectbox("Mode", ["Login", "Register", "Logout"])

# Ensure session state user
if 'user' not in st.session_state:
    st.session_state['user'] = None

# Registration form
if auth_mode == "Register":
    st.sidebar.subheader("Daftar Pengguna Baru")
    new_user = st.sidebar.text_input("Username (daftar)", key="reg_user")
    new_pw = st.sidebar.text_input("Password (daftar)", type="password", key="reg_pw")
    admin_check = st.sidebar.checkbox("Daftarkan sebagai admin", key="reg_admin")
    if st.sidebar.button("Daftar", key="btn_register"):
        ok, msg = register_user(new_user, new_pw, 1 if admin_check else 0)
        if ok:
            st.sidebar.success(msg)
        else:
            st.sidebar.error(msg)

# Login form
elif auth_mode == "Login":
    st.sidebar.subheader("Masuk")
    login_user = st.sidebar.text_input("Username", key="login_user")
    login_pw = st.sidebar.text_input("Password", type="password", key="login_pw")
    if st.sidebar.button("Masuk", key="btn_login"):
        ok, info = authenticate_user(login_user, login_pw)
        if ok:
            # store minimal user in session_state
            st.session_state['user'] = info
            st.sidebar.success(f"Selamat datang, {info['username']}")
        else:
            st.sidebar.error(info)

# Logout
else:
    if st.sidebar.button("Logout", key="btn_logout"):
        st.session_state['user'] = None
        st.sidebar.info("Anda telah logout.")

# If not logged in, show landing page and stop
if not st.session_state['user']:
    st.title("Aplikasi Kuesioner AHP — Multi-user (Cloud)")
    st.write("Silakan login atau daftar melalui panel kiri (sidebar).")
    st.write("Setelah login, pengguna dapat mengisi kuesioner dan menyimpan hasil ke cloud.")
    # helpful debug when supabase missing
    if supabase is None:
        st.warning("Supabase belum dikonfigurasi. Pastikan SUPABASE_URL & SUPABASE_KEY ada di Streamlit Secrets.")
    st.stop()

# current user
user = st.session_state['user']
st.sidebar.markdown(f"**User:** {user['username']}  {'(admin)' if user['is_admin'] else ''}")

# ------------------------------
# Page selector
# ------------------------------
if user['is_admin']:
    page = st.sidebar.selectbox("Halaman", [
        "Isi Kuesioner",
        "My Submissions",
        "Hasil Akhir Penilaian",
        "Admin Panel",
        "Laporan Final Gabungan Pakar"
    ])
else:
    page = st.sidebar.selectbox("Halaman", [
        "Isi Kuesioner",
        "My Submissions",
        "Hasil Akhir Penilaian"
    ])

# ------------------------------
# Pairwise input helper (UI)
# ------------------------------
def _short_key(prefix, a, b):
    h = hashlib.sha1((prefix + "::" + a + "|||" + b).encode("utf-8")).hexdigest()
    return h[:12]

def pairwise_inputs(items, key_prefix):
    """
    Render pairwise inputs for items.
    Returns dict with keys (a,b) -> float where (a,b) indicates a/b = value.
    """
    pairs = list(itertools.combinations(items, 2))
    out = {}
    for (a, b) in pairs:
        col_l, col_mid, col_r, col_scale = st.columns([6, 1, 6, 2])
        col_l.markdown(f"<div style='white-space:normal'>{a}</div>", unsafe_allow_html=True)
        col_r.markdown(f"<div style='white-space:normal'>{b}</div>", unsafe_allow_html=True)
        k = _short_key(key_prefix, a, b)
        # direction radio: L means left more important
        direction = col_mid.radio("", ["L", "R"], index=0, key=f"{k}_dir", label_visibility="collapsed", horizontal=True)
        val = col_scale.selectbox("", list(range(1, 10)), index=1, key=f"{k}_scale", label_visibility="collapsed")
        if direction == "L":
            out[(a, b)] = float(val)
        else:
            out[(a, b)] = float(1.0 / val)
    return out

# ------------------------------
# Page: Isi Kuesioner
# ------------------------------
if page == "Isi Kuesioner":
    st.header("Isi Kuesioner AHP — Penataan Ruang Publik")
    st.write("Isi perbandingan berpasangan menggunakan skala 1–9. (1 = sama penting, 9 = mutlak lebih penting).")

    st.markdown("### 1) Perbandingan Kriteria Utama (A–G)")
    main_pairs = pairwise_inputs(CRITERIA, "MAIN")

    st.markdown("---")
    st.markdown("### 2) Sub-Kriteria per Grup")
    sub_pairs = {}
    for group in CRITERIA:
        st.markdown(f"#### {group}")
        sp = pairwise_inputs(SUBCRITERIA[group], key_prefix=group[:12].replace(" ", "_"))
        sub_pairs[group] = {f"{a} ||| {b}": v for (a, b), v in sp.items()}

    if st.button("Simpan hasil ke cloud (Supabase)", key="save_submission"):
        try:
            # compute main AHP
            main_mat = build_matrix_from_pairs(CRITERIA, main_pairs)
            main_w = geometric_mean_weights(main_mat)
            main_cons = consistency_metrics(main_mat, main_w)

            local = {}
            global_rows = []
            for i, group in enumerate(CRITERIA):
                # reconstruct pairs for group
                pairdict = {tuple(k.split(" ||| ")): v for k, v in sub_pairs[group].items()}
                mat = build_matrix_from_pairs(SUBCRITERIA[group], pairdict)
                w = geometric_mean_weights(mat)
                cons = consistency_metrics(mat, w)
                local[group] = {"keys": SUBCRITERIA[group], "weights": list(map(float, w)), "cons": cons}
                for sk, lw in zip(SUBCRITERIA[group], w):
                    global_rows.append({
                        "Kriteria": group,
                        "SubKriteria": sk,
                        "LocalWeight": float(lw),
                        "MainWeight": float(main_w[i]),
                        "GlobalWeight": float(main_w[i] * lw)
                    })

            result = {
                "main": {"keys": CRITERIA, "weights": list(map(float, main_w)), "cons": main_cons, "mat": main_mat.tolist()},
                "local": local,
                "global": global_rows
            }
            ts = datetime.now().isoformat()
            main_pairs_store = {f"{a} ||| {b}": v for (a, b), v in main_pairs.items()}

            # save to supabase
            save_submission(user['id'], main_pairs_store, sub_pairs, result)
            st.success("Hasil berhasil disimpan ke Supabase.")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Gagal menyimpan submission: {e}")

# ------------------------------
# Page: My Submissions
# ------------------------------
elif page == "My Submissions":
    st.header("Submission Saya")
    rows = get_submissions_by_user(user['id'])
    if not rows:
        st.info("Belum ada submission.")
    else:
        for row in rows:
            sid = row.get("id")
            ts = row.get("timestamp")
            rjson = row.get("result_json")
            res = json.loads(rjson) if isinstance(rjson, str) else (rjson or {})
            st.subheader(f"Submission #{sid} — {ts}")
            dfg = pd.DataFrame(res.get("global", [])).sort_values("GlobalWeight", ascending=False).head(10)
            st.table(dfg)

            col1, col2 = st.columns(2)
            with col1:
                df_main = pd.DataFrame({"Kriteria": res.get("main", {}).get("keys", []),
                                        "Weight": res.get("main", {}).get("weights", [])})
                df_global = pd.DataFrame(res.get("global", [])).sort_values("GlobalWeight", ascending=False)
                excel_out = to_excel_bytes({
                    "Kriteria_Utama": df_main,
                    "Global_Weights": df_global
                })
                st.download_button(f"Download Excel #{sid}", data=excel_out,
                                   file_name=f"submission_{sid}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key=f"ex_{sid}")

            with col2:
                submission_row = {"id": sid, "username": user['username'], "timestamp": ts, "result": res}
                try:
                    pdf_bio = generate_pdf_bytes(submission_row)
                    st.download_button(f"Download PDF #{sid}", data=pdf_bio,
                                       file_name=f"submission_{sid}.pdf", mime="application/pdf", key=f"pdf_{sid}")
                except RuntimeError as e:
                    st.warning(str(e))

# End of Part 2
# Next: Part 3 (Admin Panel, Hasil Per Pakar, Laporan Gabungan)
# Ask: "lanjutkan part 3"
# ------------------------------
# Part 3/3 — Admin Panel, Hasil Akhir, Laporan Gabungan Pakar (AIJ + AIP)
# ------------------------------

# ------------------------------
# Page: Hasil Akhir Penilaian (untuk user sendiri)
# ------------------------------
elif page == "Hasil Akhir Penilaian":
    st.header("Hasil Akhir Penilaian AHP — Penilaian Anda")

    rows = get_submissions_by_user(user['id'])
    if not rows:
        st.info("Anda belum mengisi kuesioner AHP.")
        st.stop()

    row = rows[0]  # latest
    res = json.loads(row["result_json"])
    sid = row["id"]
    ts = row["timestamp"]

    st.subheader("1. Bobot Kriteria Utama")
    df_main = pd.DataFrame({
        "Kriteria": res["main"]["keys"],
        "Bobot": res["main"]["weights"]
    })
    st.table(df_main)

    st.write(f"**CI = {res['main']['cons']['CI']:.4f}, CR = {res['main']['cons']['CR']:.4f}**")

    st.markdown("---")
    st.subheader("2. Bobot Sub-Kriteria (per Kriteria)")

    for group_name, info in res["local"].items():
        st.markdown(f"### {group_name}")
        df_local = pd.DataFrame({
            "Sub-Kriteria": info["keys"],
            "Bobot Lokal": info["weights"]
        })
        st.table(df_local)
        st.write(f"**CI = {info['cons']['CI']:.4f}, CR = {info['cons']['CR']:.4f}**")

    st.markdown("---")
    st.subheader("3. Bobot Global (Ranking)")
    df_global = pd.DataFrame(res["global"]).sort_values("GlobalWeight", ascending=False)
    st.table(df_global)

    st.subheader("Grafik Bobot Global (Top 20)")
    try:
        import altair as alt
        chart = alt.Chart(df_global.head(20)).mark_bar().encode(
            x='GlobalWeight:Q',
            y=alt.Y('SubKriteria:N', sort='-x')
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.info("Altair tidak tersedia.")

    st.markdown("---")
    st.subheader("4. Download Laporan")

    submission_row = {
        "id": sid,
        "username": user["username"],
        "timestamp": ts,
        "result": res
    }
    pdf_bytes = generate_pdf_bytes(submission_row)
    st.download_button("📄 Download PDF", data=pdf_bytes,
                       file_name=f"hasil_ahp_{sid}.pdf", mime="application/pdf")

    excel_bytes = to_excel_bytes({
        "Kriteria_Utama": df_main,
        "Global_Weights": df_global,
    })
    st.download_button("📊 Download Excel", data=excel_bytes,
                       file_name=f"hasil_ahp_{sid}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ------------------------------
# Page: Admin Panel
# ------------------------------
elif page == "Admin Panel":
    if not user["is_admin"]:
        st.error("Anda bukan admin.")
        st.stop()

    st.header("📊 Admin Panel — Manajemen Penilaian Pakar")

    # Ambil semua submission
    cur = supabase.table("submissions").select("*, users(username)").execute()
    data = cur.data if cur.data else []

    if not data:
        st.info("Belum ada submission dari pakar.")
        st.stop()

    # Ringkasan Admin
    table_data = []
    for row in data:
        res = json.loads(row["result_json"])
        table_data.append({
            "ID": row["id"],
            "User": row["users"]["username"],
            "Timestamp": row["timestamp"],
            "CR Utama": res["main"]["cons"]["CR"],
            "Bobot Kriteria": ", ".join(f"{w:.3f}" for w in res["main"]["weights"])
        })

    df_admin = pd.DataFrame(table_data)
    st.dataframe(df_admin, use_container_width=True)

    st.markdown("---")

    # Hapus submission
    st.subheader("🗑 Hapus Submission Pakar")
    del_id = st.number_input("Masukkan ID submission", step=1, min_value=1)

    if st.button("Hapus Submission"):
        try:
            supabase.table("submissions").delete().eq("id", del_id).execute()
            st.success("Data berhasil dihapus.")
            st.rerun()
        except Exception as e:
            st.error(f"Gagal menghapus: {e}")

    st.markdown("---")

    # Download semua data
    st.subheader("📥 Download Semua Data (Excel)")
    excel_output = BytesIO()

    df_admin.to_excel(excel_output, index=False)
    excel_output.seek(0)

    st.download_button(
        "📊 Download Excel Semua Data",
        data=excel_output,
        file_name="all_submissions.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ------------------------------
# Page: Laporan Final Gabungan Pakar (AIJ + AIP)
# ------------------------------
elif page == "Laporan Final Gabungan Pakar":
    if not user["is_admin"]:
        st.error("Anda bukan admin.")
        st.stop()

    st.header("📘 Laporan Final Gabungan Antar Pakar (AIJ & AIP)")

    # Ambil submission terbaru per user
    cur = supabase.rpc("get_latest_submissions").execute()
    experts = cur.data if cur.data else []

    if not experts:
        st.warning("Belum ada pakar yang mengisi kuesioner.")
        st.stop()

    st.success(f"Ditemukan {len(experts)} pakar.")

    # ===========================
    # 1. AIJ — Aggregation of Individual Judgments
    # ===========================
    all_main_matrices = []

    for row in experts:
        mp = json.loads(row["main_pairs"]) if row["main_pairs"] else {}
        pair_values = {}
        for k, v in mp.items():
            a, b = [s.strip() for s in k.split("|||")]
            pair_values[(a, b)] = float(v)

        M = build_matrix_from_pairs(CRITERIA, pair_values)
        all_main_matrices.append(M)

    GM = np.exp(np.mean([np.log(m) for m in all_main_matrices], axis=0))
    weights_aij = geometric_mean_weights(GM)
    cons_aij = consistency_metrics(GM, weights_aij)

    df_aij = pd.DataFrame({
        "Kriteria": CRITERIA,
        "Bobot AIJ": weights_aij
    })

    st.subheader("1) Bobot Kriteria Gabungan (AIJ)")
    st.table(df_aij)
    st.info(f"CI = {cons_aij['CI']:.4f}, CR = {cons_aij['CR']:.4f}")

    # ===========================
    # 2. AIP — Aggregation of Individual Priorities
    # ===========================
    all_weights = []
    for row in experts:
        res = json.loads(row["result_json"])
        all_weights.append(np.array(res["main"]["weights"]))

    AIP = np.exp(np.mean(np.log(all_weights), axis=0))
    AIP = AIP / AIP.sum()

    df_aip = pd.DataFrame({
        "Kriteria": CRITERIA,
        "Bobot AIP": AIP
    })

    st.subheader("2) Bobot Gabungan (AIP)")
    st.table(df_aip)

    # ===========================
    # 3. Global Combined Weights (AIJ)
    # ===========================
    st.subheader("3) Bobot Global Gabungan Sub-Kriteria (AIJ)")

    global_rows = []
    for row in experts:
        res = json.loads(row["result_json"])
        # gunakan AIJ main weights
        for group in CRITERIA:
            local_w = np.array(res["local"][group]["weights"])
            local_w = local_w / local_w.sum()
            idx = CRITERIA.index(group)
            for sk, lw in zip(SUBCRITERIA[group], local_w):
                global_rows.append({
                    "Kriteria": group,
                    "SubKriteria": sk,
                    "LocalWeight": lw,
                    "MainWeight": weights_aij[idx],
                    "GlobalWeight": lw * weights_aij[idx]
                })

    df_global = pd.DataFrame(global_rows).sort_values("GlobalWeight", ascending=False)
    st.table(df_global)

    st.subheader("Grafik Ranking Global (Top 20)")
    try:
        import altair as alt
        chart = alt.Chart(df_global.head(20)).mark_bar().encode(
            x="GlobalWeight:Q",
            y=alt.Y("SubKriteria:N", sort="-x")
        )
        st.altair_chart(chart, use_container_width=True)
    except:
        st.info("Altair tidak tersedia.")

    # ===========================
    # 4. Download Final Excel & PDF
    # ===========================
    excel_bytes = to_excel_bytes({
        "AIJ": df_aij,
        "AIP": df_aip,
        "GlobalWeights": df_global
    })

    st.download_button("📊 Download Excel Gabungan",
                       data=excel_bytes,
                       file_name="AHP_Final_Gabungan.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    submission_row = {
        "username": "GABUNGAN PAKAR",
        "timestamp": "FINAL",
        "result": {
            "main": {"keys": CRITERIA, "weights": list(weights_aij), "cons": cons_aij},
            "global": df_global.to_dict(orient="records")
        }
    }

    pdf_bytes = generate_pdf_bytes(submission_row)
    st.download_button("📄 Download PDF Final",
                       data=pdf_bytes,
                       file_name="AHP_FINAL_Pakar.pdf",
                       mime="application/pdf")

# END OF PART 3
# ------------------------------

