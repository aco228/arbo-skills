"""Builds one upload zip per skill into dist/, for the Claude web and desktop apps.

Run from anywhere: python build_zips.py            (all skills)
                   python build_zips.py arbo-scripts (only the named ones)

Entry names always use "/" and the zip root is the skill folder, so the zips
upload fine even when built on Windows (Compress-Archive writes "\" and is rejected).
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.join(ROOT, "skills")
DIST = os.path.join(ROOT, "dist")


def build(name):
    source = os.path.join(SKILLS, name)
    if not os.path.isfile(os.path.join(source, "SKILL.md")):
        sys.exit(f"{name}: no SKILL.md in {source}")

    os.makedirs(DIST, exist_ok=True)
    target = os.path.join(DIST, name + ".zip")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(name + "/", "")
        for folder, dirs, files in os.walk(source):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for file in sorted(f for f in files if not f.startswith(".")):
                path = os.path.join(folder, file)
                z.write(path, name + "/" + os.path.relpath(path, source).replace(os.sep, "/"))
    print("built", os.path.relpath(target, ROOT))


names = sys.argv[1:] or sorted(d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d)))
for n in names:
    build(n)
