import gradio as gr
import pandas as pd
import copy, json

from feature.weights import (
    node_category_weights,
    node_substring_weights,
    node_cluster_weights,
    cross_node_fuzzy
)
FEATURES = ["categorical", "substring", "cluster", "cross_node_fuzzy"]

node_features_2_weight = {
    "categorical": node_category_weights,
    "substring": node_substring_weights,
    "cluster": node_cluster_weights,
    "cross_node_fuzzy": cross_node_fuzzy
}

def func(slider_1, slider_2, *args):
    return slider_1 + slider_2 * 5


def debug_weights(weights_state):
    for node, feature_map in weights_state.items():
        print(node, feature_map)
    return f"```json\n{json.dumps(weights_state, indent=2)}\n```"

def normalize_weights(weights: dict) -> dict:
    total = sum(weights.values())
    if total == 0:
        return {k: 0 for k in weights}
    return {k: v / total for k, v in weights.items()}

def check_total(*values):
    total = sum(values)

    if abs(total - 1.0) < 1e-6:
        return f"Total = {total:.3f}"
    else:
        return f"Total = {total:.3f} (should be 1.0)"

def normalize_and_update(*values):
    total = sum(values)

    if total == 0:
        normalized = [0] * len(values)
    else:
        normalized = [v / total for v in values]

    # slider updates
    slider_updates = [gr.update(label=v) for v in normalized]

    updates = []
    for i, v in enumerate(normalized):
        updates.append(
            gr.update(
                value=v,
                label=f"attr {i} ({v:.3f})"   # ✅ updated label
            )
        )

    return slider_updates

def normalize(values):
    total = sum(values)
    if total == 0:
        return [0.0] * len(values)
    return [v / total for v in values]

# def update_normalized_labels(node: str, feature: str, *values, feature_names=None):
#     norm_vals = normalize(values)
#     return [f"Normalized: {v:.3f}" for v in norm_vals]

def update_single_weight_state(raw_state, normalized_state, node, feature, weight_key, new_value):
    raw_state = copy.deepcopy(raw_state or {})
    normalized_state = copy.deepcopy(normalized_state or {})

    # raw_state shape: {feature: {node: {weight_key: value}}}
    raw_state.setdefault(feature, {})
    raw_state[feature].setdefault(node, {})
    raw_state[feature][node][weight_key] = float(new_value)

    # normalize only this node/feature group
    group = raw_state[feature][node]
    total = sum(group.values())
    norm_group = {
        k: (v / total if total else 0.0)
        for k, v in group.items()
    }

    normalized_state.setdefault(feature, {})
    normalized_state[feature].setdefault(node, {})
    normalized_state[feature][node].update(norm_group)

    return raw_state, normalized_state, f"Normalized: {norm_group[weight_key]:.3f}"

def update_normalized_state(
    node: str,
    feature: str,
    weights: dict,
    *values,
    feature_names=None):
    """
    values = current raw slider values for one node/feature group
    returns:
      1) updated normalized dict for state
      2) markdown labels for normalized values
    """
    total = sum(values)
    if total == 0:
        normalized = [0.0] * len(values)
    else:
        normalized = [v / total for v in values]

    # build: {node: {feature: {key: normalized_value}}}
    normalized_dict = {
        node: {
            feature: {
                feature_names[i]: normalized[i] for i in range(len(normalized))
            }
        }
    }

    try:
        copy_weights = copy.deepcopy(weights)
        copy_weights[feature][node] = {
            feature_names[i]: values[i] for i in range(len(values))
        }
    except Exception as e:
        print(f"error on {feature} / {node}: {e}")


    labels = [f"Normalized: {v:.3f}" for v in normalized]
    return (gr.State(copy_weights), normalized_dict, *labels)

def view_feature_weights(node_list_state, weights_state, normalized_weights_state):
    with gr.Accordion("## Adjust weights", open=True):
        @gr.render(inputs=[node_list_state])
        def _render(node_list):
            if not node_list:
                gr.Markdown("No nodes available yet.")
                return
            for node in node_list:
                with gr.Accordion(f"##{node}", open=False):
                    with gr.Row():
                        for index, feature in enumerate(FEATURES):
                            weights = node_features_2_weight.get(feature, {})
                            # print(weights)
                            if not weights:
                                continue
                            node_weights = weights.get(node, {})
                            norm_vals = normalize_weights(node_weights)
                            feature_names = list(node_weights.keys())
                            sliders = []
                            norm_outputs = []
                            with gr.Column(scale=1, min_width=0, elem_classes=["col-max"]):
                                gr.Markdown(f"{feature}")
                                # gr.Markdown(f"{norm_outputs}")
                                for key in node_weights:
                                    value = node_weights[key]
                                    s = gr.Slider(
                                        minimum=0,
                                        maximum=1,
                                        value=value,
                                        interactive=True,
                                        label=f"{key}",
                                        key=f"{node}_{feature}_{key}"
                                    )
                                    sliders.append(s)
                                    md = gr.Markdown(f"Normalized: {norm_vals[key]:.3f}")
                                    norm_outputs.append(md)

                                    s.input(
                                        fn=lambda new_value, rs, ns, n=node, f=feature, k=key: update_single_weight_state(
                                            rs, ns, n, f, k, new_value
                                        ),
                                        inputs=[s, weights_state, normalized_weights_state],
                                        outputs=[weights_state, normalized_weights_state, md],
                                    )
                                
                            # for s in sliders:
                            #     s.input(
                            #         fn=lambda *vals, n=node, f=feature, w=weights, names=feature_names: update_normalized_state(
                            #             n, f, w, *vals, feature_names=names
                            #         ),
                            #         inputs=sliders,
                            #         outputs=[weights_state, normalized_weights_state, *norm_outputs],
                            #     )
    with gr.Accordion("## View weights in JSON", open=False):
        debug_btn = gr.Button("view weights")
        debug_box = gr.Markdown("Debug output will appear here")
        debug_btn.click(
            fn=debug_weights,
            inputs=[weights_state],
            outputs=[debug_box],
        )

    return weights_state, normalized_weights_state
  