import pandas as pd
import streamlit as st

# ==========================
# CONFIGURATION
# ==========================
st.set_page_config(
    page_title="Sistem Hierarki Pangkat Tentera",
    page_icon="🪖",
    layout="wide"
)

st.title("🪖 Sistem Hierarki Pangkat Tentera")
st.caption("Upload fail CSV/Excel untuk susun anggota mengikut hierarki pangkat, nombor tentera, dan servis.")

# ==========================
# UPLOAD FILE
# ==========================
uploaded_file = st.sidebar.file_uploader("Upload fail anggota", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    # Load the file
    df = pd.read_excel(uploaded_file)
    
    # ==========================
    # ADD 'SERVICE' BASED ON 'no_tentera'
    # ==========================
    def assign_service(no_tentera):
        no_tentera = str(no_tentera)
        if no_tentera.startswith('37'):
            return 'Air Force'
        elif no_tentera.startswith('N/40'):
            return 'Navy'
        elif no_tentera.startswith('30'):
            return 'Army'
        else:
            return 'Other'

    # Apply the function to the 'no_tentera' column to create the 'service' column
    df['service'] = df['no_tentera'].apply(assign_service)

    # Display services for verification
    st.write(df[['no_tentera', 'service']].drop_duplicates())

    # ==========================
    # PROCESSING DATA FOR EACH SERVICE
    # ==========================
    for service in df['service'].unique():
        st.subheader(f"Service: {service}")

        # Filter data by service
        service_df = df[df['service'] == service]

        # Check and process required columns
        missing_cols = [col for col in ['nama', 'no_tentera', 'pangkat'] if col not in service_df.columns]
        if missing_cols:
            st.error(f"Missing required columns in {service} data: {', '.join(missing_cols)}")
            continue
        
        # Clean and prepare data (standardize columns, normalize ranks, etc.)
        service_df['pangkat_standard'] = service_df['pangkat'].apply(normalize_rank)
        service_df['level_pangkat'] = service_df['pangkat_standard'].apply(get_rank_level)

        # Sorting data based on military number and rank
        service_df = service_df.sort_values(by=['level_pangkat', 'no_tentera_numeric', 'nama']).reset_index(drop=True)

        # Display the sorted DataFrame for each service
        st.write(service_df[['nama', 'no_tentera', 'pangkat', 'service']])

        # Add a download button for each service's data
        st.download_button(
            label=f"Download {service} Data",
            data=service_df.to_csv(index=False).encode('utf-8'),
            file_name=f"{service}_sorted_data.csv",
            mime="text/csv"
        )

else:
    st.info("Sila upload fail CSV atau Excel untuk mula.")
