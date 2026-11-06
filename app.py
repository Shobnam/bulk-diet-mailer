import base64
import time
from datetime import datetime
from email.utils import parseaddr

import pandas as pd
import requests
import streamlit as st


# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="Diet Chart Bulk Emailer",
    page_icon="📋",
    layout="wide"
)

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

st.title("📋 Bulk Patient Diet Chart Mailer")

current_time = datetime.now().strftime(
    "%d-%b-%Y | %I:%M:%S %p"
)

st.markdown(
    f"⏱️ **System Current Time:** `{current_time}`"
)

st.markdown("---")


# =========================================================
# HELPER FUNCTIONS
# =========================================================
def clean_patient_id(value):
    """
    Clean Patient ID imported from CSV or Excel.

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
    Perform basic email validation.
    """

    if not email_address:
        return False

    parsed_email = parseaddr(email_address)[1]

    if "@" not in parsed_email:
        return False

    domain = parsed_email.split("@")[-1]

    return "." in domain


def get_access_token():
    """
    Get the Microsoft access token exposed by Streamlit OIDC.
    """

    try:
        return st.user.tokens["access"]
    except Exception:
        return None


def get_signed_in_user(access_token):
    """
    Get signed-in Microsoft 365 account details.
    """

    response = requests.get(
        f"{GRAPH_BASE_URL}/me",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        params={
            "$select": (
                "displayName,mail,userPrincipalName"
            )
        },
        timeout=30
    )

    if response.status_code == 200:
        user_data = response.json()

        user_email = (
            user_data.get("mail")
            or user_data.get("userPrincipalName")
            or ""
        )

        return {
            "name": user_data.get(
                "displayName",
                ""
            ),
            "email": user_email
        }

    raise Exception(
        f"Microsoft Graph user check failed: "
        f"{response.status_code} - {response.text}"
    )


def send_graph_email(
    access_token,
    patient_name,
    patient_email,
    patient_id,
    pdf_name,
    pdf_content
):
    """
    Send email using Microsoft Graph with a PDF attachment.
    """

    encoded_pdf = base64.b64encode(
        pdf_content
    ).decode("utf-8")

    email_body = f"""Hello {patient_name},

Your personalized diet chart for Patient ID {patient_id} is attached to this email.

Please review the attached PDF document for your detailed nutrition guidelines.

If you have any questions regarding your diet chart, please contact your assigned health coach.

Regards,
Diet & Health Team
"""

    request_body = {
        "message": {
            "subject": (
                "Your Personalized Diet Chart - "
                f"Patient ID: {patient_id}"
            ),
            "body": {
                "contentType": "Text",
                "content": email_body
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": patient_email
                    }
                }
            ],
            "attachments": [
                {
                    "@odata.type": (
                        "#microsoft.graph.fileAttachment"
                    ),
                    "name": pdf_name,
                    "contentType": "application/pdf",
                    "contentBytes": encoded_pdf
                }
            ]
        },
        "saveToSentItems": True
    }

    response = requests.post(
        f"{GRAPH_BASE_URL}/me/sendMail",
        headers={
            "Authorization": (
                f"Bearer {access_token}"
            ),
            "Content-Type": "application/json"
        },
        json=request_body,
        timeout=120
    )

    if response.status_code == 202:
        return True, ""

    return (
        False,
        f"Graph API Error {response.status_code}: "
        f"{response.text}"
    )


# =========================================================
# SESSION STATE
# =========================================================
if "report_df" not in st.session_state:
    st.session_state["report_df"] = None


# =========================================================
# LOGIN SCREEN
# =========================================================
if not st.user.is_logged_in:

    st.subheader("🔐 Microsoft 365 Sign-In")

    st.info(
        "Microsoft account se secure login karein. "
        "Email ID, password aur OTP Microsoft ki official "
        "login screen par enter hoga."
    )

    st.write(
        "Login successful hone ke baad isi Microsoft 365 "
        "mailbox se diet chart emails send hongi."
    )

    st.button(
        "🔐 Login with Microsoft",
        type="primary",
        use_container_width=True,
        on_click=st.login
    )

    st.stop()


# =========================================================
# GET SIGNED-IN USER
# =========================================================
access_token = get_access_token()

if not access_token:

    st.error(
        "Microsoft access token available nahi hai. "
        "Streamlit Secrets mein expose_tokens = "
        '["id", "access"] check karein.'
    )

    if st.button(
        "Sign Out and Try Again",
        use_container_width=True
    ):
        st.logout()

    st.stop()


try:
    signed_in_user = get_signed_in_user(
        access_token
    )

except Exception as user_error:

    st.error(
        "Signed-in Microsoft account verify nahi ho saka."
    )

    st.code(str(user_error))

    if st.button(
        "Sign Out",
        use_container_width=True
    ):
        st.logout()

    st.stop()


# =========================================================
# SIDEBAR ACCOUNT INFORMATION
# =========================================================
st.sidebar.header("✅ Microsoft Account Connected")

st.sidebar.write(
    f"**Name:** {signed_in_user['name']}"
)

st.sidebar.write(
    f"**Sender Email:** {signed_in_user['email']}"
)

st.sidebar.success(
    "Password aur OTP Microsoft ne securely verify kiya hai."
)

email_delay = st.sidebar.number_input(
    "Delay Between Emails",
    min_value=0.0,
    max_value=30.0,
    value=1.0,
    step=0.5,
    help="Delay in seconds between two emails."
)

if st.sidebar.button(
    "🚪 Sign Out",
    use_container_width=True
):
    st.logout()


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

    st.success(
        "Emails will be sent from: "
        f"{signed_in_user['email']}"
    )

    upload_col1, upload_col2 = st.columns(
        [1, 1]
    )

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
            "Patient CSV ya Excel file upload karein."
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

            elif file_extension in [
                "xlsx",
                "xls"
            ]:

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
                f"Patient file read nahi hui: "
                f"{read_error}"
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
            .astypee(str)
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
            apply(clean_patient_id)
        )

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
                "Patient file mein valid records nahi mile."
            )

            st.stop()

        # =================================================
        # PDF MATCHING
        # =================================================
        pdf_dictionary = {
            uploaded_pdf.name.strip().lower():
            uploaded_pdf
            for uploaded_pdf in uploaded_pdfs
        }

        df["Expected_PDF"] = (
            df["PatientID"].apply(
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

        df["Name_Valid"] = (
            df["Name"] != ""
        )

        df["PatientID_Valid"] = (
            df["PatientID"] != ""
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
            & df["Name_Valid"]
            & df["PatientID_Valid"]
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

        duplicate_patient_count = int(
            df["Duplicate_PatientID"].sum()
        )

        metric1, metric2, metric3, metric4 = (
            st.columns(4)
        )

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
                f"⚠️ {missing_pdf_count} records ki "
                "matching PDF nahi mili."
            )

        if invalid_email_count > 0:

            st.warning(
                f"⚠️ {invalid_email_count} records mein "
                "email invalid ya blank hai."
            )

        if duplicate_patient_count > 0:

            st.warning(
                "⚠️ Duplicate Patient IDs present hain. "
                "Send karne se pehle verify karein."
            )

        if (
            missing_pdf_count == 0
            and invalid_email_count == 0
        ):

            st.success(
                "✅ All records passed the main validation."
            )

        # =================================================
        # VALIDATION TABLE
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
            "Duplicate_Email",
            "Ready_To_Send"
        ]

        st.dataframe(
            df[validation_columns],
            use_container_width=True,
            hide_index=True
        )

        # =================================================
        # CONFIRMATION
        # =================================================
        confirmation = st.checkbox(
            f"I confirm that I want to send "
            f"{ready_count} patient emails from "
            f"{signed_in_user['email']}."
        )

        send_button = st.button(
            "🚀 Send Diet Charts",
            type="primary",
            use_container_width=True,
            disabled=(
                not confirmation
                or ready_count == 0
            )
        )

        # =================================================
        # SEND EMAILS
        # =================================================
        if send_button:

            df["Status"] = "Pending"
            df["Sent_At_Timestamp"] = ""
            df["Error_Details"] = ""

            progress_bar = st.progress(0)

            status_placeholder = st.empty()

            live_report_placeholder = st.empty()

            total_patients = len(df)

            token_expired = False

            for position, (index, row) in enumerate(
                df.iterrows(),
                start=1
            ):

                patient_name = row["Name"]
                patient_email = row["Email"]
                patient_id = row["PatientID"]
                pdf_name = row["Expected_PDF"]

                processing_time = (
                    datetime.now()
                    .strftime("%Y-%m-%d %H:%M:%S")
                )

                status_placeholder.markdown(
                    f"⏳ **[{processing_time}]** "
                    f"Processing {position}/{total_patients}: "
                    f"**{patient_name}** (`{patient_id}`)"
                )

                # -----------------------------------------
                # VALIDATION FAILURES
                # -----------------------------------------
                if not row["Name_Valid"]:

                    df.at[
                        index,
                        "Status"
                    ] = "Failed"

                    df.at[
                        index,
                        "Error_Details"
                    ] = "Patient name is blank"

                elif not row["PatientID_Valid"]:

                    df.at[
                        index,
                        "Status"
                    ] = "Failed"

                    df.at[
                        index,
                        "Error_Details"
                    ] = "Patient ID is blank"

                elif not row["Email_Valid"]:

                    df.at[
                        index,
                        "Status"
                    ] = "Failed"

                    df.at[
                        index,
                        "Error_Details"
                    ] = (
                        "Invalid or blank email address"
                    )

                elif not row["PDF_Found"]:

                    df.at[
                        index,
                        "Status"
                    ] = "Failed"

                    df.at[
                        index,
                        "Error_Details"
                    ] = (
                        f"PDF missing or mismatch: "
                        f"{pdf_name}"
                    )

                else:

                    try:

                        pdf_file = pdf_dictionary[
                            pdf_name.lower()
                        ]

                        pdf_file.seek(0)

                        pdf_content = pdf_file.read()

                        success, error_details = (
                            send_graph_email(
                                access_token=access_token,
                                patient_name=patient_name,
                                patient_email=patient_email,
                                patient_id=patient_id,
                                pdf_name=pdf_name,
                                pdf_content=pdf_content
                            )
                        )

                        if success:

                            df.at[
                                index,
                                "Status"
                            ] = "Success"

                            df.at[
                                index,
                                "Sent_At_Timestamp"
                            ] = (
                                datetime.now()
                                .strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                            )

                        else:

                            df.at[
                                index,
                                "Status"
                            ] = "Failed"

                            df.at[
                                index,
                                "Error_Details"
                            ] = error_details

                            if (
                                "InvalidAuthenticationToken"
                                in error_details
                                or "401" in error_details
                            ):

                                token_expired = True

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

                if token_expired:

                    status_placeholder.error(
                        "Microsoft login token expired. "
                        "Please sign out and sign in again."
                    )

                    break

                time.sleep(
                    float(email_delay)
                )

            # =================================================
            # FINAL REPORT
            # =================================================
            st.session_state["report_df"] = (
                df.copy()
            )

            success_count = int(
                (df["Status"] == "Success").sum()
            )

            failed_count = int(
                (df["Status"] == "Failed").sum()
            )

            pending_count = int(
                (df["Status"] == "Pending").sum()
            )

            if not token_expired:

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


# =========================================================
# TAB 2: DELIVERY REPORT
# =========================================================
with report_tab:

    st.subheader("📊 Delivery Report")

    report_df = st.session_state.get(
        "report_df"
    )

    if report_df is None:

        st.info(
            "Abhi koi delivery report available nahi hai."
        )

    else:

        success_count = int(
            (report_df["Status"] == "Success").sum()
        )

        failed_count = int(
            (report_df["Status"] == "Failed").sum()
        )

        pending_count = int(
            (report_df["Status"] == "Pending").sum()
        )

        report1, report2, report3, report4 = (
            st.columns(4)
        )

        report1.metric(
            "Total",
            len(report_df)
        )

        report2.metric(
            "Success",
            success_count
        )

        report3.metric(
            "Failed",
            failed_count
        )

        report4.metric(
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
                label="⚠️ Download Failed Records",
                data=failed_csv,
                file_name=(
                    "failed_diet_chart_emails_"
                    f"{report_timestamp}.csv"
                ),
                mime="text/csv",
                use_container_width=True
            )
