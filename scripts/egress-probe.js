// Runs INSIDE a LibreChat container, against that container's own config and
// its own guard function.  Nothing here is a reimplementation — the whole
// point is that the verdict comes from the code that actually enforces.
const yaml = require('js-yaml');
const fs = require('fs');
const { isActionDomainAllowed } = require('/app/packages/api/dist/index.cjs');

const CONFIG = process.env.CONFIG_PATH || '/app/librechat.yaml';
const OFF_LIST = 'definitely-not-allowed.invalid';
const PRIVATE = '169.254.169.254'; // cloud metadata — the SSRF prize

const pad = (s, n) => String(s).padEnd(n);
let failed = 0;
const bad = (m) => { failed++; console.log(`  FAIL  ${m}`); };
const ok = (m) => console.log(`  ok    ${m}`);

(async () => {
  const cfg = yaml.load(fs.readFileSync(CONFIG, 'utf8')) || {};

  // ---- Layer 1: is the knob where the code reads it? -------------------------
  // An `actions:` block nested under `endpoints:` parses cleanly, validates,
  // and is never read.  That is the failure this layer exists to catch.
  const topLevel = Object.prototype.hasOwnProperty.call(cfg, 'actions');
  const nested = !!(cfg.endpoints && cfg.endpoints.actions);
  console.log('\nLayer 1 — placement');
  if (nested) bad('`actions:` is nested under `endpoints:` — it parses and does NOTHING');
  if (topLevel) ok('`actions:` is top-level, where ToolService reads it');
  else if (!nested) console.log('  --    no `actions:` block at all');

  const domains = (cfg.actions && cfg.actions.allowedDomains) || null;
  const caps = ((cfg.endpoints && cfg.endpoints.agents && cfg.endpoints.agents.capabilities) || []);
  const actionsOn = caps.includes('actions');
  console.log(`        capabilities: [${caps.join(', ')}]`);
  console.log(`        actions capability: ${actionsOn ? 'ON' : 'off'}`);
  console.log(`        allowedDomains: ${domains === null ? '(absent)' : JSON.stringify(domains)}`);

  // ---- Layer 2: what does that configuration actually MEAN? ------------------
  console.log('\nLayer 2 — posture');
  if (!actionsOn) {
    ok('`actions` is not in capabilities — agent Actions cannot run at all.');
    console.log('        This is the ONLY complete answer.  There is no deny-all list.');
  } else if (!domains || domains.length === 0) {
    bad('`actions` is ON with no allowlist — the ENTIRE public internet is reachable');
    console.log('        An empty list is NO allowlist, not an empty one.  Add domains,');
    console.log('        or drop `actions` from capabilities.');
  } else {
    ok(`\`actions\` is ON and scoped to ${domains.length} rule(s)`);
  }

  // ---- Layer 3: is the guard load-bearing? ----------------------------------
  // Ask the image's own function, not our understanding of it.
  //
  // This layer only ASSERTS when there is something to enforce.  With
  // `actions` off there is no egress to scope, and with `actions` on and no
  // list the hole is already Layer 2's finding — re-failing it here would
  // report one problem twice and make a passing run look like two problems.
  // A check that cries wolf gets ignored, which is how you end up with a
  // guardrail nobody verified.
  console.log('\nLayer 3 — enforcement (the pinned image\'s own isActionDomainAllowed)');
  if (!actionsOn) {
    console.log('  --    not applicable: `actions` is off, so no egress to scope.');
    console.log('        (The allowlist below would be inert even if it were set.)');
  } else {
    const probes = [];
    for (const d of domains || []) {
      const subject = d.replace(/^\*\./, 'probe.').split('/')[0];
      probes.push([subject, true, `listed rule ${JSON.stringify(d)} permits it`, true]);
      if (d.includes('/')) {
        // A path-shaped rule does NOT scope to that path — it widens to the
        // whole host.  The registrar rejects these at validate time; this
        // catches one that reached a running instance some other way.
        const host = d.split('/')[0].replace(/^\*\./, 'probe.');
        probes.push([`https://${host}/somewhere/else`, false,
          `path-shaped rule ${JSON.stringify(d)} does NOT widen to the host`, true]);
      }
    }
    // With no allowlist these two demonstrate Layer 2's finding rather than
    // adding a new one — shown, but not counted against the exit code.
    const scoped = !!(domains && domains.length);
    probes.push([OFF_LIST, false, 'a domain nobody listed is refused', scoped]);
    probes.push([PRIVATE, false, 'cloud metadata endpoint is refused', true]);

    for (const [subject, want, label, assert] of probes) {
      let got;
      try { got = await isActionDomainAllowed(subject, domains); }
      catch (e) { got = `THREW ${e.message}`; }
      const line = `${pad(label, 52)} ${pad(subject, 34)} -> ${got}`;
      if (got === want) ok(line);
      else if (assert) bad(`${line}   (expected ${want})`);
      else console.log(`  --    ${line}   (consequence of the Layer 2 finding)`);
    }
  }

  console.log('');
  process.exit(failed ? 1 : 0);
})();
