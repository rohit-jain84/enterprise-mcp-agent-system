-- ==========================================================================
-- Initial database setup for Enterprise MCP Agent System
-- This script runs on first PostgreSQL container creation via
-- docker-entrypoint-initdb.d. For ongoing schema changes use Alembic
-- migrations (alembic upgrade head).
-- ==========================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- Users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

-- ---------------------------------------------------------------------------
-- Sessions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL DEFAULT 'New Chat',
    metadata JSONB,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost FLOAT NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON sessions(user_id);

-- ---------------------------------------------------------------------------
-- Messages
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    tool_calls JSONB,
    tool_results JSONB,
    token_count INTEGER NOT NULL DEFAULT 0,
    cost FLOAT NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_messages_session_created ON messages(session_id, created_at);

-- ---------------------------------------------------------------------------
-- Approvals (human-in-the-loop)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tool_name VARCHAR(255) NOT NULL,
    tool_args JSONB NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    responded_by UUID REFERENCES users(id),
    responded_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_approvals_session_id ON approvals(session_id);
CREATE INDEX IF NOT EXISTS ix_approvals_status ON approvals(status);

-- ---------------------------------------------------------------------------
-- Audit logs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    action VARCHAR(255) NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_created ON audit_logs(user_id, created_at);

-- ---------------------------------------------------------------------------
-- Seed demo users
-- Passwords: admin@acme.com / admin123, user@acme.com / user123
-- ---------------------------------------------------------------------------
INSERT INTO users (email, hashed_password, full_name, role) VALUES
    ('admin@acme.com', '$2b$12$Zw35EfkGcLSdNKvjRPSvzOXOPehH0bbbI7d0ZOlbqwmEz9iInNFw2', 'Admin User', 'admin'),
    ('user@acme.com', '$2b$12$GnAvoO3RkjnHoq..qtz37uMpwjyFr5e6tTsMdchCMud/FHwNf5cq2', 'Demo User', 'user')
ON CONFLICT (email) DO NOTHING;
