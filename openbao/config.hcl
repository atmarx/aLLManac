# OpenBao — the escrow.  Single node, integrated (raft) storage: raft is
# the backend with the ONLINE snapshot API (`bao operator raft snapshot
# save`), which the one-VM backup story leans on.  TLS is off because this
# listener never leaves the compose network (plus a 127.0.0.1 host bind for
# the operator CLI).  Init/unseal/policies: `just bao-init` — the once-per-
# box ritual; `just up` re-unseals after restarts (BAO_UNSEAL_KEY in .env).
ui = false

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = true
}

# /openbao/file is the image's pre-owned data dir (the container runs as the
# unprivileged openbao user; a volume mounted anywhere else lands root-owned
# and raft can't open its bolt file — found the hard way on first boot):
storage "raft" {
  path    = "/openbao/file"
  node_id = "almanac"
}

# The receipts.  OpenBao 2.x refuses `bao audit enable` over the API ("use
# declarative, config-based audit device management") — so this block is the
# ONLY way the device exists.  Read at every unseal: an already-initialized
# store gains it on its next restart (measured on 2.4.1, 2026-10-02).  The
# file is HMAC'd JSON, one line per request and per response, in the
# bao-logs volume, which the data bundle carries.  If the device can't write,
# bao refuses requests rather than serve them unrecorded — that is the point.
audit "file" "file" {
  description = "every request and response, HMAC'd"
  options {
    file_path = "/openbao/logs/audit.log"
  }
}

api_addr     = "http://openbao:8200"
cluster_addr = "http://openbao:8201"
