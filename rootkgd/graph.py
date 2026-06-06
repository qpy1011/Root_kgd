from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    name: str
    kind: str


@dataclass(frozen=True)
class Triple:
    head: str
    relation: str
    tail: str


class KnowledgeGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.triples: list[Triple] = []
        self._outgoing: dict[str, list[Triple]] = defaultdict(list)

    def add_node(self, name: str, kind: str) -> None:
        existing = self.nodes.get(name)
        if existing is not None:
            if existing.kind != kind:
                raise ValueError(f"Node {name!r} already has kind {existing.kind!r}")
            return
        self.nodes[name] = Node(name=name, kind=kind)

    def add_edge(self, head: str, relation: str, tail: str) -> None:
        if head not in self.nodes:
            self.add_node(head, "physical")
        if tail not in self.nodes:
            self.add_node(tail, "physical")
        triple = Triple(head=head, relation=relation, tail=tail)
        self.triples.append(triple)
        self._outgoing[head].append(triple)

    def outgoing(self, node: str) -> list[Triple]:
        return list(self._outgoing.get(node, ()))

    def by_kind(self, kind: str) -> list[str]:
        return [name for name, node in self.nodes.items() if node.kind == kind]

