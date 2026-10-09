"""The prerequisite graph.

Nodes are canonical records (a feat, a talent, a class, a skill...). Directed
edges ``A -> B`` mean "B is required by A". This is the structure that makes the
option space navigable: it answers *what does this unlock*, *what must I take
first*, *is this option reachable at level 1*, and *are there circular or
dangling prerequisites in the source data*.

Every edge keeps the predicate it came from, so a wrong edge can be traced back
to the exact prerequisite sentence and the source cell.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from typing import Iterator

from .ids import norm_key, slugify

#: predicate types that gate on numbers rather than on other options
NUMERIC_TYPES = {"ability_min", "bab_min", "level_min", "dark_side_score",
                 "dark_side_equals_ability", "size_min"}
#: predicate types that express a rule but point at no record
RULE_TYPES = {"creature_type", "force_sensitive", "affiliation", "requires_item",
              "special", "not_nonheroic", "any_of_category", "other"}


class PrereqGraph:
    def __init__(self, db):
        self.db = db
        self._edges: list[dict] | None = None
        self._out: dict[str, list[dict]] = defaultdict(list)
        self._in: dict[str, list[dict]] = defaultdict(list)

    # ------------------------------------------------------------------ build
    def _targets(self, pred: dict, mode: str = "all") -> Iterator[dict]:
        t = pred.get("type")
        if t in NUMERIC_TYPES:
            yield {"req_type": t, "req_entity": None, "req_id": None, "req_key": None,
                   "mode": mode, "predicate": pred, "resolved": True, "numeric": True}
            return
        if t in RULE_TYPES and t != "any_of":
            yield {"req_type": t, "req_entity": None, "req_id": None, "req_key": None,
                   "mode": mode, "predicate": pred, "resolved": False, "numeric": False}
            return
        if t == "any_of":
            for opt in pred.get("options", []):
                yield from self._targets(opt, mode="any")
            return
        if isinstance(pred.get("nested"), dict):
            yield from self._targets(pred["nested"], mode=mode)

        index = self.db.index()

        def hit(entity: str, name: str) -> tuple[str | None, str]:
            found = index.find(name, (entity,))
            if found:
                return found[1], norm_key(name)
            found = index.find(name)
            if found:
                return found[1], norm_key(name)
            return None, norm_key(name)

        if pred.get("id") and t not in {"any_of"}:
            yield {"req_type": t, "req_entity": t, "req_id": pred["id"],
                   "req_key": norm_key(pred.get("name") or pred.get("text") or ""),
                   "mode": mode, "predicate": pred, "resolved": True,
                   "param": pred.get("param")}
        for ref in pred.get("refs") or []:
            yield {"req_type": t, "req_entity": ref.get("entity_type"), "req_id": ref.get("id"),
                   "req_key": norm_key(ref.get("name", "")), "mode": mode,
                   "predicate": pred, "resolved": bool(ref.get("id")),
                   "param": ref.get("param")}
        if t == "trained_skill":
            names = ([pred["skill"]] if pred.get("skill") else []) + list(pred.get("skills") or [])
            for name in names:
                if not name:
                    continue
                if name.lower().startswith("knowledge (all") or norm_key(name) == norm_key("Knowledge"):
                    for sk in self.db.all("skill"):
                        if sk["name"].lower().startswith("knowledge"):
                            yield {"req_type": "trained_skill", "req_entity": "skill",
                                   "req_id": sk["id"], "req_key": norm_key(sk["name"]),
                                   "mode": "any", "predicate": pred, "resolved": True}
                    continue
                rid, key = hit("skill", name)
                yield {"req_type": "trained_skill", "req_entity": "skill", "req_id": rid,
                       "req_key": key, "mode": mode, "predicate": pred, "resolved": bool(rid)}
        if t == "weapon_proficiency":
            group = (pred.get("group") or "").strip()
            if pred.get("any") or not group:
                rid, key = hit("feat", "Weapon Proficiency")
                yield {"req_type": t, "req_entity": "feat", "req_id": rid, "req_key": key,
                       "mode": mode, "predicate": pred, "resolved": bool(rid), "param": None,
                       "param_axis": "weapon_group"}
            else:
                # the corpus stores one generic "Weapon Proficiency" feat; the
                # group in parentheses is a parameter choice, not a separate feat
                rid, key = hit("feat", f"Weapon Proficiency ({group.title()})")
                param = group
                if not rid:
                    rid, key = hit("feat", "Weapon Proficiency")
                yield {"req_type": t, "req_entity": "feat", "req_id": rid, "req_key": key,
                       "mode": mode, "predicate": pred, "resolved": bool(rid),
                       "param": param, "param_axis": "weapon_group"}
        if t == "armor_proficiency":
            for grade in ([pred["grade"]] if pred.get("grade") else []) + list(pred.get("grades") or []):
                rid, key = hit("feat", f"Armor Proficiency ({grade})")
                yield {"req_type": t, "req_entity": "feat", "req_id": rid, "req_key": key,
                       "mode": "any" if pred.get("grades") else mode, "predicate": pred,
                       "resolved": bool(rid)}
        if t == "talent":
            for tree in pred.get("trees") or []:
                rid, key = hit("talent_tree", tree)
                if not rid:
                    rid, key = hit("talent_tree", f"{tree} Talent Tree")
                yield {"req_type": "talent_tree", "req_entity": "talent_tree", "req_id": rid,
                       "req_key": key, "mode": "any", "predicate": pred, "resolved": bool(rid),
                       "count": pred.get("count", 1)}
            for name in pred.get("names") or []:
                rid, key = hit("talent", name)
                yield {"req_type": "talent", "req_entity": "talent", "req_id": rid,
                       "req_key": key, "mode": mode, "predicate": pred, "resolved": bool(rid)}
        if t == "class_level_min":
            rid, key = hit("class", pred.get("class", ""))
            yield {"req_type": t, "req_entity": "class", "req_id": rid, "req_key": key,
                   "mode": mode, "predicate": pred, "resolved": bool(rid),
                   "min_level": pred.get("min")}
        if t == "trained_skill" and pred.get("count"):
            return
        if t in {"force_power", "force_technique", "force_secret", "species", "skill",
                 "racial_ability", "droid_option", "droid_locomotion", "cybernetic",
                 "equipment", "language", "background", "destiny", "near_human_trait",
                 "lightsaber_form", "force_regimen", "starship_maneuver", "weapon", "armor"}:
            if not pred.get("id") and pred.get("name"):
                rid, key = hit(t, pred["name"])
                yield {"req_type": t, "req_entity": t, "req_id": rid, "req_key": key,
                       "mode": mode, "predicate": pred, "resolved": bool(rid)}

    def edges(self) -> list[dict]:
        """Every prerequisite edge in the corpus."""
        if self._edges is not None:
            return self._edges
        edges = []
        for entity, recs in self.db.records.items():
            for rec in recs:
                parsed = rec.get("prerequisites")
                if not parsed:
                    continue
                for pred in parsed.get("predicates", []):
                    for target in self._targets(pred):
                        edge = {"src_entity": entity, "src_id": rec["id"], **target}
                        edges.append(edge)
                        self._out[rec["id"]].append(edge)
                        if edge.get("req_id"):
                            self._in[edge["req_id"]].append(edge)
        self._edges = edges
        return edges

    # ---------------------------------------------------------------- queries
    def requires(self, record_id: str) -> list[dict]:
        self.edges()
        return list(self._out.get(record_id, []))

    def required_by(self, record_id: str) -> list[dict]:
        self.edges()
        return list(self._in.get(record_id, []))

    def closure(self, record_id: str, include_numeric: bool = False) -> set[str]:
        """Transitive set of record ids required to take ``record_id``."""
        self.edges()
        seen: set[str] = set()
        queue = deque([record_id])
        while queue:
            cur = queue.popleft()
            for edge in self._out.get(cur, []):
                rid = edge.get("req_id")
                if not rid or rid in seen:
                    continue
                if edge.get("numeric") and not include_numeric:
                    continue
                seen.add(rid)
                queue.append(rid)
        seen.discard(record_id)
        return seen

    def unlocks(self, record_id: str) -> set[str]:
        """Records that (transitively) require ``record_id``."""
        self.edges()
        seen: set[str] = set()
        queue = deque([record_id])
        while queue:
            cur = queue.popleft()
            for edge in self._in.get(cur, []):
                if edge["src_id"] in seen:
                    continue
                seen.add(edge["src_id"])
                queue.append(edge["src_id"])
        seen.discard(record_id)
        return seen

    def dangling(self) -> list[dict]:
        """Edges whose requirement could not be resolved to a record."""
        out = []
        for edge in self.edges():
            if edge.get("numeric") or edge.get("req_id"):
                continue
            if edge["req_type"] in RULE_TYPES:
                continue
            out.append(edge)
        return out

    def cycles(self) -> list[list[str]]:
        """Strongly connected components with more than one node (or self-loops)."""
        self.edges()
        adj: dict[str, set[str]] = defaultdict(set)
        nodes: set[str] = set()
        for edge in self._edges:
            if edge.get("req_id"):
                adj[edge["src_id"]].add(edge["req_id"])
                nodes |= {edge["src_id"], edge["req_id"]}
        index: dict[str, int] = {}
        low: dict[str, int] = {}
        on_stack: set[str] = set()
        stack: list[str] = []
        sccs: list[list[str]] = []
        counter = [0]

        def strongconnect(v: str) -> None:
            work = [(v, iter(sorted(adj[v])))]
            index[v] = low[v] = counter[0]
            counter[0] += 1
            stack.append(v)
            on_stack.add(v)
            while work:
                node, it = work[-1]
                advanced = False
                for w in it:
                    if w not in index:
                        index[w] = low[w] = counter[0]
                        counter[0] += 1
                        stack.append(w)
                        on_stack.add(w)
                        work.append((w, iter(sorted(adj[w]))))
                        advanced = True
                        break
                    elif w in on_stack:
                        low[node] = min(low[node], index[w])
                if advanced:
                    continue
                work.pop()
                if work:
                    low[work[-1][0]] = min(low[work[-1][0]], low[node])
                if low[node] == index[node]:
                    comp = []
                    while True:
                        w = stack.pop()
                        on_stack.discard(w)
                        comp.append(w)
                        if w == node:
                            break
                    if len(comp) > 1 or node in adj[node]:
                        sccs.append(sorted(comp))

        for n in sorted(nodes):
            if n not in index:
                strongconnect(n)
        return sccs

    def depth(self) -> dict[str, int]:
        """Longest prerequisite chain ending at each record (0 = no prerequisites)."""
        self.edges()
        memo: dict[str, int] = {}
        visiting: set[str] = set()

        def d(node: str) -> int:
            if node in memo:
                return memo[node]
            if node in visiting:            # cycle: break it
                return 0
            visiting.add(node)
            best = 0
            for edge in self._out.get(node, []):
                rid = edge.get("req_id")
                if rid:
                    best = max(best, 1 + d(rid))
            visiting.discard(node)
            memo[node] = best
            return best

        for rec_id in list(self.db.by_id):
            d(rec_id)
        return memo

    def deepest_chains(self, limit: int = 20) -> list[list[str]]:
        """The longest prerequisite chains in the corpus, most-gated first."""
        depth = self.depth()
        out = []
        for rec_id, d in sorted(depth.items(), key=lambda kv: (-kv[1], kv[0])):
            if d == 0:
                break
            chain = [rec_id]
            cur = rec_id
            while True:
                nxt = None
                for edge in self._out.get(cur, []):
                    rid = edge.get("req_id")
                    if rid and depth.get(rid, 0) == len(chain) - 1 + 0:
                        pass
                candidates = [e["req_id"] for e in self._out.get(cur, []) if e.get("req_id")]
                if not candidates:
                    break
                nxt = max(candidates, key=lambda r: depth.get(r, 0))
                if depth.get(nxt, 0) >= depth.get(cur, 0):
                    break
                chain.append(nxt)
                cur = nxt
            if len(chain) > 1:
                out.append(chain)
            if len(out) >= limit:
                break
        return out

    def stats(self) -> dict:
        edges = self.edges()
        by_type: dict[str, int] = defaultdict(int)
        by_entity: dict[str, int] = defaultdict(int)
        modes: dict[str, int] = defaultdict(int)
        for e in edges:
            by_type[e["req_type"]] += 1
            by_entity[e["src_entity"]] += 1
            modes[e.get("mode", "all")] += 1
        resolved = sum(1 for e in edges if e.get("req_id") or e.get("numeric"))
        depth = self.depth()
        return {
            "edges": len(edges),
            "resolved_edges": resolved,
            "dangling_edges": len(self.dangling()),
            "unresolved_share": round(1 - resolved / max(len(edges), 1), 4),
            "by_requirement_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
            "by_source_entity": dict(sorted(by_entity.items(), key=lambda kv: -kv[1])),
            "by_mode": dict(modes),
            "nodes": len({e["src_id"] for e in edges} | {e["req_id"] for e in edges if e.get("req_id")}),
            "max_chain_depth": max(depth.values()) if depth else 0,
            "cycles": len(self.cycles()),
            "records_with_no_prerequisites": sum(
                1 for e, recs in self.db.records.items()
                for r in recs if not r.get("prerequisites")),
        }

    # ----------------------------------------------------------------- export
    def to_json(self) -> dict:
        return {"stats": self.stats(),
                "edges": [{k: v for k, v in e.items() if k != "predicate"} for e in self.edges()],
                "cycles": self.cycles()}

    def to_dot(self, entity_filter: str | None = None, limit: int = 4000) -> str:
        lines = ["digraph prerequisites {", '  rankdir=LR; node [shape=box, fontsize=9];']
        n = 0
        for e in self.edges():
            if not e.get("req_id"):
                continue
            if entity_filter and e["src_entity"] != entity_filter:
                continue
            src = self.db.by_id.get(e["src_id"], {})
            dst = self.db.by_id.get(e["req_id"], {})
            style = "" if e.get("mode") == "all" else ' style=dashed'
            lines.append(f'  "{e["src_id"]}" [label="{src.get("name", e["src_id"])}"];')
            lines.append(f'  "{e["req_id"]}" [label="{dst.get("name", e["req_id"])}"];')
            lines.append(f'  "{e["src_id"]}" -> "{e["req_id"]}"[{style}];')
            n += 1
            if n >= limit:
                break
        lines.append("}")
        return "\n".join(lines)


def write_report(graph: PrereqGraph, out_path=None) -> str:
    """Markdown report on the prerequisite graph."""
    from . import paths

    stats = graph.stats()
    lines = ["# Prerequisite graph report", "",
             "## Summary", "",
             f"- edges: **{stats['edges']}** ({stats['resolved_edges']} resolved to a record, "
             f"{stats['dangling_edges']} dangling)",
             f"- nodes touched: {stats['nodes']}",
             f"- deepest requirement chain: {stats['max_chain_depth']}",
             f"- cycles detected: {stats['cycles']}",
             "", "## Edge types", "", "| requirement type | edges |", "|---|---:|"]
    for t, n in stats["by_requirement_type"].items():
        lines.append(f"| `{t}` | {n} |")
    lines += ["", "## Edges by requiring entity", "", "| entity | edges |", "|---|---:|"]
    for t, n in stats["by_source_entity"].items():
        lines.append(f"| `{t}` | {n} |")

    cycles = graph.cycles()
    lines += ["", "## Cycles", ""]
    if cycles:
        for comp in cycles[:40]:
            names = [f"`{c}` ({graph.db.by_id.get(c, {}).get('name', '?')})" for c in comp]
            lines.append("- " + " -> ".join(names))
    else:
        lines.append("None. The requirement relation is acyclic.")

    dangling = graph.dangling()
    lines += ["", "## Dangling requirements", "",
              f"{len(dangling)} edges point at a name that no canonical record matches.",
              "", "| requiring record | requirement type | unresolved name |", "|---|---|---|"]
    seen = set()
    for e in dangling:
        key = (e["src_id"], e["req_type"], e.get("req_key"))
        if key in seen:
            continue
        seen.add(key)
        src = graph.db.by_id.get(e["src_id"], {})
        lines.append(f"| `{e['src_id']}` ({src.get('name','?')}) | `{e['req_type']}` | `{e.get('req_key')}` |")
        if len(seen) > 120:
            lines.append("| ... | ... | truncated |")
            break

    lines += ["", "## Deepest prerequisite chains", ""]
    for chain in graph.deepest_chains(15):
        pretty = []
        for rid in chain:
            rec = graph.db.by_id.get(rid, {})
            pretty.append(f"{rec.get('name', rid)} (`{rid}`)")
        lines.append("- " + " \u2190 requires \u2190 ".join(pretty))

    text = "\n".join(lines) + "\n"
    out = out_path or (paths.REPORTS_DIR / "prerequisite-graph.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return str(out)
