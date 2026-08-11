# CI on anything — the pipeline is three lines

All deployment logic lives in the [`justfile`](../justfile).  Every CI system is the same thin wrapper: **ssh to the box, sync, `just deploy`.**  Below are working pipelines for Woodpecker, GitLab CI and GitHub Actions — swap the host and you're deployed.

**Your box's details belong in CI secrets, not in the pipeline file.**  Every
CI system reads its pipeline config out of the repo at the commit it's building, so you can't gitignore it — a gitignored pipeline is a pipeline that never runs.  If your fork is public, that means the hostname and ssh user you type into this file are published with it.  All three wrappers below take them from secrets for that reason, which is the same seam as [`site.example/` vs. `site/`](design-walls.md): the platform is tracked and generic, the deployment's own details are the box's business.

Two things that surprise people.  Log masking is best-effort — a `set -x`, or an error message that echoes the host, can still print a secret; the secret keeps the value out of *git*, which is the actual goal.  And **prefer an IP or an FQDN over a short hostname**: the ssh runs inside the pipeline's own container, which doesn't inherit your workstation's DNS search domain, so `deploy-box` can resolve from your desk and fail in CI.

One-time on the target box (any Docker host — a VM, a bare-metal box, wherever):

```bash
sudo apt install just        # or: brew install just / dnf install just
git clone <your-fork> /opt/almanac
cd /opt/almanac
just setup                   # .env + generated secrets
# edit .env: ALMANAC_HOST, INFERENCE_BASE_URL, OPENID_ISSUER
just up
```

And three repo secrets: an ssh private key the box accepts, plus the host and user (`DEPLOY_SSH_KEY` / `DEPLOY_HOST` / `DEPLOY_USER` below).

---

## Why the sync is inline `git` and not `just sync`

There *is* a `just sync` recipe and it does exactly this — but every wrapper below spells the two git commands out by hand instead, which looks like duplication and isn't.

`just` refuses to run **any** recipe if the justfile doesn't parse.  So the moment a syntax error lands in the justfile, `just sync` can no longer fetch the commit that fixes the justfile, and the pipeline fails on every subsequent run — including the ones carrying the fix.  We did this: pipeline #38 failed with #37's error after #37's fix was already merged, and it took a human with ssh to break the loop.

The two git lines are **bootstrap, not deployment logic**: they get the box to the right commit, after which everything still lives in the justfile.  Keep them dependency-free for that reason, and gate on `just --list` so a broken justfile fails fast and legibly instead of halfway through a deploy.

---

## Woodpecker

Ours, in full: [`.woodpecker/deploy.yml`](../.woodpecker/deploy.yml) — it adds guards for "not bootstrapped yet," "`just` not installed," and "no `.env`," which are worth copying.  The shape:

```yaml
# .woodpecker/deploy.yml
when:
  - branch: main
    event: push

steps:
  - name: deploy-almanac
    image: alpine
    environment:
      SSH_KEY:     {from_secret: deploy_ssh_key}
      DEPLOY_HOST: {from_secret: deploy_host}
      DEPLOY_USER: {from_secret: deploy_user}
    commands:
      - apk add --no-cache openssh-client
      - mkdir -p ~/.ssh
      - echo "$SSH_KEY" > ~/.ssh/id_ed25519 && chmod 600 ~/.ssh/id_ed25519
      - ssh-keyscan -p 22 "$DEPLOY_HOST" >> ~/.ssh/known_hosts 2>/dev/null
      - |
        ssh -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" << 'ENDSSH'
        set -e
        cd /opt/almanac
        git fetch origin && git reset --hard origin/main
        just --list >/dev/null || { echo "justfile does not parse"; exit 1; }
        just deploy
        ENDSSH
```

Set the three under repo → Settings → Secrets.  Note the heredoc is quoted (`<< 'ENDSSH'`) so nothing expands locally — everything inside runs on the box. Resist unquoting it to pass a variable across: that expands every `$` in the remote script on the wrong side of the ssh.  Nothing needs to cross.

Secrets don't reach pull requests from forks, which doesn't matter for a `branch: main, event: push` pipeline — but it will bite you if you widen the trigger.

## GitLab CI

```yaml
# .gitlab-ci.yml
deploy:
  stage: deploy
  image: alpine
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  before_script:
    - apk add --no-cache openssh-client
    - mkdir -p ~/.ssh && chmod 700 ~/.ssh
    - echo "$DEPLOY_SSH_KEY" > ~/.ssh/id_ed25519 && chmod 600 ~/.ssh/id_ed25519
    - ssh-keyscan "$DEPLOY_HOST" >> ~/.ssh/known_hosts
  script:
    - |
      ssh "$DEPLOY_USER@$DEPLOY_HOST" 'set -e
        cd /opt/almanac
        git fetch origin && git reset --hard origin/main
        just --list >/dev/null || { echo "justfile does not parse"; exit 1; }
        just deploy'
```

Set all three in Settings → CI/CD → Variables (the key as type *file* or *variable*, protected).

## GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy over ssh
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            set -e
            cd /opt/almanac
            git fetch origin && git reset --hard origin/main
            just --list >/dev/null || { echo "justfile does not parse"; exit 1; }
            just deploy
```

Set all three in Settings → Secrets and variables → Actions.

---

## No CI at all

The contract works by hand, too — and here `just sync` is fine, because the thing that makes it unsafe in CI is that a pipeline can't ssh in and fix a broken justfile.  You can.

```bash
ssh deploy-box 'cd /opt/almanac && just sync && just deploy'
```

## SBOMs for infosec

`just sbom` writes an SPDX JSON per image (both stacks) to `sbom/` plus a tarball to hand over — images already on the box scan from the daemon in seconds; absent ones stream from the registry without polluting the daemon.  SBOMs change when the **pins** change, not per deploy, so it's not part of `just deploy` — run it at pin-bump time (and generate the vLLM one on the GPU box, where the image already lives, unless you enjoy multi-GB registry streams).  If your org wants it in the pipeline anyway, it's one more line in the wrapper:

```bash
ssh deploy-box 'cd /opt/almanac && just sbom'
```

## Kubernetes / Azure Container Apps / whatever

The stack is plain Compose — every image is upstream, all state is in named volumes, all config is env + a few mounted config dirs (`litellm/`, `librechat/`, `fleet/conf/<slug>/`) and the Keycloak realm import.  Those are directory mounts and not file mounts deliberately — a single-file bind pins an inode, so a config replaced by rename never reaches the running container.  See [design-walls.md](design-walls.md).  Translating to k8s manifests or an Azure Container environment is mechanical; the `justfile` recipes (`secrets`, `smoke`, `key`, `spend`) still apply anywhere you can reach the endpoints.  If you get there before we do, send it back.
