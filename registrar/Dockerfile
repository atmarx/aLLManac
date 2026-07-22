# The registrar: rosters, key minting, escrow custody — the enrollment
# machine.  Same base pin as usage-mcp; bump the two together.
# NOTE: compose runs this container as the repo owner's uid (user: in
# compose.yml) so renders land host-owned in ./fleet and ./usage-mcp —
# no USER here on purpose.
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py reconcile.py render.py course_admin.py ./
EXPOSE 8080
CMD ["python", "server.py"]
