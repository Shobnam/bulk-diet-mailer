import time
import smtplib
import pandas as pd
import streamlit as st

from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr, parseaddr


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Diet Chart Bulk Emailer",
    page_icon="📋",
    layout="wide"
)

st.title("📋 Bulk Patient Diet Chart Mailer")

current_time = datetime.now().strftime("%d-%b-%Y | %I:%M:%S %p")
st.markdown(f"⏱️ **System Current Time:** `{current_time}`")

st.markdown("---")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_patient_id(value):
    """
    Clean Patient ID.

    Example:
    P65088   -> P65088
    65088.0  -> 65088
    """

    if pd.isna(value):
        return ""

    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value


def is_valid_email(email):
    """
    Basic email validation.
    """

    if pd.isna(email):
        return False

    email = str(email).strip()

    if not email:
        return False

    parsed_email = parseaddr(email)[1]

    if "@" not in parsed_email:
        return False

    domain = parsed_email.split("@")[-1]

    if "." not in domain:
        return False

    return True


def create_email_message(
    sender_email,
    patient_name,
    patient_email,
    patient_id,
    pdf_name,
    pdf_content
):
    """
    Create patient email with PDF attachment.
    """

    msg = MIMEMultipart()

    msg["From"] = formataddr(
        ("Diet & Health Clinic", sender_email)
    )

    msg["To"] = patient_email

    msg["Subject"] = (
        f"Your Personalized Diet Chart - Patient ID: {patient_id}"
    )

    body = f"""Hello {patient_name},

Your personalized diet chart for Patient ID {patient_id} is attached to this email.

Please review the attached PDF document for your detailed nutrition guidelines.

If you have any questions regarding your diet chart, please contact your assigned health coach.

Regards,
Diet & Health Team
"""

    msg.attach(
        MIMEText(
            body,
            "plain",
            "utf-8"
        )
    )

    # --------------------------------------------------------
    # PDF Attachment
    # --------------------------------------------------------

    pdf_part = MIMEBase(
        "application",
        "pdf"
    )

    pdf_part.set_payload(pdf_content)

    encoders.encode_base64(pdf_part)

    pdf_part.add_header(
        "Content-Disposition",
        "attachment",
        filename=pdf_name
    )

    msg.attach(pdf_part)

    return msg


# ============================================================
# SIDEBAR CONFIGURATION
# ============================================================

st.sidebar.header("⚙️ Sender Email Configuration")

sender_email = st.sidebar.text_input(
    "Sender Email Address",
    value="yourclinic@gmail.com"
).strip()

app_password = st.sidebar.text_input(
    "Google App Password",
    type="password",
    help="Enter your Google App Password here."
)

smtp_server = st.sidebar.text_input(
    "SMTP Host",
    value="smtp.gmail.com"
).strip()

smtp_port = st.sidebar.number_input(
    "SMTP Port",
    min_value=1,
    max_value=65535,
    value=587,
    step=1
)

email_delay = st.sidebar.number_input(
    "Delay Between Emails (seconds)",
    min_value=0.0,
    max_value=10.0,
    value=0.5,
    step=0.1
)


# ============================================================
# TABS
# ============================================================

tab1, tab2 = st.tabs(
    [
        "📤 Send Bulk Emails",
        "📊 Delivery Reports"
    ]
)


# ============================================================
# TAB 1
# ============================================================

with tab1:

    col1, col2 = st.columns([1, 1])

    # --------------------------------------------------------
    # Patient File
    # --------------------------------------------------------

    with col1:

        st.subheader("1. Patient List")

        uploaded_file = st.file_uploader(
            "Upload Patient CSV / Excel File",
            type=[
                "csv",
                "xlsx",
                "xls"
            ]
        )

        st.caption(
            "Required columns: Name, Email, PatientID"
        )

    # --------------------------------------------------------
    # PDF Files
    # --------------------------------------------------------

    with col2:

        st.subheader("2. Diet Chart PDFs")

        uploaded_pdfs = st.file_uploader(
            "Drag & Drop All Patient PDFs",
            type=["pdf"],
            accept_multiple_files=True
        )

        st.caption(
            "Expected PDF format: Diet_chart_PatientID.pdf"
        )


    # ========================================================
    # PROCESS FILES
    # ========================================================

    if uploaded_file is not None and uploaded_pdfs:

        file_extension = (
            uploaded_file.name
            .rsplit(".", 1)[-1]
            .lower()
        )

        try:

            if file_extension == "csv":

                df = pd.read_csv(
                    uploaded_file,
                    dtype=str
                )

            elif file_extension in ["xlsx", "xls"]:

                df = pd.read_excel(
                    uploaded_file,
                    dtype=str
                )

            else:

                st.error(
                    "Unsupported patient file format."
                )

                st.stop()

        except Exception as read_error:

            st.error(
                f"Error reading patient file: {read_error}"
            )

            st.stop()


        # ====================================================
        # CLEAN COLUMN NAMES
        # ====================================================

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
        )


        # ====================================================
        # REQUIRED COLUMN VALIDATION
        # ====================================================

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
                "Missing required columns: "
                + ", ".join(missing_columns)
            )

            st.stop()


        # ====================================================
        # CLEAN PATIENT DATA
        # ====================================================

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


        # ====================================================
        # REMOVE COMPLETELY BLANK RECORDS
        # ====================================================

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
                "Patient file does not contain any patient records."
            )

            st.stop()


        # ====================================================
        # PDF DICTIONARY
        # ====================================================

        pdf_dict = {}

        for pdf_file in uploaded_pdfs:

            pdf_name = (
                pdf_file.name
                .strip()
                .lower()
            )

            pdf_dict[pdf_name] = pdf_file


        # ====================================================
        # EXPECTED PDF
        # ====================================================

        df["Expected_PDF"] = (
            df["PatientID"]
            .apply(
                lambda patient_id:
                f"Diet_chart_{patient_id}.pdf"
            )
        )


        # ====================================================
        # PDF MATCH
        # ====================================================

        df["PDF_Found"] = (
            df["Expected_PDF"]
            .str.lower()
            .isin(pdf_dict.keys())
        )


        # ====================================================
        # EMAIL VALIDATION
        # ====================================================

        df["Email_Valid"] = (
            df["Email"]
            .apply(is_valid_email)
        )


        # ====================================================
        # DUPLICATE CHECK
        # ====================================================

        df["Duplicate_PatientID"] = (
            df.duplicated(
                subset=["PatientID"],
                keep=False
            )
        )

        df["Duplicate_Email"] = (
            df.duplicated(
                subset=["Email"],
                keep=False
            )
        )


        # ====================================================
        # COUNTS
        # ====================================================

        total_records = len(df)

        matched_count = int(
            df["PDF_Found"].sum()
        )

        missing_pdf_count = int(
            (~df["PDF_Found"]).sum()
        )

        invalid_email_count = int(
            (~df["Email_Valid"]).sum()
        )

        duplicate_patient_count = int(
            df["Duplicate_PatientID"].sum()
        )

        ready_count = int(
            (
                df["PDF_Found"]
                & df["Email_Valid"]
            ).sum()
        )


        # ====================================================
        # PRE-CHECK SUMMARY
        # ====================================================

        st.markdown("---")

        st.subheader(
            "🔍 Pre-Send Validation"
        )

        metric1, metric2, metric3, metric4 = st.columns(4)

        metric1.metric(
            "Total Patients",
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


        # ====================================================
        # WARNINGS
        # ====================================================

        if missing_pdf_count > 0:

            st.warning(
                f"⚠️ {missing_pdf_count} patient(s) ki matching PDF "
                "nahi mili."
            )


        if invalid_email_count > 0:

            st.warning(
                f"⚠️ {invalid_email_count} patient(s) ka email "
                "blank ya invalid hai."
            )


        if duplicate_patient_count > 0:

            st.warning(
                "⚠️ Duplicate Patient IDs detected. "
                "Sending se pehle duplicate records check karein."
            )


        if (
            missing_pdf_count == 0
            and invalid_email_count == 0
            and duplicate_patient_count == 0
        ):

            st.success(
                "✅ All patient records are valid and PDFs are matched."
            )


        # ====================================================
        # VALIDATION TABLE
        # ====================================================

        preview_columns = [
            "Name",
            "Email",
            "PatientID",
            "Expected_PDF",
            "PDF_Found",
            "Email_Valid",
            "Duplicate_PatientID",
            "Duplicate_Email"
        ]

        st.dataframe(
            df[preview_columns],
            use_container_width=True,
            hide_index=True
        )


        # ====================================================
        # SEND CONFIRMATION
        # ====================================================

        st.markdown("---")

        confirm_send = st.checkbox(
            f"I confirm that I want to send "
            f"{ready_count} valid patient email(s)."
        )


        send_button = st.button(
            "🚀 Send Diet Charts to Patients",
            type="primary",
            disabled=not confirm_send
        )


        # ====================================================
        # EMAIL SENDING
        # ====================================================

        if send_button:

            # ------------------------------------------------
            # Sender Email Validation
            # ------------------------------------------------

            if not sender_email:

                st.error(
                    "Please enter sender email address."
                )

                st.stop()


            if not is_valid_email(sender_email):

                st.error(
                    "Sender email address is invalid."
                )

                st.stop()


            # ------------------------------------------------
            # App Password Validation
            # ------------------------------------------------

            if not app_password:

                st.error(
                    "Please enter Google App Password."
                )

                st.stop()


            # ------------------------------------------------
            # Ready Record Validation
            # ------------------------------------------------

            if ready_count == 0:

                st.error(
                    "No valid patient records are available for sending."
                )

                st.stop()


            # =================================================
            # CREATE REPORT COLUMNS
            # =================================================

            df["Status"] = "Pending"

            df["Sent_At_Timestamp"] = ""

            df["Error_Details"] = ""


            progress_bar = st.progress(0)

            status_text = st.empty()

            live_results = st.empty()


            smtp_connection = None


            # =================================================
            # SMTP CONNECTION
            # =================================================

            try:

                status_text.info(
                    "📡 Connecting to Gmail SMTP server..."
                )

                smtp_connection = smtplib.SMTP(
                    smtp_server,
                    int(smtp_port),
                    timeout=60
                )

                smtp_connection.ehlo()

                smtp_connection.starttls()

                smtp_connection.ehlo()


                # Remove accidental spaces from App Password
                clean_app_password = (
                    app_password
                    .replace(" ", "")
                    .strip()
                )


                smtp_connection.login(
                    sender_email,
                    clean_app_password
                )


                st.success(
                    "✅ SMTP connection successful."
                )


                total_patients = len(df)


                # =================================================
                # SEND EACH PATIENT EMAIL
                # =================================================

                for position, (index, row) in enumerate(
                    df.iterrows(),
                    start=1
                ):

                    patient_name = row["Name"]
                    patient_email = row["Email"]
                    patient_id = row["PatientID"]
                    target_pdf_name = row["Expected_PDF"]


                    process_timestamp = (
                        datetime.now()
                        .strftime("%Y-%m-%d %H:%M:%S")
                    )


                    status_text.markdown(
                        f"⏳ **[{process_timestamp}]** "
                        f"Processing {position}/{total_patients}: "
                        f"**{patient_name}** "
                        f"(`{patient_id}`)"
                    )


                    # =================================================
                    # INVALID EMAIL
                    # =================================================

                    if not row["Email_Valid"]:

                        df.at[
                            index,
                            "Status"
                        ] = "Failed"

                        df.at[
                            index,
                            "Error_Details"
                        ] = "Invalid or blank email address"


                    # =================================================
                    # MISSING PDF
                    # =================================================

                    elif not row["PDF_Found"]:

                        df.at[
                            index,
                            "Status"
                        ] = "Failed"

                        df.at[
                            index,
                            "Error_Details"
                        ] = (
                            f"PDF Missing: {target_pdf_name}"
                        )


                    # =================================================
                    # SEND EMAIL
                    # =================================================

                    else:

                        try:

                            pdf_file = pdf_dict[
                                target_pdf_name.lower()
                            ]


                            # Always reset PDF pointer
                            pdf_file.seek(0)

                            pdf_content = (
                                pdf_file.read()
                            )


                            email_message = (
                                create_email_message(
                                    sender_email=sender_email,
                                    patient_name=patient_name,
                                    patient_email=patient_email,
                                    patient_id=patient_id,
                                    pdf_name=target_pdf_name,
                                    pdf_content=pdf_content
                                )
                            )


                            smtp_connection.sendmail(
                                sender_email,
                                [patient_email],
                                email_message.as_string()
                            )


                            sent_timestamp = (
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
                            ] = sent_timestamp


                            df.at[
                                index,
                                "Error_Details"
                            ] = ""


                        except Exception as send_error:

                            df.at[
                                index,
                                "Status"
                            ] = "Failed"

                            df.at[
                                index,
                                "Error_Details"
                            ] = str(send_error)


                    # =================================================
                    # UPDATE PROGRESS
                    # =================================================

                    progress_bar.progress(
                        position / total_patients
                    )


                    live_results.dataframe(
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


                # =================================================
                # FINAL COUNTS
                # =================================================

                success_count = int(
                    (
                        df["Status"]
                        == "Success"
                    ).sum()
                )


                failed_count = int(
                    (
                        df["Status"]
                        == "Failed"
                    ).sum()
                )


                # Save report in session
                st.session_state["report_df"] = df.copy()


                status_text.success(
                    "✅ Email dispatch process completed."
                )


                # =================================================
                # FINAL SUMMARY
                # =================================================

                result1, result2, result3 = st.columns(3)


                result1.metric(
                    "Total Processed",
                    total_patients
                )


                result2.metric(
                    "Successfully Sent",
                    success_count
                )


                result3.metric(
                    "Failed / Skipped",
                    failed_count
                )


                if failed_count == 0:

                    st.success(
                        "🎉 All diet chart emails were sent successfully."
                    )

                else:

                    st.warning(
                        f"⚠️ Process completed. "
                        f"{failed_count} record(s) failed or were skipped."
                    )


            # =================================================
            # AUTHENTICATION ERROR
            # =================================================

            except smtplib.SMTPAuthenticationError:

                st.error(
                    "❌ Gmail authentication failed.\n\n"
                    "Please check:\n"
                    "1. Sender Gmail address\n"
                    "2. Google 2-Step Verification\n"
                    "3. Google App Password\n"
                    "4. Do not use your normal Gmail password"
                )


            # =================================================
            # CONNECTION ERROR
            # =================================================

            except smtplib.SMTPConnectError as connection_error:

                st.error(
                    f"❌ Unable to connect to SMTP server: "
                    f"{connection_error}"
                )


            # =================================================
            # OTHER ERROR
            # =================================================

            except Exception as smtp_error:

                st.error(
                    f"❌ SMTP / Processing Error: {smtp_error}"
                )


            # =================================================
            # ALWAYS CLOSE CONNECTION
            # =================================================

            finally:

                if smtp_connection is not None:

                    try:

                        smtp_connection.quit()

                    except Exception:

                        try:

                            smtp_connection.close()

                        except Exception:

                            pass


# ============================================================
# TAB 2 - DELIVERY REPORT
# ============================================================

with tab2:

    st.subheader(
        "📊 Diet Chart Email Delivery Report"
    )


    if "report_df" in st.session_state:

        report_df = (
            st.session_state["report_df"]
            .copy()
        )


        # ====================================================
        # COUNTS
        # ====================================================

        success_count = int(
            (
                report_df["Status"]
                == "Success"
            ).sum()
        )

        failed_count = int(
            (
                report_df["Status"]
                == "Failed"
            ).sum()
        )

        pending_count = int(
            (
                report_df["Status"]
                == "Pending"
            ).sum()
        )


        col1, col2, col3, col4 = st.columns(4)


        col1.metric(
            "Total Records",
            len(report_df)
        )


        col2.metric(
            "✅ Success",
            success_count
        )


        col3.metric(
            "❌ Failed",
            failed_count
        )


        col4.metric(
            "⏳ Pending",
            pending_count
        )


        # ====================================================
        # STATUS FILTER
        # ====================================================

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


        # ====================================================
        # DISPLAY REPORT
        # ====================================================

        st.dataframe(
            filtered_report,
            use_container_width=True,
            hide_index=True
        )


        # ====================================================
        # FULL CSV DOWNLOAD
        # ====================================================

        csv_data = (
            report_df
            .to_csv(index=False)
            .encode("utf-8-sig")
        )


        report_filename = (
            "diet_chart_delivery_report_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".csv"
        )


        st.download_button(
            label="📥 Download Complete Delivery Report",
            data=csv_data,
            file_name=report_filename,
            mime="text/csv"
        )


        # ====================================================
        # FAILED RECORDS DOWNLOAD
        # ====================================================

        failed_report = report_df[
            report_df["Status"]
            == "Failed"
        ]


        if not failed_report.empty:

            failed_csv = (
                failed_report
                .to_csv(index=False)
                .encode("utf-8-sig")
            )


            failed_filename = (
                "failed_diet_chart_emails_"
                + datetime.now().strftime(
                    "%Y%m%d_%H%M%S"
                )
                + ".csv"
            )


            st.download_button(
                label="⚠️ Download Failed Records Only",
                data=failed_csv,
                file_name=failed_filename,
                mime="text/csv"
            )


    else:

        st.info(
            "No delivery report available yet. "
            "Please send emails from the "
            "'Send Bulk Emails' tab first."
        )
