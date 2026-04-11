CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS employees (
    id BIGSERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    created TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assets (
    id BIGSERIAL PRIMARY KEY,
    asset_type TEXT NOT NULL,
    description TEXT,
    estimated_value INTEGER,
    geom_point geometry(point, 4326),
    geom_line geometry(linestring, 4326),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT check_geom CHECK (geom_point IS NOT NULL OR geom_line IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS issues (
    id BIGSERIAL PRIMARY KEY,
    issue_type TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'open',
    asset_id BIGINT REFERENCES assets(id),
    description TEXT NOT NULL,
    estimated_cost INTEGER,
    reported_by BIGINT REFERENCES employees(id),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    created TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tickets (
    id BIGSERIAL PRIMARY KEY,
    issue_id BIGINT REFERENCES issues(id),
    work_description TEXT,
    employee_id BIGINT REFERENCES employees(id),
    completed_at TIMESTAMPTZ,
    asset_id BIGINT REFERENCES assets(id),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    created TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inspections (
    id BIGSERIAL PRIMARY KEY,
    asset_id BIGINT REFERENCES assets(id),
    result TEXT NOT NULL DEFAULT 'review',
    description TEXT NOT NULL,
    completed_at TIMESTAMPTZ,
    employee_id BIGINT REFERENCES employees(id),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    created TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assets_geom ON assets USING GIST(geom_point);
CREATE INDEX IF NOT EXISTS idx_assets_geom ON assets USING GIST(geom_line);
