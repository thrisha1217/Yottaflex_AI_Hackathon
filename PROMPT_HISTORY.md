# Prompt History — AI Tool Usage Disclosure

## Tool Used
**Kiro (AI-powered development environment)** — used throughout the project for code generation, architecture design, and implementation.

---

## How AI Was Used

### What AI accelerated
- Boilerplate generation (FastAPI routers, SQLAlchemy models, Pydantic schemas) — AI generated initial structure; I reviewed and validated field types, relationships, and business rules
- React component scaffolding — AI generated page/chart components; I verified the data flow and hook patterns
- SQL query construction for analytics — AI translated the design doc SQL into SQLAlchemy ORM expressions; I reviewed join chains for correctness
- Property-based test outlines — AI generated Hypothesis test structure; I verified the properties match the spec invariants

### Where I relied heavily on AI
- Initial FastAPI project structure setup
- SQLAlchemy ORM model definitions (14 models with relationships)
- React hooks pattern (useState/useEffect with JSON.stringify deps)
- Recharts chart component wiring

### What I personally reviewed, changed, or validated
- **All business rules**: The core invariant (`review_required = TRUE` ≠ guilt) was my design decision enforced throughout
- **Entity relationships**: Reviewed all FK chains, cardinality, and bridge table designs in `data_dictionary.md`
- **Edge case injection**: Designed the 4 edge case categories and verified they match the brief
- **Ground truth separation**: Ensured `ground_truth.csv` is never loaded into the application DB
- **ID format compliance**: Caught and corrected the `EVD-<case-id>-001` format gap after gap analysis
- **SQLite migration**: Identified the `DATE_FORMAT` MySQL-specific function and fixed it for SQLite compatibility
- **Reproducibility verification**: Designed and ran `verify_reproducibility.py` — confirmed all 14 CSVs byte-identical
- **API validation**: Verified all 34 endpoints return correct data via live API calls
- **Full gap analysis**: Reviewed the brief point-by-point and identified 6 missing items after initial implementation

---

## Prompts Summary

The following prompts were submitted to Kiro during development:

1. Requirements analysis — describing the full brief and asking for a spec breakdown into milestones
2. Data generator implementation — generating each of the 14 table generators with FK dependency order
3. SQLAlchemy ORM models — one model per table with relationships
4. Pydantic schemas — request/response schemas for all endpoints
5. FastAPI service layer — business logic for case management, evidence, decisions, appeals
6. Audit service — log_insert, log_update, insert_case_event functions
7. Analytics service — 5 aggregate queries including cross-entity JOIN chains
8. Audit compliance service — conflict reassignments, post-decision evidence, appeals without review
9. React frontend — all 6 pages, 5 charts, shared components, custom hooks
10. SQLite migration — DATABASE_URL switch, check_same_thread, DATE_FORMAT fix
11. Ground truth generation — designing edge case categories and labelling logic
12. Gap analysis — point-by-point review against the brief requirements
13. EVD ID format fix — changing from global counter to per-case `EVD-<case-id>-001` format
14. GitHub push — .gitignore, .env.example, final commit

---

## What Was Not AI-Generated
- Business rule design decisions (flag ≠ guilt invariant)
- Edge case category design (4 categories matching the brief exactly)
- Gap analysis identification (manually reviewed all 10 brief steps)
- Validation of data integrity (personally ran and interpreted all verification outputs)
- This disclosure document
