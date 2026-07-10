# Caddy with the Azure DNS module baked in — so the edge can do ACME DNS-01
# against a delegated zone when this box sits on RFC 1918 (no public port 80).
# Costs nothing if you stay on `tls internal`.
FROM caddy:2-builder AS build
RUN xcaddy build --with github.com/caddy-dns/azure

FROM caddy:2
COPY --from=build /usr/bin/caddy /usr/bin/caddy

# Caddy writes its PKI dirs 0700-root, but other containers (librechat) mount
# caddy-data read-only to trust the internal CA via NODE_EXTRA_CA_CERTS.  Open
# the traversal path + the PUBLIC root cert once it exists; private keys stay
# 0600.  (compose sets init: true, so the backgrounded fixer is reaped.)
CMD ["sh", "-c", "(until [ -f /data/caddy/pki/authorities/local/root.crt ]; do sleep 1; done; chmod 755 /data /data/caddy /data/caddy/pki /data/caddy/pki/authorities /data/caddy/pki/authorities/local; chmod 644 /data/caddy/pki/authorities/local/root.crt) & exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile"]
