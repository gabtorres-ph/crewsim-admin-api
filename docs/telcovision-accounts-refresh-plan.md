# Plan: Refresh accounts from Telcovision

> [!NOTE]
> This is the original implementation plan. Its eSIM delinking steps and six-count refresh
> response were superseded by migration `c9e6f4a2b718` and the subsequent refresh changes.
> Refresh now leaves eSIM `account_id` and `use_account_for_charging` values intact when deleting
> accounts and returns five account counts. See the [current operating instructions](../README.md#telcovision-account-refresh).

## Context

Telcovision is the source of truth for account data. The application's `accounts.id` is the
unique `id` supplied for each element of a reseller's `account` array; eSIMs reference that
same account ID. Add an operator-triggered refresh that requests every account visible to the
configured Telcovision token, validates the complete response, and makes the `accounts` table
match that snapshot by inserting, updating, and deleting rows.
Keep the provider protocol in `app/integrations/telcovision/` so later documented operations can
reuse the transport and error handling.

Provider contract: [listResellerAccount](https://github.com/telco-vision/ocs-api/blob/main/doc/v1/API.md#11-listreselleraccount)
accepts `{"listResellerAccount": {}}` to list accounts across all visible resellers. A successful
response has `status.code == 0` and `listResellerAccount.reseller[]`; each reseller contains
`id` and `account[]`. An account contains `id`, `name`, `balance`, `packageOnly`, and optionally
`steeringListId`. The documentation does not specify pagination. Provider error codes are
documented [here](https://github.com/telco-vision/ocs-api/blob/main/doc/v1/API.md#error-codes).

## Scope

- In scope: Runtime configuration and a reusable Telcovision HTTP client; strict parsing of the
  full account response; transactional replacement of account rows by ID; deletion of rows
  missing from the response; `POST /api/accounts/refresh`; safe error reporting, concurrency
  control, and deployment instructions.
- Non-goals: Reseller table, background schedule, provider write operations, and deletion of
  eSIMs associated with a removed account. Those eSIMs stay in the database without an account.

## Design decisions

- Identity: Match each provider account's `id` directly to the existing `accounts.id` primary
  key. Insert new rows with that explicit ID and update existing rows with the same ID. Rejected
  adding a second provider ID because the user confirmed the IDs already correspond and are
  unique across the account list.
- Provider fields: Store `reseller_id`, `package_only`, and `steering_list_id` with name and
  balance. The new fields are nullable for pre-refresh rows; `package_only` is required in each
  provider account. Rejected dropping provider fields because they identify the parent reseller
  and useful account properties needed by future features.
- Snapshot semantics: Insert unseen IDs, update changed rows, and delete every database account
  ID absent from a successfully parsed full response. Report created/updated/unchanged/deleted
  counts. An empty valid response therefore deletes every account and delinks every linked eSIM.
  Rejected preserving absent rows because the user requires the database to mirror the returned
  account array.
- Linked eSIMs: Before deleting absent accounts, set `esims.accountid` to null for eSIMs
  referencing them and set `use_account_for_charging` to false. The eSIM rows remain available
  for later reassignment. Rejected cascading eSIM deletion because the user requested delinking.
  This requires making the eSIM account foreign key nullable and its read schema nullable.
- Authority: Reject direct account `POST`, `PATCH`, and `DELETE` writes with HTTP 409 after the
  refresh feature is enabled; only the refresh may change accounts. Rejected retaining local
  writes because they would create or modify records outside the source of truth. Existing read
  routes and eSIM routes continue to use `accounts.id`.
- Layering: A provider-agnostic `AccountManager.refresh_accounts(fetch_snapshot)` owns the
  transaction; `AccountResourceAccess` owns SQL. An integration orchestration function supplies
  the Telcovision fetch/parse callback. The account route only wires the trigger to that
  function. Rejected HTTP calls and payload parsing in the route or persistence layer.
- Transaction and overlap: Acquire a PostgreSQL transaction-scoped advisory lock before fetching,
  so only one refresh runs across API replicas. Fetch and validate the entire response before
  changing any account; apply all changes in the same transaction and roll back on any error.
  The lock keeps a database transaction open during the bounded provider call. Rejected a
  process-local lock because it cannot coordinate multiple replicas.
- Provider client: Use one `TelcovisionClient` with a private `_request(operation, payload)`
  method for the JSON envelope, token query parameter, HTTP status, timeout, and provider
  `status.code`. Add `list_reseller_accounts()` as the first operation. Later operations add a
  method and response schema without repeating transport code. Use a synchronous `httpx.Client`
  in the synchronous FastAPI route, with a 10-second connect and 30-second read timeout, no
  automatic retry. Rejected embedding the token in a configured URL or exception text.
- Security: Require a nonempty `ACCOUNTS_REFRESH_KEY` and compare it against the
  `X-Accounts-Refresh-Key` request header with `secrets.compare_digest`. Return 503 when the key, provider URL, or provider token
  is unconfigured, 401 for a missing/invalid key, 409 for concurrent refresh, and 502 for
  Telcovision transport, HTTP, protocol, or provider-status failures. Response bodies and logs
  must never include the token, request URL, raw provider response, or refresh key. Keep the
  existing Cloudflare Access perimeter in production as another control. Treat this as a
  server-to-server trigger; it does not need a new allowed browser CORS header.
- API: `POST /api/accounts/refresh` takes no body and returns HTTP 200 with
  `{"fetched": int, "created": int, "updated": int, "unchanged": int, "deleted": int,
  "delinked_esims": int}` after commit. The route does not launch a background task; a caller
  can tell whether the refresh succeeded.
- Assumptions: The endpoint supplied through `TELCOVISION_API_URL` (host plus `/ocs-custo/main/v1` path) is the correct endpoint for
  `listResellerAccount`; the token grants access to every reseller this application should
  represent; account IDs are unique across those resellers and equal `accounts.id`; the
  documented response has no pagination. An empty, valid reseller list is a legitimate empty
  snapshot and is subject to the same deletion rule.

## Files affected

- New: `app/integrations/telcovision/client.py`: shared HTTP transport and provider errors.
- New: `app/integrations/telcovision/accounts.py`: response models, flattening, and refresh
  orchestration.
- New: `migrations/versions/<new_revision>_refresh_accounts_from_telcovision.py`: nullable
  account metadata columns and a nullable eSIM account foreign key.
- Modified: `app/accounts/models.py`: provider identity and account properties.
- Modified: `app/accounts/schemas.py`: snapshot and refresh result types; additive read fields.
- Modified: `app/esims/models.py`, `app/esims/schemas.py`: permit an eSIM without an account.
- Modified: `app/esims/resource_access.py`: bulk delink eSIMs from removed accounts.
- Modified: `app/accounts/resource_access.py`: lock, lookup, upsert, and delete queries.
- Modified: `app/accounts/manager.py`: refresh transaction and direct-write guard.
- Modified: `app/accounts/routes.py`: authenticated refresh endpoint and error mapping.
- Modified: `app/config.py`, `.env.example`: provider URL, token, and refresh-key settings.
- Modified: `pyproject.toml`, `uv.lock`, `requirements.lock`: make `httpx` a runtime dependency.
- Modified: `README.md`: configuration, deployment, and trigger instructions.

## Steps

### Step 1: Add account metadata and make the eSIM account link optional

- **Goal:** Store provider account properties and permit delinking eSIMs when an account disappears.
- **Files:** `app/accounts/models.py`, `app/esims/models.py`,
  `migrations/versions/<new_revision>_refresh_accounts_from_telcovision.py`
- **Instructions:**
  - Keep `Account.id` as the unique primary key supplied by Telcovision. Add nullable
    `reseller_id: Mapped[int | None]`, `package_only: Mapped[bool | None]`, and
    `steering_list_id: Mapped[int | None]`. These may be null only on rows not yet refreshed.
  - Change `ESIM.accountid` to `Mapped[int | None]` with `nullable=True`; keep its foreign key
    to `accounts.id` and the existing relationship. Do not add cascade deletion.
  - Create an Alembic revision after the repository's current head. Add the three nullable
    account columns and alter `esims.accountid` to nullable. Reverse those changes in
    `downgrade()` only after checking that no eSIM has a null account ID; otherwise raise a
    descriptive migration error instead of dropping eSIMs or silently assigning accounts.
- **Reuse:** `migrations/versions/4f9a6c1e2b7d_add_account_and_profile_columns.py`:
  account and eSIM column conventions; `app/accounts/models.py` and `app/esims/models.py`:
  existing mappings.
- **Depends on:** none.
- **Done when:** The model and migration agree, `accounts.id` remains the provider ID, and eSIMs
  can retain their records with a null `accountid`.

### Step 2: Define domain schemas

- **Goal:** Give the integration a provider-neutral account snapshot to hand to the domain.
- **Files:** `app/accounts/schemas.py`, `app/esims/schemas.py`
- **Instructions:**
  - Add `AccountSnapshot(BaseModel)` with `id: int`, `reseller_id: int`, `name: str`,
    `balance: float`, `package_only: bool`, and `steering_list_id: int | None = None`. Require
    positive IDs, a nonblank name of at most 255 characters, and a finite balance.
  - Add `AccountRefreshResult(BaseModel)` with nonnegative integer fields `fetched`, `created`,
    `updated`, `unchanged`, `deleted`, and `delinked_esims`. Ensure
    `fetched == created + updated + unchanged` at the manager boundary. Add nullable metadata
    fields to `AccountRead`; preserve `id`, `name`, and `balance`.
  - Change `ESIMRead.account_id` to `int | None` so delinked eSIMs serialize as JSON `null`.
    Keep `ESIMCreate.account_id` required and `ESIMUpdate.account_id` non-null when provided;
    callers can reassign an eSIM to another existing account later.
- **Reuse:** `app/accounts/schemas.py`: `AccountName` and `AccountRead` conventions;
  `app/esims/schemas.py`: `ESIMRead` alias for database `accountid`.
- **Depends on:** Step 1.
- **Done when:** The domain schema represents one complete provider account without importing a
  Telcovision payload type, and eSIM reads represent a missing account safely.

### Step 3: Configure and build the reusable provider client

- **Goal:** Isolate Telcovision's shared request envelope and failure handling.
- **Files:** `app/config.py`, `.env.example`, `app/integrations/telcovision/client.py`
- **Instructions:**
  - Add `TELCOVISION_API_URL` (plain `str`, empty default; the real endpoint, e.g.
    `https://ocs-api.telco-vision.com:7443/ocs-custo/main/v1`, must come from the environment and
    never be hardcoded as a default), `TELCOVISION_API_TOKEN` (default empty `SecretStr`), and
    `ACCOUNTS_REFRESH_KEY` (default empty `SecretStr`) to `Settings`; document them without
    values in `.env.example`. A missing provider URL or token makes refresh return 503. Unwrap
    secret values only at the call sites that need them.
  - Implement `TelcovisionClient.__init__(self, api_url: str, token: str,
    http_client: httpx.Client) -> None`, `_request(self, operation: str,
    payload: dict[str, object]) -> dict[str, object]`, and
    `list_reseller_accounts(self) -> dict[str, object]`. `_request` sends POST with
    `params={"token": token}`, `json={operation: payload}`, and JSON content type; checks HTTP
    success, JSON object shape, and numeric `status.code == 0`. The list method sends `{}`.
  - Define `TelcovisionError` carrying a safe error category and optional numeric provider code.
    Catch `httpx.RequestError`, non-success HTTP responses, JSON errors, and nonzero provider
    codes; do not propagate exception strings or provider messages to callers or logs. Give the
    HTTP client a 10-second connect and 30-second read timeout; close it after each refresh.
- **Reuse:** `app/integrations/telcovision/`: existing provider namespace;
  `app/config.py`: environment-backed settings.
- **Depends on:** none.
- **Done when:** Other Telcovision operations can reuse `_request` by adding one typed operation
  method, while the token stays in configuration and never appears in application errors.

### Step 4: Parse and flatten the provider account response

- **Goal:** Reject incomplete snapshots before any database changes.
- **Files:** `app/integrations/telcovision/accounts.py`
- **Instructions:**
  - Define private Pydantic models for the `listResellerAccount.reseller[]` nesting and account
    fields. Require `reseller` and each `account` array to be present and correctly typed;
    require positive reseller/account IDs, name, finite balance, and `packageOnly`. Accept
    optional `steeringListId` and ignore other documented provider fields.
  - Implement `parse_account_snapshot(payload: dict[str, object]) -> list[AccountSnapshot]`.
    Flatten all reseller account arrays, copy reseller ID onto each snapshot, and reject
    duplicate account IDs, malformed or missing fields, and an absent `listResellerAccount`
    object with `TelcovisionError`. An empty valid list returns `[]`.
- **Reuse:** `app/integrations/telcovision/schemas.py`: provider payload modeling convention;
  `app/accounts/schemas.py`: `AccountSnapshot`.
- **Depends on:** Steps 2 and 3.
- **Done when:** The full response is either a valid, unique list of domain snapshots or a safe
  provider error; partial lists are never returned.

### Step 5: Add eSIM delinking persistence

- **Goal:** Keep eSIMs while removing their references to accounts absent from Telcovision.
- **Files:** `app/esims/resource_access.py`
- **Instructions:**
  - Add `delink_accounts(self, account_ids: list[int]) -> int`. In batches of at most 500 IDs,
    issue SQLAlchemy `update(ESIM)` for rows whose `accountid` is in the batch, setting
    `accountid=None` and `use_account_for_charging=False`. Return the sum of affected row counts.
    An empty ID list makes no update. Do not commit here.
- **Reuse:** `app/esims/resource_access.py`: `ESIMResourceAccess` and session ownership.
- **Depends on:** Step 1.
- **Done when:** Delinking changes only eSIMs tied to the supplied absent account IDs and leaves
  their other data intact.

### Step 6: Add account persistence for snapshot replacement

- **Goal:** Keep lock, account upsert, and deletion SQL inside the persistence layer.
- **Files:** `app/accounts/resource_access.py`
- **Instructions:**
  - Add `try_acquire_refresh_lock(self) -> bool`, using PostgreSQL
    `pg_try_advisory_xact_lock` with one fixed, documented key. Return immediately if another
    refresh holds it; the lock lasts until the manager commits or rolls back.
  - Add `upsert_snapshot(self, accounts: list[AccountSnapshot]) -> tuple[int, int, int]`.
    Read current rows by primary key in batches of at most 500, then insert missing rows with
    explicit `id` or update changed `name`, `balance`, `reseller_id`, `package_only`, and
    `steering_list_id`. Compare those five mutable fields; leave unchanged rows untouched.
    Return `(created, updated, unchanged)`; do not commit.
  - Add `list_missing_ids(self, present_ids: set[int]) -> list[int]` by selecting current
    `Account.id` values and returning IDs absent from `present_ids` in ascending order. Add
    `delete_ids(self, account_ids: list[int]) -> int`, deleting those account rows in batches of
    at most 500 after eSIMs have been delinked. Return the affected row count; do not commit.
- **Reuse:** `app/common/resource_access.py`: session ownership and SQLAlchemy query style;
  `app/accounts/resource_access.py`: existing account persistence class.
- **Depends on:** Steps 1 and 2.
- **Done when:** Provider IDs populate `accounts.id`, absent IDs can be removed, and no
  persistence method commits part of the refresh.

### Step 7: Own the refresh transaction in the account manager

- **Goal:** Apply the complete snapshot and eSIM delinking atomically.
- **Files:** `app/accounts/manager.py`
- **Instructions:**
  - Implement `refresh_accounts(self, fetch_snapshot: Callable[[], list[AccountSnapshot]])
    -> AccountRefreshResult`. Inside a single `_write` operation, acquire the refresh lock,
    raise `ResourceConflictError("Account refresh is already running")` when unavailable, call
    `fetch_snapshot`, upsert all returned accounts, calculate absent account IDs, delink their
    eSIMs through `ESIMResourceAccess`, delete those accounts, and return the six counts. Commit
    once through `_write`; a fetch, parsing, or database error rolls the entire operation back.
  - Change `create_account`, `update_account`, and `delete_account` to raise
    `ResourceConflictError("Accounts are managed by Telcovision")` before writing. Preserve
    their routes so existing clients receive an explicit 409; keep read methods unchanged.
- **Reuse:** `app/common/manager.py`: `TransactionalManager._write` and rollback handling;
  `app/accounts/manager.py`: existing CRUD manager; `app/esims/resource_access.py`:
  `ESIMResourceAccess.delink_accounts`.
- **Depends on:** Steps 5 and 6.
- **Done when:** One successful refresh leaves account IDs exactly equal to the provider set,
  linked eSIMs are delinked without deletion, and local account writes return 409.

### Step 8: Wire the integration and refresh endpoint

- **Goal:** Expose one authenticated, synchronous trigger with safe response codes.
- **Files:** `app/integrations/telcovision/accounts.py`, `app/accounts/routes.py`
- **Instructions:**
  - Add `refresh_telcovision_accounts(session: Session, settings: Settings)
    -> AccountRefreshResult` in the integration module. Create a bounded `httpx.Client` context,
    build `TelcovisionClient`, and pass a callback that fetches and parses the full snapshot to
    `AccountManager(session).refresh_accounts`. Provider code stays inside this module.
  - Add `POST /refresh` on the existing `/accounts` router before `/{account_id}` routes.
    Require `X-Accounts-Refresh-Key` using a FastAPI header dependency and constant-time
    comparison. Return the result schema as HTTP 200; map missing configuration to 503 and
    `TelcovisionError` to 502 with generic `{"detail": ...}` content. Let the existing
    `ResourceConflictError` handler return 409.
- **Reuse:** `app/accounts/routes.py`: router and database dependency;
  `app/main.py`: existing conflict handler.
- **Depends on:** Steps 3, 4, and 7.
- **Done when:** An authorized `POST /api/accounts/refresh` reports committed counts, and all
  provider failures leave accounts unchanged with a safe error response.

### Step 9: Package and document deployment

- **Goal:** Make the feature installable and operable in this repository's deployment flow.
- **Files:** `pyproject.toml`, `uv.lock`, `requirements.lock`, `README.md`
- **Instructions:**
  - Move `httpx>=0.27.0` from the dev extra to runtime dependencies. Update both lockfiles with
    UV as documented in `README.md`; do not add another HTTP library.
  - Document `TELCOVISION_API_URL`, `TELCOVISION_API_TOKEN`, and `ACCOUNTS_REFRESH_KEY` as
    deployment secrets. Show a trigger example with a placeholder refresh key and no provider
    token in the command or URL. State that this operation is synchronous, that 502/409/503
    have the meanings above, and that the refresh deletes local account IDs absent from the
    provider response while delinking associated eSIMs. Document that account create/update/
    delete routes now return 409.
- **Reuse:** `README.md`: configuration, Cloudflare Access, and dependency workflow.
- **Depends on:** Steps 1 through 8.
- **Done when:** A deployer can configure and trigger the refresh without exposing the provider
  token and understands the deletion and eSIM delinking behavior.

## Risks and mitigations

- **Provider visibility governs deletion:** A valid but unexpectedly empty or reduced response
  deletes every omitted account. Require the full, unfiltered request, reject malformed results
  and nonzero provider status, and review the configured token's access before rollout. An empty
  successful `reseller` list is still a deletion snapshot under the stated rule.
- **eSIM relationship change:** Deleted accounts may have eSIMs. Delink those rows and turn off
  account charging in the same transaction before account deletion; expose `account_id: null` in
  eSIM reads. The operation must not delete eSIMs.
- **Failed or partial refresh:** Reject missing arrays, duplicate IDs, non-finite balances, and
  nonzero provider status before changing rows. Roll back all inserts, updates, delinks, and
  deletes if any database operation fails.
- **Long provider call:** Bound HTTP timeouts; the advisory lock holds a transaction/connection
  during the request. If normal responses exceed the timeout or account volume is large,
  reconsider a job-based refresh and staged writes before rollout.
- **Provider credentials in logs:** Query-string tokens can appear in HTTP exception strings or
  tracing. Never log the client URL, exception string, raw response, or configuration values.
- **Existing write clients:** Account POST/PATCH/DELETE callers receive 409 after this change.
  Coordinate that API behavior with callers before deployment; eSIM creation still requires an
  existing account ID.

## Manual verification (for the human)

- Confirm the migration adds nullable account metadata and makes `esims.accountid` nullable,
  while retaining the `accounts.id` primary key and eSIM foreign key; apply it in staging.
- Use a stubbed Telcovision response with multiple resellers to check flattening, first import
  with explicit provider IDs, changed-field update, unchanged rerun, optional `steeringListId`,
  deletion of absent account IDs, and all six result counts.
- Check that deleting an omitted account with linked eSIMs keeps the eSIMs, sets `account_id`
  to null and `use_account_for_charging` to false, and allows later reassignment to an existing
  account. Check that the account list contains exactly the returned IDs after commit.
- Check malformed responses, duplicate account IDs, provider `status.code != 0`, HTTP failure,
  timeout, and missing token; verify each leaves accounts and eSIMs unchanged and returns no
  secrets. Check an empty successful list explicitly because it clears the account table.
- Trigger two refreshes together from separate API processes; one should return 409 while the
  other completes. Check 401 for missing/wrong refresh key and 503 for missing configuration.
- Check POST/PATCH/DELETE account routes return 409; existing account and eSIM read routes still
  work, including eSIMs with null account IDs. The human-owned account tests will need updating
  for this API change.
- Review production account IDs and eSIM links before enabling the trigger; compare a real
  Telcovision response to the rows that will be deleted and delinked.

## Open questions

- Is Cloudflare Access plus the dedicated refresh key the intended authorization boundary for
  every environment where this endpoint will be exposed? The plan assumes yes.
