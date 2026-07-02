CREATE TABLE IF NOT EXISTS jobs (
    job_id SERIAL PRIMARY KEY,
    source_id TEXT UNIQUE NOT NULL,
    company_name TEXT NOT NULL,
    position TEXT NOT NULL,
    category TEXT NOT NULL,
    industry TEXT NOT NULL,
    location TEXT,
    deadline DATE,
    url TEXT,
    description TEXT,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_skills (
    job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    PRIMARY KEY (job_id, skill_name)
);

CREATE TABLE IF NOT EXISTS trend_data (
    skill_name TEXT PRIMARY KEY,
    frequency INTEGER NOT NULL,
    trend_score NUMERIC(8, 4) NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS user_skills (
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'beginner',
    PRIMARY KEY (user_id, skill_name)
);

