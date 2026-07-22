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

api_addr     = "http://openbao:8200"
cluster_addr = "http://openbao:8201"
