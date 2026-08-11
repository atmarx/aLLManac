# `site/infra/` — how this box came to exist

Empty on purpose, and shipped that way.

Everything else in this repo assumes it is talking to **a fresh Linux VM
with Docker installed**.  Getting to that state is where deployments differ
most and share least: an Azure Local VM template, a vSphere clone, a
Terraform module, a cloud-init file, or an afternoon with `apt`.  An example
here would be one institution's answer wearing the costume of a default.

So: whatever provisions and configures the metal underneath `just up` goes
in this directory, in whatever form your institution actually uses.  It is
gitignored along with the rest of `site/`, which is the point — this is the
part that is nobody else's business.

**Current state of the real deployment:** the target is a single VM on Azure
Local running the whole platform *except* inference.  Its IaC will land here
once it has been written against the actual VM rather than guessed at.  Until
then the honest instruction is the one above — bring up a Docker host, then:

```
just setup      # .env + every generated secret
just up         # the stack
just smoke      # prove it
```

If something you write here turns out to generalize — a hardening script,
a backup unit, a health probe that isn't Azure-shaped — promote it to
`site.example/infra/` so the next deployment starts with it.
