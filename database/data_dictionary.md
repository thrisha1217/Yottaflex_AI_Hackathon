# Data Dictionary — Academic Integrity and Similarity Review Management System

## Database: `academic_integrity`  |  Target: MySQL 8.0.16+

---

## Table Index

| # | Table | Type | Records (target) |
|---|-------|------|-----------------|
| 1 | Learner | Core | ~500 |
| 2 | Assessment | Core | ~50 |
| 3 | IntegrityRule | Core | ~10 (configurable) |
| 4 | Reviewer | Core | ~30 |
| 5 | Submission | Core | 10,000 |
| 6 | SimilarityReport | Core | 10,000 (1,000 flagged) |
| 7 | IntegrityCase | Core | 300 |
| 8 | EvidenceItem | Core | ~900 |
| 9 | CaseReviewer | Bridge | ~350 |
| 10 | Decision | Core | ~300 |
| 11 | DecisionEvidence | Bridge | ~1,200 |
| 12 | Appeal | Core | ~90 |
| 13 | AppealReview | Core | ~80 |
| 14 | CaseEvent | Supporting | ~3,000+ |
| 15 | AuditLog | Supporting | Auto-generated |

---

## 1. Learner

Stores registered student information.

| Column | SQL Type | Required | Unique | Allowed Values | Notes |
|--------|----------|----------|--------|----------------|-------|
| learner_id | VARCHAR(20) | Yes | Yes (PK) | e.g. `LRN-001` | Primary key |
| full_name | VARCHAR(100) | Yes | No | Any string | Student full name |
| email | VARCHAR(150) | Yes | Yes | Valid email format | Institutional email |
| program | VARCHAR(100) | No | No | Any string | Degree programme name |
| year_of_study | TINYINT | No | No | 1–10 | Current year of study |
| status | ENUM | No | No | `ACTIVE`, `INACTIVE` | Default: `ACTIVE` |
| created_at | DATETIME | No | No | Valid datetime | Auto-set on insert |

**Foreign keys referenced by:** Submission, Appeal

---

## 2. Assessment

Stores assignment and examination definitions.

| Column | SQL Type | Required | Unique | Allowed Values | Notes |
|--------|----------|----------|--------|----------------|-------|
| assessment_id | VARCHAR(20) | Yes | Yes (PK) | e.g. `ASM-001` | Primary key |
| title | VARCHAR(200) | Yes | No | Any string | Assessment title |
| course_code | VARCHAR(30) | Yes | No | e.g. `CS101` | Module/course code |
| assessment_type | ENUM | Yes | No | `ASSIGNMENT`, `EXAM`, `PROJECT`, `QUIZ` | Type of work |
| due_at | DATETIME | Yes | No | Valid datetime | Submission deadline |
| status | ENUM | No | No | `DRAFT`, `ACTIVE`, `CLOSED` | Default: `DRAFT` |
| created_at | DATETIME | No | No | Valid datetime | Auto-set on insert |

**Foreign keys referenced by:** Submission

---

## 3. IntegrityRule

Configurable similarity thresholds. Multiple rules create a range-based escalation ladder.

| Column | SQL Type | Required | Unique | Allowed Values | Notes |
|--------|----------|----------|--------|----------------|-------|
| rule_id | VARCHAR(20) | Yes | Yes (PK) | e.g. `RULE-001` | Primary key |
| rule_name | VARCHAR(100) | Yes | No | Any string | Human-readable name |
| min_similarity | DECIMAL(5,2) | Yes | No | 0–100 | Lower bound of range |
| max_similarity | DECIMAL(5,2) | Yes | No | 0–100 | Upper bound of range |
| action_type | ENUM | Yes | No | `NO_REVIEW`, `MONITOR`, `REVIEW`, `HIGH_PRIORITY_REVIEW` | Escalation action |
| priority | INT | Yes | No | Any integer | Rule evaluation order |
| effective_from | DATE | Yes | No | Valid date | Rule start date |
| effective_to | DATE | No | No | Valid date or NULL | NULL = still active |
| is_active | BOOLEAN | No | No | TRUE / FALSE | Default: TRUE |

**Constraints:** `min_similarity <= max_similarity`, `effective_to >= effective_from` if set

**Example ruleset:**

| rule_id | Range | action_type |
|---------|-------|-------------|
| RULE-001 | 0–40% | NO_REVIEW |
| RULE-002 | 41–70% | MONITOR |
| RULE-003 | 71–85% | REVIEW |
| RULE-004 | 86–100% | HIGH_PRIORITY_REVIEW |

**Foreign keys referenced by:** SimilarityReport

---

## 4. Reviewer

Academic staff authorised to investigate cases and conduct appeal reviews.

| Column | SQL Type | Required | Unique | Allowed Values | Notes |
|--------|----------|----------|--------|----------------|-------|
| reviewer_id | VARCHAR(20) | Yes | Yes (PK) | e.g. `REV-001` | Primary key |
| full_name | VARCHAR(100) | Yes | No | Any string | Reviewer full name |
| email | VARCHAR(150) | Yes | Yes | Valid email format | Institutional email |
| reviewer_role | ENUM | Yes | No | `INSTRUCTOR`, `ACADEMIC_ADMIN`, `REVIEWER` | Role determines case access |
| status | ENUM | No | No | `ACTIVE`, `INACTIVE` | Default: `ACTIVE` |
| created_at | DATETIME | No | No | Valid datetime | Auto-set on insert |

**Foreign keys referenced by:** CaseReviewer, Decision, AppealReview

---

## 5. Submission

Every student submission for an assessment. Target: **10,000 records**.

| Column | SQL Type | Required | Unique | Allowed Values | Notes |
|--------|----------|----------|--------|----------------|-------|
| submission_id | VARCHAR(30) | Yes | Yes (PK) | e.g. `SUB-2026-000001` | Primary key |
| learner_id | VARCHAR(20) | Yes | No | FK → Learner | |
| assessment_id | VARCHAR(20) | Yes | No | FK → Assessment | |
| attempt_no | SMALLINT | Yes | No | ≥ 1 | Default: 1 |
| submitted_at | DATETIME | Yes | No | Valid datetime | Actual submission time |
| content_reference | VARCHAR(255) | No | No | Path or URL | Reference to submitted file |
| content_hash | CHAR(64) | No | No | SHA-256 hex | Hash of submitted content |
| status | ENUM | No | No | `SUBMITTED`, `LATE`, `WITHDRAWN` | Default: `SUBMITTED` |

**Unique constraint:** (learner_id, assessment_id, attempt_no)

---

## 6. SimilarityReport

Synthetic similarity analysis result. Target: **10,000 records**, of which **~1,000 have review_required = TRUE**.

| Column | SQL Type | Required | Unique | Allowed Values | Notes |
|--------|----------|----------|--------|----------------|-------|
| report_id | VARCHAR(80) | Yes | Yes (PK) | e.g. `SIM-SUB-2026-000001-01` | Primary key |
| submission_id | VARCHAR(30) | Yes | No | FK → Submission | |
| rule_id | VARCHAR(20) | No | No | FK → IntegrityRule | Rule used for threshold check |
| report_no | SMALLINT | Yes | No | ≥ 1 | Report sequence for this submission |
| similarity_score | DECIMAL(5,2) | Yes | No | 0–100 | Percentage similarity |
| matched_source_count | INT | No | No | ≥ 0 | Number of matched sources |
| review_required | BOOLEAN | Yes | No | TRUE / FALSE | TRUE = exceeds threshold → flag |
| report_status | ENUM | Yes | No | `GENERATED`, `REVIEW_REQUIRED`, `MONITOR`, `NO_REVIEW` | Derived from rule |
| generated_at | DATETIME | Yes | No | Valid datetime | When report was generated |

**Unique constraint:** (submission_id, report_no)

> **Key business rule:** `review_required = TRUE` means the submission needs human investigation.  
> It does **not** mean the student cheated.

---

## 7. IntegrityCase

Central investigation record. Created when a SimilarityReport has `review_required = TRUE`. Target: **300 records**.

| Column | SQL Type | Required | Unique | Allowed Values | Notes |
|--------|----------|----------|--------|----------------|-------|
| case_id | VARCHAR(30) | Yes | Yes (PK) | e.g. `INT-2026-000001` | Primary key |
| report_id | VARCHAR(80) | Yes | Yes | FK → SimilarityReport | One case per report |
| case_status | ENUM | No | No | `OPEN`, `UNDER_REVIEW`, `AWAITING_INFORMATION`, `DECIDED`, `APPEAL_PENDING`, `CLOSED` | Default: `OPEN` |
| priority | ENUM | No | No | `LOW`, `MEDIUM`, `HIGH` | Default: `MEDIUM` |
| opened_at | DATETIME | Yes | No | Valid datetime | When the case was opened |
| closed_at | DATETIME | No | No | Valid datetime or NULL | NULL = case still open |

**Constraint:** `closed_at >= opened_at`

> **Key business rule:** `case_status = OPEN` does **not** imply guilt. Only a human reviewer's Decision record can record a VIOLATION outcome.

---

## 8. EvidenceItem

Evidence collected during case investigation. Target: **~900 records** (~3 per case).

| Column | SQL Type | Required | Unique | Allowed Values | Notes |
|--------|----------|----------|--------|----------------|-------|
| evidence_id | VARCHAR(80) | Yes | Yes (PK) | e.g. `EVD-000001` | Primary key |
| case_id | VARCHAR(30) | Yes | No | FK → IntegrityCase | |
| evidence_type | ENUM | Yes | No | `SIMILARITY_MATCH`, `QUOTATION`, `TEMPLATE`, `STUDENT_EXPLANATION`, `DOCUMENT`, `OTHER` | Category of evidence |
| description | TEXT | Yes | No | Any text | What the evidence shows |
| evidence_reference | VARCHAR(255) | No | No | Path or URL | Link to evidence file |
| added_by_role | ENUM | Yes | No | `LEARNER`, `INSTRUCTOR`, `REVIEWER`, `ACADEMIC_ADMIN`, `SYSTEM` | Who added the evidence |
| added_by_ref | VARCHAR(30) | No | No | learner_id or reviewer_id | ID of the person who added it |
| added_at | DATETIME | Yes | No | Valid datetime | When evidence was added |
| is_material | BOOLEAN | No | No | TRUE / FALSE | Default: TRUE; FALSE = exculpatory or post-decision |

> **Key business rule:** Evidence added after a decision is preserved by inserting a new row with `is_material = FALSE`. The original Decision record is never modified.

---

## 9. CaseReviewer  *(bridge table)*

Tracks all reviewer assignments for a case, including reassignments and recusals. Full assignment history is retained.

| Column | SQL Type | Required | Unique | Allowed Values | Notes |
|--------|----------|----------|--------|----------------|-------|
| assignment_id | BIGINT | Yes | Yes (PK) | Auto-increment | Primary key |
| case_id | VARCHAR(30) | Yes | No | FK → IntegrityCase | |
| reviewer_id | VARCHAR(20) | Yes | No | FK → Reviewer | |
| assignment_role | ENUM | Yes | No | `PRIMARY`, `SECONDARY`, `INDEPENDENT_APPEAL` | Role on this case |
| assigned_at | DATETIME | Yes | No | Valid datetime | When assigned |
| unassigned_at | DATETIME | No | No | Valid datetime or NULL | NULL = still assigned |
| conflict_status | ENUM | No | No | `PENDING`, `CLEARED`, `CONFLICT` | Default: `PENDING` |
| conflict_reason | TEXT | No | No | Any text | Required if CONFLICT |

**Constraint:** `unassigned_at >= assigned_at`

> **Key business rule:** A reviewer with `conflict_status = CONFLICT` must be unassigned and replaced. The application layer enforces this; the row is retained as history.

---

## 10. Decision

Investigation outcome. Immutable once inserted. Target: **~300 records**.

| Column | SQL Type | Required | Unique | Allowed Values | Notes |
|--------|----------|----------|--------|----------------|-------|
| decision_id | BIGINT | Yes | Yes (PK) | Auto-increment | Primary key |
| case_id | VARCHAR(30) | Yes | No | FK → IntegrityCase | |
| reviewer_id | VARCHAR(20) | Yes | No | FK → Reviewer | |
| previous_decision_id | BIGINT | No | No | FK → Decision or NULL | Links to superseded decision |
| decision_outcome | ENUM | Yes | No | `NO_VIOLATION`, `VIOLATION`, `INCONCLUSIVE` | The finding |
| rationale | TEXT | Yes | No | Any text | Written justification |
| decided_at | DATETIME | Yes | No | Valid datetime | When decision was recorded |
| is_final | BOOLEAN | No | No | TRUE / FALSE | Default: TRUE |

> **Key business rule:** Decisions are never updated. An appeal outcome creates a **new** Decision row, with `previous_decision_id` pointing to the superseded record.

---

## 11. DecisionEvidence  *(bridge table)*

Records which evidence items were considered in each decision.

| Column | SQL Type | Required | Unique | Allowed Values | Notes |
|--------|----------|----------|--------|----------------|-------|
| decision_id | BIGINT | Yes | Yes (composite PK) | FK → Decision | |
| evidence_id | VARCHAR(80) | Yes | Yes (composite PK) | FK → EvidenceItem | |

---

## 12. Appeal

Student's formal challenge to an investigation decision. Target: **~90 records** (~30% of cases).

| Column | SQL Type | Required | Unique | Allowed Values | Notes |
|--------|----------|----------|--------|----------------|-------|
| appeal_id | VARCHAR(80) | Yes | Yes (PK) | e.g. `APL-000001` | Primary key |
| case_id | VARCHAR(30) | Yes | No | FK → IntegrityCase | |
| learner_id | VARCHAR(20) | Yes | No | FK → Learner | |
| appeal_no | SMALLINT | Yes | No | ≥ 1 | Appeal sequence for this case |
| reason | TEXT | Yes | No | Any text | Student's grounds for appeal |
| submitted_at | DATETIME | Yes | No | Valid datetime | When filed |
| appeal_status | ENUM | No | No | `SUBMITTED`, `UNDER_REVIEW`, `UPHELD`, `OVERTURNED`, `REMANDED` | Default: `SUBMITTED` |
| resolved_at | DATETIME | No | No | Valid datetime or NULL | NULL = unresolved |

**Unique constraint:** (case_id, appeal_no)

> **Key business rule:** `appeal_status` cannot be set to `UPHELD` or `OVERTURNED` unless a corresponding AppealReview row exists with `independence_verified = TRUE`. Enforced at the application layer.

---

## 13. AppealReview

Independent reviewer's evaluation of an appeal. Target: **~80 records**.

| Column | SQL Type | Required | Unique | Allowed Values | Notes |
|--------|----------|----------|--------|----------------|-------|
| review_id | BIGINT | Yes | Yes (PK) | Auto-increment | Primary key |
| appeal_id | VARCHAR(80) | Yes | No | FK → Appeal | |
| reviewer_id | VARCHAR(20) | Yes | No | FK → Reviewer | Must differ from original case reviewer |
| outcome | ENUM | Yes | No | `UPHELD`, `OVERTURNED`, `REMANDED` | Appeal finding |
| rationale | TEXT | Yes | No | Any text | Written evaluation |
| independence_verified | BOOLEAN | Yes | No | TRUE / FALSE | Default: FALSE; must be TRUE to close appeal |
| reviewed_at | DATETIME | Yes | No | Valid datetime | When the review was completed |

---

## 14. CaseEvent  *(INSERT-only timeline)*

Immutable audit trail of everything that happens to an IntegrityCase. Target: **~3,000+ records**.

| Column | SQL Type | Required | Allowed Values | Notes |
|--------|----------|----------|----------------|-------|
| event_id | BIGINT | Yes (PK) | Auto-increment | Primary key |
| case_id | VARCHAR(30) | Yes | FK → IntegrityCase | |
| event_type | VARCHAR(50) | Yes | e.g. `CASE_CREATED`, `REVIEWER_ASSIGNED`, `EVIDENCE_ADDED`, `DECISION_RECORDED`, `APPEAL_SUBMITTED`, `STATUS_CHANGED` | Event category |
| actor_role | VARCHAR(30) | Yes | e.g. `SYSTEM`, `REVIEWER`, `LEARNER` | Who performed the action |
| actor_ref | VARCHAR(30) | No | reviewer_id or learner_id | Specific actor reference |
| previous_status | VARCHAR(40) | No | Any case_status value | Status before the event |
| new_status | VARCHAR(40) | No | Any case_status value | Status after the event |
| event_details | JSON | No | Any JSON object | Structured detail of the event |
| occurred_at | DATETIME | Yes | Valid datetime | When the event occurred |

> **Design principle:** Rows are INSERT-only. They are never updated or deleted.

---

## 15. AuditLog

Application-wide change log for all sensitive tables.

| Column | SQL Type | Required | Allowed Values | Notes |
|--------|----------|----------|----------------|-------|
| audit_id | BIGINT | Yes (PK) | Auto-increment | Primary key |
| entity_type | VARCHAR(50) | Yes | Table name | e.g. `IntegrityCase`, `Decision` |
| entity_id | VARCHAR(80) | Yes | Primary key value | ID of the affected row |
| action | VARCHAR(50) | Yes | `INSERT`, `UPDATE`, `DELETE` | Type of change |
| actor_role | VARCHAR(30) | Yes | Role string | Who made the change |
| actor_ref | VARCHAR(30) | No | ID string | Specific actor reference |
| old_values | JSON | No | JSON object | Full row snapshot before change |
| new_values | JSON | No | JSON object | Full row snapshot after change |
| created_at | DATETIME | Yes | Valid datetime | When the change occurred |

---

## Entity Relationship Diagram (text)

```
LEARNER ──────────┐                      ASSESSMENT
                  │ creates                  │ receives
                  └──────────► SUBMISSION ◄──┘
                                    │
                                    │ generates
                                    ▼
INTEGRITY_RULE ──── evaluates ──► SIMILARITY_REPORT
                                    │
                                    │ triggers (1:1)
                                    ▼
                               INTEGRITY_CASE ◄──── submits ──── LEARNER
                                    │
          ┌─────────────────────────┼──────────────────────────┐
          │                         │                          │
          ▼                         ▼                          ▼
    CASE_REVIEWER            EVIDENCE_ITEM                  DECISION ──► DECISION_EVIDENCE
    (bridge: Reviewer)            │                             │
          │                        └──────────── links ─────────┘
          │                         
    CASE_EVENT (timeline)    
                                   
                              APPEAL ◄──── submits ──── LEARNER
                                    │
                                    ▼
                              APPEAL_REVIEW
                              (independent Reviewer)

All mutations → AUDIT_LOG
```

---

## Business Rules Summary

| # | Rule | Where Enforced |
|---|------|---------------|
| 1 | Similarity flag ≠ guilty | `case_status` starts as `OPEN`; only a Decision row records VIOLATION | App layer + schema default |
| 2 | Reviewer conflict blocks assignment | `conflict_status = CONFLICT` → must reassign; history retained in CaseReviewer | App layer |
| 3 | Evidence after decision preserved | New EvidenceItem row with `is_material = FALSE`; Decision never updated | App layer + append-only design |
| 4 | Appeal closure requires independent review | AppealReview row with `independence_verified = TRUE` must exist before closing | App layer |
| 5 | Full case history | CaseEvent table (INSERT-only) | Schema design |
| 6 | Full change history | AuditLog table | App layer / DB triggers |
| 7 | Reproducible synthetic data | Fixed seed `20261022` in data generator | data_generator module |

---

## ID Format Reference

| Table | Format | Example |
|-------|--------|---------|
| Learner | `LRN-{NNN}` | `LRN-001` |
| Assessment | `ASM-{NNN}` | `ASM-001` |
| IntegrityRule | `RULE-{NNN}` | `RULE-001` |
| Reviewer | `REV-{NNN}` | `REV-001` |
| Submission | `SUB-{YYYY}-{NNNNNN}` | `SUB-2026-000001` |
| SimilarityReport | `SIM-{submission_id}-{NN}` | `SIM-SUB-2026-000001-01` |
| IntegrityCase | `INT-{YYYY}-{NNNNNN}` | `INT-2026-000001` |
| EvidenceItem | `EVD-{NNNNNN}` | `EVD-000001` |
| Appeal | `APL-{NNNNNN}` | `APL-000001` |
