"""LMS export utilities for SCORM 1.2 and xAPI."""

import json
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from xml.etree import ElementTree as ET

from mtm.config import get_config
from mtm.storage.db import get_db


def create_scorm_manifest(
    title: str,
    identifier: str,
    organization: str = "default",
    items: Optional[list[dict[str, Any]]] = None,
) -> ET.Element:
    """Create SCORM 1.2 manifest XML.

    Args:
        title: Course title
        identifier: Unique identifier
        organization: Organization identifier
        items: List of manifest items

    Returns:
        XML ElementTree root
    """
    # Create manifest root
    manifest = ET.Element(
        "manifest",
        {
            "identifier": identifier,
            "version": "1.2",
            "xmlns": "http://www.imsproject.org/xsd/imscp_rootv1p1p2",
            "xmlns:adlcp": "http://www.adlnet.org/xsd/adlcp_rootv1p2",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd",
        },
    )

    # Metadata
    metadata = ET.SubElement(manifest, "metadata")
    schema = ET.SubElement(metadata, "schema")
    schema.text = "ADL SCORM"
    schemaversion = ET.SubElement(metadata, "schemaversion")
    schemaversion.text = "1.2"

    # Organizations
    organizations = ET.SubElement(manifest, "organizations", {"default": organization})
    org = ET.SubElement(organizations, "organization", {"identifier": organization})
    org_title = ET.SubElement(org, "title")
    org_title.text = title

    # Resources
    resources = ET.SubElement(manifest, "resources")
    
    if items:
        for item in items:
            # Add item to organization
            item_elem = ET.SubElement(org, "item", {"identifier": item["identifier"]})
            item_title = ET.SubElement(item_elem, "title")
            item_title.text = item.get("title", "")
            
            # Add resource
            resource = ET.SubElement(
                resources,
                "resource",
                {
                    "identifier": item["identifier"],
                    "type": "webcontent",
                    "adlcp:scormtype": "sco",
                    "href": item.get("href", "index.html"),
                },
            )
            file_elem = ET.SubElement(resource, "file", {"href": item.get("href", "index.html")})

    return manifest


def create_scorm_package(
    modules: list[dict[str, Any]],
    output_path: Path,
    title: str = "Meeting-to-Modules Course",
) -> Path:
    """Create a SCORM 1.2 package.

    Args:
        modules: List of module dictionaries
        output_path: Output path for SCORM package (zip file)
        title: Course title

    Returns:
        Path to created SCORM package
    """
    # Create temporary directory for package contents
    package_dir = output_path.parent / f"{output_path.stem}_temp"
    package_dir.mkdir(parents=True, exist_ok=True)

    # Create manifest items
    items = []
    for i, module in enumerate(modules, 1):
        module_id = f"module_{i}"
        items.append(
            {
                "identifier": module_id,
                "title": module.get("title", f"Module {i}"),
                "href": f"module_{i}.html",
            }
        )

    # Create manifest
    manifest_id = str(uuid.uuid4())
    manifest_xml = create_scorm_manifest(title, manifest_id, items=items)

    # Write manifest
    manifest_path = package_dir / "imsmanifest.xml"
    tree = ET.ElementTree(manifest_xml)
    ET.indent(tree, space="  ")
    tree.write(manifest_path, encoding="utf-8", xml_declaration=True)

    # Create launch HTML
    launch_html = package_dir / "index.html"
    with open(launch_html, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>SCORM Course</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>Meeting-to-Modules Course</h1>
    <div id="content">
        <p>Course content will be loaded here.</p>
    </div>
    <script>
        // SCORM API integration would go here
        // This is a basic placeholder
    </script>
</body>
</html>""")

    # Create module HTML files
    for i, module in enumerate(modules, 1):
        module_html = package_dir / f"module_{i}.html"
        with open(module_html, "w", encoding="utf-8") as f:
            content = module.get("content", "").replace("\n", "<br>\n")
            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{module.get('title', f'Module {i}')}</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>{module.get('title', f'Module {i}')}</h1>
    <div>{content}</div>
</body>
</html>""")

    # Create ZIP package
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in package_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)

    # Clean up temp directory
    import shutil
    shutil.rmtree(package_dir)

    return output_path


def create_xapi_statement(
    actor: dict[str, Any],
    verb: dict[str, Any],
    object: dict[str, Any],
    result: Optional[dict[str, Any]] = None,
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create an xAPI statement.

    Args:
        actor: Actor (learner) information
        verb: Verb (action) information
        object: Object (activity) information
        result: Optional result information
        context: Optional context information

    Returns:
        xAPI statement dictionary
    """
    statement = {
        "id": str(uuid.uuid4()),
        "actor": actor,
        "verb": verb,
        "object": object,
        "timestamp": datetime.now().isoformat(),
    }

    if result:
        statement["result"] = result
    if context:
        statement["context"] = context

    return statement


def create_xapi_package(
    modules: list[dict[str, Any]],
    output_path: Path,
    title: str = "Meeting-to-Modules Course",
) -> Path:
    """Create an xAPI package.

    Args:
        modules: List of module dictionaries
        output_path: Output path for xAPI package (JSON file)
        title: Course title

    Returns:
        Path to created xAPI package
    """
    # Create xAPI statements for each module
    statements = []

    for module in modules:
        # Statement for module launch
        statement = create_xapi_statement(
            actor={
                "objectType": "Agent",
                "name": "Learner",
                "mbox": "mailto:learner@example.com",
            },
            verb={
                "id": "http://adlnet.gov/expapi/verbs/launched",
                "display": {"en-US": "launched"},
            },
            object={
                "objectType": "Activity",
                "id": f"http://example.com/modules/{module.get('id', '')}",
                "definition": {
                    "name": {"en-US": module.get("title", "")},
                    "description": {"en-US": module.get("description", "")},
                },
            },
            context={
                "contextActivities": {
                    "parent": [{"id": "http://example.com/course", "objectType": "Activity"}]
                }
            },
        )
        statements.append(statement)

    # Write xAPI package
    package = {
        "title": title,
        "created": datetime.now().isoformat(),
        "statements": statements,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(package, f, indent=2, ensure_ascii=False)

    return output_path


def export_to_lms(
    format: str,
    project: Optional[str] = None,
    output_path: Optional[str | Path] = None,
    title: Optional[str] = None,
) -> Path:
    """Export modules to LMS format (SCORM 1.2 or xAPI).

    Args:
        format: Export format ('scorm' or 'xapi')
        project: Project name (None for all projects)
        output_path: Output path for package
        title: Course title

    Returns:
        Path to created package
    """
    config = get_config()
    db = get_db()

    # Get modules
    if project:
        modules = list(db.db["modules"].rows_where("project = ?", [project]))
    else:
        modules = list(db.db["modules"].rows_where("1=1"))

    if not modules:
        raise ValueError("No modules found to export")

    # Determine output path
    if output_path is None:
        output_dir = Path(config.output_dir) / "lms_exports"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if format.lower() == "scorm":
            output_path = output_dir / f"scorm_{timestamp}.zip"
        else:
            output_path = output_dir / f"xapi_{timestamp}.json"
    else:
        output_path = Path(output_path)

    # Set title
    if title is None:
        title = f"{project or 'All Projects'} - Meeting-to-Modules Course"

    # Export based on format
    if format.lower() == "scorm":
        return create_scorm_package(modules, output_path, title=title)
    elif format.lower() == "xapi":
        return create_xapi_package(modules, output_path, title=title)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'scorm' or 'xapi'")

