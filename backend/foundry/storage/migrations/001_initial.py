from __future__ import annotations

import aiosqlite


async def upgrade(conn: aiosqlite.Connection) -> None:
    await conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            status TEXT DEFAULT 'active',
            workspace_path TEXT,
            settings JSON,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS subprojects (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            name TEXT,
            description TEXT,
            type TEXT,
            status TEXT DEFAULT 'discovered',
            workspace_path TEXT,
            dependencies JSON,
            setup_steps JSON,
            complexity TEXT,
            sort_order INTEGER,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS resources (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            type TEXT,
            url TEXT,
            title TEXT,
            original_filename TEXT,
            mime_type TEXT,
            metadata JSON,
            content_hash TEXT,
            raw_content_path TEXT,
            pipeline_status TEXT DEFAULT 'pending',
            pipeline_error TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS extraction_results (
            id TEXT PRIMARY KEY,
            resource_id TEXT,
            summary TEXT,
            key_concepts JSON,
            entities JSON,
            content_sections JSON,
            discovered_projects JSON,
            open_questions JSON,
            follow_up_suggestions JSON,
            model_used TEXT,
            token_usage JSON,
            raw_response TEXT,
            created_at TEXT,
            FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            subproject_id TEXT,
            title TEXT,
            description TEXT,
            status TEXT DEFAULT 'todo',
            priority TEXT,
            source TEXT DEFAULT 'extracted',
            sort_order INTEGER,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (subproject_id) REFERENCES subprojects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            subproject_id TEXT,
            title TEXT,
            content TEXT,
            source TEXT DEFAULT 'user',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (subproject_id) REFERENCES subprojects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS file_assets (
            id TEXT PRIMARY KEY,
            subproject_id TEXT,
            path TEXT,
            type TEXT,
            description TEXT,
            size_bytes INTEGER,
            created_at TEXT,
            FOREIGN KEY (subproject_id) REFERENCES subprojects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS environments (
            id TEXT PRIMARY KEY,
            subproject_id TEXT,
            type TEXT,
            status TEXT DEFAULT 'planned',
            config JSON,
            path TEXT,
            error TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (subproject_id) REFERENCES subprojects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS agent_sessions (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            subproject_id TEXT,
            provider TEXT,
            model TEXT,
            mode TEXT DEFAULT 'explore',
            status TEXT DEFAULT 'active',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
            FOREIGN KEY (subproject_id) REFERENCES subprojects(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS agent_messages (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            role TEXT,
            content TEXT,
            tool_call JSON,
            created_at TEXT,
            FOREIGN KEY (session_id) REFERENCES agent_sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS provenance_links (
            id TEXT PRIMARY KEY,
            resource_id TEXT,
            target_type TEXT,
            target_id TEXT,
            context TEXT,
            quote TEXT,
            confidence REAL DEFAULT 1.0,
            created_at TEXT,
            FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS git_configs (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            remote_url TEXT,
            branch TEXT DEFAULT 'main',
            auto_push BOOLEAN DEFAULT FALSE,
            last_push_at TEXT,
            status TEXT DEFAULT 'disconnected',
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            type TEXT,
            project_id TEXT,
            subproject_id TEXT,
            status TEXT DEFAULT 'queued',
            progress_pct INTEGER DEFAULT 0,
            progress_steps JSON,
            pid INTEGER,
            started_at TEXT,
            completed_at TEXT,
            error TEXT,
            result JSON,
            created_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
            FOREIGN KEY (subproject_id) REFERENCES subprojects(id) ON DELETE SET NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
            entity_type,
            entity_id,
            project_id,
            title,
            content,
            tokenize='porter unicode61'
        );

        CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
        CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at);

        CREATE INDEX IF NOT EXISTS idx_subprojects_project_id ON subprojects(project_id);
        CREATE INDEX IF NOT EXISTS idx_subprojects_status ON subprojects(status);
        CREATE INDEX IF NOT EXISTS idx_subprojects_sort_order ON subprojects(sort_order);

        CREATE INDEX IF NOT EXISTS idx_resources_project_id ON resources(project_id);
        CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(type);
        CREATE INDEX IF NOT EXISTS idx_resources_pipeline_status ON resources(pipeline_status);
        CREATE INDEX IF NOT EXISTS idx_resources_content_hash ON resources(content_hash);
        CREATE INDEX IF NOT EXISTS idx_resources_created_at ON resources(created_at);

        CREATE INDEX IF NOT EXISTS idx_extraction_results_resource_id ON extraction_results(resource_id);
        CREATE INDEX IF NOT EXISTS idx_extraction_results_created_at ON extraction_results(created_at);

        CREATE INDEX IF NOT EXISTS idx_tasks_subproject_id ON tasks(subproject_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
        CREATE INDEX IF NOT EXISTS idx_tasks_sort_order ON tasks(sort_order);

        CREATE INDEX IF NOT EXISTS idx_notes_project_id ON notes(project_id);
        CREATE INDEX IF NOT EXISTS idx_notes_subproject_id ON notes(subproject_id);
        CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);

        CREATE INDEX IF NOT EXISTS idx_file_assets_subproject_id ON file_assets(subproject_id);
        CREATE INDEX IF NOT EXISTS idx_file_assets_path ON file_assets(path);

        CREATE INDEX IF NOT EXISTS idx_environments_subproject_id ON environments(subproject_id);
        CREATE INDEX IF NOT EXISTS idx_environments_status ON environments(status);

        CREATE INDEX IF NOT EXISTS idx_agent_sessions_project_id ON agent_sessions(project_id);
        CREATE INDEX IF NOT EXISTS idx_agent_sessions_subproject_id ON agent_sessions(subproject_id);
        CREATE INDEX IF NOT EXISTS idx_agent_sessions_status ON agent_sessions(status);

        CREATE INDEX IF NOT EXISTS idx_agent_messages_session_id ON agent_messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_agent_messages_created_at ON agent_messages(created_at);

        CREATE INDEX IF NOT EXISTS idx_provenance_links_resource_id ON provenance_links(resource_id);
        CREATE INDEX IF NOT EXISTS idx_provenance_links_target ON provenance_links(target_type, target_id);

        CREATE INDEX IF NOT EXISTS idx_git_configs_project_id ON git_configs(project_id);

        CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(type);
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_project_id ON jobs(project_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_subproject_id ON jobs(subproject_id);
        CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
        """
    )
