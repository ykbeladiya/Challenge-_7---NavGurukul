"""FastAPI application for meeting-to-modules web UI."""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from mtm.config import get_config
from mtm.storage.db import get_db
from mtm.utils.review import get_modules_by_state, set_module_state

app = FastAPI(title="Meeting-to-Modules", version="0.1.0")

# Mount static files if directory exists
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Home page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Meeting-to-Modules</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            nav { background: #f0f0f0; padding: 10px; margin-bottom: 20px; }
            nav a { margin-right: 20px; text-decoration: none; color: #333; }
            h1 { color: #333; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f0f0f0; }
            .state-draft { color: orange; }
            .state-review { color: blue; }
            .state-approved { color: green; }
        </style>
    </head>
    <body>
        <nav>
            <a href="/">Home</a>
            <a href="/modules">Modules</a>
            <a href="/upload">Upload</a>
            <a href="/approvals">Approvals</a>
            <a href="/exports">Exports</a>
        </nav>
        <h1>Meeting-to-Modules</h1>
        <p>Convert meeting notes into reusable training modules.</p>
        <h2>Quick Actions</h2>
        <ul>
            <li><a href="/upload">Upload Notes</a></li>
            <li><a href="/modules">View Modules</a></li>
            <li><a href="/approvals">Review Approvals</a></li>
            <li><a href="/exports">View Exports</a></li>
        </ul>
    </body>
    </html>
    """


@app.get("/modules", response_class=HTMLResponse)
async def list_modules(project: Optional[str] = None, state: Optional[str] = None):
    """List modules."""
    db = get_db()
    
    if state:
        modules = get_modules_by_state(state, project=project)
    elif project:
        modules = list(db.db["modules"].rows_where("project = ?", [project]))
    else:
        modules = list(db.db["modules"].rows_where("1=1", limit=100))
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Modules - Meeting-to-Modules</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            nav { background: #f0f0f0; padding: 10px; margin-bottom: 20px; }
            nav a { margin-right: 20px; text-decoration: none; color: #333; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f0f0f0; }
            .state-draft { color: orange; }
            .state-review { color: blue; }
            .state-approved { color: green; }
        </style>
    </head>
    <body>
        <nav>
            <a href="/">Home</a>
            <a href="/modules">Modules</a>
            <a href="/upload">Upload</a>
            <a href="/approvals">Approvals</a>
            <a href="/exports">Exports</a>
        </nav>
        <h1>Modules</h1>
        <table>
            <tr>
                <th>Title</th>
                <th>Project</th>
                <th>Type</th>
                <th>State</th>
                <th>Owner</th>
            </tr>
    """
    
    for module in modules:
        state = module.get("approval_state", "draft")
        html += f"""
            <tr>
                <td>{module.get('title', 'N/A')}</td>
                <td>{module.get('project', 'N/A')}</td>
                <td>{module.get('module_type', 'N/A')}</td>
                <td class="state-{state}">{state}</td>
                <td>{module.get('owner', 'N/A')}</td>
            </tr>
        """
    
    html += """
        </table>
    </body>
    </html>
    """
    
    return html


@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    """Upload page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upload - Meeting-to-Modules</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            nav { background: #f0f0f0; padding: 10px; margin-bottom: 20px; }
            nav a { margin-right: 20px; text-decoration: none; color: #333; }
            form { margin-top: 20px; }
            input[type="file"] { margin: 10px 0; }
            button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
        </style>
    </head>
    <body>
        <nav>
            <a href="/">Home</a>
            <a href="/modules">Modules</a>
            <a href="/upload">Upload</a>
            <a href="/approvals">Approvals</a>
            <a href="/exports">Exports</a>
        </nav>
        <h1>Upload Notes</h1>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <label for="file">Select file:</label>
            <input type="file" id="file" name="file" accept=".md,.txt,.docx,.pdf" required>
            <br>
            <button type="submit">Upload</button>
        </form>
    </body>
    </html>
    """


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and ingest a file."""
    # Save file temporarily
    config = get_config()
    upload_dir = Path(config.output_dir) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Ingest file (would call ingest command)
    return JSONResponse({"message": f"File {file.filename} uploaded successfully", "path": str(file_path)})


@app.get("/approvals", response_class=HTMLResponse)
async def approvals_page():
    """Approvals page."""
    db = get_db()
    draft_modules = get_modules_by_state("draft")
    review_modules = get_modules_by_state("review")
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Approvals - Meeting-to-Modules</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            nav { background: #f0f0f0; padding: 10px; margin-bottom: 20px; }
            nav a { margin-right: 20px; text-decoration: none; color: #333; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f0f0f0; }
            button { padding: 5px 10px; margin: 2px; cursor: pointer; }
        </style>
    </head>
    <body>
        <nav>
            <a href="/">Home</a>
            <a href="/modules">Modules</a>
            <a href="/upload">Upload</a>
            <a href="/approvals">Approvals</a>
            <a href="/exports">Exports</a>
        </nav>
        <h1>Module Approvals</h1>
        <h2>Draft Modules</h2>
        <table>
            <tr><th>Title</th><th>Project</th><th>Actions</th></tr>
    """
    
    for module in draft_modules:
        html += f"""
            <tr>
                <td>{module.get('title', 'N/A')}</td>
                <td>{module.get('project', 'N/A')}</td>
                <td>
                    <button onclick="setState('{module['id']}', 'review')">Send to Review</button>
                </td>
            </tr>
        """
    
    html += """
        </table>
        <h2>In Review</h2>
        <table>
            <tr><th>Title</th><th>Project</th><th>Actions</th></tr>
    """
    
    for module in review_modules:
        html += f"""
            <tr>
                <td>{module.get('title', 'N/A')}</td>
                <td>{module.get('project', 'N/A')}</td>
                <td>
                    <button onclick="setState('{module['id']}', 'approved')">Approve</button>
                    <button onclick="setState('{module['id']}', 'draft')">Reject</button>
                </td>
            </tr>
        """
    
    html += """
        </table>
        <script>
            async function setState(moduleId, state) {
                const response = await fetch(`/api/modules/${moduleId}/state`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({state: state})
                });
                if (response.ok) {
                    location.reload();
                }
            }
        </script>
    </body>
    </html>
    """
    
    return html


@app.get("/exports", response_class=HTMLResponse)
async def exports_page():
    """Exports page."""
    config = get_config()
    exports_dir = Path(config.output_dir) / "exports"
    
    exports = []
    if exports_dir.exists():
        exports = sorted(exports_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Exports - Meeting-to-Modules</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            nav { background: #f0f0f0; padding: 10px; margin-bottom: 20px; }
            nav a { margin-right: 20px; text-decoration: none; color: #333; }
            ul { list-style: none; padding: 0; }
            li { padding: 10px; border-bottom: 1px solid #ddd; }
        </style>
    </head>
    <body>
        <nav>
            <a href="/">Home</a>
            <a href="/modules">Modules</a>
            <a href="/upload">Upload</a>
            <a href="/approvals">Approvals</a>
            <a href="/exports">Exports</a>
        </nav>
        <h1>Exports</h1>
        <ul>
    """
    
    for export_path in exports:
        html += f'<li><a href="/exports/{export_path.name}">{export_path.name}</a></li>'
    
    html += """
        </ul>
    </body>
    </html>
    """
    
    return html


@app.post("/api/modules/{module_id}/state")
async def update_module_state(module_id: str, state: dict):
    """Update module approval state."""
    try:
        set_module_state(module_id, state.get("state", "draft"))
        return JSONResponse({"message": "State updated successfully"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

