# B03 - Lakehouse governance

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (Trino file-based access control) / DEMO (Analytics Engine built-in access control) | 2 h | SEC, DAT, LAK | B01, B02 |

[DEMO] The Dell Data Analytics Engine (Starburst) has built-in role-based access control with a UI: roles, privileges, row filters, column masks and a query log. Build the same policies there.
[SIM] Open-source Trino uses a JSON rules file. The lab ships one in `labs/env/trino/governance/`.

Personas:

| User | Persona | Should see |
|---|---|---|
| `admin` / `trino` | platform admin | everything |
| `fin` | finance analyst | all customers, unmasked. Read-only. |
| `ana` | EMEA marketing analyst | EMEA customers only, with name/email masked. Read-only. |

## Steps

### Step 1 - Read the policy
```bash
cd labs/env
cat trino/governance/rules.json
```
Find the rule for `ana` on `postgresql.crm.customers`:
```json
{"user": "ana", "catalog": "postgresql", "schema": "crm", "table": "customers", "privileges": ["SELECT"],
 "filter": "region = 'EMEA'",
 "columns": [{"name": "email", "mask": "'***masked***'"}, {"name": "name", "mask": "substr(name, 1, 1) || '***'"}]}
```

### Step 2 - Turn governance on
```bash
docker compose -f docker-compose.yml -f docker-compose.governance.yml --profile core up -d --force-recreate trino
until docker compose ps trino | grep -q healthy; do sleep 5; done
```
The lab has no authentication, so `--user` selects the identity. In production, identities come from OIDC/LDAP/Kerberos and groups come from the directory. See Step 7.

### Step 3 - Same query, three answers
```bash
for u in admin fin ana; do
  echo "== $u"
  bin/trino --user $u --execute "SELECT region, count(*) FROM postgresql.crm.customers GROUP BY 1 ORDER BY 1"
  bin/trino --user $u --execute "SELECT name, email FROM postgresql.crm.customers ORDER BY customer_id LIMIT 2"
done
```
Expected:
- `admin` and `fin`: four regions with 250 rows each, real names and emails.
- `ana`: only `"EMEA","250"`, names shown as `"C***"`, email shown as `"***masked***"`.

### Step 4 - Denied actions
```bash
bin/trino --user ana --execute "SELECT count(*) FROM tpch.tiny.orders"               # Access Denied: Cannot access catalog tpch
bin/trino --user ana --execute "DELETE FROM iceberg.curated.orders WHERE order_id=1"  # Access Denied: Cannot delete from table
bin/trino --user ana --execute "SELECT count(*) FROM iceberg.curated.orders"          # allowed (curated is readable)
```

### Step 5 - Masking survives joins and views
```bash
bin/trino --user ana --execute "
SELECT c.name, c.email, round(sum(o.amount)) FROM iceberg.curated.orders o
JOIN postgresql.crm.customers c USING (customer_id) GROUP BY 1, 2 LIMIT 3"
```
Names and emails are still masked. Only EMEA customers are included.

### Step 6 - Audit trail
```bash
bin/trino --execute "
SELECT \"user\", state, created, substr(query, 1, 60) AS query
FROM system.runtime.queries WHERE \"user\" IN ('ana', 'fin') ORDER BY created DESC LIMIT 10"
```
Expected: a row for every query, including the `FAILED` (denied) ones.
`system.runtime.queries` only holds recent queries kept in memory. For a durable audit trail:
- [SIM] configure a Trino event listener (HTTP or Kafka) that sends query-completed events to your log store.
- [DEMO] export the Starburst query log for one query, including the user, the SQL, the tables and columns accessed, and the policy applied.

### Step 7 - Plan the production mapping
Write down how each of these will work:
1. Identity: OIDC (e.g. Entra ID / Okta) for UI and JDBC users. Service accounts for pipelines.
2. Groups: from LDAP/AD (a group provider). Rules reference groups (`"group": "emea-marketing"`), not users.
3. Classification-driven masking: tag columns as `pii` in the catalog (B02/A08) and write one mask rule per tag, not per column. Starburst supports attribute/tag-based policies.
4. Policy as code: keep the rules in git and deploy them through review (the same approach as A05).

## Verify
- [ ] The same SQL returns different rows/values per persona.
- [ ] Denied actions fail with Access Denied.
- [ ] An audit record exists for allowed and denied queries.

## Record for the standards
`LAK-09` query-layer access control model. `SEC-02` authorisation model (RBAC/ABAC). `SEC-01` identity source and SSO. `SEC-10` query audit logging / SIEM. `DAT-01` handling rules (PII masking).

## Cleanup
Return to the open configuration (later labs assume it):
```bash
docker compose --profile core up -d --force-recreate trino
```
