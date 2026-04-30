import streamlit as st

from src.constants import DATA_DIR, ORDERS_ZIP

AMAZON_REQUEST_URL = "https://amazon.com/gp/privacycentral/dsar/preview.html"


def render() -> None:
    st.info(
        f"No Amazon export found yet. Drop `Your Orders.zip` into `{DATA_DIR}/` " "to get started."
    )

    st.subheader("Already have the export?")
    st.markdown("Place `Your Orders.zip` at this exact path, then click **Refresh** below:")
    st.code(str(ORDERS_ZIP), language=None)

    st.subheader("Don't have it yet?")
    st.markdown(
        f"""
Amazon doesn't expose a public API for personal purchase history, so you need to
request a data export:

1. Open Amazon's data request page: [{AMAZON_REQUEST_URL}]({AMAZON_REQUEST_URL})
2. Select **Your Orders** and submit the request
3. Wait for Amazon to email a download link (typically a few hours to a few days)
4. Drop the resulting `Your Orders.zip` into `data/` and click **Refresh**
"""
    )

    if st.button("Refresh", type="primary"):
        st.rerun()
