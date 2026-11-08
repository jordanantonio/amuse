# Hosted identity setup

This milestone adds email/password sign-in, verified JWTs, database policies, and
confirmed-assignment overlap protection. It does not deploy the app, provide
self-service onboarding, or implement schedule approval/invitation acceptance.
Keep the first hosted environment on fictional data until its integration checks pass.

## Supabase and database setup

1. Create a Supabase project. Use asymmetric signing keys (ES256 or RS256), enable
   email/password authentication, disable public signup, and create test accounts
   administratively. Record their Auth user UUIDs. No role comes from user metadata.
2. Apply migrations using the database owner/migration credentials, supplied in the
   shell environment as `SHIFT_DATABASE_URL`. Use the direct PostgreSQL connection
   with the `postgresql+psycopg://` scheme. Never use owner credentials for runtime.

   ```sh
   uv run alembic upgrade head
   uv run alembic check
   ```

3. The migration creates the `shift_app` NOLOGIN group. With privileged database
   administration, create a separate LOGIN with a strong password, NOSUPERUSER,
   NOBYPASSRLS, NOCREATEDB, NOCREATEROLE, and membership only in `shift_app`.
   Do not grant it table ownership, migration-owner membership, or other elevated
   roles. Keep public-schema CREATE privilege restricted to trusted migration owners.
   PostgreSQL's default CONNECT privilege must be available for this login.
4. Provision each user's organization membership with migration credentials:

   ```sh
   uv run python scripts/provision_membership.py \
     --subject USER_UUID --organization-id YOUR_ORG_ID \
     --organization-name 'Your fictional organization' \
     --name 'Your fictional manager' --role manager
   ```

   Set `SHIFT_ENVIRONMENT=hosted`, `SHIFT_DEMO_MODE=false`, and
   `SHIFT_SUPABASE_URL=https://PROJECT.supabase.co` for this command. Provisioning
   refuses to overwrite an existing membership. Each user belongs to one organization.
   `--worker-id` explicitly binds an existing worker profile from the same organization.
   Creating/editing worker profiles and projects remains a subsequent milestone;
   newly provisioned organizations start with empty screens. No fixtures auto-seed.

## API and web configuration

For the API, set:

- `SHIFT_ENVIRONMENT=hosted`
- `SHIFT_DEMO_MODE=false`
- `SHIFT_DATABASE_URL`: restricted runtime login URL
- `SHIFT_SUPABASE_URL`: your project's HTTPS origin
- `SHIFT_JWT_AUDIENCE=authenticated` (default)

Start without the demo launcher:

```sh
uv run uvicorn shift_api.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

Put the web configuration in `apps/web/.env.local` for local hosted-mode testing:

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLIC_PUBLISHABLE_KEY
API_INTERNAL_URL=http://127.0.0.1:8000
```

```sh
npm run dev:hosted --workspace=@shift/web
```

For a production build, provide the public Auth settings at build time, run
`npm run build`, and start with `npm run start --workspace=@shift/web` behind your
hosting proxy. Configure `API_INTERNAL_URL` when building the proxy rewrites.
Keep demo mode disabled in both services. Hosting and TLS configuration are outside
this milestone; loopback commands above exercise hosted authentication locally.

The browser stores the Supabase session and sends access tokens to the same-origin
API proxy. FastAPI validates signatures against the configured issuer's JWKS;
HS256, untrusted issuers, missing claims, and expired tokens are rejected. Runtime
roles come from memberships, not JWT metadata. Tokens/passwords must never be logged.
Supabase browser roles have no direct access to application tables or helper functions.

## Database boundaries

The runtime role is trusted server infrastructure. Each transaction installs a
transaction-local verified subject; it is reinstalled after commit and cleared on
connection return. RLS restricts organizations, manager projects and worker records.
Private commitments can be read in full only by their owner. Definer functions,
owned by the migration role with a fixed search path, expose only opaque busy
intervals and external scheduling capacity. Their implementation must remain
inaccessible to untrusted schema writers. Do not expose database credentials to users.

Confirmed assignments use a `[start,end)` exclusion constraint per worker across
projects. Cancelled/disrupted history does not reserve time. SQLite has no equivalent
concurrent-write guarantee. This constraint is one safeguard; future acceptance must
also revalidate skills, availability, task coverage, budget and project constraints
inside its reservation transaction.

## Verification gate

Use the dedicated disposable database name `shift_identity_test` for integration tests:

```sh
SHIFT_TEST_POSTGRES_URL='postgresql+psycopg://TEST_OWNER:TEST_PASSWORD@HOST:5432/shift_identity_test' \
  uv run pytest -q
```

This suite migrates/seeds fictional fixtures and creates a restricted test login.
Never point it at a non-test database. In addition, manually verify the configured
Supabase project's account sign-in, refresh, logout and membership mapping. Local
signed-token tests and PostgreSQL tests do not establish that a cloud project works.

References: [Supabase password sign-in](https://supabase.com/docs/reference/javascript/auth-signinwithpassword),
[Auth events](https://supabase.com/docs/reference/javascript/auth-onauthstatechange),
[PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html).
