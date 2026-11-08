import time
import smtplib
import pandas as pd
import streamlit as st
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr, parseaddr

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Diet Chart Bulk Emailer",
    page_icon="📋",
    layout="wide"
)
st.title("📋 Bulk Patient Diet Chart Mailer via SendGrid")
st.markdown(
    f"⏱️ System Current Time: "
    f"`{datetime.now().strftime('%d-%b-%Y | %I:%M:%S %p')}`"
)
st.markdown("---")

# =========================================================
# SENDGRID SMTP SETTINGS
# =========================================================
SMTP_SERVER = "smtp.sendgrid.net"
SMTP_PORT = 587

# MULTIPLE BCC EMAILS CONFIGURATION (Shobnam, Shraddha & Tatpar)
BCC_EMAILS = [
    "shobnambegum@lupindigitalhealth.com",
    "shraddhabjadhav@lupindigitalhealth.com",
    "c_tatparmishra@nivabupa.com"
]

# =========================================================
# SESSION STATE
# =========================================================
if "login_verified" not in st.session_state:
    st.session_state["login_verified"] = False
if "verified_email" not in st.session_state:
    st.session_state["verified_email"] = ""
if "report_df" not in st.session_state:
    st.session_state["report_df"] = None

# =========================================================
# FUNCTIONS
# =========================================================
def clean_patient_id(value):
    if pd.isna(value):
        return ""
    patient_id = str(value).strip()
    if patient_id.endswith(".0"):
        patient_id = patient_id[:-2]
    return patient_id

def is_valid_email(email_address):
    if not email_address:
        return False
    parsed_email = parseaddr(email_address)[1]
    if "@" not in parsed_email:
        return False
    domain = parsed_email.split("@")[-1]
    return "." in domain

def connect_sendgrid(api_key):
    server = smtplib.SMTP(
        SMTP_SERVER,
        SMTP_PORT,
        timeout=60
    )
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login("apikey", api_key.strip())
    return server

def find_pdf_file(patient_id, pdf_dictionary):
    """
    Uploaded PDFs mein se us file ko dhoondta hai jiske naam mein Patient ID maujud ho 
    (jaise DietplanP67861NainikaVerma04112026_120054.pdf mein P67861).
    """
    if not patient_id:
        return None, False
    
    clean_pid = patient_id.lower()
    for filename, pdf_obj in pdf_dictionary.items():
        if clean_pid in filename.lower():
            return filename, True
            
    return None, False

def create_email(
    sender_email,
    sender_name,
    patient_name,
    patient_email,
    patient_id,
    pdf_name,
    pdf_content,
    bcc_list
):
    message = MIMEMultipart()
    message["From"] = formataddr(
        (sender_name, sender_email)
    )
    message["To"] = patient_email
    message["Bcc"] = ", ".join(bcc_list)
    message["Subject"] = f"Niva Bupa Personalized Diet Plan - Patient ID: {patient_id}"
    
    body = f"""Dear {patient_name},

Greetings from Niva Bupa!

Thank you for attending your consultation with health coach. Please find your personalized diet plan attached for your reference.

We encourage you to follow the recommendations discussed during your consultation to help you achieve your health goals.

We wish you good health and look forward to supporting you on your wellness journey.

Regards,
Niva Bupa Post Discharge Care Team
"""
    message.attach(
        MIMEText(
            body,
            "plain",
            "utf-8"
        )
    )
    attachment = MIMEApplication(
        pdf_content,
        _subtype="pdf"
    )
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=pdf_name
    )
    message.attach(attachment)
    return message

# =========================================================
# SIDEBAR LOGIN
# =========================================================
st.sidebar.header("🔐 SendGrid Credentials")
sender_name = st.sidebar.text_input(
    "Sender Display Name",
    value="Niva Bupa Post Discharge Care Team"
)
sender_email = st.sidebar.text_input(
    "Work Email ID (Verified Sender)",
    value="c_tatparmishra@nivabupa.com",
    placeholder="yourname@company.com"
).strip()
sendgrid_api_key = st.sidebar.text_input(
    "SendGrid API Key",
    type="password",
    placeholder="SG.xxxxxxxxxxxxxxxxxxxx"
)
email_delay = st.sidebar.number_input(
    "Delay Between Emails (seconds)",
    min_value=0.0,
    max_value=30.0,
    value=1.0,
    step=0.5
)
st.sidebar.caption(
    "SendGrid SMTP: smtp.sendgrid.net | Port 587"
)

# =========================================================
# RESET LOGIN IF EMAIL CHANGES
# =========================================================
if (
    st.session_state["verified_email"]
    and sender_email != st.session_state["verified_email"]
):
    st.session_state["login_verified"] = False
    st.session_state["verified_email"] = ""

# =========================================================
# TEST CONNECTION
# =========================================================
if st.sidebar.button(
    "🔐 Test SendGrid Connection",
    use_container_width=True
):
    st.session_state["login_verified"] = False
    st.session_state["verified_email"] = ""
    if not sender_email:
        st.sidebar.error("Work Email ID enter karein.")
    elif not is_valid_email(sender_email):
        st.sidebar.error("Valid Email ID enter karein.")
    elif not sendgrid_api_key:
        st.sidebar.error("SendGrid API Key enter karein.")
    else:
        test_server = None
        try:
            with st.sidebar:
                with st.spinner("SendGrid connection check ho raha hai..."):
                    test_server = connect_sendgrid(sendgrid_api_key)
            st.session_state["login_verified"] = True
            st.session_state["verified_email"] = sender_email
            st.sidebar.success("✅ SendGrid connection successful.")
        except Exception as error:
            st.sidebar.error("❌ SendGrid connection failed.")
            st.sidebar.code(str(error))
        finally:
            if test_server is not None:
                try:
                    test_server.quit()
                except Exception:
                    pass

# =========================================================
# LOGIN STATUS
# =========================================================
if st.session_state["login_verified"]:
    st.sidebar.success(f"✅ Verified Sender: {st.session_state['verified_email']}")
else:
    st.sidebar.info("Email send karne se pehle Test SendGrid Connection karein.")

# =========================================================
# TABS
# =========================================================
tab1, tab2 = st.tabs(["📤 Send Bulk Emails", "📊 Delivery Report"])

# =========================================================
# TAB 1
# =========================================================
with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("1. Patient List")
        uploaded_file = st.file_uploader(
            "Upload Patient CSV or Excel",
            type=["csv", "xlsx", "xls"]
        )
        st.caption("Required columns: Name, Email, PatientID")
    with col2:
        st.subheader("2. Diet Chart PDFs")
        uploaded_pdfs = st.file_uploader(
            "Upload All Patient PDFs (e.g., DietplanP67861...)",
            type=["pdf"],
            accept_multiple_files=True
        )
        st.caption("Filenames can include timestamps/dates; app will match using Patient ID.")

    if uploaded_file is None:
        st.info("Patient CSV/Excel upload karein.")
    elif not uploaded_pdfs:
        st.info("Diet chart PDFs upload karein.")
    else:
        extension = uploaded_file.name.rsplit(".", 1)[-1].lower()
        try:
            if extension == "csv":
                df = pd.read_csv(uploaded_file, dtype=str)
            elif extension in ["xlsx", "xls"]:
                df = pd.read_excel(uploaded_file, dtype=str)
            else:
                st.error("Unsupported file format.")
                st.stop()
        except Exception as error:
            st.error(f"File read error: {error}")
            st.stop()

        df.columns = df.columns.astype(str).str.strip()
        required_columns = ["Name", "Email", "PatientID"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Required columns missing: {', '.join(missing_columns)}")
            st.stop()

        df["Name"] = df["Name"].fillna("").astype(str).str.strip()
        df["Email"] = df["Email"].fillna("").astype(str).str.strip()
        df["PatientID"] = df["PatientID"].apply(clean_patient_id)
        df = df[(df["Name"] != "") | (df["Email"] != "") | (df["PatientID"] != "")].copy()
        df.reset_index(drop=True, inplace=True)
        if df.empty:
            st.error("Patient file mein valid records nahi hain.")
            st.stop()

        pdf_dictionary = {pdf.name.strip().lower(): pdf for pdf in uploaded_pdfs}
        
        matched_files = []
        pdf_found_flags = []
        for pid in df["PatientID"]:
            matched_name, found = find_pdf_file(pid, pdf_dictionary)
            matched_files.append(matched_name if found else "Not Found")
            pdf_found_flags.append(found)

        df["Matched_PDF"] = matched_files
        df["PDF_Found"] = pdf_found_flags

        df["Email_Valid"] = df["Email"].apply(is_valid_email)
        df["Name_Valid"] = df["Name"] != ""
        df["PatientID_Valid"] = df["PatientID"] != ""
        df["Ready_To_Send"] = df["PDF_Found"] & df["Email_Valid"] & df["Name_Valid"] & df["PatientID_Valid"]

        total_count = len(df)
        ready_count = int(df["Ready_To_Send"].sum())
        missing_pdf_count = int((~df["PDF_Found"]).sum())
        invalid_email_count = int((~df["Email_Valid"]).sum())

        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Total Records", total_count)
        metric2.metric("Ready to Send", ready_count)
        metric3.metric("Missing PDFs", missing_pdf_count)
        metric4.metric("Invalid Emails", invalid_email_count)

        if missing_pdf_count > 0:
            st.warning(f"⚠️ {missing_pdf_count} patients ki matching PDF nahi mili.")
        if invalid_email_count > 0:
            st.warning(f"⚠️ {invalid_email_count} invalid email addresses hain.")

        st.subheader("Pre-Send Validation")
        st.dataframe(
            df[["Name", "Email", "PatientID", "Matched_PDF", "PDF_Found", "Email_Valid", "Ready_To_Send"]],
            use_container_width=True,
            hide_index=True
        )

        confirmation = st.checkbox(f"I confirm that I want to send {ready_count} patient emails.")

        if not st.session_state["login_verified"]:
            st.warning("⚠️ Pehle sidebar mein Test SendGrid Connection karein.")

        send_button = st.button(
            "🚀 Send Diet Charts",
            type="primary",
            use_container_width=True,
            disabled=not confirmation or ready_count == 0 or not st.session_state["login_verified"]
        )

        if send_button:
            if sender_email != st.session_state["verified_email"]:
                st.error("Sender email change hua hai. Connection dobara test karein.")
                st.stop()

            df["Status"] = "Pending"
            df["Sent_At_Timestamp"] = ""
            df["Error_Details"] = ""

            progress_bar = st.progress(0)
            status_text = st.empty()
            live_report = st.empty()
            server = None

            try:
                server = connect_sendgrid(sendgrid_api_key)
                total_patients = len(df)

                for position, (index, row) in enumerate(df.iterrows(), start=1):
                    patient_name = row["Name"]
                    patient_email = row["Email"]
                    patient_id = row["PatientID"]
                    matched_pdf_name = row["Matched_PDF"]

                    status_text.markdown(f"⏳ Processing {position}/{total_patients}: {patient_name} (`{patient_id}`)")

                    if not row["Ready_To_Send"]:
                        df.at[index, "Status"] = "Failed"
                        df.at[index, "Error_Details"] = "Validation failed (Matching PDF not found or invalid fields)"
                    else:
                        try:
                            pdf_file = pdf_dictionary[matched_pdf_name.lower()]
                            pdf_file.seek(0)
                            pdf_content = pdf_file.read()

                            message = create_email(
                                sender_email=sender_email,
                                sender_name=sender_name,
                                patient_name=patient_name,
                                patient_email=patient_email,
                                patient_id=patient_id,
                                pdf_name=matched_pdf_name,
                                pdf_content=pdf_content,
                                bcc_list=BCC_EMAILS
                            )

                            recipients = [patient_email] + BCC_EMAILS

                            server.sendmail(
                                sender_email,
                                recipients,
                                message.as_string()
                            )

                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            df.at[index, "Status"] = "Success"
                            df.at[index, "Sent_At_Timestamp"] = timestamp

                        except Exception as send_error:
                            df.at[index, "Status"] = "Failed"
                            df.at[index, "Error_Details"] = str(send_error)

                    progress_bar.progress(position / total_patients)
                    live_report.dataframe(
                        df[["PatientID", "Name", "Email", "Status", "Sent_At_Timestamp", "Error_Details"]],
                        use_container_width=True,
                        hide_index=True
                    )
                    time.sleep(float(email_delay))

                st.session_state["report_df"] = df.copy()
                success_count = int((df["Status"] == "Success").sum())
                failed_count = int((df["Status"] == "Failed").sum())

                status_text.success("✅ Email dispatch completed.")
                res1, res2, res3 = st.columns(3)
                res1.metric("Total", total_patients)
                res2.metric("Success", success_count)
                res3.metric("Failed", failed_count)

            except Exception as error:
                st.error("❌ Email sending process failed.")
                st.code(str(error))
            finally:
                if server is not None:
                    try:
                        server.quit()
                    except Exception:
                        pass

# =========================================================
# TAB 2 - REPORT
# =========================================================
with tab2:
    st.subheader("📊 Delivery Report")
    report_df = st.session_state.get("report_df")

    if report_df is None:
        st.info("Abhi delivery report available nahi hai.")
    else:
        st.dataframe(report_df, use_container_width=True, hide_index=True)
        csv_data = report_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 Download Delivery Report",
            data=csv_data,
            file_name=f"diet_chart_delivery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
