"""Skill folders and the graph seed stay in step: every SKILL.md is served by get_skill as written."""

import re
from pathlib import Path

from propadmin_core import Store, seed_demo

SKILLS = Path(__file__).resolve().parents[3] / "skills"
FRONTMATTER = re.compile(r"---\nname: ([a-z0-9-]+)\ndescription: (.+?)\n---\n", re.S)


def test_every_skill_folder_is_seeded_with_its_own_file():
    store = Store()
    seed_demo(store)
    seeded = store.snapshot()["skills"]
    folders = sorted(path.parent for path in SKILLS.glob("*/SKILL.md"))
    assert folders
    for folder in folders:
        skill = seeded.get(f"skill:{folder.name}")
        assert skill, f"skills/{folder.name} has no seeded skill"
        assert skill["content"] == (folder / "SKILL.md").read_text()


def test_skill_frontmatter_names_its_folder():
    for path in SKILLS.glob("*/SKILL.md"):
        match = FRONTMATTER.match(path.read_text())
        assert match, f"{path} lacks name/description frontmatter"
        assert match.group(1) == path.parent.name
        assert len(match.group(2)) <= 1024


def test_reseeding_updates_seed_versions_but_keeps_admin_versions():
    store = Store()
    seed_demo(store)

    def age(state):
        stub = "# Book a contractor\n\nstub\n"
        state["skills"]["skill:book-contractor"].update(content=stub)
        state["skills"]["skill:book-contractor"]["versions"][-1]["content"] = stub
        state["skills"].pop("skill:landlord-approval")  # a graph seeded before this skill existed
        for key in ("skill:landlord-approval", "skill_version:landlord-approval-v1"):
            state["entities"].pop(key)
        for edge_id in [k for k, e in state["edges"].items() if e["source"] == "skill:landlord-approval"]:
            del state["edges"][edge_id]
        admin = state["skills"]["skill:tenant-call"]
        admin["versions"].append({"version": 2, "content": "admin text", "created_by": "admin"})
        admin.update(content="admin text", current_version=2)

    store.mutate(age)
    seed_demo(store)
    state = store.snapshot()
    book = state["skills"]["skill:book-contractor"]
    assert book["content"] == (SKILLS / "book-contractor/SKILL.md").read_text()
    assert book["current_version"] == 2
    current = [e["target"] for e in state["edges"].values()
               if e["source"] == "skill:book-contractor" and e["relation"] == "current"]
    assert current == ["skill_version:book-contractor-v2"]
    assert state["skills"]["skill:landlord-approval"]["content"] == (
        SKILLS / "landlord-approval/SKILL.md").read_text()
    assert state["skills"]["skill:tenant-call"]["content"] == "admin text"
