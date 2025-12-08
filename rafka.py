# hadiahp.py — PART 1/3
"""
AHP Multi-User (Cloud-ready) — PART 1

Contents:
- imports
- config (criteria/subcriteria)
- excel/pdf helpers
- AHP core functions (matrix, gm, CI/CR)
- Supabase init (cache_resource) + DB helpers (register/auth/save/fetch)
- PBKDF2 hashing helpers

Notes:
- Put SUPABASE_URL and SUPABASE_KEY into Streamlit Secrets (Settings -> Secrets):
  SUPABASE_URL = "https://xxxx.supabase.co"
  SUPABASE_KEY = "eyJ...."
- Part 2 contains UI (pairwise inputs, pages) and Part 3 contains admin & aggregation.
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

# Supabase
try:
    from supabase import create_client, Client
except Exception:
    create_client = None
    Client = None

# PDF & report
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
except Exception:
    canvas = None
    A4 = None
    mm = None

# Excel writer (openpyxl)
try:
    from openpyxl import Workbook
except Exception:
    Workbook = None

# ------------------------------
# Page config
# ------------------------------
st.set_page_config(page_title="AHP Multi-User (Cloud)", layout="wide")

# ------------------------------
# Utility: Excel bytes writer (openpyxl without pandas.ExcelWriter)
# ------------------------------
def to_excel_bytes(df_dict):
    """
    df_dict: {"SheetName": pd.DataFrame or list/dict}
    returns: BytesIO of .xlsx
    """
    if Workbook is None:
        raise RuntimeError("openpyxl tidak terinstall. Pastikan 'openpyxl' ada di requirements.")
    wb = Workbook()
    # remove default sheet
    default = wb.active
    wb.remove(default)
    for sheet_name, df in df_dict.items():
        # convert to DataFrame
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

# Random Index (RI) untuk CI/CR
RI_DICT = {1:0.0,2:0.0,3:0.58,4:0.90,5:1.12,6:1.24,7:1.32,8:1.41,9:1.45,10:1.49}

# ------------------------------
# AHP core functions
# ------------------------------
def build_matrix_from_pairs(items, pair_values):
    """
    items: list of item labels (length n)
    pair_values: dict with keys either (a,b) tuples or "a ||| b" strings -> numerical value
    """
    n = len(items)
    M = np.ones((n, n), dtype=float)
    idx = {it: i for i, it in enumerate(items)}
    # normalize keys: allow both tuple keys and "a ||| b"
    for k, val in pair_values.items():
        try:
            if isinstance(k, tuple) and len(k) == 2:
                a, b = k
            elif isinstance(k, str) and "|||" in k:
                a, b = [s.strip() for s in k.split("|||")]
            else:
                # try to unpack
                a, b = k
        except Exception:
            continue
        if a not in idx or b not in idx:
            continue
        i = idx[a]; j = idx[b]
        try:
            v = float(val)
            M[i, j] = v
            if v != 0:
                M[j, i] = 1.0 / v
        except Exception:
            continue
    return M

def geometric_mean_weights(mat):
    n = mat.shape[0]
    # handle degenerate
    with np.errstate(divide='ignore', invalid='ignore'):
        gm = np.prod(mat, axis=1) ** (1.0 / n)
    # if gm contains nan, fallback to eigenvector (np.linalg)
    if np.isnan(gm).any() or np.isinf(gm).any():
        eigvals, eigvecs = np.linalg.eig(mat)
        max_idx = np.argmax(eigvals.real)
        w = np.abs(eigvecs[:, max_idx].real)
        w = w / np.sum(w)
        return w
    w = gm / np.sum(gm)
    return w

def consistency_metrics(mat, weights):
    n = mat.shape[0]
    # avoid divide by zero
    if np.any(weights == 0):
        return {"lambda_max": float(np.nan), "CI": float(np.nan), "CR": float(np.nan)}
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
    """
    submission_row: dict with keys: username, timestamp, result (as dict)
    returns: BytesIO of PDF
    """
    if canvas is None or A4 is None or mm is None:
        raise RuntimeError("reportlab tidak terinstall. Tambahkan 'reportlab' ke requirements.")
    bio = BytesIO()
    c = canvas.Canvas(bio, pagesize=A4)
    width, height = A4
    margin = 18 * mm
    x = margin
    y = height - margin

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
            c.showPage()
            y = height - margin
        try:
            c.drawString(x + 2 * mm, y, f"{k} — {w:.4f}")
        except Exception:
            c.drawString(x + 2 * mm, y, f"{k} — {w}")
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
                c.showPage()
                y = height - margin
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
                c.showPage()
                y = height - margin
            c.drawString(x + 2 * mm, y, f"Perhatian: CR>0.1 pada {grp} (CR={grp_cons.get('CR'):.3f})")
            y -= 5 * mm

    c.showPage()
    c.save()
    bio.seek(0)
    return bio

# ------------------------------
# Supabase initialization (safe, cache_resource)
# ------------------------------
@st.cache_resource
def init_supabase_client():
    """
    Initialize and return a Supabase client from st.secrets.
    Expects in Streamlit Secrets:
      SUPABASE_URL = "https://....supabase.co"
      SUPABASE_KEY = "xxxx"
    """
    if create_client is None:
        raise RuntimeError("Library supabase tidak tersedia. Pastikan 'supabase' ada di requirements.")
    url = None
    key = None
    # Prefer st.secrets (Streamlit Cloud). Fallback to env vars for local dev.
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL or SUPABASE_KEY not found in st.secrets or environment variables.")
    client = create_client(url, key)
    return client

# Create global supabase variable but delay init until called.
try:
    supabase = init_supabase_client()
except Exception as e:
    # Do not crash on import; we will show errors in UI later.
    supabase = None
    _supabase_init_error = str(e)

# ------------------------------
# DB helpers (Supabase)
# ------------------------------
def register_user(username, password, is_admin=0):
    """
    Returns (ok:bool, message:str)
    """
    if supabase is None:
        return False, "Supabase belum dikonfigurasi. Periksa st.secrets."
    if not username or not password:
        return False, "Username dan password wajib diisi."
    # check existing
    r = supabase.table("users").select("id").eq("username", username).execute()
    if r.data and len(r.data) > 0:
        return False, "Username sudah terdaftar."
    salt, pw_hash = hash_password(password)
    payload = {"username": username, "pw_salt": salt, "pw_hash": pw_hash, "is_admin": bool(is_admin)}
    res = supabase.table("users").insert(payload).execute()
    # Supabase client returns response with 'status_code' or raises — check 'status_code' where available
    try:
        status = getattr(res, "status_code", None)
        if status in (200, 201) or (hasattr(res, "data") and res.data):
            return True, "Registrasi berhasil."
    except Exception:
        pass
    return False, "Gagal registrasi. Periksa konfigurasi Supabase."

def authenticate_user(username, password):
    """
    Returns (ok:bool, user_dict_or_message)
    """
    if supabase is None:
        return False, "Supabase belum dikonfigurasi. Periksa st.secrets."
    r = supabase.table("users").select("*").eq("username", username).limit(1).execute()
    if not r.data or len(r.data) == 0:
        return False, "User tidak ditemukan."
    user = r.data[0]
    if verify_password(password, user.get("pw_salt", ""), user.get("pw_hash", "")):
        return True, {"id": int(user["id"]), "username": user["username"], "is_admin": bool(user.get("is_admin", False))}
    return False, "Password salah."

def save_submission(user_id, main_pairs_dict, sub_pairs_dict, result_dict):
    """
    Insert submission. main_pairs_dict and sub_pairs_dict typically JSON-serializable.
    Returns Supabase response or raises.
    """
    if supabase is None:
        raise RuntimeError("Supabase belum dikonfigurasi.")
    payload = {
        "user_id": int(user_id),
        "timestamp": datetime.now().isoformat(),
        "main_pairs": json.dumps(main_pairs_dict),
        "sub_pairs": json.dumps(sub_pairs_dict),
        "result_json": json.dumps(result_dict)
    }
    res = supabase.table("submissions").insert(payload).execute()
    return res

def get_submissions_by_user(user_id):
    if supabase is None:
        return []
    r = supabase.table("submissions").select("*").eq("user_id", int(user_id)).order("id", {"ascending": False}).execute()
    return r.data or []

def get_submission_by_id(submission_id):
    if supabase is None:
        return None
    r = supabase.table("submissions").select("*").eq("id", int(submission_id)).limit(1).execute()
    return (r.data[0] if r.data and len(r.data) > 0 else None)

def get_all_submissions():
    if supabase is None:
        return []
    r = supabase.table("submissions").select("*").order("id", {"ascending": False}).execute()
    return r.data or []

def get_latest_submission_per_user():
    """
    Efficient approach: call a Supabase RPC that returns latest submission per user.
    If RPC not available, fallback to fetching users and per-user query (less efficient).
    """
    if supabase is None:
        return []
    # try RPC first
    try:
        r = supabase.rpc("get_latest_submissions").execute()
        if r.data:
            return r.data
    except Exception:
        pass
    # fallback
    users_resp = supabase.table("users").select("id,username").order("username").execute()
    out = []
    for u in users_resp.data or []:
        s = supabase.table("submissions").select("*").eq("user_id", u["id"]).order("id", {"ascending": False}).limit(1).execute()
        if s.data and len(s.data) > 0:
            out.append({
                "username": u["username"],
                "result_json": s.data[0].get("result_json"),
                "main_pairs": s.data[0].get("main_pairs")
            })
    return out

# ------------------------------
# PBKDF2 hashing helpers
# ------------------------------
def hash_password(password, salt=None):
    """
    Returns (salt_hex, hash_hex)
    """
    if salt is None:
        salt_bytes = os.urandom(16)
    else:
        try:
            salt_bytes = bytes.fromhex(salt)
        except Exception:
            salt_bytes = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt_bytes, 200000)
    return salt_bytes.hex(), dk.hex()

def verify_password(password, salt_hex, hash_hex):
    try:
        salt = bytes.fromhex(salt_hex)
    except Exception:
        return False
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 200000)
    return dk.hex() == hash_hex

# ------------------------------
# End of PART 1
# ------------------------------
# Next: Part 2/3 contains the interactive Streamlit UI (pairwise widgets, pages "Isi Kuesioner", "My Submissions", "Hasil Akhir Penilaian")
# Request: "lanjut part 2"
# ==============================================================
# PART 2 — UI MAIN (Login, Register, Input AHP, Hitung, Export)
# ==============================================================

# --------------------------------------------------------------
# Fungsi UI: Pairwise Comparison Widget
# --------------------------------------------------------------
def pairwise_input_ui(title, items):
    """
    items: list of labels
    returns dict { "a ||| b" : nilai }
    """
    st.subheader(title)
    pairs = list(itertools.combinations(items, 2))
    out = {}

    for a, b in pairs:
        col1, col2, col3 = st.columns([5, 2, 5])
        with col1:
            st.write(f"**{a}**")
        with col2:
            val = st.selectbox(
                f"{a} vs {b}",
                options=[1,2,3,4,5,6,7,8,9],
                index=4,
                key=f"{title}-{a}-{b}"
            )
        with col3:
            st.write(f"**{b}**")

        out[f"{a} ||| {b}"] = val

    return out

# --------------------------------------------------------------
# Fungsi Hitung AHP dari seluruh pairwise
# --------------------------------------------------------------
def compute_full_ahp(main_pairs, sub_pairs_dict):
    # ---- HITUNG MAIN
    M_main = build_matrix_from_pairs(CRITERIA, main_pairs)
    w_main = geometric_mean_weights(M_main)
    cons_main = consistency_metrics(M_main, w_main)

    # ---- HITUNG SUB
    local_results = {}
    global_rows = []

    for crit in CRITERIA:
        subs = SUBCRITERIA.get(crit, [])
        if len(subs) == 0:
            continue

        pairs = sub_pairs_dict.get(crit, {})
        Msub = build_matrix_from_pairs(subs, pairs)
        wsub = geometric_mean_weights(Msub)
        cons_sub = consistency_metrics(Msub, wsub)

        local_results[crit] = {
            "keys": subs,
            "weights": wsub,
            "cons": cons_sub
        }

        # global weight
        idx = CRITERIA.index(crit)
        gw_factor = w_main[idx]
        for sk, sw in zip(subs, wsub):
            global_rows.append({
                "Kriteria": crit,
                "SubKriteria": sk,
                "LocalWeight": sw,
                "GlobalWeight": float(sw * gw_factor)
            })

    df_global = pd.DataFrame(global_rows).sort_values("GlobalWeight", ascending=False)

    result = {
        "main": {"keys": CRITERIA, "weights": w_main, "cons": cons_main},
        "local": local_results,
        "global": df_global.to_dict(orient="records")
    }
    return result

# --------------------------------------------------------------
# Halaman Login
# --------------------------------------------------------------
def page_login():
    st.title("🔐 Login Pengguna")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        ok, data = authenticate_user(username, password)
        if ok:
            st.session_state["auth"] = True
            st.session_state["user"] = data
            st.success("Login berhasil!")
            st.rerun()
        else:
            st.error(data)

    st.info("Belum punya akun?")
    if st.button("Daftar Akun Baru"):
        st.session_state["page"] = "register"
        st.rerun()

# --------------------------------------------------------------
# Halaman Register
# --------------------------------------------------------------
def page_register():
    st.title("📝 Registrasi Pengguna Baru")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    admin_flag = st.checkbox("Daftar sebagai Admin")

    if st.button("Daftar"):
        ok, msg = register_user(username, password, admin_flag)
        if ok:
            st.success(msg)
            st.session_state["page"] = "login"
            st.rerun()
        else:
            st.error(msg)

    if st.button("Kembali ke Login"):
        st.session_state["page"] = "login"
        st.rerun()

# --------------------------------------------------------------
# Halaman Isi Kuesioner
# --------------------------------------------------------------
def page_input_kuesioner():
    st.title("📋 Formulir Penilaian AHP — Penataan Ruang Publik")

    st.info(f"User: **{st.session_state['user']['username']}**")

    st.header("1️⃣ Perbandingan Kriteria Utama")
    main_pairs = pairwise_input_ui("Pairwise Kriteria", CRITERIA)

    st.header("2️⃣ Perbandingan Subkriteria per Kriteria")
    sub_pairs = {}
    for crit in CRITERIA:
        st.subheader(f"### {crit}")
        subs = SUBCRITERIA.get(crit, [])
        if len(subs) == 0:
            st.warning("Tidak ada subkriteria.")
            continue
        sub_pairs[crit] = pairwise_input_ui(f"Subkriteria {crit}", subs)

    if st.button("💾 Hitung & Simpan ke Database"):
        with st.spinner("Menghitung AHP..."):
            result = compute_full_ahp(main_pairs, sub_pairs)

            # simpan
            try:
                save_submission(
                    st.session_state["user"]["id"],
                    main_pairs,
                    sub_pairs,
                    result
                )
                st.success("Berhasil disimpan ke database!")
            except Exception as e:
                st.error(f"❌ Gagal menyimpan ke database: {e}")

        st.session_state["last_result"] = result
        st.session_state["page"] = "hasil"
        st.rerun()

# --------------------------------------------------------------
# Halaman Hasil Perhitungan
# --------------------------------------------------------------
def page_hasil():
    st.title("📊 Hasil Perhitungan AHP Anda")

    if "last_result" not in st.session_state:
        st.warning("Belum ada hasil.")
        return

    result = st.session_state["last_result"]

    # ---- Tampilkan MAIN
    main = result["main"]
    df_main = pd.DataFrame({
        "Kriteria": main["keys"],
        "Bobot": main["weights"]
    })

    st.subheader("🔹 Bobot Kriteria Utama")
    st.dataframe(df_main)

    st.write(f"CI = {main['cons']['CI']:.4f}  |  CR = {main['cons']['CR']:.4f}")

    # ---- GLOBAL
    df_global = pd.DataFrame(result["global"])
    st.subheader("🔹 Bobot Global Subkriteria")
    st.dataframe(df_global)

    # ---- Unduh Excel
    excel_bytes = to_excel_bytes({
        "MainCriteria": df_main,
        "GlobalWeights": df_global
    })

    st.download_button(
        "⬇ Unduh Excel Hasil",
        data=excel_bytes,
        file_name="AHP_Result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ---- Unduh PDF
    try:
        pdf_bytes = generate_pdf_bytes({
            "username": st.session_state["user"]["username"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "result": result
        })

        st.download_button(
            "⬇ Unduh PDF Hasil",
            data=pdf_bytes,
            file_name="AHP_Result.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"PDF gagal dibuat: {e}")

    if st.button("Kembali ke Menu"):
        st.session_state["page"] = "home"
        st.rerun()

# --------------------------------------------------------------
# HOME PAGE
# --------------------------------------------------------------
def page_home():
    st.title("🏠 Beranda AHP Multi-User")

    st.write("Silakan pilih menu di sebelah kiri.")
    st.write(f"User login: **{st.session_state['user']['username']}**")

    if st.button("Isi Kuesioner AHP"):
        st.session_state["page"] = "input"
        st.rerun()

    if st.button("Lihat Hasil Saya"):
        st.session_state["page"] = "my_submissions"
        st.rerun()

    if st.session_state["user"]["is_admin"]:
        st.success("Anda adalah ADMIN.")
        if st.button("Admin Dashboard"):
            st.session_state["page"] = "admin"
            st.rerun()

# --------------------------------------------------------------
# ROUTER
# --------------------------------------------------------------
def run_app():
    # initialize state
    if "page" not in st.session_state:
        st.session_state["page"] = "login"
    if "auth" not in st.session_state:
        st.session_state["auth"] = False

    # login screen if not authenticated
    if not st.session_state["auth"]:
        if st.session_state["page"] == "register":
            page_register()
        else:
            page_login()
        return

    # sidebar
    menu = st.sidebar.radio(
        "Menu",
        ["Home", "Isi Kuesioner", "Hasil Terakhir", "My Submissions"] +
        (["Admin"] if st.session_state["user"]["is_admin"] else [])
    )

    if menu == "Home":
        page_home()
    elif menu == "Isi Kuesioner":
        page_input_kuesioner()
    elif menu == "Hasil Terakhir":
        page_hasil()
    elif menu == "My Submissions":
        st.session_state["page"] = "my_submissions"
        page_my_submissions()
    elif menu == "Admin":
        st.session_state["page"] = "admin"
        page_admin()


# Jalankan aplikasi
run_app()
# ==============================================================
# PART 3 — My Submissions, Admin Panel, Agregasi Gabungan Pakar
# ==============================================================

# ------------------------------
# Page: My Submissions (detail, download, delete)
# ------------------------------
def page_my_submissions():
    st.title("🗂️ Submission Saya")
    user = st.session_state["user"]

    rows = get_submissions_by_user(user["id"])
    if not rows:
        st.info("Anda belum menyimpan submission apapun.")
        return

    for row in rows:
        sid = row.get("id")
        ts = row.get("timestamp")
        rjson = row.get("result_json")
        res = json.loads(rjson) if isinstance(rjson, str) else (rjson or {})

        st.subheader(f"Submission #{sid} — {ts}")
        # show top global
        try:
            df_global = pd.DataFrame(res.get("global", [])).sort_values("GlobalWeight", ascending=False)
            st.table(df_global.head(8))
        except Exception:
            st.write("Gagal menampilkan ringkasan global.")

        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            # download excel
            try:
                df_main = pd.DataFrame({
                    "Kriteria": res.get("main", {}).get("keys", []),
                    "Bobot": res.get("main", {}).get("weights", [])
                })
                df_global_full = pd.DataFrame(res.get("global", [])).sort_values("GlobalWeight", ascending=False)
                excel_bytes = to_excel_bytes({
                    "Kriteria_Utama": df_main,
                    "Global_Weights": df_global_full
                })
                st.download_button(f"Download Excel #{sid}", data=excel_bytes,
                                   file_name=f"submission_{sid}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key=f"dl_ex_{sid}")
            except Exception as e:
                st.warning(f"Excel gagal dibuat: {e}")

        with c2:
            # download pdf
            try:
                submission_row = {"username": user["username"], "timestamp": ts, "result": res}
                pdf_bio = generate_pdf_bytes(submission_row)
                st.download_button(f"Download PDF #{sid}", data=pdf_bio,
                                   file_name=f"submission_{sid}.pdf",
                                   mime="application/pdf",
                                   key=f"dl_pdf_{sid}")
            except Exception as e:
                st.warning(f"PDF gagal: {e}")

        with c3:
            if st.button(f"Hapus #{sid}", key=f"del_{sid}"):
                try:
                    ok, _ = safe_supabase_call(supabase.table("submissions").delete().eq("id", sid).execute)
                    # direct call wrapper above requires function, so do:
                    try:
                        supabase.table("submissions").delete().eq("id", sid).execute()
                        st.success(f"Submission #{sid} dihapus.")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus: {e}")
                except Exception as e:
                    st.error(f"Gagal menghapus: {e}")

# ------------------------------
# Helper: export all submissions to Excel (admin)
# ------------------------------
def export_all_submissions_excel(all_rows):
    # all_rows: list of submission rows with user info if joined
    # Build summary and per-submission sheets
    try:
        df_summary = []
        sheets = {}
        for r in all_rows:
            try:
                res = json.loads(r.get("result_json", "{}")) if isinstance(r.get("result_json"), str) else (r.get("result_json") or {})
            except Exception:
                res = {}
            uid = r.get("user_id") or r.get("user", {}).get("id") or r.get("users", {}).get("id")
            username = (r.get("users") or {}).get("username") if r.get("users") else (r.get("username") or "")
            df_summary.append({
                "id": r.get("id"),
                "user_id": uid,
                "username": username,
                "timestamp": r.get("timestamp"),
                "main_CR": (res.get("main", {}).get("cons") or {}).get("CR") if res else None
            })
            # per-submission sheets
            df_main = pd.DataFrame({
                "Kriteria": res.get("main", {}).get("keys", []),
                "Bobot": res.get("main", {}).get("weights", [])
            })
            df_global = pd.DataFrame(res.get("global", []))
            sheets[f"Main_{r.get('id')}"] = df_main
            sheets[f"Global_{r.get('id')}"] = df_global
        sheets["Ringkasan"] = pd.DataFrame(df_summary)
        return to_excel_bytes(sheets)
    except Exception as e:
        raise

# ------------------------------
# Page: Admin Panel (manage users & submissions, aggregasi)
# ------------------------------
def page_admin():
    st.title("🔧 Admin Panel — Manajemen Pakar & Submissions")
    if not st.session_state["user"]["is_admin"]:
        st.error("Akses ditolak. Anda bukan admin.")
        return

    # fetch all submissions joined with users (client supports rpc or embed)
    try:
        # Try to select with foreign relation "users" (if PostgREST configured to expand)
        all_resp = supabase.table("submissions").select("*, users:users(username, id)").order("id", {"ascending": False}).execute()
        all_rows = all_resp.data or []
    except Exception:
        # fallback plain
        all_rows = get_all_submissions()

    if not all_rows:
        st.info("Belum ada submission.")
        return

    # Show summary table
    summary = []
    for r in all_rows:
        try:
            res = json.loads(r.get("result_json", "{}")) if isinstance(r.get("result_json"), str) else (r.get("result_json") or {})
        except Exception:
            res = {}
        username = (r.get("users") or {}).get("username") if r.get("users") else r.get("username", "")
        summary.append({
            "ID": r.get("id"),
            "User": username,
            "Timestamp": r.get("timestamp"),
            "CR Main": (res.get("main", {}).get("cons") or {}).get("CR") if res else None
        })

    df_summary = pd.DataFrame(summary)
    st.dataframe(df_summary, use_container_width=True)

    # Delete submission by id
    st.markdown("---")
    st.subheader("🗑 Hapus Submission")
    del_id = st.number_input("Masukkan ID submission", min_value=1, step=1, key="admin_del_id")
    if st.button("Hapus Submission (Admin)"):
        try:
            supabase.table("submissions").delete().eq("id", int(del_id)).execute()
            st.success(f"Submission #{del_id} dihapus.")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Gagal menghapus: {e}")

    st.markdown("---")
    # Export all to Excel
    if st.button("📥 Export Semua Data ke Excel"):
        try:
            excel_bytes = export_all_submissions_excel(all_rows)
            st.download_button("Download Excel Semua Data", data=excel_bytes, file_name="all_submissions.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"Gagal export: {e}")

    st.markdown("---")
    st.subheader("📊 Agregasi & Laporan Gabungan Pakar (AIJ & AIP)")

    # Use latest submission per user to avoid duplicates
    try:
        latest = None
        # Prefer RPC if available
        try:
            rpc_resp = supabase.rpc("get_latest_submissions").execute()
            latest = rpc_resp.data or None
        except Exception:
            latest = None

        if latest is None:
            latest = get_latest_submission_per_user()
    except Exception as e:
        st.error(f"Gagal mengambil latest submissions: {e}")
        latest = []

    if not latest:
        st.info("Tidak ada submission terbaru per pakar.")
        return

    st.write(f"Total pakar (unique): {len(latest)}")

    # AIJ
    all_main_matrices = []
    for item in latest:
        # item could be dict with keys 'main_pairs' or 'main' depending on source
        mp = item.get("main_pairs") or (item.get("main_pairs_json") if item.get("main_pairs_json") else None)
        if not mp:
            # maybe result_json present
            try:
                res = json.loads(item.get("result_json")) if isinstance(item.get("result_json"), str) else item.get("result_json")
                if res and res.get("main") and res["main"].get("weights"):
                    all_main_matrices.append(np.array(res["main"].get("weights")))
                    continue
            except Exception:
                pass
            continue
        try:
            mp_dict = json.loads(mp) if isinstance(mp, str) else mp
        except Exception:
            mp_dict = mp
        pair_values = {}
        for k, v in mp_dict.items():
            try:
                a, b = [s.strip() for s in k.split("|||")]
                pair_values[(a, b)] = float(v)
            except Exception:
                continue
        M = build_matrix_from_pairs(CRITERIA, pair_values)
        all_main_matrices.append(M)

    if not all_main_matrices:
        st.warning("Tidak ditemukan matriks main dari pakar.")
        return

    GM = np.exp(np.mean([np.log(m) for m in all_main_matrices], axis=0))
    weights_aij = geometric_mean_weights(GM)
    cons_aij = consistency_metrics(GM, weights_aij)

    df_aij = pd.DataFrame({"Kriteria": CRITERIA, "Bobot_AI J": list(weights_aij)})
    st.subheader("AIJ — Aggregation of Individual Judgments (Kriteria)")
    st.table(df_aij)
    st.write(f"CI={cons_aij['CI']:.4f}, CR={cons_aij['CR']:.4f}")

    # AIP
    collected_priorities = []
    for item in latest:
        try:
            res = json.loads(item.get("result_json")) if isinstance(item.get("result_json"), str) else item.get("result_json")
            if res and res.get("main") and res["main"].get("weights"):
                collected_priorities.append(np.array(res["main"]["weights"]))
        except Exception:
            continue

    if not collected_priorities:
        st.warning("Tidak ditemukan bobot prioritas dari pakar untuk AIP.")
    else:
        AIP_vec = np.exp(np.mean(np.log(np.vstack(collected_priorities)), axis=0))
        AIP_vec = AIP_vec / AIP_vec.sum()
        df_aip = pd.DataFrame({"Kriteria": CRITERIA, "Bobot_AIP": list(AIP_vec)})
        st.subheader("AIP — Aggregation of Individual Priorities")
        st.table(df_aip)

    # Global ranking (use AIJ main weights)
    st.subheader("Ranking Global Sub-Kriteria (menggunakan AIJ sebagai bobot utama)")
    global_rows = []
    for item in latest:
        try:
            res = json.loads(item.get("result_json")) if isinstance(item.get("result_json"), str) else item.get("result_json")
            if not res or not res.get("local"):
                continue
            for grp in CRITERIA:
                local_w = np.array(res["local"][grp]["weights"])
                local_w = local_w / local_w.sum()
                idx = CRITERIA.index(grp)
                for sk, lw in zip(SUBCRITERIA[grp], local_w):
                    global_rows.append({
                        "Kriteria": grp,
                        "SubKriteria": sk,
                        "LocalWeight": float(lw),
                        "MainWeight": float(weights_aij[idx]),
                        "GlobalWeight": float(lw * weights_aij[idx])
                    })
        except Exception:
            continue

    df_global = pd.DataFrame(global_rows).sort_values("GlobalWeight", ascending=False)
    st.table(df_global.head(50))

    # Downloads: Excel & PDF final
    st.markdown("---")
    st.subheader("Unduh Laporan Gabungan")

    try:
        excel_bytes = to_excel_bytes({
            "AIJ": df_aij,
            "AIP": (df_aip if 'df_aip' in locals() else pd.DataFrame({"Kriteria": CRITERIA, "Bobot_AIP": [None]*len(CRITERIA)})),
            "GlobalRanking": df_global
        })
        st.download_button("📥 Unduh Excel Gabungan", data=excel_bytes, file_name="AHP_Gabungan.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"Gagal membuat Excel gabungan: {e}")

    # PDF summary (simple)
    try:
        submission_row = {
            "username": "GABUNGAN_PAKAR",
            "timestamp": datetime.now().isoformat(),
            "result": {
                "main": {"keys": CRITERIA, "weights": list(weights_aij), "cons": cons_aij},
                "global": df_global.to_dict(orient="records")
            }
        }
        pdf_bio = generate_pdf_bytes(submission_row)
        st.download_button("📄 Unduh PDF Gabungan", data=pdf_bio, file_name="AHP_Gabungan.pdf",
                           mime="application/pdf")
    except Exception as e:
        st.error(f"Gagal membuat PDF gabungan: {e}")


# ------------------------------
# Wire up pages into router if run_app uses names
# If run_app references page_my_submissions or page_admin, ensure those names exist.
# ------------------------------
# If run_app from Part2 calls page_my_submissions() and page_admin(), these functions will now resolve.

# (Do not call run_app() again — Part2 already invoked run_app())
# End of PART 3
