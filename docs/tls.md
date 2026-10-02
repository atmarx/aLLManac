---
title: How do I get certificates for the fleet?
description: A decision guide for standing the edge up at an institution — the ten questions only your CA can answer, and the measured half of what Caddy does once you have the answers.
audience: operator
also_reaches: [builder]
status: draft
owner: geordi
tags: [encryption-in-transit, caddy, gateway, chokepoint, tenancy, rendered-config, key-rotation, oidc, keycloak, operator-duty]
tethered_to:
  - caddy/Caddyfile
  - fleet/caddy/
  - registrar/render.py
  - compose.yml
  - .env.example
  - justfile
---
# TLS at the edge — a decision guide

This page is for whoever is standing the aLLManac up at an institution.  It does not tell you what your certificates should be, because that depends on a CA this project has never met.  It tells you **which questions decide the shape of your deployment, who can answer each one, and what each answer costs you.**

Two kinds of question live here and they are deliberately kept apart:

- **Caddy behaviour** — knowable, and answered below with citations.  If something here is wrong, it is a bug in this page and it should be fixed in the same commit as whatever it misled you into.
- **Your CA's behaviour** — *not* answered, on purpose.  Every ACME provider draws these lines differently, and a confident guess in this file would be worse than a blank.  Each one comes with what the answer means for your build, so a wrong assumption surfaces as a question rather than as an outage.

---

## The thing that makes this non-obvious: the fleet is subdomain-per-course

One LibreChat instance per course, each at `<slug>.<ALMANAC_DOMAIN>`.  The control plane adds three more names — chat, auth, gateway.  So the edge is not serving one hostname, it is serving **an open-ended and growing set of them**, created by faculty request rather than by an operator editing a config.

Every decision below is really the same decision wearing different clothes: **when a new course appears, what mints its certificate, and what happens when that fails?**

---

## Three postures

| | What it is | When it's right |
|---|---|---|
| `EDGE_TLS=internal` | Caddy's own local CA.  Browsers warn once and you install the root. | Dev, lab, pilot.  Also the honest answer for an air-gapped box. |
| **Public ACME** | Let's Encrypt / ZeroSSL, HTTP-01 or DNS-01. | A box a public CA can actually reach, on a domain you control. |
| **Enterprise ACME** | Your institution's CA.  Often pre-validated: the domain is authorized once out-of-band, then orders skip challenges entirely. | Most campuses.  This is the case the rest of this page is about. |

The third is the interesting one, because **pre-validation removes the challenge, and the challenge is what most ACME documentation is about.**  If your CA authorizes the domain up front, you need no DNS-01 plugin, no port 80 reachability, and no `acme_dns` block.  You need credentials and a directory URL.

---

## Questions for your ACME provider

Ask these before you write any config.  The answers are not knowable from this repo, and several of them change the architecture rather than a setting.

### 1. What is the *scope* of a domain validation — one FQDN, a subdomain tree, or a wildcard?

**Why it matters more than anything else here.**  If validating `almanac.example.edu` also authorizes `*.almanac.example.edu`, then every future course is already authorized and provisioning stays self-service.  If each FQDN must be validated individually, **course creation acquires a human step at your CA**, and the registrar can no longer finish the job on its own.

That is not a config difference.  That is the difference between a professor getting a course in ten minutes and getting one in three business days.

### 2. Can you issue a **wildcard** on a pre-validated identifier, with no DNS-01?

Public CAs require DNS-01 for wildcards under the CA/Browser Forum baseline requirements.  That is a *challenge-type* rule — and you are skipping challenges.  Whether your CA extends the same shortcut to wildcards is their policy call, and it is worth asking explicitly rather than inferring from the public-CA rule.

- **Yes** → one certificate covers the entire fleet forever.  Simplest possible answer.
- **No, but wildcards can be minted manually** → you have a wildcard, renewed by hand on a calendar.  Workable, and a recurring human obligation that will eventually be missed by whoever inherits it.
- **No wildcards at all** → per-hostname issuance, and question 1 decides whether that can be automated.

### 3. How long does pre-validation last, and what happens to renewals when it lapses?

**This is the one that bites a year later.**  A pre-authorization with a fixed lifetime produces a system that works perfectly until it silently doesn't, and the first symptom is an expired certificate on a Monday morning.

Ask for the duration, ask whether re-validation is automatic or manual, and ask **whether an expired domain validation causes renewals to fail loudly or to fail quietly.**  Then put the expiry date somewhere a human will see it, because your monitoring will not invent it for you.

### 4. Do you require External Account Binding, and in what encoding?

EAB binds your ACME account to your organisation's account with a key ID and an HMAC key from the CA's portal.  Most enterprise CAs require it.  It is the single most common reason a first issuance fails, usually with an unhelpful error.

Ask for both values **and the encoding of the MAC key** — base64url is typical, but a raw or standard-base64 key pasted into a config expecting base64url fails in a way that looks like a credential problem rather than a formatting one.

### 5. Is there a staging or test directory?

You want to prove issuance works before pointing it at the edge that fronts Keycloak, and you want to do that without consuming quota or minting real certificates for a domain you are still experimenting with.  If there is no staging directory, plan on a throwaway hostname instead.

### 6. What are the rate limits — per domain, per account, per period, and on *active* certificates?

Per-course certificates multiply.  A hundred courses is a hundred certificates, each renewing on its own schedule.  Ask about issuance rate *and* total active certificates, because they are different limits and the second one is the one nobody thinks about until a semester rollover.

If the limits are tight, that is an argument for a wildcard even if per-host issuance is technically available.

### 7. What is the certificate lifetime?

Ninety days makes automation mandatory and failure fast.  A year makes failure slow and easy to ignore — you find out about a broken renewal pipeline eleven months after it broke.  Shorter is genuinely safer here, provided the automation works.

### 8. Is there a CAA record requirement?

CAA lives in DNS and must name the issuing CA, or issuance fails no matter how correct your ACME config is.  This one is worth asking because **it is enforced somewhere you are not looking** — the failure is at the CA, the cause is in a zone file, and the two are usually owned by different teams.

### 9. What happens when you request a name that is *not* pre-validated?

Does the order come back with a challenge you cannot solve, or an outright rejection?  This decides how a stray hostname behaves — see the on-demand section below, where a request for an unknown subdomain can trigger an issuance attempt.

### 10. What is the recovery story for a lost ACME account key?

Caddy stores the account key in its data volume.  If that volume is lost, does your CA let you re-register against the same validated domains, or is there a human step?  Worth knowing before you need to know.

---

## When should a course's certificate be minted?

Two shapes, and the repo already leans one way.

**On creation (what the current design does).**  `just course` renders the course's vhost into `fleet/caddy/<slug>.caddy` and reloads the edge.  With a real ACME issuer configured, that reload is what triggers issuance — the certificate is obtained at provisioning time, while an operator is watching, and a failure surfaces as a provisioning error.

**On first access (on-demand TLS).**  Caddy mints per-hostname certificates as requests arrive, gated by an `ask` endpoint so the edge cannot be walked into unbounded issuance.  No config entry is needed per course.

**Prefer mint-on-create, and the reason is not technical.**  Both work.  The difference is *who meets the failure*: at creation it is an operator running a provisioning command, and on first access it is a student hitting a TLS error at eight in the morning on the first day of class.  Push failures toward the person equipped to fix them.

**But the two options fail in opposite directions at renewal time, and this is not obvious.**  A statically-configured site whose renewal breaks keeps serving its expired certificate silently; an on-demand certificate that expires and cannot be renewed fails the handshake outright.  So mint-on-create moves the *first* failure toward the operator and the *recurring* failure away from everyone — into a silence you have to go looking for.  See the renewal section below; the practical answer is **mint-on-create plus explicit alerting on renewal failure**, because Caddy will not raise its hand.

On-demand earns its place as a **fallback**, not a default — if per-FQDN validation (question 1) makes creation-time issuance slow or manual, on-demand at least degrades to "works once the CA catches up" instead of "provisioning is blocked."  If you do enable it, the `ask` endpoint should consult the registrar, which already knows exactly which slugs are real.

**If you get a wildcard, this whole section is moot.**  Caddy uses an automated wildcard for individual subdomains, so no course needs a certificate of its own and there is nothing to time.

---

## What Caddy does — the answerable half

Everything below was either read from Caddy's own source and libraries or run against the image this repo uses.  Each claim is marked:

- **[measured]** — run against `caddy:2` (**v2.11.4**) on a real container.  If you are on a different version, re-measure.
- **[source]** — read from `acmez` v3.1.6 / `certmagic` v0.25.4 / Caddy `master`.  True of the code, not independently exercised.
- **[docs]** — stated in Caddy's documentation.

### Pre-authorization is a supported shape, not a fight

**A CA that pre-authorizes your domain works with no challenge solvers configured at all.** This is the finding that makes the enterprise-ACME path viable, so it is worth being precise about.

`acmez` checks each authorization's status before trying to solve it, and skips any that is already `valid` — guarded in three separate places, then proceeds straight to finalize.  **[source]**  A config with HTTP-01 and TLS-ALPN-01 both disabled and no DNS provider **loads and validates cleanly** — Caddy has no config-time rule requiring a solver.  **[measured]**

The consequence is precise and worth internalising: **an absent solver is not an error until an identifier arrives with a `pending` authorization.**  Your edge will run indefinitely against a CA that always pre-authorizes, and will fail at issuance — not at boot, not at reload — the first time it meets a name your CA has not already validated.  That is the failure mode question 9 above is asking about.

### The config shapes

Naming a CA is what turns off the public-CA defaults:

```caddyfile
{
	acme_ca      https://acme.your-ca.example/directory
	acme_ca_root /path/to/ca-root.crt      # if the ACME endpoint itself uses an internal root
	email        ops@example.edu

	acme_eab {
		key_id  <from your CA's portal>
		mac_key <base64url, no padding>
	}
}
```

Both snippets on this page were adapted against `caddy:2.11.4` rather than written from memory.  One thing that bites while you are wiring this up: **`acme_ca_root` must point at a real PEM**, and if it doesn't, Caddy refuses to start with `unable to add /path to trust pool: <nil>` — a `<nil>` where the reason should be.  It means the file was read and contained no certificate.

**Setting `acme_ca` automatically collapses the issuer list to just that CA** — Caddy does *not* keep Let's Encrypt and ZeroSSL as silent fallbacks once you name an endpoint.  **[source]**  That is the behaviour you want, and it is worth knowing it happens by construction rather than by your remembering to disable something.  The only way to get a public-CA fallback is to explicitly write multiple `issuer` blocks, which certmagic then tries in order.  If someone adds Let's Encrypt "as a backup" to an internal-only deployment, they have built a fallback to a CA that cannot validate your names — noisy at best.

Two EAB details that cost debugging time:

- The MAC key is decoded as **base64url without padding**.  A key containing `+`, `/`, or trailing `=` fails to decode, and the error looks like a credential problem rather than a formatting one.  **[source]**
- **EAB credentials are bound to one directory URL.**  The binding signature is computed against that directory's `newAccount` endpoint, so the same key ID and MAC key generally will *not* work if you point Caddy at a different `dir`.  **[source]**  Plan for staging and production to need separate credentials, and ask your CA for both at once.

### Wildcards are your CA's policy, not Caddy's rule

Neither Caddy nor its ACME libraries contain any "wildcards require DNS-01" logic, and **RFC 8555 does not mandate it either** — it is a CA/Browser Forum policy that public CAs implement by offering only `dns-01` in the challenge list for wildcard authorizations.  **[source, docs]**

So: **if your CA pre-authorizes a wildcard identifier, Caddy will request and use a wildcard certificate with zero solvers configured.**  Same code path as any other pre-authorized name.

One distinction to raise with your CA, because it decides the answer to question 2:

- **Client-initiated pre-authorization** (the client POSTs to `newAuthz`) **cannot be used for wildcards** — RFC 8555 §7.4.1 forbids it outright.
- **Externally-provisioned authorization** — where the CA validates out-of-band and reflects the authorization as already `valid` in your orders — carries **no such restriction**.

If your CA says "we don't support wildcards via ACME," it is worth asking *which* of those two they mean.  The second mechanism is the one an enterprise CA with a validation portal is almost certainly using, and it can cover wildcards.

If you do get a wildcard, the fleet needs nothing per course: **from Caddy 2.10 on, an automated wildcard is used for individual subdomains and Caddy will not obtain per-subdomain certificates unless explicitly told to** (`force_automate`).  **[docs]**  A wildcard already in the cache or on disk also short-circuits on-demand issuance — checked in both places before the issuer is consulted.  **[source]**

### Self-healing: yes — but it does not fail safe

- **Missing certificate** → obtained without a restart.  Static sites check storage on every config load and issue if absent; on-demand issues during the handshake.  **[source]**
- **Renewal** → a maintenance loop every **10 minutes**, renewing when remaining lifetime drops below **⅓** of the total (30 days on a 90-day cert), and deferring to the CA's ARI hint when one is offered.  **[source, docs]**
- **Retry** → escalating backoff from 1 minute out to 6-hour intervals, giving up after **30 days**.  **[source]**
- **Restart** → storage is consulted before any ACME call, so restarting a container with a **persistent** data volume does not re-issue.  An ephemeral data directory re-issues on every restart and will burn through rate limits.  **[source]**

**The part that matters most, and the part nobody expects:**

> If renewal fails permanently on a statically-configured site — lapsed pre-validation, wrong EAB credentials, an unreachable CA — **Caddy keeps serving the expired certificate indefinitely.**  It does not fail closed, and it does not fall back to an internal certificate.  **[source]**

On-demand behaves in the opposite direction: an on-demand certificate that has expired and cannot be renewed **fails the handshake outright**.  And on-demand certificates are **skipped by the background renewal scan entirely** — they are renewed only when a handshake arrives for that name, so a hostname that goes quiet is not maintained while it is quiet.  **[source]**

Neither behaviour is wrong.  But they are opposite, and **which one you get depends on a choice you probably made for unrelated reasons.**

### There is no "list my certificates" endpoint

Caddy's admin API exposes the running *config*, and PKI endpoints for its own internal CA.  Neither tells you what leaf certificates are loaded, when they expire, or what failed to renew.  **[docs]**

Given the paragraph above — a broken renewal serving an expired certificate in silence — **this is the monitoring gap that matters.**  What you have instead:

- **Structured logs** from the `tls.obtain`, `tls.renew`, `tls.maintenance`, and `tls.on_demand` loggers, carrying `identifiers`, `expiration`, and `remaining`.  **[source]**
- **Events** you can subscribe to: `cert_obtained`, `cert_failed`, `cert_ocsp_revoked`.  **[source]**

Alert on `cert_failed` and on the retry loop's give-up message.  If you do nothing else from this page, do that one — it is the difference between finding out from your monitoring and finding out from a student.

### On-demand TLS, if you need it

```caddyfile
{
	on_demand_tls {
		ask http://registrar:8091/tls-ask
	}
}
```

The `ask` endpoint contract, precisely:  Caddy sends a **GET** with the hostname in a **`?domain=`** query parameter, follows no redirects, times out at **10 seconds**, and **never reads the response body** — only the status code, where any **2xx** permits issuance.  **[source]**  Make it a fast local lookup: a slow endpoint blocks the first handshake for that name.

`interval` and `burst` are **gone**.  They are not deprecated — they are a hard config-adapt error that stops Caddy loading at all.  **[measured]**  If you find them in an example, the example predates current Caddy.

### Account identity is keyed by directory URL — quietly

Caddy stores its ACME account under a path derived from the **CA endpoint plus the account email**.  Two consequences, both silent:  **[source]**

- **Changing the directory URL creates a brand-new account** — no error, no prompt.  Moving from a staging directory to production is not a continuation; it is a new identity.
- **Losing the storage volume creates a brand-new account** too, and orphans anything scoped to the old account key.

Since pre-authorizations under RFC 8555 are **account-scoped**, this is where questions 3 and 10 land: if your CA ties domain validations to an ACME account, then a lost volume or a directory change **discards your pre-validations along with the account**, and re-establishing them is a conversation with a human.  Back up the data directory, or pin an explicit `account_key` so the identity survives the storage.


---

## The hostname agreement

Independent of the CA, three things must agree on the auth hostname, and they fail at different times:

- the URL the **browser** uses to reach Keycloak
- `OPENID_ISSUER` in `.env`
- `KC_HOSTNAME` on the Keycloak container

On top of that, the edge **aliases `AUTH_HOST` on the compose network** (see the `edge` service in `compose.yml`), because course instances perform OIDC discovery *through* the edge at the public hostname rather than at an internal service name.  Change the auth hostname and that alias has to move with it.  In hostname mode this means **`KC_HOSTNAME` is exactly `https://$AUTH_HOST`, and `AUTH_HOST` is a bare hostname** — no port, or the alias names something the issuer never mentions.

That discovery is **one-shot at boot**, and it does **not** fail safe.  The instance boots anyway, logs `OpenID Connect configuration failed - strategy not registered` once, and serves a login page whose SSO is dead.  `/api/config` still reports `openidLoginEnabled: true`, because that flag reads env, not the strategy.  The flagship on the docker host ran that way from launch night (2026-07-16) to 2026-09-11.  Its `AUTH_HOST` carried the `:8443` LAN-mode shape while `KC_HOSTNAME` named a different, hostname-mode name, so the alias missed and discovery fell out to a DNS answer nothing routed.  **The only honest check is the log line, or following the login redirect to a Keycloak page that renders** — never the config endpoint.

### Behind a TLS-terminating proxy

A campus load balancer, or a docker host behind a homelab gateway, puts a second TLS hop in front of the edge.  The edge routes by `Host` and picks its cert by SNI, so the proxy has to preserve both — and **with an HTTPS upstream, Caddy ≥ 2.11 sends neither by default.**  Dialing `https://<edge-ip>:<port>` sends the IP as SNI (the edge answers with a TLS alert) and, it turns out, `Host` as the dial address (the edge matches no site and returns an **empty 200**, which a status-code check calls healthy).  On a Caddy front:

```
reverse_proxy https://<edge-ip>:<port> {
    header_up Host {http.request.host}
    transport http {
        tls_server_name {http.request.host}
        tls_insecure_skip_verify    # only if the edge still runs EDGE_TLS=internal
    }
}
```

One wildcard route on the proxy (`*.<ALMANAC_DOMAIN>`) covers chat, auth, gateway and every course, because the edge does the routing — a new course never touches the proxy.  Check bodies, not codes: `content-length: 0` with `via: Caddy` is the signature of a lost `Host`.

### The trap: "real" certificates that Node still doesn't trust

`.env.example` says you can drop `NODE_EXTRA_CA_CERTS` once `EDGE_TLS` is real ACME.  **That is written for a publicly trusted CA.**  If your institution's internal PKI issues the certificate, it is real in every sense that matters to your browser — the root is in the OS trust store, the padlock is green — and it is still not in Node's bundle.

LibreChat's OIDC discovery will fail with a certificate error that looks exactly like a wrong-issuer error.  Keep `NODE_EXTRA_CA_CERTS` pointed at **your** root rather than Caddy's, and only drop it if the CA is publicly trusted.

---

## Prove it before it fronts anything

The cheapest first move is a rig, not a config change: a throwaway Caddy in a container, one hostname, your CA's directory and EAB credentials, and nothing else running.  If it mints, you know pre-authorization works end to end and the real config is a transcription job.  If it doesn't, you found out on a test domain instead of on the edge in front of your identity provider.

Then, and only then, put it on the edge — and check the certificate the running process is actually serving, not the one you believe you configured.  `just config-refresh` exists because a config that changed on disk is not a config the process has read.
