import sys

from rope.base.project import Project
from rope.refactor.move import create_move
from rope.refactor.rename import Rename

src_file, dest = (
    sys.argv[1],
    sys.argv[2],
)  # dest: a package dir, or a new module name for a rename

proj = Project(".", ropefolder=None)
proj.prefs.set("source_folders", ["src"])

res = proj.get_file(src_file)
try:
    if dest.endswith("/"):
        changes = create_move(proj, res).get_changes(proj.get_folder(dest.rstrip("/")))
    else:
        changes = Rename(proj, res).get_changes(dest)
    print(changes.get_description())
    proj.do(changes)
finally:
    proj.close()
