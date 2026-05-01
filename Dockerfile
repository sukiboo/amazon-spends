FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# HF Spaces runs the container as a non-root user (uid 1000) and mounts a
# writeable home there. Streamlit needs $HOME writeable for its config/cache,
# and it must bind to 0.0.0.0:8501 (the port declared in README's `app_port`).
# XSRF must be disabled because HF's reverse proxy doesn't pass through the
# XSRF cookie on the upload endpoint, so st.file_uploader 403s otherwise.
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
