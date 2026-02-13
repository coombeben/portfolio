DROP TABLE IF EXISTS endpoint_usage;
DROP TABLE IF EXISTS sessions;

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    identifier TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_sessions_id_created ON sessions (identifier, created_at);

CREATE TABLE endpoint_usage (
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    usage_date DATE DEFAULT CURRENT_DATE,
    message_count INT DEFAULT 0,
    PRIMARY KEY (session_id, usage_date)
);

ALTER TABLE endpoint_usage ADD CONSTRAINT check_positive_count CHECK (message_count >= 0);
