# The usage service: LiteLLM's ledger, served back into the chat as MCP
# tools.  Small on purpose — one file, three tools, a read-only DB role.
# Pinned like everything else — bump deliberately: edit, rig-test, commit.
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
RUN useradd -r -u 10001 svc
USER svc
EXPOSE 8080
CMD ["python", "server.py"]
