# CI on anything — the pipeline is three lines

All deployment logic lives in the [`justfile`](../justfile).  Every CI system
is the same thin wrapper: **ssh to the box, `just sync`, `just deploy`.**
Below are working equivalents of our Woodpecker pipeline
([`.woodpecker/deploy.yml`](../.woodpecker/deploy.yml)) for GitLab CI and
GitHub Actions — swap the host and you're deployed.

One-time on the target box (any Docker host — a VM, a bare-metal box, wherever):

```bash
sudo apt install just        # or: brew install just / dnf install just
git clone <your-fork> /opt/almanac
cd /opt/almanac
just setup                   # .env + generated secrets
# edit .env: ALMANAC_HOST, INFERENCE_BASE_URL, OPENID_ISSUER
just up
```

And a repo secret holding an ssh private key the box accepts (`DEPLOY_SSH_KEY`
below).

---

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
    - ssh-keyscan deploy-box.example.edu >> ~/.ssh/known_hosts
  script:
    - ssh deploy@deploy-box.example.edu 'cd /opt/almanac && just sync && just deploy'
```

Set `DEPLOY_SSH_KEY` in Settings → CI/CD → Variables (type: file or variable,
protected).

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
          host: deploy-box.example.edu
          username: deploy
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: cd /opt/almanac && just sync && just deploy
```

Set `DEPLOY_SSH_KEY` in Settings → Secrets and variables → Actions.

---

## No CI at all

The contract works by hand, too:

```bash
ssh deploy-box 'cd /opt/almanac && just sync && just deploy'
```

## Kubernetes / Azure Container Apps / whatever

The stack is plain Compose — every image is upstream, all state is in named
volumes, all config is env + three mounted files (`litellm/config.yaml`,
`librechat/librechat.yaml`, `keycloak/realm-northwinds.json`).  Translating to
k8s manifests or an Azure Container environment is mechanical; the `justfile`
recipes (`secrets`, `smoke`, `key`, `spend`) still apply anywhere you can reach
the endpoints.  If you get there before we do, send it back.
