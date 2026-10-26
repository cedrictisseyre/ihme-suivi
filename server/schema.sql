CREATE TABLE IF NOT EXISTS projects (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  student_name TEXT NOT NULL,
  title TEXT NOT NULL,
  repository_url TEXT NOT NULL DEFAULT '',
  deployed_url TEXT NOT NULL DEFAULT '',
  objective TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS milestones (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','doing','done','blocked')),
  due_date DATE,
  evidence TEXT NOT NULL DEFAULT '',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(project_id,position)
);
CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  reviewed_on DATE NOT NULL,
  commit_ref TEXT NOT NULL DEFAULT '',
  achievements TEXT NOT NULL,
  blocker TEXT NOT NULL DEFAULT '',
  next_step TEXT NOT NULL,
  assistance TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS assessments (
  project_id INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
  functionality NUMERIC CHECK(functionality BETWEEN 0 AND 6),
  design NUMERIC CHECK(design BETWEEN 0 AND 4),
  quality NUMERIC CHECK(quality BETWEEN 0 AND 3),
  progression NUMERIC CHECK(progression BETWEEN 0 AND 3),
  explanation NUMERIC CHECK(explanation BETWEEN 0 AND 4),
  comment TEXT NOT NULL DEFAULT '',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  expires_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS git_snapshots (
  project_id INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
  last_sha TEXT,
  last_title TEXT,
  last_committed_at TIMESTAMPTZ,
  checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  error TEXT NOT NULL DEFAULT ''
);

ALTER TABLE git_snapshots ADD COLUMN IF NOT EXISTS daily_activity JSONB;
