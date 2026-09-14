import os

project_root = r"c:\Users\kudch\Downloads\chrono-audit"
replacements = [
    ("ChronoAuditor", "AuditLaneVerifier"),
    ("ChronoAuditHandler", "AuditLaneHandler"),
    ("Chrono Audit", "AuditLane"),
    ("chrono audit", "AuditLane"),
    ("ChronoAudit", "AuditLane"),
    ("chronoAudit", "auditlane"),
    ("Chrono-Audit", "AuditLane"),
    ("chrono-audit", "auditlane"),
    ("CHRONO-AUDIT", "AUDITLANE"),
    ("Chrono", "AuditLane"),
    ("chrono", "auditlane"),
    ("CHRONO", "AUDITLANE"),
]

EXCLUDE_DIRS = {'.git', 'node_modules', '__pycache__', 'upstream_repo', '.gemini', 'scratch'}
VALID_EXTS = {'.py', '.js', '.html', '.css', '.md', '.json', '.env', '.yaml', '.yml', '.txt', '.sh', '.ini'}

for root, dirs, files in os.walk(project_root):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext in VALID_EXTS or file in ['.env', '.gitignore']:
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                continue
            
            new_content = content
            for old_str, new_str in replacements:
                new_content = new_content.replace(old_str, new_str)
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {filepath}")
