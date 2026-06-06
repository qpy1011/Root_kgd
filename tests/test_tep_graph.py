from rootkgd.tep import build_tep_graph, tep_rfpa_parameters, tep_variable_nodes


def test_build_tep_graph_maps_paper_root_variables_to_physical_entities() -> None:
    graph = build_tep_graph()

    assert "x4" in graph.nodes
    assert "x45" in graph.nodes
    assert "Stream 4" in graph.nodes
    assert "Stream 12" in graph.nodes
    assert "Stream 14" in graph.nodes

    triples = {(triple.head, triple.relation, triple.tail) for triple in graph.triples}
    assert ("Stream 4", "State", "x4") in triples
    assert ("x45", "State of", "Stream 4") in triples
    assert ("Stream 12", "State", "x51") in triples
    assert ("Stream 14", "State", "x11") in triples


def test_build_tep_graph_uses_realistic_tep_process_flow() -> None:
    graph = build_tep_graph()

    triples = {(triple.head, triple.relation, triple.tail) for triple in graph.triples}

    assert ("Stream 4", "Output", "Stripper") in triples
    assert ("Stripper", "Output", "Stream 5") in triples
    assert ("Stream 5", "Output", "Stream 6") in triples
    assert ("Stream 8", "Output", "Compressor") in triples
    assert ("Compressor", "Output", "Stream 6") in triples
    assert ("Condenser", "Output", "Stream 14") in triples
    assert ("Stream 14", "Output", "Separator") in triples

    assert ("Stream 4", "Output", "Stream 6") not in triples
    assert ("Stripper", "Output", "Stream 8") not in triples
    assert ("Compressor", "Output", "Stream 5") not in triples


def test_build_tep_graph_contains_te_reactions_and_utilities() -> None:
    graph = build_tep_graph()

    triples = {(triple.head, triple.relation, triple.tail) for triple in graph.triples}

    assert ("Stream 4", "Contain", "B") in triples
    assert ("Stream 14", "Contain", "H") in triples
    assert ("D", "Generate", "F") in triples
    assert ("Stream 12", "Contain", "Cooling Water") in triples
    assert ("Stream 13", "Contain", "Cooling Water") in triples
    assert ("Stripper Steam", "Output", "Stripper") in triples
    assert ("Stripper Steam", "Contain", "Steam") in triples
    assert ("Stripper Steam", "State", "x19") in triples
    assert ("Stripper Steam", "State", "x50") in triples


def test_tep_helpers_match_paper_experiment_setup() -> None:
    assert tep_variable_nodes() == [f"x{i}" for i in range(1, 53)]

    params = tep_rfpa_parameters()

    assert params.distances["State"] == 1
    assert params.distances["Output"] == 3
    assert params.distances["Contain"] == 5
    assert params.distances["Generate"] == 20
    assert params.priorities["Output"] == 5
    assert params.sigma == 0.1
