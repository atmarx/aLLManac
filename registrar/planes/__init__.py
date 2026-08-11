"""The registrar's planes — one module per system this thing talks to.

`reconcile.py` used to be all of this in one 727-line file, with the
boundaries drawn as comment rules.  The rules were real; they are
directories now.  Nothing about the trust model changed in the split:

    config    env + constants.  No credentials USED, only named.
    courses   registrar/courses.yaml — read, normalize, validate, write.
              The only plane with no network calls at all.
    keycloak  course OIDC clients and the admin/member door roles.
    gateway   LiteLLM teams (the course pool) and keys (the fuses).
    escrow    OpenBao — custody of every minted key.
    verbs     the reconcile verbs, which are the ONLY things that compose
              the planes above.  If a plane imports a sibling plane, that
              is the bug: composition happens here or not at all.

Import it through `reconcile` — that module is the public face of this
package and the seam server.py is allowed to touch.  See its docstring for
why the credential boundary is worth this much ceremony.
"""
