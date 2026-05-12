
node_category_weights = {
    "human_relevance": {
        "support": 0.001,
        "predictive_strength": 0.001,
        "determinism": 0.001,
        "stability": 0.001,
        "doc_alignment": 0.8,
    },
    "sample": {
        "support": 0.25,
        "predictive_strength": 0.30,
        "determinism": 0.20,
        "stability": 0.15,
        "doc_alignment": 0.10,
    },
    "diagnosis": {
        "support": 0.25,
        "predictive_strength": 0.0,
        "determinism": 0.00,
        "stability": 0.05,
        "doc_alignment": 0.10,
    },
    "file": {
        "support": 0.20,
        "predictive_strength": 0.20,
        "determinism": 0.20,
        "stability": 0.10,
        "doc_alignment": 0.20,
    },
    "study": {
        "support": 0.20,
        "predictive_strength": 0.20,
        "determinism": 0.15,
        "stability": 0.20,
        "doc_alignment": 0.25,
    },
}

node_substring_weights = {
    "human_relevance": {
        "support": 0.10,
        "prefix_match": 0.02,
        "suffix_match": 0.02,
        "substring_match": 0.05,
        "doc_alignment": 0.05,
    },
    "sample": {
        "support": 0.10,
        "prefix_match": 0.0,
        "suffix_match": 0.0,
        "substring_match": 0.0,
        "doc_alignment": 0.05,
    },
    "file": {
        "support": 0.15,
        "prefix_match": 0.25,
        "suffix_match": 0.30,
        "substring_match": 0.25,
        "doc_alignment": 0.05,
    },
     "case": {
        "support": 0.15,
        "prefix_match": 0.25,
        "suffix_match": 0.30,
        "substring_match": 0.25,
        "doc_alignment": 0.05,
    },
    "study": {
        "support": 0.10,
        "prefix_match": 0.30,
        "suffix_match": 0.30,
        "substring_match": 0.25,
        "doc_alignment": 0.05,
    },
}

node_cluster_weights = {
    "file": {
        "support": 0.20,
        "separation": 0.60,
        "doc_alignment": 0.20,
    },
}

cross_node_fuzzy = {
    "support": 0.15,
    "ratio": 0.10,
    "partial_ratio": 0.35,
    "token_sort_ratio": 0.20,
    "token_set_ratio": 0.15,
    "doc_alignment": 0.05,
}

node_features_2_weight = {
    "categorical": node_category_weights,
    "substring": node_substring_weights,
    "cluster": node_cluster_weights,
    "cross_node_fuzzy": cross_node_fuzzy
}