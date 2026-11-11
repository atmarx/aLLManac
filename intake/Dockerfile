# The intake room's tool service.  Same pinned base as usage-mcp.
FROM python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY svc/ svc/
RUN useradd -r -u 10001 svc && mkdir -p /data && chown svc /data
USER svc
EXPOSE 8080
CMD ["python", "-m", "svc.server"]
