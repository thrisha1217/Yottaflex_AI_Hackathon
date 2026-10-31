-- =============================================================
-- Academic Integrity and Similarity Review Management System
-- Database Schema — MySQL 8.0.16+
-- Seed for synthetic data: 20261022
-- =============================================================

CREATE DATABASE IF NOT EXISTS academic_integrity;
USE academic_integrity;

-- =============================================================
-- 1. LEARNER
--    Stores registered student information.
-- =============================================================
CREATE TABLE Learner (
    learner_id      VARCHAR(20)     NOT NULL,
    full_name       VARCHAR(100)    NOT NULL,
    email           VARCHAR(150)    NOT NULL,
    program         VARCHAR(100),
    year_of_study   TINYINT,
    status          ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE',
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_learner           PRIMARY KEY (learner_id),
    CONSTRAINT uq_learner_email     UNIQUE (email),
    CONSTRAINT chk_year_of_study    CHECK (year_of_study BETWEEN 1 AND 10)
);

-- =============================================================
-- 2. ASSESSMENT
--    Stores assignment and examination definitions.
-- =============================================================
CREATE TABLE Assessment (
    assessment_id   VARCHAR(20)     NOT NULL,
    title           VARCHAR(200)    NOT NULL,
    course_code     VARCHAR(30)     NOT NULL,
    assessment_type ENUM('ASSIGNMENT', 'EXAM', 'PROJECT', 'QUIZ') NOT NULL,
    due_at          DATETIME        NOT NULL,
    status          ENUM('DRAFT', 'ACTIVE', 'CLOSED') DEFAULT 'DRAFT',
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_assessment        PRIMARY KEY (assessment_id)
);

-- =============================================================
-- 3. INTEGRITY RULE
--    Configurable similarity thresholds and escalation actions.
--    Multiple rules allow range-based escalation:
--      0-40%   → NO_REVIEW
--     41-70%   → MONITOR
--     71-85%   → REVIEW
--     86-100%  → HIGH_PRIORITY_REVIEW
-- =============================================================
CREATE TABLE IntegrityRule (
    rule_id         VARCHAR(20)     NOT NULL,
    rule_name       VARCHAR(100)    NOT NULL,
    min_similarity  DECIMAL(5,2)    NOT NULL,
    max_similarity  DECIMAL(5,2)    NOT NULL,
    action_type     ENUM('NO_REVIEW', 'MONITOR', 'REVIEW', 'HIGH_PRIORITY_REVIEW') NOT NULL,
    priority        INT             NOT NULL,
    effective_from  DATE            NOT NULL,
    effective_to    DATE,
    is_active       BOOLEAN         DEFAULT TRUE,
    CONSTRAINT pk_integrity_rule    PRIMARY KEY (rule_id),
    CONSTRAINT chk_similarity_range CHECK (min_similarity >= 0 AND max_similarity <= 100),
    CONSTRAINT chk_similarity_order CHECK (min_similarity <= max_similarity),
    CONSTRAINT chk_effective_dates  CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

-- =============================================================
-- 4. REVIEWER
--    Academic staff authorised to investigate cases and appeals.
-- =============================================================
CREATE TABLE Reviewer (
    reviewer_id     VARCHAR(20)     NOT NULL,
    full_name       VARCHAR(100)    NOT NULL,
    email           VARCHAR(150)    NOT NULL,
    reviewer_role   ENUM('INSTRUCTOR', 'ACADEMIC_ADMIN', 'REVIEWER') NOT NULL,
    status          ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE',
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_reviewer          PRIMARY KEY (reviewer_id),
    CONSTRAINT uq_reviewer_email    UNIQUE (email)
);

-- =============================================================
-- 5. SUBMISSION
--    Every student submission for an assessment.
--    One learner + one assessment + attempt_no must be unique.
-- =============================================================
CREATE TABLE Submission (
    submission_id       VARCHAR(30)     NOT NULL,
    learner_id          VARCHAR(20)     NOT NULL,
    assessment_id       VARCHAR(20)     NOT NULL,
    attempt_no          SMALLINT        NOT NULL DEFAULT 1,
    submitted_at        DATETIME        NOT NULL,
    content_reference   VARCHAR(255),
    content_hash        CHAR(64),
    status              ENUM('SUBMITTED', 'LATE', 'WITHDRAWN') DEFAULT 'SUBMITTED',
    CONSTRAINT pk_submission            PRIMARY KEY (submission_id),
    CONSTRAINT uq_submission_attempt    UNIQUE (learner_id, assessment_id, attempt_no),
    CONSTRAINT fk_submission_learner    FOREIGN KEY (learner_id)
                                            REFERENCES Learner(learner_id),
    CONSTRAINT fk_submission_assessment FOREIGN KEY (assessment_id)
                                            REFERENCES Assessment(assessment_id),
    CONSTRAINT chk_attempt_no          CHECK (attempt_no >= 1)
);

CREATE INDEX idx_submission_learner     ON Submission(learner_id);
CREATE INDEX idx_submission_assessment  ON Submission(assessment_id);

-- =============================================================
-- 6. SIMILARITY REPORT
--    Synthetic similarity analysis result for a submission.
--    review_required is set by comparing score to IntegrityRule.
--    BUSINESS RULE: review_required = TRUE means flag for human
--    review only. It does NOT imply the student is guilty.
-- =============================================================
CREATE TABLE SimilarityReport (
    report_id           VARCHAR(80)     NOT NULL,
    submission_id       VARCHAR(30)     NOT NULL,
    rule_id             VARCHAR(20),
    report_no           SMALLINT        NOT NULL,
    similarity_score    DECIMAL(5,2)    NOT NULL,
    matched_source_count INT            DEFAULT 0,
    review_required     BOOLEAN         NOT NULL,
    report_status       ENUM('GENERATED', 'REVIEW_REQUIRED', 'MONITOR', 'NO_REVIEW') NOT NULL,
    generated_at        DATETIME        NOT NULL,
    CONSTRAINT pk_similarity_report     PRIMARY KEY (report_id),
    CONSTRAINT uq_report_no             UNIQUE (submission_id, report_no),
    CONSTRAINT fk_report_submission     FOREIGN KEY (submission_id)
                                            REFERENCES Submission(submission_id),
    CONSTRAINT fk_report_rule           FOREIGN KEY (rule_id)
                                            REFERENCES IntegrityRule(rule_id),
    CONSTRAINT chk_score_range          CHECK (similarity_score BETWEEN 0 AND 100),
    CONSTRAINT chk_source_count         CHECK (matched_source_count >= 0)
);

CREATE INDEX idx_similarity_score ON SimilarityReport(similarity_score);

-- =============================================================
-- 7. INTEGRITY CASE
--    Central investigation record, created when a similarity
--    report triggers review_required = TRUE.
--    BUSINESS RULE: case_status = 'OPEN' does NOT mean guilty.
--    Only a human decision can result in a VIOLATION outcome.
-- =============================================================
CREATE TABLE IntegrityCase (
    case_id         VARCHAR(30)     NOT NULL,
    report_id       VARCHAR(80)     NOT NULL,
    case_status     ENUM(
                        'OPEN',
                        'UNDER_REVIEW',
                        'AWAITING_INFORMATION',
                        'DECIDED',
                        'APPEAL_PENDING',
                        'CLOSED'
                    )               DEFAULT 'OPEN',
    priority        ENUM('LOW', 'MEDIUM', 'HIGH') DEFAULT 'MEDIUM',
    opened_at       DATETIME        NOT NULL,
    closed_at       DATETIME,
    CONSTRAINT pk_integrity_case    PRIMARY KEY (case_id),
    CONSTRAINT uq_case_report       UNIQUE (report_id),
    CONSTRAINT fk_case_report       FOREIGN KEY (report_id)
                                        REFERENCES SimilarityReport(report_id),
    CONSTRAINT chk_closed_at        CHECK (closed_at IS NULL OR closed_at >= opened_at)
);

CREATE INDEX idx_case_status ON IntegrityCase(case_status);

-- =============================================================
-- 8. EVIDENCE ITEM
--    Evidence collected during a case investigation.
--    Evidence added AFTER a decision is preserved with is_material
--    flag — the original decision record is never modified.
-- =============================================================
CREATE TABLE EvidenceItem (
    evidence_id         VARCHAR(80)     NOT NULL,
    case_id             VARCHAR(30)     NOT NULL,
    evidence_type       ENUM(
                            'SIMILARITY_MATCH',
                            'QUOTATION',
                            'TEMPLATE',
                            'STUDENT_EXPLANATION',
                            'DOCUMENT',
                            'OTHER'
                        )               NOT NULL,
    description         TEXT            NOT NULL,
    evidence_reference  VARCHAR(255),
    added_by_role       ENUM('LEARNER', 'INSTRUCTOR', 'REVIEWER', 'ACADEMIC_ADMIN', 'SYSTEM') NOT NULL,
    added_by_ref        VARCHAR(30),
    added_at            DATETIME        NOT NULL,
    is_material         BOOLEAN         DEFAULT TRUE,
    CONSTRAINT pk_evidence          PRIMARY KEY (evidence_id),
    CONSTRAINT fk_evidence_case     FOREIGN KEY (case_id)
                                        REFERENCES IntegrityCase(case_id)
);

CREATE INDEX idx_evidence_case ON EvidenceItem(case_id);

-- =============================================================
-- 9. CASE REVIEWER  (bridge table)
--    Tracks all reviewer assignments for a case including
--    reassignments and recusals. Full assignment history is kept.
--    BUSINESS RULE: conflict_status = 'CONFLICT' must result in
--    reassignment — the reviewer cannot remain ACTIVE on the case.
-- =============================================================
CREATE TABLE CaseReviewer (
    assignment_id   BIGINT          NOT NULL AUTO_INCREMENT,
    case_id         VARCHAR(30)     NOT NULL,
    reviewer_id     VARCHAR(20)     NOT NULL,
    assignment_role ENUM('PRIMARY', 'SECONDARY', 'INDEPENDENT_APPEAL') NOT NULL,
    assigned_at     DATETIME        NOT NULL,
    unassigned_at   DATETIME,
    conflict_status ENUM('PENDING', 'CLEARED', 'CONFLICT') DEFAULT 'PENDING',
    conflict_reason TEXT,
    CONSTRAINT pk_case_reviewer     PRIMARY KEY (assignment_id),
    CONSTRAINT fk_cr_case           FOREIGN KEY (case_id)
                                        REFERENCES IntegrityCase(case_id),
    CONSTRAINT fk_cr_reviewer       FOREIGN KEY (reviewer_id)
                                        REFERENCES Reviewer(reviewer_id),
    CONSTRAINT chk_unassigned_at    CHECK (unassigned_at IS NULL OR unassigned_at >= assigned_at)
);

-- =============================================================
-- 10. DECISION
--     Records the investigation outcome. Immutable once inserted.
--     If an appeal changes the outcome, a new Decision row is
--     inserted and previous_decision_id links them.
-- =============================================================
CREATE TABLE Decision (
    decision_id             BIGINT          NOT NULL AUTO_INCREMENT,
    case_id                 VARCHAR(30)     NOT NULL,
    reviewer_id             VARCHAR(20)     NOT NULL,
    previous_decision_id    BIGINT,
    decision_outcome        ENUM('NO_VIOLATION', 'VIOLATION', 'INCONCLUSIVE') NOT NULL,
    rationale               TEXT            NOT NULL,
    decided_at              DATETIME        NOT NULL,
    is_final                BOOLEAN         DEFAULT TRUE,
    CONSTRAINT pk_decision              PRIMARY KEY (decision_id),
    CONSTRAINT fk_decision_case         FOREIGN KEY (case_id)
                                            REFERENCES IntegrityCase(case_id),
    CONSTRAINT fk_decision_reviewer     FOREIGN KEY (reviewer_id)
                                            REFERENCES Reviewer(reviewer_id),
    CONSTRAINT fk_previous_decision     FOREIGN KEY (previous_decision_id)
                                            REFERENCES Decision(decision_id)
);

-- =============================================================
-- BRIDGE TABLE: DECISION EVIDENCE
--    Records which evidence items were considered in each decision.
-- =============================================================
CREATE TABLE DecisionEvidence (
    decision_id     BIGINT          NOT NULL,
    evidence_id     VARCHAR(80)     NOT NULL,
    CONSTRAINT pk_decision_evidence     PRIMARY KEY (decision_id, evidence_id),
    CONSTRAINT fk_de_decision           FOREIGN KEY (decision_id)
                                            REFERENCES Decision(decision_id),
    CONSTRAINT fk_de_evidence           FOREIGN KEY (evidence_id)
                                            REFERENCES EvidenceItem(evidence_id)
);

-- =============================================================
-- 11. APPEAL
--     Student's formal challenge to an investigation decision.
--     BUSINESS RULE: appeal cannot be resolved (UPHELD/OVERTURNED)
--     without a completed AppealReview by an independent reviewer.
-- =============================================================
CREATE TABLE Appeal (
    appeal_id       VARCHAR(80)     NOT NULL,
    case_id         VARCHAR(30)     NOT NULL,
    learner_id      VARCHAR(20)     NOT NULL,
    appeal_no       SMALLINT        NOT NULL,
    reason          TEXT            NOT NULL,
    submitted_at    DATETIME        NOT NULL,
    appeal_status   ENUM(
                        'SUBMITTED',
                        'UNDER_REVIEW',
                        'UPHELD',
                        'OVERTURNED',
                        'REMANDED'
                    )               DEFAULT 'SUBMITTED',
    resolved_at     DATETIME,
    CONSTRAINT pk_appeal                PRIMARY KEY (appeal_id),
    CONSTRAINT uq_appeal_no             UNIQUE (case_id, appeal_no),
    CONSTRAINT fk_appeal_case           FOREIGN KEY (case_id)
                                            REFERENCES IntegrityCase(case_id),
    CONSTRAINT fk_appeal_learner        FOREIGN KEY (learner_id)
                                            REFERENCES Learner(learner_id),
    CONSTRAINT chk_appeal_no           CHECK (appeal_no >= 1),
    CONSTRAINT chk_appeal_resolved     CHECK (resolved_at IS NULL OR resolved_at >= submitted_at)
);

CREATE INDEX idx_appeal_status ON Appeal(appeal_status);

-- =============================================================
-- 12. APPEAL REVIEW
--     Independent reviewer's evaluation of an appeal.
--     BUSINESS RULE: independence_verified must be TRUE before
--     the Appeal record can be set to UPHELD or OVERTURNED.
-- =============================================================
CREATE TABLE AppealReview (
    review_id               BIGINT          NOT NULL AUTO_INCREMENT,
    appeal_id               VARCHAR(80)     NOT NULL,
    reviewer_id             VARCHAR(20)     NOT NULL,
    outcome                 ENUM('UPHELD', 'OVERTURNED', 'REMANDED') NOT NULL,
    rationale               TEXT            NOT NULL,
    independence_verified   BOOLEAN         NOT NULL DEFAULT FALSE,
    reviewed_at             DATETIME        NOT NULL,
    CONSTRAINT pk_appeal_review         PRIMARY KEY (review_id),
    CONSTRAINT fk_ar_appeal             FOREIGN KEY (appeal_id)
                                            REFERENCES Appeal(appeal_id),
    CONSTRAINT fk_ar_reviewer           FOREIGN KEY (reviewer_id)
                                            REFERENCES Reviewer(reviewer_id)
);

-- =============================================================
-- 13. CASE EVENT  (timeline — INSERT only, never update/delete)
--     Immutable audit trail of every status change and action
--     taken on an IntegrityCase.
-- =============================================================
CREATE TABLE CaseEvent (
    event_id        BIGINT          NOT NULL AUTO_INCREMENT,
    case_id         VARCHAR(30)     NOT NULL,
    event_type      VARCHAR(50)     NOT NULL,
    actor_role      VARCHAR(30)     NOT NULL,
    actor_ref       VARCHAR(30),
    previous_status VARCHAR(40),
    new_status      VARCHAR(40),
    event_details   JSON,
    occurred_at     DATETIME        NOT NULL,
    CONSTRAINT pk_case_event        PRIMARY KEY (event_id),
    CONSTRAINT fk_ce_case           FOREIGN KEY (case_id)
                                        REFERENCES IntegrityCase(case_id)
);

CREATE INDEX idx_case_event_time ON CaseEvent(case_id, occurred_at);

-- =============================================================
-- 14. AUDIT LOG
--     Application-wide change log. Captures every INSERT, UPDATE
--     and DELETE on sensitive tables with before/after snapshots.
-- =============================================================
CREATE TABLE AuditLog (
    audit_id        BIGINT          NOT NULL AUTO_INCREMENT,
    entity_type     VARCHAR(50)     NOT NULL,
    entity_id       VARCHAR(80)     NOT NULL,
    action          VARCHAR(50)     NOT NULL,
    actor_role      VARCHAR(30)     NOT NULL,
    actor_ref       VARCHAR(30),
    old_values      JSON,
    new_values      JSON,
    created_at      DATETIME        NOT NULL,
    CONSTRAINT pk_audit_log         PRIMARY KEY (audit_id)
);

CREATE INDEX idx_audit_entity   ON AuditLog(entity_type, entity_id);
CREATE INDEX idx_audit_created  ON AuditLog(created_at);

-- =============================================================
-- VERIFICATION QUERIES
--    Run these after executing this script to confirm setup.
-- =============================================================

-- SHOW TABLES;
-- DESCRIBE Learner;
-- DESCRIBE Submission;
-- DESCRIBE IntegrityCase;
-- SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
-- FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
-- WHERE TABLE_SCHEMA = 'academic_integrity'
-- AND REFERENCED_TABLE_NAME IS NOT NULL;
