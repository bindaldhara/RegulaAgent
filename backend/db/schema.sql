-- RegulaAgent PostgreSQL schema (applied via psycopg, no ORM)
-- Run against Supabase SQL editor or: make migrate

-- App profile + consent keyed by Supabase auth.users.id
CREATE TABLE IF NOT EXISTS patient_profiles (
    user_id UUID PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL DEFAULT '',
    email VARCHAR(255),
    phone VARCHAR(32),
    consent_granted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS doctors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    specialty VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_doctors_specialty ON doctors (specialty);

-- Bookable time catalog (IST). Availability = row exists and no booked appointment at same doctor+time.
CREATE TABLE IF NOT EXISTS schedule_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(128) NOT NULL UNIQUE,
    doctor_id UUID NOT NULL REFERENCES doctors (id) ON DELETE CASCADE,
    starts_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (doctor_id, starts_at)
);

CREATE INDEX IF NOT EXISTS ix_schedule_slots_starts_at ON schedule_slots (starts_at);
CREATE INDEX IF NOT EXISTS ix_schedule_slots_doctor_id ON schedule_slots (doctor_id);

CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_ref VARCHAR(32) NOT NULL UNIQUE,
    patient_id UUID NOT NULL REFERENCES patients (id),
    doctor_id UUID NOT NULL REFERENCES doctors (id),
    scheduled_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'booked',
    idempotency_key VARCHAR(128) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_appointments_patient_id ON appointments (patient_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_appointments_doctor_time_booked
    ON appointments (doctor_id, scheduled_at)
    WHERE status = 'booked';

CREATE SEQUENCE IF NOT EXISTS appointment_external_ref_seq START WITH 1;

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations (id),
    role VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    intent VARCHAR(64),
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages (conversation_id);

CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations (id),
    run_id VARCHAR(64) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    current_step VARCHAR(64),
    final_outcome VARCHAR(64),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_agent_runs_conversation_id ON agent_runs (conversation_id);
CREATE INDEX IF NOT EXISTS ix_agent_runs_run_id ON agent_runs (run_id);

CREATE TABLE IF NOT EXISTS tool_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id UUID NOT NULL REFERENCES agent_runs (id),
    tool_name VARCHAR(128) NOT NULL,
    request_json JSONB,
    response_json JSONB,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    latency_ms DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_tool_calls_agent_run_id ON tool_calls (agent_run_id);

CREATE TABLE IF NOT EXISTS policy_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id UUID NOT NULL REFERENCES agent_runs (id),
    decision VARCHAR(16) NOT NULL,
    risk_level VARCHAR(16) NOT NULL,
    reason TEXT NOT NULL,
    proposed_action VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_policy_decisions_agent_run_id ON policy_decisions (agent_run_id);

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id UUID REFERENCES agent_runs (id),
    conversation_id UUID REFERENCES conversations (id),
    event_type VARCHAR(64) NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_audit_events_event_type ON audit_events (event_type);

-- Upgrades for databases created before external_id / external_ref
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS external_id VARCHAR(64);
DROP INDEX IF EXISTS ix_doctors_external_id;
CREATE UNIQUE INDEX IF NOT EXISTS uq_doctors_external_id ON doctors (external_id);

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS external_ref VARCHAR(32);
DROP INDEX IF EXISTS ix_appointments_external_ref;
CREATE UNIQUE INDEX IF NOT EXISTS uq_appointments_external_ref ON appointments (external_ref);

CREATE SEQUENCE IF NOT EXISTS appointment_external_ref_seq START WITH 1;
CREATE UNIQUE INDEX IF NOT EXISTS uq_appointments_doctor_time_booked
    ON appointments (doctor_id, scheduled_at)
    WHERE status = 'booked';
