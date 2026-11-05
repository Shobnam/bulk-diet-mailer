import os
import time
import smtplib
import pandas as pd
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import streamlit as st

# Page Configuration
st.set_page_config(page_title="Diet Chart Bulk Emailer", page_icon="📋", layout="wide")

# Header with Live Time Display
st.title("📋 Bulk Patient Diet Chart Mailer")
live_time_placeholder = st.empty()
current_time_str = datetime.now().strftime("%d-%b-%Y | %I:%M:%S %p")
live_time_placeholder.markdown(f"⏱️ **System Current Time:** `{current_time_str}`")

st.markdown("---")

# Sidebar - Settings
st.sidebar.header("⚙️ Sender Email Configuration")
sender_email = st.sidebar.text_input("Sender Email Address", value="yourclinic@gmail.com")
app_password = st.sidebar.text_input("Google App Password", type="password", help="Enter your 16-digit Google App Password from Account Security settings.")
smtp_server = st.sidebar.text_input("SMTP Host", value="smtp.gmail.com")
smtp_port = st.sidebar.number_input("SMTP Port", value=587)

# Main UI Tabs
tab1, tab2 = st.tabs(["📤 Send Bulk Emails", "📊 Delivery Reports"])

with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1. Patient List (CSV)")
        uploaded_csv = st.file_uploader("Upload Patient CSV File", type=["csv"])
        
    with col2:
        st.subheader("2. Diet Chart PDFs")
        uploaded_pdfs = st.file_uploader("Drag & Drop All Patient PDFs", type=["pdf"], accept_multiple_files=True)

    if uploaded_csv and uploaded_pdfs:
        df = pd.read_csv(uploaded_csv)
        pdf_dict = {file.name.strip(): file for file in uploaded_pdfs}

        # --- PRE-CHECK MISMATCH VALIDATION BEFORE SENDING ---
        df["Expected_PDF"] = df["PatientID"].astype(str).str.strip().apply(lambda x: f"Diet_chart_{x}.pdf")
        df["PDF_Found"] = df["Expected_PDF"].isin(pdf_dict.keys())

        matched_count = df["PDF_Found"].sum()
        missing_count = len(df) - matched_count

        st.info(f"📂 **Pre-Check Summary:** Total Records: {len(df)} | ✅ Matched PDFs: {matched_count} | ⚠️ Mismatch/Missing PDFs: {missing_count}")

        if missing_count > 0:
            st.warning("⚠️ Kuch patients ke liye matching PDF nahi mili hai (Mismatch detected)! Niche table mein check karein:")
            st.dataframe(df[["Name", "Email", "PatientID", "Expected_PDF", "PDF_Found"]], use_container_width=True)
        else:
            st.success("🎉 Sabhi patients ki PDFs successfully match ho gayi hain! Aap email send kar sakte hain.")
            st.dataframe(df.head(5), use_container_width=True)

        if st.button("🚀 Send Diet Charts to All Patients", type="primary"):
            if not app_password:
                st.error("Please enter your App Password in the sidebar settings!")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                df["Status"] = "Pending"
                df["Sent_At_Timestamp"] = ""

                # Connect to SMTP Server
                try:
                    server = smtplib.SMTP(smtp_server, int(smtp_port))
                    server.starttls()
                    server.login(sender_email, app_password)
                    
                    total_patients = len(df)

                    for index, row in df.iterrows():
                        p_name = str(row['Name']).strip()
                        p_email = str(row['Email']).strip()
                        p_id = str(row['PatientID']).strip()
                        target_pdf_name = row['Expected_PDF']

                        live_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        status_text.markdown(f"⏳ **[{live_now}]** Processing ({index + 1}/{total_patients}): **{p_name}** (`{p_id}`)...")

                        # Email Message Construction
                        msg = MIMEMultipart()
                        msg['From'] = f"Diet & Health Clinic <{sender_email}>"
                        msg['To'] = p_email
                        msg['Subject'] = f"Your Personalized Diet Chart - Patient ID: #{p_id}"

                        body = f"""Hello {p_name},

Your personalized diet chart (Patient ID: {p_id}) is attached to this email.
Please review the attached PDF document for your detailed nutrition guidelines.

Regards,
Diet & Health Team
"""
                        msg.attach(MIMEText(body, 'plain'))

                        # Attach PDF if present
                        if row['PDF_Found']:
                            pdf_file = pdf_dict[target_pdf_name]
                            pdf_file.seek(0)
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(pdf_file.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename="{target_pdf_name}"')
                            msg.attach(part)

                            try:
                                server.sendmail(sender_email, p_email, msg.as_string())
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                df.at[index, 'Status'] = 'Success'
                                df.at[index, 'Sent_At_Timestamp'] = timestamp
                            except Exception as err:
                                df.at[index, 'Status'] = f"Failed: {err}"
                        else:
                            df.at[index, 'Status'] = f"Failed: Mismatch - PDF '{target_pdf_name}' Missing"

                        progress_bar.progress((index + 1) / total_patients)
                        time.sleep(0.05)

                    server.quit()
                    st.success("🎉 Process complete! Delivery report generated with mismatch status.")
                    
                    st.session_state['report_df'] = df

                except Exception as conn_err:
                    st.error(f"SMTP Connection Error: {conn_err}")

with tab2:
    st.subheader("📊 Delivery Report with Live Timestamps & Mismatch Details")
    if 'report_df' in st.session_state:
        report_df = st.session_state['report_df']
        st.dataframe(report_df, use_container_width=True)

        csv_data = report_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Timestamp Report (CSV)",
            data=csv_data,
            file_name=f"diet_chart_delivery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No execution record found yet. Please run the dispatch process in the 'Send Bulk Emails' tab.")
