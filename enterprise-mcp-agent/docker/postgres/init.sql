-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum types
CREATE TYPE user_role AS ENUM ('admin', 'user', 'viewer');
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system', 'tool');
CREATE TYPE approval_status AS ENUM ('pending', 'approved', 'denied', 'expired');

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    role user_role NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role message_role NOT NULL,
    content TEXT NOT NULL,
    tool_calls JSONB,
    cost_usd FLOAT,
    tokens_input INT,
    tokens_output INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Approvals table
CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id),
    tool_name VARCHAR(255) NOT NULL,
    tool_args JSONB DEFAULT '{}',
    status approval_status NOT NULL DEFAULT 'pending',
    decided_by UUID REFERENCES users(id),
    decided_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Audit logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(255) NOT NULL,
    detail JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_approvals_session_id ON approvals(session_id);
CREATE INDEX idx_approvals_status ON approvals(status);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Seed demo users
-- admin123: $2b$12$LJ3m4ys3Lez.B3MJHdoj0eLMblGDnCIBOBcUsVmiOKs5gPKhEPMtO
-- user123:  $2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi
INSERT INTO users (email, hashed_password, display_name, role) VALUES
    ('admin@acme.com', '$2b$12$LJ3m4ys3Lez.B3MJHdoj0eLMblGDnCIBOBcUsVmiOKs5gPKhEPMtO', 'Admin User', 'admin'),
    ('user@acme.com', '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'Demo User', 'user');
