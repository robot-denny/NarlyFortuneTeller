# Kept deliberately. pyproject.toml's pythonpath = ["."] is what makes the root
# modules importable; this file is not needed for that today. It marks tests/ as
# a package so that, once test files live in subdirectories, two files with the
# same basename cannot collide during collection.
