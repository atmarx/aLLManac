# The usage service: LiteLLM's ledger, served back into the chat as MCP
# tools.  Small on purpose — one file, three tools, a read-only DB role.
# Pinned like everything else — bump deliberately: edit, rig-test, commit.
FROM python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
RUN useradd -r -u 10001 svc
USER svc
EXPOSE 8080
CMD ["python", "server.py"]
