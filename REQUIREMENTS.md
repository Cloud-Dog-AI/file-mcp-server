
### Database Abstraction (cloud_dog_db adoption)

- R-DB-01: All database access MUST use `cloud_dog_db` engine/session/CRUD abstractions
- R-DB-02: Engine creation MUST use `cloud_dog_db` engine factories
- R-DB-03: Session management MUST use `cloud_dog_db.session.SyncSessionManager`/`AsyncSessionManager`
- R-DB-04: Schema migrations MUST use `cloud_dog_db` migration runner
- R-DB-05: Direct sqlite3/create_engine()/sessionmaker()/raw Session() FORBIDDEN in app code
- R-DB-06: DB health MUST use `cloud_dog_db.health.probe_database()`
- R-DB-07: DB connection config MUST come from cloud_dog_config/Vault-backed env hierarchy
- R-DB-08: Schema versioning MUST be tested across SQLite, MySQL, and PostgreSQL
- R-DB-09: Schema upgrade/downgrade MUST be validated with at least two migrations per dialect
- R-DB-10: CRUD outcomes MUST be consistent across SQLite, MySQL, and PostgreSQL

### W25A-B Compliance Closure Status (2026-03-09)

- RC-01 (hardcoded URLs/hosts): DELIVERED
  - Google Drive and HTTP fallback literals migrated into typed config schema/defaults chain.
- RC-03 (external import centralisation): DELIVERED
  - Direct `requests`/`yaml` imports consolidated behind `src/file_tools/adapters/`.
- RC-09 (stubs/placeholders in delivered paths): DELIVERED
  - `NotImplementedError`/`TODO:` markers removed from delivered runtime paths.
- RC-10 (UK English user-facing strings): DELIVERED
  - User-facing Google admin and auth strings aligned to UK English.
