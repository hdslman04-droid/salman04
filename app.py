import pandas as pd
import streamlit as st

# ==========================
# Upload file section
# ==========================
st.title("Sistem Hierarki Pangkat Tentera")
uploaded_file = st.file_uploader("Upload fail CSV/Excel", type=["csv", "xlsx"])

if uploaded_file is not None:
    # Load the data
    df = pd.read_excel(uploaded_file)

    # Check for necessary columns
    if 'no_tentera' not in df.columns:
        st.error("Column 'no_tentera' is missing from the data.")
        st.stop()

    # ==========================
    # Step 1: Detect first 3 no_tentera
    # ==========================
    first_three_no_tentera = df['no_tentera'].head(3).tolist()

    # ==========================
    # Step 2: Sort the data by 'no_tentera'
    # ==========================
    sorted_df = df.sort_values(by='no_tentera')

    # ==========================
    # Step 3: Filter out the first 3 no_tentera for display
    # ==========================
    first_three_data = sorted_df[sorted_df['no_tentera'].isin(first_three_no_tentera)]

    # ==========================
    # Step 4: Combine first 3 with the rest of the data
    # ==========================
    final_sorted_df = pd.concat([first_three_data, sorted_df[~sorted_df['no_tentera'].isin(first_three_no_tentera)]])
    final_sorted_df = final_sorted_df.reset_index(drop=True)

    # Display the final sorted DataFrame
    st.write(final_sorted_df)

    # Optional: Button to download the sorted data as a CSV file
    st.download_button(
        label="Download Sorted Data",
        data=final_sorted_df.to_csv(index=False).encode('utf-8'),
        file_name="sorted_military_data.csv",
        mime="text/csv"
    )
else:
    st.info("Please upload a CSV/Excel file.")

# =========================================================
# HIERARKI PANGKAT
# Nombor lebih kecil = pangkat lebih tinggi
# Boleh ubah ikut struktur sebenar organisasi anda
# =========================================================
RANK_HIERARCHY = {
    "jeneral": 1,
    "leftenan jeneral": 2,
    "mejar jeneral": 3,
    "brigedier jeneral": 4,
    "kolonel": 5,
    "leftenan kolonel": 6,
    "mejar": 7,
    "kapten": 8,
    "leftenan": 9,
    "leftenan muda": 10,
    "pegawai waran 1": 11,
    "pegawai waran 2": 12,
    "staf sarjan": 13,
    "sarjan": 14,
    "koperal": 15,
    "lans koperal": 16,
    "prebet": 17
}

# Alias / variasi ejaan pangkat
RANK_ALIASES = {
    "lt jeneral": "leftenan jeneral",
    "lt. jeneral": "leftenan jeneral",
    "mej jeneral": "mejar jeneral",
    "brig jen": "brigedier jeneral",
    "brig. jeneral": "brigedier jeneral",
    "lt kolonel": "leftenan kolonel",
    "lt. kolonel": "leftenan kolonel",
    "lt kol": "leftenan kolonel",
    "lt. kol": "leftenan kolonel",
    "captain": "kapten",
    "capt": "kapten",
    "lt": "leftenan",
    "2nd lt": "leftenan muda",
    "second lieutenant": "leftenan muda",
    "pw1": "pegawai waran 1",
    "pw 1": "pegawai waran 1",
    "pw2": "pegawai waran 2",
    "pw 2": "pegawai waran 2",
    "ssjn": "staf sarjan",
    "sarjan staf": "staf sarjan",
    "lkpl": "lans koperal",
    "l/kpl": "lans koperal",
    "pbt": "prebet"
}

# Kolum minimum yang sistem perlukan
REQUIRED_COLUMNS = ["nama", "no_tentera", "pangkat"]

# Kolum alternatif jika fail asal tidak ikut nama standard
COLUMN_ALIASES = {
    "nama": ["nama", "name", "full_name", "anggota", "nama_anggota"],
    "no_tentera": ["no_tentera", "nombor_tentera", "military_no", "no tentera", "army_no", "service_no"],
    "pangkat": ["pangkat", "rank"],
    "unit": ["unit", "pasukan", "batalion", "kompeni", "cawangan"],
    "jawatan": ["jawatan", "position", "role", "appointment"],
    "bilik": ["bilik", "room", "no_bilik", "room_no", "bilik_penginapan"]
}

# =========================================================
# HELPERS
# =========================================================
def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()

def prettify_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tukar nama kolum kepada format standard jika jumpa padanan.
    """
    df = df.copy()
    original_columns = list(df.columns)
    normalized_columns = [normalize_text(c) for c in original_columns]
    rename_map = {}

    for standard_name, alias_list in COLUMN_ALIASES.items():
        alias_set = {normalize_text(a) for a in alias_list}
        for original, normalized in zip(original_columns, normalized_columns):
            if normalized in alias_set and original not in rename_map:
                rename_map[original] = standard_name
                break

    return df.rename(columns=rename_map)

def normalize_rank(rank: str) -> str:
    r = normalize_text(rank)
    if r in RANK_ALIASES:
        r = RANK_ALIASES[r]
    return r

def get_rank_level(rank: str) -> int:
    r = normalize_rank(rank)
    return RANK_HIERARCHY.get(r, 999)

def extract_number_for_sort(value: str) -> int:
    """
    Ambil digit daripada nombor tentera untuk sorting.
    Contoh T10002 -> 10002
    Jika tiada digit, letak nombor besar.
    """
    s = prettify_text(value)
    digits = "".join(ch for ch in s if ch.isdigit())
    if digits:
        return int(digits)
    return 999999999

@st.cache_data
def load_file(uploaded_file) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(uploaded_file)
    elif suffix in [".xlsx", ".xls"]:
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Format fail tidak disokong. Sila upload CSV atau Excel.")

    df.columns = [prettify_text(c) for c in df.columns]
    df = standardize_columns(df)
    return df

def validate_columns(df: pd.DataFrame):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return missing

def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()

    # Bersihkan semua kolum jenis object
    for col in data.columns:
        if data[col].dtype == "object":
            data[col] = data[col].astype(str).str.strip()

    # Pastikan kolum optional wujud
    for optional_col in ["unit", "jawatan", "bilik"]:
        if optional_col not in data.columns:
            data[optional_col] = ""

    # Simpan nilai asal
    data["pangkat_asal"] = data["pangkat"]

    # Standardkan pangkat
    data["pangkat_standard"] = data["pangkat"].apply(normalize_rank)
    data["level_pangkat"] = data["pangkat_standard"].apply(get_rank_level)

    # Medan carian
    data["nama_carian"] = data["nama"].astype(str).str.lower()
    data["no_tentera_carian"] = data["no_tentera"].astype(str).str.lower()
    data["unit_carian"] = data["unit"].astype(str).str.lower()
    data["jawatan_carian"] = data["jawatan"].astype(str).str.lower()
    data["bilik_carian"] = data["bilik"].astype(str).str.lower()

    # Untuk sorting nombor tentera
    data["no_tentera_numeric"] = data["no_tentera"].apply(extract_number_for_sort)
    data["no_tentera_text"] = data["no_tentera"].astype(str)

    return data

def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")

def convert_df_to_excel(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="hierarki_tentera")
    return output.getvalue()

def build_rank_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(["level_pangkat", "pangkat_standard"], dropna=False)
        .size()
        .reset_index(name="jumlah")
        .sort_values(["level_pangkat", "pangkat_standard"])
    )
    return summary

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("Tetapan Sistem")

uploaded_file = st.sidebar.file_uploader(
    "Upload fail anggota",
    type=["csv", "xlsx", "xls"]
)

sort_by_number = st.sidebar.checkbox("Susun nombor tentera", value=True)
show_unknown_rank_only = st.sidebar.checkbox("Tunjuk pangkat tidak dikenali sahaja", value=False)
show_duplicates_only = st.sidebar.checkbox("Tunjuk duplicate nombor tentera sahaja", value=False)

# =========================================================
# MAIN
# =========================================================
if uploaded_file is None:
    st.info("Sila upload fail CSV atau Excel untuk mula.")
    st.markdown("""
### Format minimum fail
Fail perlu ada sekurang-kurangnya kolum berikut:
- `nama`
- `no_tentera`
- `pangkat`

### Kolum tambahan yang disokong
- `unit`
- `jawatan`
- `bilik`

### Contoh ringkas
| nama | no_tentera | pangkat | unit | jawatan | bilik |
|---|---|---|---|---|---|
| Ahmad bin Ali | T10001 | Kolonel | Batalion Jebat | CO | A1 |
| Mohd Faiz | T10002 | Leftenan Kolonel | Batalion Jebat | 2IC | A2 |
| Zulhilmi | T10003 | Mejar | Batalion Jebat | Pegawai Operasi | B1 |
""")
    st.stop()

try:
    raw_df = load_file(uploaded_file)
except Exception as e:
    st.error(f"Gagal membaca fail: {e}")
    st.stop()

missing_cols = validate_columns(raw_df)
if missing_cols:
    st.error(
        "Kolum wajib tiada dalam fail anda: "
        + ", ".join(missing_cols)
        + ". Sila betulkan nama kolum atau tambah kolum tersebut."
    )
    st.write("Kolum yang sistem jumpa:", list(raw_df.columns))
    st.stop()

df = prepare_data(raw_df)

# =========================================================
# FILTERS
# =========================================================
st.subheader("Penapis dan Carian")

f1, f2, f3, f4 = st.columns(4)

with f1:
    unit_values = sorted([u for u in df["unit"].dropna().astype(str).unique() if u.strip() != ""])
    selected_unit = st.selectbox("Pilih unit", ["Semua"] + unit_values)

with f2:
    rank_values = sorted([r for r in df["pangkat_standard"].dropna().astype(str).unique() if r.strip() != ""])
    selected_rank = st.selectbox("Pilih pangkat", ["Semua"] + rank_values)

with f3:
    room_values = sorted([b for b in df["bilik"].dropna().astype(str).unique() if b.strip() != ""])
    selected_room = st.selectbox("Pilih bilik", ["Semua"] + room_values)

with f4:
    keyword = st.text_input("Carian", placeholder="Nama / no tentera / jawatan")

filtered = df.copy()

if selected_unit != "Semua":
    filtered = filtered[filtered["unit"] == selected_unit]

if selected_rank != "Semua":
    filtered = filtered[filtered["pangkat_standard"] == selected_rank]

if selected_room != "Semua":
    filtered = filtered[filtered["bilik"] == selected_room]

if keyword.strip():
    k = keyword.strip().lower()
    filtered = filtered[
        filtered["nama_carian"].str.contains(k, na=False)
        | filtered["no_tentera_carian"].str.contains(k, na=False)
        | filtered["jawatan_carian"].str.contains(k, na=False)
    ]

if show_unknown_rank_only:
    filtered = filtered[filtered["level_pangkat"] == 999]

# Semak duplicate nombor tentera
duplicate_mask = filtered["no_tentera"].astype(str).duplicated(keep=False)
duplicates_df = filtered[duplicate_mask].copy()

if show_duplicates_only:
    filtered = duplicates_df.copy()

# Sorting utama: pangkat -> no tentera -> nama
sort_columns = ["level_pangkat"]
if sort_by_number:
    sort_columns.append("no_tentera_numeric")
sort_columns.extend(["no_tentera_text", "nama"])

filtered = filtered.sort_values(by=sort_columns, ascending=True).reset_index(drop=True)

# =========================================================
# METRICS
# =========================================================
st.subheader("Ringkasan")

total_records = len(df)
filtered_records = len(filtered)
duplicate_count = int(df["no_tentera"].astype(str).duplicated(keep=False).sum())
unknown_rank_count = int((df["level_pangkat"] == 999).sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("Jumlah rekod", total_records)
m2.metric("Rekod selepas tapis", filtered_records)
m3.metric("Duplicate no tentera", duplicate_count)
m4.metric("Pangkat tidak dikenali", unknown_rank_count)

# =========================================================
# RANK SUMMARY
# =========================================================
st.subheader("Rumusan Mengikut Hierarki Pangkat")
rank_summary = build_rank_summary(filtered)
st.dataframe(rank_summary, use_container_width=True)

# =========================================================
# DUPLICATES
# =========================================================
st.subheader("Semakan Duplicate Nombor Tentera")

if len(duplicates_df) > 0:
    st.warning("Terdapat duplicate nombor tentera dalam data yang ditapis.")
    duplicate_display_cols = [c for c in ["nama", "no_tentera", "pangkat", "unit", "jawatan", "bilik"] if c in duplicates_df.columns]
    st.dataframe(
        duplicates_df[duplicate_display_cols].sort_values(["no_tentera", "nama"]),
        use_container_width=True
    )
else:
    st.success("Tiada duplicate nombor tentera dikesan untuk data yang ditapis.")

# =========================================================
# MAIN TABLE
# =========================================================
st.subheader("Senarai Anggota Mengikut Hierarki")

display_columns = [
    "nama",
    "no_tentera",
    "pangkat",
    "pangkat_standard",
    "level_pangkat",
    "unit",
    "jawatan",
    "bilik"
]
display_columns = [c for c in display_columns if c in filtered.columns]

st.dataframe(filtered[display_columns], use_container_width=True)

# =========================================================
# DOWNLOAD
# =========================================================
st.subheader("Muat Turun Data Yang Telah Disusun")

download_df = filtered[display_columns].copy()

d1, d2 = st.columns(2)

with d1:
    st.download_button(
        label="⬇️ Download CSV",
        data=convert_df_to_csv(download_df),
        file_name="anggota_tentera_disusun.csv",
        mime="text/csv"
    )

with d2:
    st.download_button(
        label="⬇️ Download Excel",
        data=convert_df_to_excel(download_df),
        file_name="anggota_tentera_disusun.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# =========================================================
# CHAIN OF COMMAND PREVIEW
# =========================================================
st.subheader("Paparan Ringkas Chain of Command")

preview_df = filtered[display_columns].copy()
preview_df = preview_df.sort_values(sort_columns).head(20)

if len(preview_df) == 0:
    st.info("Tiada data untuk dipaparkan.")
else:
    for _, row in preview_df.iterrows():
        pangkat = str(row.get("pangkat_standard", "")).title()
        nama = str(row.get("nama", ""))
        no_tentera = str(row.get("no_tentera", ""))
        unit = str(row.get("unit", ""))
        jawatan = str(row.get("jawatan", ""))
        bilik = str(row.get("bilik", ""))

        line = f"**{pangkat}** — {nama} ({no_tentera})"
        extras = []

        if unit.strip():
            extras.append(unit)
        if jawatan.strip():
            extras.append(jawatan)
        if bilik.strip():
            extras.append(f"Bilik: {bilik}")

        if extras:
            line += " | " + " | ".join(extras)

        st.write(line)

# =========================================================
# RAW DATA
# =========================================================
with st.expander("Lihat data asal"):
    st.dataframe(raw_df, use_container_width=True)
