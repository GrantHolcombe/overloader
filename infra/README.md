# Production setup (AWS + Neon)

The API runs on **AWS Lambda as a container image** (`backend/Dockerfile`, Lambda Web Adapter,
ARM64) behind a **Lambda Function URL**, in **us-west-2** next to the Neon database. Two
CloudFormation stacks, deployed by Grant from the console as root (like `hiregrant-contact`),
because they create IAM roles:

| Stack | Template | Creates |
| --- | --- | --- |
| `overloader-registry` | `registry.yaml` | ECR repo `overloader-api` (immutable tags, scan on push, keeps 10 images) and IAM role `overloader-github-deploy` (GitHub Actions on `main` only: push images, update this one function) |
| `overloader-api` | `api.yaml` | Lambda `overloader-api` (ARM64, 512 MB, reserved concurrency 5, kill switch), IAM role `overloader-api-role` (writes its own logs, nothing else), log group (30 days), public Function URL |

Deploys run from GitHub Actions (`.github/workflows/deploy-api.yml`, manual "Run workflow" for
now): build and push the image, migrate the database and sync the catalog, point the function at
the new image, smoke-test `/api/health`.

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

In the Neon console, project **overloader**, open the **production** branch (separate from dev
and test) and use **Connect** to copy two strings for the owner role `neondb_owner`:

- **Direct** (connection pooling *off*): for migrations.
- **Pooled** (pooling *on*, host contains `-pooler`): the base for the API's own string in step 5.

Keep them in your password manager. They don't need to be in `backend/.env`. (Today `.env`'s
`DATABASE_URL` is still the dev database, which is right for local work.)

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

### 5. 🧑 Neon: the API's least-privilege login

`overloader_app` can read and write rows in the app's tables and nothing else (no schema changes,
no roles, no `alembic_version`). Migration `0004_app_role.py` created it without a password; give it
one now.

1. Make a password (in your terminal, not chat):

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. Connect as the owner with the **direct** string and set it. `\password` asks twice and shows
   nothing:

   ```powershell
   psql "<direct owner string from step 1>"
   ```
   ```
   \password overloader_app
   \q
   ```

3. Build the API's connection string from the **pooled** owner string: replace
   `neondb_owner:<owner password>` with `overloader_app:<new password>`. Everything after the `@`
   (the `-pooler` host, `/neondb?sslmode=require…`) stays the same. Save it in your password
   manager.

Also make a **new JWT secret** for production (not the dev one):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 6. 🧑 AWS: the API stack

Same console, **us-west-2** → CloudFormation → **Create stack** → upload `infra/api.yaml` → stack
name `overloader-api`. Parameters:

| Parameter | Value |
| --- | --- |
| ImageTag | the commit SHA from step 4 |
| DatabaseUrl | the `overloader_app` pooled string from step 5 |
| JwtSecret | the new production secret from step 5 |
| ResendApiKey, OriginSecret, CorsOrigins | leave empty for now |
| everything else | defaults |

Tick the IAM acknowledgement → **Submit**. The **FunctionUrl** output is the API's address.

### 7. Check it

- Open `<FunctionUrl>api/health`: expect `{"ok":true}`. (The first call after idle takes a second
  or two while Lambda starts the container.)
- Run **deploy-api** again: this time it updates the function and smoke-tests it.

---

## Not working yet (on purpose)

- **Sign-in emails:** with no `ResendApiKey`, asking for a code returns a 502. That needs the
  domain and the Resend sending domain (their own board cards), then a stack update with the key
  and `SigninEmailFrom`.
- **Cloudflare in front:** once there's a domain, route it to the Function URL, have Cloudflare add
  an `X-Origin-Verify` header, and update the stack with the same value as `OriginSecret` so direct
  calls to the Function URL get a 403. `ClientIpHeader` (`cf-connecting-ip`) then gives the sign-in
  rate limit each user's real address.
- **The frontend** isn't hosted yet (S3 + Cloudflare card); set `CorsOrigins` when it is.

## Day to day

- **Deploy:** Actions → deploy-api → Run workflow. (Deploying automatically on push to `main` can
  be switched on later.)
- **Stack updates** (secrets, memory, kill switch): CloudFormation → `overloader-api` → Update →
  *Use existing template*. Leave secret parameters as they are unless changing them, and set
  **ImageTag to the tag that's live now** (Lambda console → the function → Image), otherwise the
  update rolls the code back to the tag the stack last had.
- **Kill switch:** update the stack with `ApiEnabled=false`. Reserved concurrency goes to 0 and every
  request gets a free 429. Set it back to `true` to re-enable.
- **Rollback:** Lambda console → the function → Deploy new image → pick an older tag in ECR (the
  last 10 are kept).
