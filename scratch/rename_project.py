import os
import re
import shutil

# Exclude directories
EXCLUDE_DIRS = {'.git', 'node_modules', '__pycache__', 'upstream_repo', '.gemini', 'scratch'}
# Valid file extensions to process
VALID_EXTS = {'.py', '.js', '.html', '.css', '.md', '.json', '.env', '.yaml', '.yml', '.txt', '.sh'}

project_root = r"c:\Users\kudch\Downloads\chrono-audit"

# 1. Rename the main package directory
old_pkg_dir = os.path.join(project_root, "chrono_audit")
new_pkg_dir = os.path.join(project_root, "auditline")
if os.path.exists(old_pkg_dir):
    os.rename(old_pkg_dir, new_pkg_dir)
    print(f"Renamed {old_pkg_dir} -> {new_pkg_dir}")

# 2. Text replacements
replacements = [
    ("CHRONO-AUDIT", "AuditLine"),
    ("chrono-audit", "auditline"),
    ("Chrono-Audit", "AuditLine"),
    ("chrono_audit", "auditline"),
    ("CHRONO_AUDIT", "AUDITLINE"),
]

def replace_in_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        return  # skip binary files
    
    new_content = content
    for old_str, new_str in replacements:
        new_content = new_content.replace(old_str, new_str)
        
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {filepath}")

for root, dirs, files in os.walk(project_root):
    # Filter out excluded directories
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext in VALID_EXTS or file in ['.env', '.gitignore']:
            filepath = os.path.join(root, file)
            replace_in_file(filepath)

print("Project rename completed!")
