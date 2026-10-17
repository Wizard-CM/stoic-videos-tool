"""URLs for files inside a project's files/ folder. ?v=<mtime> makes the browser reload a file that changed."""

from app.core.paths import project_files_dir


def project_file_url(project_id: str, relative_path: str) -> str:
    file_path = project_files_dir(project_id) / relative_path
    version = int(file_path.stat().st_mtime) if file_path.exists() else 0
    return f"/api/projects/{project_id}/files/{relative_path}?v={version}"
