# Caddy with the Azure DNS module baked in — so the edge can do ACME DNS-01
# against a delegated zone when this box sits on RFC 1918 (no public port 80).
# Costs nothing if you stay on `tls internal`.
FROM caddy:2-builder AS build
RUN xcaddy build --with github.com/caddy-dns/azure

FROM caddy:2
COPY --from=build /usr/bin/caddy /usr/bin/caddy
