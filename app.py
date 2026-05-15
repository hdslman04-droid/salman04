import io
from pathlib import Path
import pandas as pd
import streamlit as st

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(page_title="Sistem Hierarki Pangkat Tentera",
                   page_icon="🪖", layout="wide")

st.title("🪖 Sistem Hierarki Pangkat Tentera")
st.caption("Upload fail CSV/Excel untuk susun anggota mengikut hierarki pangkat, nombor tentera, "
           "serta tapis ikut unit dan semak duplicate.")

# =========================================================
# HIERARCHI & ALIASES
# =========================================================
RANK_HIERARCHY = {
    "jeneral":1,"leftenan jeneral":2,"mejar jeneral":3,"brigedier jeneral":4,
    "kolonel":5,"leftenan kolonel":6,"mejar":7,"kapten":8,"leftenan":9,
    "leftenan muda":10,"pegawai waran 1":11,"pegawai waran 2":12,
    "staf sarjan":13,"sarjan":14,"koperal":15,"lans koperal":16,"prebet":17
}

RANK_ALIASES = {
    "lt jeneral":"leftenan jeneral","lt. jeneral":"leftenan jeneral",
    "mej jeneral":"mejar jeneral","brig jen":"brigedier jeneral","brig. jeneral":"brigedier jeneral",
    "lt kolonel":"leftenan kolonel","lt. kolonel":"leftenan kolonel","lt kol":"leftenan kolonel",
    "lt. kol":"leftenan kolonel","captain":"kapten","capt":"kapten","lt":"leftenan",
    "2nd lt":"leftenan muda","second lieutenant":"leftenan muda",
    "pw1":"pegawai waran 1","pw 1":"pegawai waran 1","pw2":"pegawai waran 2","pw 2":"pegawai waran 2",
    "ssjn":"staf sarjan","sarjan staf":"staf sarjan","lkpl":"lans koperal","l/kpl":"lans koperal",
    "pbt":"prebet"
}

REQUIRED_COLUMNS = ["nama","no_tentera","pangkat"]

# =========================================================
# HELPERS
# =========================================================
def normalize_text(x): return "" if pd.isna(x) else str(x).strip().lower()
def prettify_text(x): return "" if pd.isna(x) else str(x).strip()
def normalize_rank(r): return RANK_ALIASES.get(normalize_text(r), normalize_text(r))
def get_rank_level(r): return RANK_HIERARCHY.get(normalize_rank(r), 999)
def extract_number_for_sort(v):
    s = prettify_text(v)
    digits = "".join(c for c in s if c.isdigit())
    return int(digits) if digits else 999999999
def validate_columns(df):
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]
def convert_df_to_csv(df): return df.to_csv(index=False).encode("utf-8-sig")
def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer,index=False,sheet_name="hierarki_tentera")
    return output.getvalue()
def build_rank_summary(df):
    summary = (df.groupby(["level_pangkat","pangkat_standard"],dropna=False)
                .size().reset_index(name="jumlah")
                .sort_values(["level_pangkat","pangkat_standard"]))
    return summary

# =========================================================
# LOAD FILE SAFE
# =========================================================
@st.cache_data
def load_file(uploaded_file):
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix==".csv": df=pd.read_csv(uploaded_file)
    elif suffix in [".xlsx",".xls"]: df=pd.read_excel(uploaded_file)
    else: raise ValueError("Upload CSV atau Excel sahaja.")
    df.columns = [prettify_text(c) for c in df.columns]
    return df

# =========================================================
# PREPARE DATA - ultimate safe
# =========================================================
def prepare_data(df):
    data = df.copy()
    for col in data.columns:
        try:
            data[col] = data[col].apply(lambda x: "" if pd.isna(x) else str(x).strip())
        except:
            data[col] = pd.Series([""]*len(data),index=data.index)
    for optional_col in ["unit","jawatan","bilik","kompeni","platun","subunit"]:
        if optional_col not in data.columns:
            data[optional_col] = pd.Series([""]*len(data),index=data.index)
    data["pangkat_asal"] = data.get("pangkat",pd.Series([""]*len(data),index=data.index))
    data["pangkat_standard"] = data["pangkat"].apply(normalize_rank)
    data["level_pangkat"] = data["pangkat_standard"].apply(get_rank_level)
    # Safe search columns
    search_cols = ["nama","no_tentera","unit","jawatan","bilik","kompeni","platun","subunit"]
    for col in search_cols:
        search_col = f"{col}_carian"
        try: data[search_col] = data[col].apply(lambda x: str(x).lower() if pd.notna(x) else "")
        except: data[search_col] = pd.Series([""]*len(data),index=data.index)
    data["no_tentera_numeric"] = data["no_tentera"].apply(extract_number_for_sort)
    data["no_tentera_text"] = data["no_tentera"].fillna("").astype(str)
    return data

# =========================================================
# SIDEBAR SETTINGS
# =========================================================
st.sidebar.header("Tetapan Sistem")
uploaded_file = st.sidebar.file_uploader("Upload fail anggota", type=["csv","xlsx","xls"])
sort_by_number = st.sidebar.checkbox("Susun nombor tentera",value=True)
show_unknown_rank_only = st.sidebar.checkbox("Tunjuk pangkat tidak dikenali sahaja",value=False)
show_duplicates_only = st.sidebar.checkbox("Tunjuk duplicate nombor tentera sahaja",value=False)

# =========================================================
# MAIN LOGIC
# =========================================================
if uploaded_file is None:
    st.info("Sila upload fail CSV/Excel untuk mula.")
    st.stop()

try: raw_df = load_file(uploaded_file)
except Exception as e: st.error(f"Gagal membaca fail: {e}"); st.stop()

missing_cols = validate_columns(raw_df)
if missing_cols:
    st.error("Kolum wajib tiada dalam fail: "+", ".join(missing_cols))
    st.write("Kolum ditemui:", list(raw_df.columns))
    st.stop()

df = prepare_data(raw_df)

# =========================================================
# FILTERS SAFE
# =========================================================
f1,f2,f3,f4 = st.columns(4)
with f1:
    unit_values = sorted([str(u) for u in df["unit"].fillna("").tolist() if str(u).strip()!=""])
    selected_unit = st.selectbox("Pilih unit",["Semua"]+unit_values)
with f2:
    rank_values = sorted([str(r) for r in df["pangkat_standard"].fillna("").tolist() if str(r).strip()!=""])
    selected_rank = st.selectbox("Pilih pangkat",["Semua"]+rank_values)
with f3:
    room_values = sorted([str(b) for b in df["bilik"].fillna("").tolist() if str(b).strip()!=""])
    selected_room = st.selectbox("Pilih bilik",["Semua"]+room_values)
with f4:
    keyword = st.text_input("Carian","Nama / no tentera / jawatan")

filtered = df.copy()
if selected_unit!="Semua": filtered = filtered[filtered["unit"]==selected_unit]
if selected_rank!="Semua": filtered = filtered[filtered["pangkat_standard"]==selected_rank]
if selected_room!="Semua": filtered = filtered[filtered["bilik"]==selected_room]
if keyword.strip():
    k = keyword.strip().lower()
    filtered = filtered[
        filtered["nama_carian"].str.contains(k,na=False) |
        filtered["no_tentera_carian"].str.contains(k,na=False) |
        filtered["jawatan_carian"].str.contains(k,na=False)
    ]
if show_unknown_rank_only: filtered = filtered[filtered["level_pangkat"]==999]

duplicate_mask = filtered["no_tentera"].astype(str).duplicated(keep=False)
duplicates_df = filtered[duplicate_mask].copy()
if show_duplicates_only: filtered = duplicates_df.copy()

sort_columns=["level_pangkat"]
if sort_by_number: sort_columns.append("no_tentera_numeric")
sort_columns.extend(["no_tentera_text","nama"])
if not filtered.empty: filtered = filtered.sort_values(by=sort_columns,ascending=True).reset_index(drop=True)

# =========================================================
# METRICS
# =========================================================
st.subheader("Ringkasan")
total_records=len(df); filtered_records=len(filtered)
duplicate_count=int(df["no_tentera"].astype(str).duplicated(keep=False).sum())
unknown_rank_count=int((df["level_pangkat"]==999).sum())
m1,m2,m3,m4 = st.columns(4)
m1.metric("Jumlah rekod",total_records); m2.metric("Rekod selepas tapis",filtered_records)
m3.metric("Duplicate no tentera",duplicate_count); m4.metric("Pangkat tidak dikenali",unknown_rank_count)

# =========================================================
# RANK SUMMARY
# =========================================================
st.subheader("Rumusan Mengikut Hierarki Pangkat")
rank_summary = build_rank_summary(filtered)
st.dataframe(rank_summary,use_container_width=True)

# =========================================================
# DUPLICATES
# =========================================================
st.subheader("Semakan Duplicate Nombor Tentera")
if len(duplicates_df)>0:
    st.warning("Terdapat duplicate nombor tentera dalam data yang ditapis.")
    duplicate_display_cols=[c for c in ["nama","no_tentera","pangkat","unit","jawatan","bilik"] if c in duplicates_df.columns]
    st.dataframe(duplicates_df[duplicate_display_cols].sort_values(["no_tentera","nama"]),use_container_width=True)
else: st.success("Tiada duplicate nombor tentera dikesan untuk data yang ditapis.")

# =========================================================
# MAIN TABLE
# =========================================================
st.subheader("Senarai Anggota Mengikut Hierarki")
display_columns=[c for c in ["nama","no_tentera","pangkat","pangkat_standard","level_pangkat","unit","jawatan","bilik"] if c in filtered.columns]
st.dataframe(filtered[display_columns],use_container_width=True)

# =========================================================
# DOWNLOAD
# =========================================================
st.subheader("Muat Turun Data Yang Telah Disusun")
download_df=filtered[display_columns].copy()
d1,d2 = st.columns(2)
with d1: st.download_button("⬇️ Download CSV",data=convert_df_to_csv(download_df),file_name="anggota_tentera_disusun.csv",mime="text/csv")
with d2: st.download_button("⬇️ Download Excel",data=convert_df_to_excel(download_df),file_name="anggota_tentera_disusun.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =========================================================
# TREEVIEW / CHAIN OF COMMAND
# =========================================================
st.subheader("🌳 Visual Chain of Command (TreeView)")

tree_columns = ["unit","subunit","kompeni","platun","pangkat_standard","nama","no_tentera"]
tree_df = filtered.copy()
for col in tree_columns:
    if col not in tree_df.columns: tree_df[col]=""
tree_df = tree_df.sort_values(by=["unit","subunit","kompeni","platun","level_pangkat","nama"]).reset_index(drop=True)

def print_tree(df, indent=0):
    grouped = df.groupby(["unit","subunit","kompeni","platun"], dropna=False)
    for (unit,subunit,kompeni,platun), group in grouped:
        prefix="    "*indent
        title=f"{prefix}- Unit: {unit}" if unit else f"{prefix}- (No Unit)"
        if subunit: title+=f" | Subunit: {subunit}"
        if kompeni: title+=f" | Kompeni: {kompeni}"
        if platun: title+=f" | Platun: {platun}"
        st.markdown(f"**{title}**")
        for _, row in group.iterrows():
            member_prefix="    "*(indent+1)
            st.markdown(f"{member_prefix}- {row['pangkat_standard'].title()} — {row['nama']} ({row['no_tentera']})")

print_tree(tree_df)

# =========================================================
# RAW DATA
# =========================================================
with st.expander("Lihat data asal"):
    st.dataframe(raw_df,use_container_width=True)
