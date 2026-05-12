import os
from collections import defaultdict, deque
import requests
import yaml
import pandas as pd
from itertools import combinations

NODE_MODEL_URL = os.getenv("NODE_MODEL_URL", "https://raw.githubusercontent.com/CBIIT/icdc-model-tool/master/model-desc/icdc-model.yml")

def load_yaml_from_url(url: str) -> dict:
    if not url:
        raise ValueError('Missing URL')
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return yaml.safe_load(resp.text)


def build_graph_from_yaml(node_model):
    graph = defaultdict(list)
    all_nodes = set()

    # add all nodes
    for node in node_model.get("Nodes", {}):
        all_nodes.add(node)
        graph[node]

    # build edges
    for rel_spec in node_model.get("Relationships", {}).values():
        for end in rel_spec.get("Ends", []):
            src = end.get("Src")
            dst = end.get("Dst")

            if not src or not dst or src == dst:
                continue

            parent = dst   # ✅ correct
            child = src    # ✅ correct

            all_nodes.update([parent, child])

            if child not in graph[parent]:
                graph[parent].append(child)

            graph[child]  # ensure child exists

    return dict(graph), all_nodes


def bfs_levels(graph, root):
    """
    Return nodes level-by-level as a 2D array:
        [
            [root],
            [level_1_nodes],
            [level_2_nodes],
            ...
        ]
    """
    visited = set([root])
    queue = deque([root])
    levels = []

    while queue:
        level_size = len(queue)
        level = []

        for _ in range(level_size):
            node = queue.popleft()
            level.append(node)

            for nxt in graph.get(node, []):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)

        levels.append(level)

    return levels

def bfs_parent_map(graph, root):
    # output
    # program -> ['study']
    # study -> ['study_arm', 'case', 'cohort', 'human_relevance', 'file', 'consent_group']
    # consent_group -> ['case']
    # human_relevance -> []
    # study_site -> ['study']
    # study_arm -> ['cohort', 'case']
    # cohort -> ['case']
    # case -> ['enrollment', 'demographic', 'diagnosis', 'cycle', 'sample', 'file', 'visit', 'adverse_event']
    visited = set([root])
    queue = deque([root])
    parent = {root: None}

    while queue:
        node = queue.popleft()

        for child in graph.get(node, []):
            if child not in visited:
                visited.add(child)
                parent[child] = node
                queue.append(child)

    return parent


def reconstruct_path(parent_map, node):
    path = []
    cur = node

    while cur is not None:
        path.append(cur)
        cur = parent_map.get(cur)

    return path[::-1]

def get_paths_for_nodes(parent_map, nodes):
    # output
    # ['program', 'study', 'file']
    # ['program', 'study', 'case', 'sample']
    # ['program', 'study', 'case', 'visit']
    paths = {}

    for node in nodes:
        if node in parent_map:
            paths[node] = reconstruct_path(parent_map, node)
        else:
            paths[node] = None  # node not reachable

    return paths

def paths_dict_to_edges_ordered(paths_by_node):
    # used for cross node analysis
    # [('program', 'study'), ('study', 'file'), ('study', 'case'), ('case', 'sample'), ('case', 'visit')]
    edges = []
    seen = set()

    for end_node, path in paths_by_node.items():
        if not isinstance(path, list):
            continue

        for i in range(len(path) - 1):
            edge = (path[i], path[i + 1])
            if edge not in seen:
                seen.add(edge)
                edges.append(edge)

    return edges

def graph_to_df(graph):
    rows = []

    for parent, children in graph.items():
        rows.append({
            "parent": parent,
            "child": children
        })
    return pd.DataFrame(rows)

def get_edges_for_nodes(nodes: list[str]):
    if len(nodes) > 1:
        node_model = load_yaml_from_url(NODE_MODEL_URL)
        graph, all_nodes = build_graph_from_yaml(node_model)

        parent_map = bfs_parent_map(graph, "program")
        paths = get_paths_for_nodes(parent_map, nodes)
        edges = paths_dict_to_edges_ordered(paths)
        edges_df = pd.DataFrame(edges, columns=["parent", "child"])
        # print(edges)
        return graph, paths, edges, edges_df, ""
    else:
        return None, None, None, None, f"Provide nodes"

def build_graph(edges):
    graph = defaultdict(list)

    for parent, child in edges:
        if child not in graph[parent]:
            graph[parent].append(child)
        if parent not in graph:
            graph[parent] = graph[parent]

    return dict(graph)

def shortest_path(graph, start, end):
    if start == end:
        return [start]

    queue = deque([[start]])
    visited = {start}

    while queue:
        path = queue.popleft()
        node = path[-1]

        for neighbor in graph.get(node, []):
            if neighbor in visited:
                continue

            new_path = path + [neighbor]

            if neighbor == end:
                return new_path

            visited.add(neighbor)
            queue.append(new_path)

    return None


def find_selected_edges(edges, selected_nodes):
    selected_set = set(selected_nodes)
    return [edge for edge in edges if edge[0] in selected_set and edge[1] in selected_set]

