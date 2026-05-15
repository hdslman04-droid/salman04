# app.py
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw
import io
import base64

# -------------------- CONFIG --------------------
st.set_page_config(
    page_title="MMR KPA (GAJI)",
    page_icon="TDM.png",
    layout="centered",
    initial_sidebar_state="expanded"
)

DATA_FILE = "data baru 1.csv"
ATTENDANCE_FILE = "attendance_records.csv"
LOGO_UGAT = "Logo-UGAT.png"
CENTER_IMAGE = "GAMBAR BARU 3.png"
DEFAULT_HOST_PASSWORD = "salman"
REQUIRED_COLS = ["BIL", "NOTEN", "NAMA", "MENU", "MEJA"]

# -------------------- FUNCTIONS --------------------
def prepare_csv(file_path):
    """Read CSV and clean up columns, add optional columns if missing"""
    path = Path(file_path)
    if not path.exists():
        return pd.DataFrame(columns=REQUIRED_COLS)

    df_raw = pd.read_csv(file_path, dtype=str)
    df_raw.columns = [str(col).strip().upper() for col in df_raw.columns]

    # Keep only required columns, add optional if missing
    for col in REQUIRED_COLS:
        if col not in df_raw.columns:
            df_raw[col] = ""

    # Add optional columns for flexibility
    for col in ["UNIT", "JAWATAN", "BILIK", "CATATAN"]:
        if col not in df_raw.columns:
            df_raw[col] = ""

    # Strip all string columns
    for col in df_raw.columns:
        df_raw[col] = df_raw[col].fillna("").astype(str).str.strip()

    return df_raw

def read_attendance(file_path):
    path = Path(file_path)
    if not path.exists():
        return pd.DataFrame(columns=REQUIRED_COLS + ["STATUS_KEHADIRAN", "TARIKH_MASA"])
    df = pd.read_csv(path, dtype=str)
    df.columns = [str(col).strip().upper() for col in df.columns]
    return df

def save_attendance(df):
    df.to_csv(ATTENDANCE_FILE, index=False, encoding="utf-8")

def get_seat_map():
    """Return a dictionary of MEJA coordinates for highlighting"""
    return {
        "AR3": {"x": 76, "y": 86, "w": 42, "h": 24},
        "AR2": {"x": 72, "y": 86, "w": 42, "h": 24},
        "DL11": {"x": 48, "y": 33, "w": 42, "h": 24},
        "DL12": {"x": 44, "y": 33, "w": 42, "h": 24},
        # Add more MEJA coordinates according to your layout
    }

def highlight_layout(group_df):
    """Highlight the MEJA seats on the seating layout"""
    path = Path(CENTER_IMAGE)
    if not path.exists():
        return None

    image = Image.open(path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    seat_map = get_seat_map()
    missing_meja = []

    meja_list = group_df["MEJA"].dropna().astype(str).str.strip().str.upper().unique()

    for meja in meja_list:
        if meja in seat_map:
            info = seat_map[meja]
            x, y, w, h = info["x"], info["y"], info["w"], info["h"]
            draw.rectangle([x - w//2, y - h//2, x + w//2, y + h//2],
                           fill=(0, 255, 0, 90),
                           outline=(0, 255, 0, 255),
                           width=4)
        else:
            missing_meja.append(meja)

    highlighted = Image.alpha_composite(image, overlay)
    img_byte_arr = io.BytesIO()
    highlighted.convert("RGB").save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    layout_base64 = base64.b64encode(img_byte_arr.getvalue()).decode()

    return layout_base64, missing_meja

def verify_host(password_input):
    return password_input == DEFAULT_HOST_PASSWORD

# -------------------- LOAD DATA --------------------
df_guests = prepare_csv(DATA_FILE)
df_attendance = read_attendance(ATTENDANCE_FILE)

# -------------------- SIDEBAR HOST --------------------
if "host_logged_in" not in st.session_state:
    st.session_state.host_logged_in = False

with st.sidebar:
    if st.session_state.host_logged_in:
        st.success("Logged in as Host")
        uploaded_file = st.file_uploader("Upload CSV", type="csv")
        if uploaded_file:
            df_new = prepare_csv(uploaded_file)
            df_new.to_csv(DATA_FILE, index=False)
            save_attendance(pd.DataFrame(columns=REQUIRED_COLS + ["STATUS_KEHADIRAN", "TARIKH_MASA"]))
            st.success("CSV uploaded and attendance reset.")
        if st.button("Logout"):
            st.session_state.host_logged_in = False
    else:
        password = st.text_input("Host Password", type="password")
        if st.button("Login"):
            if verify_host(password):
                st.session_state.host_logged_in = True
                st.success("Login successful")
            else:
                st.error("Wrong password")

# -------------------- USER SEARCH --------------------
st.title("Majlis Makan Malam Rejimental Penghargaan Brigedier Jeneral Dato’ Zamzuri bin Harun")

search_no = st.text_input("Enter Nombor Tentera:")
if search_no:
    search_no = search_no.strip()
    bil_value = ""
    for guest in df_guests.itertuples():
        if search_no in getattr(guest, "NOTEN"):
            bil_value = getattr(guest, "BIL")
            break

    if bil_value:
        group_df = df_guests[df_guests["BIL"] == bil_value]
        st.subheader("Guest Information")
        st.table(group_df)

        layout_base64, missing_meja = highlight_layout(group_df)
        if layout_base64:
            st.image(f"data:image/png;base64,{layout_base64}", use_column_width=True)
            if missing_meja:
                st.warning(f"These MEJA are missing in layout: {', '.join(missing_meja)}")

        all_present = all([n in df_attendance["NOTEN"].tolist() for n in group_df["NOTEN"].tolist()])
        if all_present:
            st.success("✅ All marked as present")
        elif st.session_state.host_logged_in:
            if st.button("Submit / Mark Attendance for this group"):
                now = datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).strftime("%Y-%m-%d %H:%M:%S")
                for guest in group_df.itertuples():
                    if guest.NOTEN not in df_attendance["NOTEN"].tolist():
                        df_attendance.loc[len(df_attendance)] = [
                            guest.BIL, guest.NOTEN, guest.NAMA, guest.MENU, guest.MEJA, "HADIR", now
                        ]
                save_attendance(df_attendance)
                st.success("Attendance submitted")
        else:
            st.warning("❌ Not all marked as present. Login as Host to submit.")
    else:
        st.warning("No record found")
