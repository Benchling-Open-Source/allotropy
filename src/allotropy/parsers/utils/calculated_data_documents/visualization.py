from typing import Any

import networkx as nx

from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)


def add_node(graph: nx.DiGraph, node_id: str, **attrs: Any) -> None:
    attrs["id"] = node_id[-3:]
    graph.add_node(node_id, **attrs)
    graph.nodes[node_id]["label"] = "\n".join(
        f"{key}: {attrs[key]}" for key in sorted(attrs)
    )


def construct_node(
    graph: nx.DiGraph, structure: dict[str, CalculatedDocument], calc_doc_id: str
) -> str:
    calc_doc = structure[calc_doc_id]
    add_node(
        graph,
        calc_doc.uuid,
        name=calc_doc.name,
        value=calc_doc.value,
        type="calculated document",
    )

    for data_source in calc_doc.data_sources:
        if sub_calc_doc := structure.get(data_source.reference.uuid):
            graph.add_edge(
                calc_doc.uuid,
                construct_node(graph, structure, sub_calc_doc.uuid),
            )
        else:
            node_id = f"{data_source.feature}_{data_source.reference.uuid}"
            add_node(
                graph,
                node_id,
                name=data_source.feature,
                value="unknown" if data_source.value is None else data_source.value,
                type="measurement",
            )
            graph.add_edge(calc_doc.uuid, node_id)

    return calc_doc.uuid


def construct_graph(
    calc_docs: dict[str, CalculatedDocument], target: str
) -> nx.DiGraph:
    graph = nx.DiGraph()

    for calc_doc_id, calc_doc in calc_docs.items():
        if calc_doc.name == target:
            construct_node(graph, calc_docs, calc_doc_id)

    return graph


def visualize_graph(
    calc_docs: dict[str, CalculatedDocument], calc_doc_name: str
) -> None:
    graph = construct_graph(calc_docs, calc_doc_name)
    nx.drawing.nx_agraph.write_dot(graph, "graph.dot")
