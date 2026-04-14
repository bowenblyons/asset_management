CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS employees (
    id UUID DEFAULT uuidv7() PRIMARY KEY NOT NULL,
    first_name VARCHAR(20) NOT NULL,
    last_name VARCHAR(20) NOT NULL,
    email VARCHAR(50) NOT NULL UNIQUE,
    deleted_at TIMESTAMPTZ NULL,
    created TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE IF NOT EXISTS eid (
    eid VARCHAR(50) NOT NULL UNIQUE,
    employee_id UUID NOT NULL UNIQUE REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS assets (
    id UUID DEFAULT uuidv7() PRIMARY KEY NOT NULL,
    asset_type TEXT NOT NULL,
    description TEXT,
    estimated_value INTEGER,
    geom geometry(Geometry, 4326) NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT check_geom
    CHECK (
        (GeometryType(geom) IN ('POINT', 'LINESTRING'))
    )
);

CREATE TABLE IF NOT EXISTS aid (
    aid VARCHAR(50) NOT NULL UNIQUE,
    asset_id UUID NOT NULL UNIQUE REFERENCES assets(id)
);

CREATE TABLE IF NOT EXISTS issues (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    issue_type TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'open',
    asset_id VARCHAR(50) REFERENCES aid(aid),
    description TEXT NOT NULL,
    estimated_cost INTEGER,
    reported_by VARCHAR(50) REFERENCES eid(eid),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    created TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tickets (
    id BIGSERIAL PRIMARY KEY,
    issue_id BIGINT REFERENCES issues(id),
    work_description TEXT,
    employee_id VARCHAR(50) REFERENCES eid(eid),
    completed_at TIMESTAMPTZ,
    asset_id VARCHAR(50) REFERENCES aid(aid),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    created TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inspections (
    id BIGSERIAL PRIMARY KEY,
    asset_id VARCHAR(50) REFERENCES aid(aid),
    result TEXT NOT NULL DEFAULT 'review',
    description TEXT NOT NULL,
    completed_at TIMESTAMPTZ,
    employee_id VARCHAR(50) REFERENCES eid(eid),
    deleted_at TIMESTAMPTZ DEFAULT NULL,
    created TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assets_geom ON assets USING GIST(geom);