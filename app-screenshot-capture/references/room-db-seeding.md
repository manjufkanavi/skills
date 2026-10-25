# Seeding a Room-compatible database for demo screenshots

When an app loads its first screen with **empty lists** (e.g. a Lessons list, search results), the app built its own fresh database instead of loading shipped content. To capture screens that show real rows, build a Room-compatible `content.db` on the host and place it where the app reads from.

## Why a hand-built `.db` rarely works straight away

Room validates the database on open. It reads `room_master_table`, recomputes a schema hash from every entity's DDL, and compares it to the stored `identity_hash`. If they differ → `IllegalStateException: Schema validation failed` and the app crashes on launch. So every byte of schema you reproduce must match Room's exactly.

## Procedure

1. **Read the authoritative schema.** Find it at `core/database/schemas/<DatabaseClass>/<version>.json` (or the module's generated schema). From each entity you need its `createSql` string and, at the database root level, the `identityHash`.

2. **Reproduce each entity's DDL verbatim.** Copy the column names, order, and types from `createSql` — Room's hash is computed over this exact string. A single column name or type mismatch changes the hash and fails validation.

3. **Create `room_master_table` with the stored hash.** Room's setup query is:
   ```sql
   CREATE TABLE room_master_table (id INTEGER PRIMARY KEY, identity_hash TEXT);
   INSERT INTO room_master_table VALUES(42, '<identityHash>');
   ```
   `<identityHash>` is the `identityHash` from the schema JSON. This row is what Room compares against — without it validation fails even if every entity DDL matches.

4. **Insert seed rows** matching each entity's columns, then `VACUUM`/close the connection.

5. **Place the DB where the app reads it.**
   - Shipped asset (`createFromAsset`): put `content.db` in `app/src/main/assets/`, rebuild, reinstall.
   - Runtime DB at `<package>/files/<dbfile>`: push via `adb`. Note adb runs as uid 2000 and **cannot write `/data/data/<pkg>/files`** — that path needs root, so prefer the asset route for a clean demo.

## Pitfalls
- **Empty list = fresh DB, not empty data.** Rebuild with seeded content before capturing; otherwise the screenshots are technically valid but useless.
- **Column order matters.** `INSERT` binds by position, so insert in the exact column order of your DDL.
- **Prefer asset + rebuild over adb push.** It avoids the root requirement and keeps the schema in sync with what Room expects.
