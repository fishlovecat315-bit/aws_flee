-- Reference / fallback DDL for all 6 tables.
-- In normal operation, tables are created by Alembic (alembic upgrade head).
-- This file is executed by the postgres container on first init if the DB is empty.

-- 原始费用记录（从 AWS 同步的原始数据）
CREATE TABLE IF NOT EXISTS raw_cost_records (
    id              BIGSERIAL PRIMARY KEY,
    account_id      VARCHAR(20)     NOT NULL,
    account_name    VARCHAR(50)     NOT NULL,
    date            DATE            NOT NULL,
    service         VARCHAR(100)    NOT NULL,
    tag_key         VARCHAR(100),
    tag_value       VARCHAR(200),
    amount_usd      NUMERIC(12, 4)  NOT NULL,
    currency        VARCHAR(10)     NOT NULL DEFAULT 'USD',
    synced_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_raw_cost_records UNIQUE (account_id, date, service, tag_key, tag_value)
);

-- 分摊规则表
CREATE TABLE IF NOT EXISTS allocation_rules (
    id              BIGSERIAL PRIMARY KEY,
    account_name    VARCHAR(50)     NOT NULL,
    tag_value       VARCHAR(200),
    rule_type       VARCHAR(20)     NOT NULL,
    business_module VARCHAR(100),
    department      VARCHAR(50),
    ratios          JSONB,
    special_config  JSONB,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     DEFAULT NOW()
);

-- 分摊后费用记录
CREATE TABLE IF NOT EXISTS allocated_cost_records (
    id              BIGSERIAL PRIMARY KEY,
    date            DATE            NOT NULL,
    account_name    VARCHAR(50)     NOT NULL,
    tag_value       VARCHAR(200),
    business_module VARCHAR(100),
    department      VARCHAR(50)     NOT NULL,
    amount_usd      NUMERIC(12, 4)  NOT NULL,
    rule_id         BIGINT          REFERENCES allocation_rules(id),
    calculated_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_allocated_date ON allocated_cost_records(date);
CREATE INDEX IF NOT EXISTS idx_allocated_dept ON allocated_cost_records(department);

-- 规则变更历史
CREATE TABLE IF NOT EXISTS allocation_rule_history (
    id              BIGSERIAL PRIMARY KEY,
    rule_id         BIGINT          NOT NULL,
    changed_at      TIMESTAMPTZ     DEFAULT NOW(),
    old_value       JSONB,
    new_value       JSONB,
    changed_by      VARCHAR(100)    NOT NULL DEFAULT 'admin'
);

-- 费用预警阈值
CREATE TABLE IF NOT EXISTS alert_thresholds (
    id                      BIGSERIAL PRIMARY KEY,
    department              VARCHAR(50)     NOT NULL,
    monthly_threshold_usd   NUMERIC(12, 2)  NOT NULL,
    is_active               BOOLEAN         NOT NULL DEFAULT TRUE,
    updated_at              TIMESTAMPTZ     DEFAULT NOW(),
    CONSTRAINT uq_alert_thresholds_department UNIQUE (department)
);

-- 同步任务日志
CREATE TABLE IF NOT EXISTS sync_logs (
    id              BIGSERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ     NOT NULL,
    finished_at     TIMESTAMPTZ,
    status          VARCHAR(20)     NOT NULL,
    accounts_synced VARCHAR(200),
    records_count   INT,
    error_message   TEXT
);
