import streamlit as st

from src.constants import ORDERS_ZIP

AMAZON_REQUEST_URL = "https://amazon.com/gp/privacycentral/dsar/preview.html"


def render() -> None:
    st.info("No Amazon export loaded yet. Upload `Your Orders.zip` below to get started.")

    st.subheader("Already have the export?")
    uploaded = st.file_uploader(
        "Upload `Your Orders.zip`",
        type=["zip"],
        accept_multiple_files=False,
    )
    if uploaded is not None:
        st.session_state["uploaded_zip"] = uploaded.getvalue()
        st.rerun()

    st.caption(
        f"Running locally? You can also drop the zip at `{ORDERS_ZIP}` and reload "
        "to skip the upload step on every session."
    )

    st.subheader("Don't have it yet?")
    st.markdown(
        f"""
Amazon doesn't expose a public API for personal purchase history, so you need to
request a data export:

1. Open Amazon's data request page: [{AMAZON_REQUEST_URL}]({AMAZON_REQUEST_URL})
2. Select **Your Orders** and submit the request
3. Wait for Amazon to email a download link (typically a few hours to a few days)
4. Upload the resulting `Your Orders.zip` above
"""
    )
