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
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="Diet Chart Bulk Emailer",
    page_icon="📋",
    layout="wide"
)

st.title("📋 Bulk Patient Diet Chart Mailer")

current_time = datetime.now().strftime(
    "%d-%b-%Y | %I:%M:%S %p"
)

st.markdown(
    f"⏱️ **System Current Time:** `{current_time}`"
)

st.markdown("---")


# =========================================================
# FIXED MICROSOFT 365 SMTP SETTINGS
# User does not need to enter host or port
# =========================================================
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587


# =========================================================
# HELPER FUNCTIONS
# =========================================================
def clean_patient_id(value):
    """
    Clean Patient ID imported from Excel or CSV.

    Examples:
    P65088 remains P65088
    65088.0 becomes 65088
    """

    if pd.isna(value):
        return ""

    patient_id = str(value).strip()

    if patient_id.endswith(".0"):
        patient_id = patient_id[:-2]

    return patient_id


def is_valid_email(email_address):
    """
    Basic email-format validation.
    """

    if not email_address:
        return False

    parsed_email = parseaddr(email_address)[1]

    if "@" not in parsed_email:
        return False

    domain = parsed_email.split("@")[-1]

    return "." in domain


def connect_to_smtp(sender_email, sender_password):
    """
    Connect to Microsoft 365 SMTP using STARTTLS.
    """

    server = smtplib.SMTP(
        SMTP_SERVER,
        SMTP_PORT,
        timeout=60
    )

    server.ehlo()
    server.starttls()
    server.ehlo()

    server.login(
        sender_email.strip(),
        sender_password
    )

    return server


def create_email_message(
    sender_email,
    sender_name,
    patient_name,
    patient_email,
    patient_id,
    pdf_name,
    pdf_content
):
    """
    Create patient email with PDF attachment.
    """

    message = MIMEMultipart()

    message["From"] = formataddr(
        (sender_name, sender_email)
    )

    message["To"] = patient_email

    message["Subject"] = (
        f"Your Personalized Diet Chart - "
        f"Patient ID: {patient_id}"
    )

    email_body = f"""Hello {patient_name},

Your personalized diet chart for Patient ID {patient_id} is attached to this email.

Please review the attached PDF document for your detailed nutrition guidelines.

If you have any questions regarding your diet chart, please contact your assigned health coach.

Regards,
Diet & Health Team
"""

    message.attach(
        MIMEText(
            email_body,
            "plain",
            "utf-8"
        )
    )

    pdf_attachment = MIMEApplication(
        pdf_content,
        _subtype="pdf"
    )

    pdf_attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=pdf_name
    )

    message.attach(pdf_attachment)

    return message


# =========================================================
# INITIALIZE SESSION STATE
# =========================================================
if "login_verified" not in st.session_state:
    st.session_state["login_verified"] = False

if "verified_email" not in st.session_state:
    st.session_state["verified_email"] = ""

if "report_df" not in st.session_state:
    st.session_state["report_df"] = None


# =========================================================
# SIDEBAR LOGIN
# =========================================================
st.sidebar.header("🔐 Sender Login")

sender_name = st.sidebar.text_input(
    "Sender Display Name",
    value="Diet & Health Team"
)

sender_email = st.sidebar.text_input(
    "Email ID",
    placeholder="Enter Microsoft 365 email ID"
).strip()

sender_password = st.sidebar.text_input(
    "Password",
    type="password",
    placeholder="Enter email password",
    help="Password is hidden and is not written inside the Python file."
)

email_delay = st.sidebar.number_input(
    "Delay Between Emails",
    min_value=0.0,
    max_value=30.0,
    value=1.0,
    step=0.5,
    help="Delay in seconds between two emails."
)

st.sidebar.caption(
    "Microsoft 365 SMTP settings are already configured."
)

st.sidebar.code(
    "Host: smtp.office365.com\n"
    "Port: 587\n"
    "Security: STARTTLS"
)


# =========================================================
# TEST LOGIN BUTTON
# =========================================================
if st.sidebar.button(
    "🔐 Test Email Login",
    use_container_width=True
):
    st.session_state["login_verified"] = False
    st.session_state["verified_email"] = ""

    if not sender_email:
        st.sidebar.error("Please enter the email ID.")

    elif not is_valid_email(sender_email):
        st.sidebar.error("Please enter a valid email ID.")

    elif not sender_password:
        st.sidebar.error("Please enter the password.")

    else:
        test_connection = None

        try:
            with st.sidebar:
                with st.spinner("Checking email login..."):
                    test_connection = connect_to_smtp(
                        sender_email=sender_email,
                        sender_password=sender_password
                    )

            st.session_state["login_verified"] = True
            st.session_state["verified_email"] = sender_email

            st.sidebar.success(
                "✅ Email login successful."
            )

        except smtplib.SMTPAuthenticationError as auth_error:
            st.sidebar.error(
                "❌ Login failed. Email/password incorrect ho sakta "
                "hai ya mailbox par SMTP AUTH disabled ho sakta hai."
            )

            st.sidebar.code(str(auth_error))

        except smtplib.SMTPConnectError as connection_error:
            st.sidebar.error(
                "❌ Microsoft 365 SMTP server se connection nahi hua."
            )

            st.sidebar.code(str(connection_error))

        except TimeoutError:
            st.sidebar.error(
                "❌ Connection timed out. Internet ya firewall "
                "settings check karein."
            )

        except Exception as login_error:
            st.sidebar.error(
                "❌ Email login test failed."
            )

            st.sidebar.code(str(login_error))

        finally:
            if test_connection is not None:
                try:
                    test_connection.quit()
                except Exception:
                    try:
                        test_connection.close()
                    except Exception:
                        pass


# Reset login verification if email ID changes
if (
    st.session_state["verified_email"]
    and sender_email != st.session_state["verified_email"]
):
    st.session_state["login_verified"] = False


# Login status
if st.session_state["login_verified"]:
    st.sidebar.success(
        f"✅ Verified: {st.session_state['verified_email']}"
    )
else:
    st.sidebar.info(
        "Email send karne se pehle Test Email Login karein."
    )


# =========================================================
# MAIN TABS
# =========================================================
send_tab, report_tab = st.tabs(
    [
        "📤 Send Bulk Emails",
        "📊 Delivery Report"
    ]
)


# =========================================================
# TAB 1: UPLOAD AND SEND
# =========================================================
with send_tab:

    upload_col1, upload_col2 = st.columns([1, 1])

    with upload_col1:
        st.subheader("1. Patient List")

        uploaded_patient_file = st.file_uploader(
            "Upload Patient CSV or Excel",
            type=["csv", "xlsx", "xls"],
            key="patient_file"
        )

        st.caption(
            "Required columns: Name, Email, PatientID"
        )

    with upload_col2:
        st.subheader("2. Diet Chart PDFs")

        uploaded_pdfs = st.file_uploader(
            "Upload All Patient PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            key="patient_pdfs"
        )

        st.caption(
            "Required filename: Diet_chart_PatientID.pdf"
        )

    if uploaded_patient_file is None:
        st.info(
            "Patient CSV or Excel file upload karein."
        )

    elif not uploaded_pdfs:
        st.info(
            "Patient diet chart PDFs upload karein."
        )

    else:
        # =================================================
        # READ PATIENT FILE
        # =================================================
        file_extension = (
            uploaded_patient_file.name
            .rsplit(".", 1)[-1]
            .lower()
        )

        try:
            if file_extension == "csv":
                df = pd.read_csv(
                    uploaded_patient_file,
                    dtype=str
                )

            elif file_extension in ["xlsx", "xls"]:
                df = pd.read_excel(
                    uploaded_patient_file,
                    dtype=str
                )

            else:
                st.error(
                    "Unsupported patient file format."
                )
                st.stop()

        except Exception as read_error:
            st.error(
                f"Patient file read nahi ho paayi: {read_error}"
            )
            st.stop()

        # =================================================
        # VALIDATE COLUMNS
        # =================================================
        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
        )

        required_columns = [
            "Name",
            "Email",
            "PatientID"
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:
            st.error(
                "Required columns missing hain: "
                + ", ".join(missing_columns)
            )
            st.stop()

        # =================================================
        # CLEAN DATA
        # =================================================
        df["Name"] = (
            df["Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        df["Email"] = (
            df["Email"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        df["PatientID"] = (
            df["PatientID"]
            .apply(clean_patient_id)
        )

        # Remove completely blank records
        df = df[
            (df["Name"] != "")
            | (df["Email"] != "")
            | (df["PatientID"] != "")
        ].copy()

        df.reset_index(
            drop=True,
            inplace=True
        )

        if df.empty:
            st.error(
                "Patient file mein koi valid record nahi mila."
            )
            st.stop()

        # =================================================
        # PREPARE PDF DICTIONARY
        # =================================================
        pdf_dictionary = {
            uploaded_pdf.name.strip().lower(): uploaded_pdf
            for uploaded_pdf in uploaded_pdfs
        }

        df["Expected_PDF"] = (
            df["PatientID"]
            .apply(
                lambda patient_id:
                f"Diet_chart_{patient_id}.pdf"
            )
        )

        df["PDF_Found"] = (
            df["Expected_PDF"]
            .str.lower()
            .isin(pdf_dictionary.keys())
        )

        df["Email_Valid"] = (
            df["Email"]
            .apply(is_valid_email)
        )

        df["PatientID_Valid"] = (
            df["PatientID"] != ""
        )

        df["Name_Valid"] = (
            df["Name"] != ""
        )

        df["Duplicate_PatientID"] = (
            df["PatientID"].duplicated(
                keep=False
            )
            & df["PatientID"].ne("")
        )

        df["Duplicate_Email"] = (
            df["Email"].duplicated(
                keep=False
            )
            & df["Email"].ne("")
        )

        df["Ready_To_Send"] = (
            df["PDF_Found"]
            & df["Email_Valid"]
            & df["PatientID_Valid"]
            & df["Name_Valid"]
        )

        # =================================================
        # COUNTS
        # =================================================
        total_records = len(df)

        ready_count = int(
            df["Ready_To_Send"].sum()
        )

        missing_pdf_count = int(
            (~df["PDF_Found"]).sum()
        )

        invalid_email_count = int(
            (~df["Email_Valid"]).sum()
        )

        duplicate_id_count = int(
            df["Duplicate_PatientID"].sum()
        )

        metric1, metric2, metric3, metric4 = st.columns(4)

        metric1.metric(
            "Total Records",
            total_records
        )

        metric2.metric(
            "Ready to Send",
            ready_count
        )

        metric3.metric(
            "Missing PDFs",
            missing_pdf_count
        )

        metric4.metric(
            "Invalid Emails",
            invalid_email_count
        )

        # =================================================
        # WARNINGS
        # =================================================
        if missing_pdf_count > 0:
            st.warning(
                f"⚠️ {missing_pdf_count} records ki matching "
                "PDF nahi mili."
            )

        if invalid_email_count > 0:
            st.warning(
                f"⚠️ {invalid_email_count} records mein email "
                "invalid ya blank hai."
            )

        if duplicate_id_count > 0:
            st.warning(
                "⚠️ Duplicate Patient IDs present hain. "
                "Duplicates ko send karne se pehle check karein."
            )

        if (
            missing_pdf_count == 0
            and invalid_email_count == 0
        ):
            st.success(
                "✅ All records passed the main validation."
            )

        # =================================================
        # DISPLAY VALIDATION TABLE
        # =================================================
        st.subheader("Pre-Send Validation")

        validation_columns = [
            "Name",
            "Email",
            "PatientID",
            "Expected_PDF",
            "PDF_Found",
            "Email_Valid",
            "Duplicate_PatientID",
            "Ready_To_Send"
        ]

        st.dataframe(
            df[validation_columns],
            use_container_width=True,
            hide_index=True
        )

        # =================================================
        # SEND CONFIRMATION
        # =================================================
        confirmation = st.checkbox(
            f"I confirm that I want to send "
            f"{ready_count} patient emails."
        )

        send_disabled = (
            not confirmation
            or ready_count == 0
            or not st.session_state["login_verified"]
        )

        if not st.session_state["login_verified"]:
            st.warning(
                "⚠️ Sidebar mein email ID aur password enter "
                "karke pehle 'Test Email Login' karein."
            )

        send_button = st.button(
            "🚀 Send Diet Charts",
            type="primary",
            use_container_width=True,
            disabled=send_disabled
        )

        # =================================================
        # EMAIL SENDING PROCESS
        # =================================================
        if send_button:

            if (
                sender_email
                != st.session_state["verified_email"]
            ):
                st.error(
                    "Sender email change hua hai. "
                    "Please login test dobara karein."
                )
                st.stop()

            df["Status"] = "Pending"
            df["Sent_At_Timestamp"] = ""
            df["Error_Details"] = ""

            progress_bar = st.progress(0)
            status_placeholder = st.empty()
            live_report_placeholder = st.empty()

            smtp_connection = None

            try:
                status_placeholder.info(
                    "Microsoft 365 SMTP se connect ho raha hai..."
                )

                smtp_connection = connect_to_smtp(
                    sender_email=sender_email,
                    sender_password=sender_password
                )

                total_patients = len(df)

                for position, (index, row) in enumerate(
                    df.iterrows(),
                    start=1
                ):
                    patient_name = row["Name"]
                    patient_email = row["Email"]
                    patient_id = row["PatientID"]
                    expected_pdf = row["Expected_PDF"]

                    processing_time = (
                        datetime.now()
                        .strftime("%Y-%m-%d %H:%M:%S")
                    )

                    status_placeholder.markdown(
                        f"⏳ **[{processing_time}]** "
                        f"Processing {position}/{total_patients}: "
                        f"**{patient_name}** (`{patient_id}`)"
                    )

                    # -------------------------------------
                    # INVALID NAME
                    # -------------------------------------
                    if not row["Name_Valid"]:
                        df.at[index, "Status"] = "Failed"
                        df.at[
                            index,
                            "Error_Details"
                        ] = "Patient name is blank"

                    # -------------------------------------
                    # INVALID PATIENT ID
                    # -------------------------------------
                    elif not row["PatientID_Valid"]:
                        df.at[index, "Status"] = "Failed"
                        df.at[
                            index,
                            "Error_Details"
                        ] = "Patient ID is blank"

                    # -------------------------------------
                    # INVALID EMAIL
                    # -------------------------------------
                    elif not row["Email_Valid"]:
                        df.at[index, "Status"] = "Failed"
                        df.at[
                            index,
                            "Error_Details"
                        ] = "Invalid or blank email address"

                    # -------------------------------------
                    # MISSING PDF
                    # -------------------------------------
                    elif not row["PDF_Found"]:
                        df.at[index, "Status"] = "Failed"
                        df.at[
                            index,
                            "Error_Details"
                        ] = (
                            "PDF mismatch or missing: "
                            f"{expected_pdf}"
                        )

                    # -------------------------------------
                    # SEND EMAIL
                    # -------------------------------------
                    else:
                        try:
                            pdf_file = pdf_dictionary[
                                expected_pdf.lower()
                            ]

                            pdf_file.seek(0)
                            pdf_content = pdf_file.read()

                            email_message = create_email_message(
                                sender_email=sender_email,
                                sender_name=sender_name,
                                patient_name=patient_name,
                                patient_email=patient_email,
                                patient_id=patient_id,
                                pdf_name=expected_pdf,
                                pdf_content=pdf_content
                            )

                            smtp_connection.sendmail(
                                sender_email,
                                [patient_email],
                                email_message.as_string()
                            )

                            sent_time = (
                                datetime.now()
                                .strftime("%Y-%m-%d %H:%M:%S")
                            )

                            df.at[
                                index,
                                "Status"
                            ] = "Success"

                            df.at[
                                index,
                                "Sent_At_Timestamp"
                            ] = sent_time

                            df.at[
                                index,
                                "Error_Details"
                            ] = ""

                        except smtplib.SMTPServerDisconnected:
                            try:
                                smtp_connection = connect_to_smtp(
                                    sender_email=sender_email,
                                    sender_password=sender_password
                                )

                                smtp_connection.sendmail(
                                    sender_email,
                                    [patient_email],
                                    email_message.as_string()
                                )

                                sent_time = (
                                    datetime.now()
                                    .strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    )
                                )

                                df.at[
                                    index,
                                    "Status"
                                ] = "Success"

                                df.at[
                                    index,
                                    "Sent_At_Timestamp"
                                ] = sent_time

                            except Exception as reconnect_error:
                                df.at[
                                    index,
                                    "Status"
                                ] = "Failed"

                                df.at[
                                    index,
                                    "Error_Details"
                                ] = (
                                    "SMTP reconnect failed: "
                                    f"{reconnect_error}"
                                )

                        except Exception as send_error:
                            df.at[
                                index,
                                "Status"
                            ] = "Failed"

                            df.at[
                                index,
                                "Error_Details"
                            ] = str(send_error)

                    progress_bar.progress(
                        position / total_patients
                    )

                    live_report_placeholder.dataframe(
                        df[
                            [
                                "PatientID",
                                "Name",
                                "Email",
                                "Status",
                                "Sent_At_Timestamp",
                                "Error_Details"
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True
                    )

                    time.sleep(
                        float(email_delay)
                    )

                # =========================================
                # FINAL SUMMARY
                # =========================================
                success_count = int(
                    (df["Status"] == "Success").sum()
                )

                failed_count = int(
                    (df["Status"] == "Failed").sum()
                )

                pending_count = int(
                    (df["Status"] == "Pending").sum()
                )

                st.session_state["report_df"] = df.copy()

                status_placeholder.success(
                    "✅ Email dispatch completed."
                )

                result1, result2, result3, result4 = (
                    st.columns(4)
                )

                result1.metric(
                    "Total",
                    total_patients
                )

                result2.metric(
                    "Success",
                    success_count
                )

                result3.metric(
                    "Failed",
                    failed_count
                )

                result4.metric(
                    "Pending",
                    pending_count
                )

                if failed_count == 0:
                    st.success(
                        "🎉 All valid diet chart emails "
                        "successfully sent."
                    )
                else:
                    st.warning(
                        f"Process completed. {failed_count} "
                        "records failed or were skipped."
                    )

            except smtplib.SMTPAuthenticationError as auth_error:
                st.session_state["login_verified"] = False

                st.error(
                    "❌ Authentication failed. Email/password "
                    "incorrect ho sakta hai ya SMTP AUTH disabled hai."
                )

                st.code(str(auth_error))

            except smtplib.SMTPConnectError as connection_error:
                st.error(
                    "❌ Microsoft 365 SMTP server se "
                    "connection nahi hua."
                )

                st.code(str(connection_error))

            except Exception as process_error:
                st.error(
                    "❌ Email dispatch process mein error aaya."
                )

                st.code(str(process_error))

            finally:
                if smtp_connection is not None:
                    try:
                        smtp_connection.quit()
                    except Exception:
                        try:
                            smtp_connection.close()
                        except Exception:
                            pass


# =========================================================
# TAB 2: DELIVERY REPORT
# =========================================================
with report_tab:

    st.subheader(
        "📊 Delivery Report"
    )

    report_df = st.session_state.get("report_df")

    if report_df is not None:

        success_count = int(
            (report_df["Status"] == "Success").sum()
        )

        failed_count = int(
            (report_df["Status"] == "Failed").sum()
        )

        pending_count = int(
            (report_df["Status"] == "Pending").sum()
        )

        report_metric1, report_metric2, report_metric3, report_metric4 = (
            st.columns(4)
        )

        report_metric1.metric(
            "Total Records",
            len(report_df)
        )

        report_metric2.metric(
            "Success",
            success_count
        )

        report_metric3.metric(
            "Failed",
            failed_count
        )

        report_metric4.metric(
            "Pending",
            pending_count
        )

        status_filter = st.multiselect(
            "Filter by Status",
            options=[
                "Success",
                "Failed",
                "Pending"
            ],
            default=[
                "Success",
                "Failed",
                "Pending"
            ]
        )

        filtered_report = report_df[
            report_df["Status"].isin(
                status_filter
            )
        ]

        st.dataframe(
            filtered_report,
            use_container_width=True,
            hide_index=True
        )

        report_timestamp = (
            datetime.now()
            .strftime("%Y%m%d_%H%M%S")
        )

        complete_csv = (
            report_df
            .to_csv(index=False)
            .encode("utf-8-sig")
        )

        st.download_button(
            label="📥 Download Complete Delivery Report",
            data=complete_csv,
            file_name=(
                "diet_chart_delivery_report_"
                f"{report_timestamp}.csv"
            ),
            mime="text/csv",
            use_container_width=True
        )

        failed_report = report_df[
            report_df["Status"] == "Failed"
        ]

        if not failed_report.empty:

            failed_csv = (
                failed_report
                .to_csv(index=False)
                .encode("utf-8-sig")
            )

            st.download_button(
                label="⚠️ Download Failed Records Only",
                data=failed_csv,
                file_name=(
                    "failed_diet_chart_emails_"
                    f"{report_timestamp}.csv"
                ),
                mime="text/csv",
                use_container_width=True
            )

    else:
        st.info(
            "Abhi koi delivery report available nahi hai. "
            "Pehle Send Bulk Emails tab se process run karein."
        )
