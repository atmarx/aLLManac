# The registrar: rosters, key minting, escrow custody — the enrollment
# machine.  Same base pin as usage-mcp; bump the two together.
# 3.12.15, the 10-01 rebuild: 13 fixable criticals in the 3.12.13 base -> 0
# (grype, 2026-10-11).  Built past its 7-day cooldown.
# NOTE: compose runs this container as the repo owner's uid (user: in
# compose.yml) so renders land host-owned in ./fleet and ./usage-mcp —
# no USER here on purpose.
FROM python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py reconcile.py render.py course_admin.py ./
COPY planes/ ./planes/
EXPOSE 8080
CMD ["python", "server.py"]
