# Production setup (AWS + Neon)

The API runs on **AWS Lambda as a container image** (`backend/Dockerfile`, Lambda Web Adapter,
ARM64) behind a **Lambda Function URL**, in **us-west-2** next to the Neon database. The app is
served by a Cloudflare Worker from an S3 bucket. Three CloudFormation stacks:

| Stack | Template | Creates | Deployed by |
| --- | --- | --- | --- |
| `overloader-registry` | `registry.yaml` | ECR repo `overloader-api` (immutable tags, scan on push, keeps 10 images) and **every IAM role**: `overloader-github-deploy` (GitHub Actions on `main`), `overloader-cfn-deploy` (what CloudFormation uses for those deploys), `overloader-api-exec` (the running API: its own logs, nothing else) | Grant, as root |
| `overloader-api` | `api.yaml` | Lambda `overloader-api` (ARM64, 512 MB, reserved concurrency 5, kill switch), log group (30 days), public Function URL | Grant once (secrets), then **GitHub Actions on every deploy** |
| `overloader-web` | `web.yaml` | S3 bucket for the PWA (readable only from Cloudflare) + upload rights for the deploy role | Grant, as root |

**Deploys are automatic.** A push to `main` that touches `backend/` runs
`.github/workflows/deploy-api.yml`: build and push the image, migrate and sync the catalog, then
`aws cloudformation deploy` with `ImageTag=<commit>`. Every other parameter, secrets included,
keeps its value, so nothing is typed by hand and the stack always matches what's running. A push
that touches `frontend/` runs `deploy-web.yml`. Docs-only pushes deploy nothing; both workflows
can also be started by hand (Actions → Run workflow). Claude asks Grant before pushing to `main`.

Why the split: GitHub's role can push images and start api-stack updates but has no IAM or
Lambda write access itself. CloudFormation applies the update as `overloader-cfn-deploy`, which
can manage only that function, its URL and log group, and can only hand the function the fixed
`overloader-api-exec` role. What the API may do is set in the registry stack, which only Grant
deploys.

**Secrets never go in git or chat.** Grant types them into the Neon console, `psql`, GitHub's
secret prompt and the CloudFormation console.

**Cost:** Lambda and the Function URL stay inside the free tier at this traffic; ECR storage is a
few cents. The account's $5/month budget doesn't need changing.

---

## First-time setup

Do these in order. Steps marked 🧑 are Grant's; the rest Claude can do or check.

> **Check the region selector (top right) says US West (Oregon) before creating either stack.**
> The console tends to open in N. California (us-west-1), where the rest of the account lives; a
> stack created there points its permissions at the wrong region and has to be deleted first
> (IAM role names are global). And choose **Create stack → With new resources (standard)**, not
> *With existing resources (import)*, which asks for a DeletionPolicy and hides the IAM checkbox.

### 1. 🧑 Neon: production connection strings

The overloader project's branches (set up 2026-11-27):

| Branch | Database | Used by |
| --- | --- | --- |
| **prod** (root, default) | `overloader` | production; the API and migrations |
| **dev** (child of prod) | `neondb` | local development (`backend/.env` `DATABASE_URL`) |
| **test** (child of prod) | `neondb` | pytest (`TEST_DATABASE_URL`); wiped every run |

New branches copy their parent's data *and passwords*, so `prod`'s `neondb_owner` password was
reset after `dev` was branched from it. Neon's create-branch dialog defaults to auto-deleting the
branch after a day: set it to **Never** for anything long-lived.

In the Neon console use **Connect** with branch **prod**, database **overloader**, role
`neondb_owner`, and copy two strings:

- **Direct** (connection pooling *off*): for migrations.
- **Pooled** (pooling *on*, host contains `-pooler`): the base for the API's own string in step 5.

### 2. 🧑 GitHub: the migration secret

In a terminal (it prompts for the value and doesn't show it):

```powershell
gh secret set MIGRATE_DATABASE_URL --repo GrantHolcombe/overloader
```

Paste the **direct** owner string from step 1.

### 3. 🧑 AWS: the registry stack

AWS console as root → region **US West (Oregon) us-west-2** → CloudFormation → **Create stack** →
*With new resources* → upload `infra/registry.yaml` → stack name `overloader-registry` → keep the
defaults → tick *I acknowledge that AWS CloudFormation might create IAM resources with custom
names* → **Submit**.

**Already created it before 2026-11-27?** Update it (CloudFormation → `overloader-registry` →
Update → *Replace existing template* → upload `registry.yaml`, keep the defaults, tick the IAM
box). The first version trusted `repo:GrantHolcombe/overloader`, but GitHub signs this repo in
with its immutable IDs (`repo:GrantHolcombe@8533071/overloader@1473704173`), so AWS refused it.

When it's done, copy the **DeployRoleArn** output and set it as a repository *variable* (not
secret; an ARN isn't sensitive). Claude can do this once the stack exists:

```powershell
gh variable set AWS_DEPLOY_ROLE_ARN --repo GrantHolcombe/overloader --body "arn:aws:iam::...:role/overloader-github-deploy"
```

### 4. First deploy run (pushes the image, prepares the database)

GitHub → **Actions** → **deploy-api** → **Run workflow** on `main`, with *migrate* ticked. It
builds and pushes the image, then migrates the production database: it creates the tables, the
`overloader_app` role (with no password yet) and the exercise catalog. There's no function yet, so
it ends with "create the api stack with ImageTag=…". Note that commit SHA.

### 5. 🧑 Neon: the API's least-privilege login (and the JWT secret)

`overloader_app` can read and write rows in the app's tables and nothing else (no schema changes,
no roles, no `alembic_version`). Migration `0004_app_role.py` created it without a password.

psql's `\password` doesn't work on Neon (it sends the password pre-encrypted; Neon only accepts
plain text), and `ALTER ROLE ... PASSWORD '...'` at the psql prompt would land in psql's history.
So a script does it, with nothing secret on screen:

```powershell
cd backend
.venv\Scripts\python scripts\set_app_password.py
```

It asks (hidden) for prod's **direct** owner string, sets a random password on `overloader_app`,
builds and tests the API's **pooled** string (it can read rows, it can't create tables), and puts
it on the clipboard for the stack's **DatabaseUrl**; press Enter and a new **JwtSecret** replaces
it; Enter again clears the clipboard. Have step 6's parameter page open before running it. If the
values are lost, run it again and update the stack.

### 6. 🧑 AWS: the API stack

Same console, **us-west-2** → CloudFormation → **Create stack** → upload `infra/api.yaml` → stack
name `overloader-api`. Parameters:

| Parameter | Value |
| --- | --- |
| ImageTag | the commit SHA from step 4 |
| DatabaseUrl | pasted from the script in step 5 |
| JwtSecret | pasted from the script in step 5 |
| ResendApiKey, OriginSecret, CorsOrigins | leave empty for now |
| everything else | defaults |

Tick the IAM acknowledgement → **Submit**. The **FunctionUrl** output is the API's address.

### 7. Check it

- Open `<FunctionUrl>api/health`: expect `{"ok":true}`. (The first call after idle takes a second
  or two while Lambda starts the container.)
- Run **deploy-api** again: this time it updates the function and smoke-tests it.

---

## The app on the web (temporary hostname)

Until the app has its final name and domain it lives at **https://overloader.hiregrant.today**, a
subdomain of an existing Cloudflare zone. Moving later means a new DNS record and Worker route,
and new Resend domain; the bucket and stacks don't change.

```
phone --HTTPS--> Cloudflare (overloader.hiregrant.today)
                   Worker "overloader-edge"  (cloudflare/edge/worker.js)
                     /api/*  -> Lambda Function URL  (+ X-Origin-Verify secret, X-Client-IP)
                     else    -> S3 bucket overloader-web-<account> (website endpoint, Cloudflare IPs only)
```

### 8. 🧑 AWS: registry update and the web stack (before merging the PR that adds them)

Merging the change that added automatic deploys triggers both workflows, so these two come first
(from the branch's files):

1. **Update `overloader-registry`**: CloudFormation → the stack → **Update** → *Replace existing
   template* → `infra/registry.yaml` → keep the defaults → tick the IAM box → Submit. It adds
   `overloader-cfn-deploy` and `overloader-api-exec` and lets GitHub start api-stack updates.
2. **Create `overloader-web`**: *Create stack → With new resources (standard)* → `infra/web.yaml`
   → defaults → tick the IAM box → Submit. The **WebsiteOrigin** output goes into the Worker in
   step 10.

The first automatic api deploy after the merge moves the function to `overloader-api-exec` and
removes the old `overloader-api-role` (a one-time cleanup permission in the registry stack allows
exactly that; it can be deleted afterwards).

### 9. Resend: a sending domain

Claude adds `send.hiregrant.today` to the Resend account (1 of 3 domains used) and its DNS
records to the `hiregrant.today` zone in Cloudflare (**DNS only**, grey cloud), then checks it
verifies. A subdomain keeps these emails apart from Google Workspace mail on the main domain.

🧑 Then in Resend → **API Keys** → *Create*: name `overloader-api`, permission **Sending access**,
domain `send.hiregrant.today`. Copy it only when step 11 is open (it goes straight into the stack).

### 10. Cloudflare: DNS record and Worker

- DNS for `hiregrant.today`: `AAAA overloader 100::`, **Proxied**. The address is a placeholder;
  the Worker answers every request.
- Workers & Pages → *Create* → Worker `overloader-edge` → paste `cloudflare/edge/worker.js` →
  Deploy. **Settings → Domains & Routes**: route `overloader.hiregrant.today/*`, zone
  `hiregrant.today`. **Variables**: `API_ORIGIN` = the api stack's FunctionUrl, `SITE_ORIGIN` =
  the web stack's WebsiteOrigin (plain text).
- 🧑 The shared secret: run `.venv\Scripts\python scripts\new_secret.py` in `backend/`, paste it
  into the Worker as a **Secret** named `ORIGIN_SECRET` *and* into step 11's **OriginSecret**,
  then press Enter (clears the clipboard).

### 11. 🧑 AWS: update the api stack

CloudFormation → `overloader-api` → **Update** → *Replace existing template* → `infra/api.yaml`:

| Parameter | Value |
| --- | --- |
| ImageTag | leave as is (the deploys keep it current) |
| OriginSecret | from `new_secret.py` (step 10) |
| ResendApiKey | the key from step 9 |
| SigninEmailFrom | `Overloader <signin@send.hiregrant.today>` |
| ClientIpHeader | `x-client-ip` (the Worker sets it) |
| DatabaseUrl, JwtSecret | leave as they are |

After this the Function URL answers only requests that came through the Worker (except
`/api/health`).

### 12. Deploy the frontend and try it

Claude sets the repository variable `APP_URL` = `https://overloader.hiregrant.today` and runs
**deploy-web** (asks first). Then open the site on your phone, sign in with your own email, and
**Add to Home Screen**.

## Day to day

- **Deploy:** push to `main` (backend → API, frontend → app). Or Actions → deploy-api /
  deploy-web → Run workflow.
- **Changing a secret or setting** (memory, kill switch, Resend key): CloudFormation →
  `overloader-api` → Update → *Use existing template*, change just that parameter, leave the rest
  (ImageTag included; deploys keep it current). Template changes in `infra/api.yaml` go out with
  the next API deploy on their own.
- **Changing the Worker:** paste `cloudflare/edge/worker.js` into the dashboard again and Deploy
  (not automated; it rarely changes).
- **Kill switch:** update the stack with `ApiEnabled=false`. Reserved concurrency goes to 0 and every
  request gets a free 429. Set it back to `true` to re-enable.
- **Rollback:** Actions → deploy-api → Run workflow → put an older commit in **image_tag** (any
  of the 10 newest images in ECR). It skips the build and migrations and deploys that image
  through the stack, so nothing drifts. Or revert the commit on `main` and push. (Migrations
  aren't undone; they're written to keep older code working.)
