"""
The query version tree — a git-like history of SQL refinement.

Each version is a node that remembers its PARENT only (never its children —
children are derived by scanning, so there's one source of truth). This
lets a human inspect the whole refinement chain and "rewind" to any earlier
version to branch from, exactly like git checkout + branch.
"""

from dataclasses import dataclass


@dataclass
class QueryVersion:
    id: int
    parent_id: int | None    # None for the first draft (the root)
    model: str               # which model produced this version
    sql: str                 # the query text at this version
    ran_ok: bool             # did it execute without error?
    result_summary: str      # "5 rows" or "ERROR: no such column: foo"
    rows: list = None        # actual returned rows (for the critic / final answer)


class QueryTree:
    def __init__(self):
        self.versions: list[QueryVersion] = []
        self._next_id = 0

    def add(self, parent_id, model, sql, ran_ok, result_summary, rows=None) -> int:
        version = QueryVersion(
            id=self._next_id,
            parent_id=parent_id,
            model=model,
            sql=sql,
            ran_ok=ran_ok,
            result_summary=result_summary,
            rows=rows,
        )
        self.versions.append(version)
        self._next_id += 1
        return version.id

    def get(self, version_id) -> QueryVersion:
        return self.versions[version_id]

    def children_of(self, version_id) -> list:
        # derived, never stored
        return [v for v in self.versions if v.parent_id == version_id]

    def best_ok_version(self):
        """The most recent version that ran without error, if any."""
        ok = [v for v in self.versions if v.ran_ok]
        return ok[-1] if ok else None

    def render(self) -> str:
        """Pre-order DFS: print each node, THEN its children, indented by
        depth — so the root is on top and branches show as siblings."""
        lines = []

        def walk(version_id, depth):
            v = self.get(version_id)
            indent = "  " * depth
            status = "✓" if v.ran_ok else "✗"
            lines.append(f"{indent}[{v.id}] {v.model} {status} {v.result_summary}")
            lines.append(f"{indent}    SQL: {v.sql.strip()[:70]}")
            # show the actual returned data, not just the row count, so a
            # human can verify whether the answer is correct
            if v.ran_ok and v.rows:
                preview = "; ".join(str(r) for r in v.rows[:3])
                lines.append(f"{indent}    → {preview[:90]}")
            for child in self.children_of(version_id):
                walk(child.id, depth + 1)

        for root in [v for v in self.versions if v.parent_id is None]:
            walk(root.id, 0)
        return "\n".join(lines)