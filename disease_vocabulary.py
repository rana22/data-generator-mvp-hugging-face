from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

import pandas as pd

from config import DiseaseGenerationConfig

ALL_LOADED_MODE = "All loaded source data"


class DiseaseRequestStatus(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED_DISEASE = "unsupported_disease"
    INSUFFICIENT_NODE_DATA = "insufficient_node_data"
    UNSCOPABLE_NODE = "unscopable_node"
    ALL_LOADED = "all_loaded"
    INVALID_REQUEST = "invalid_request"


@dataclass(frozen=True)
class DiseaseRequestResult:
    status: DiseaseRequestStatus
    requested_disease: str | None
    canonical_disease: str | None
    selected_node: str | None
    supported_terms: tuple[str, ...]
    selected_node_row_count: int | None
    node_row_counts: Mapping[str, int | None]
    message: str

    @property
    def can_generate(self) -> bool:
        return self.status in {
            DiseaseRequestStatus.SUPPORTED,
            DiseaseRequestStatus.ALL_LOADED,
        }

    @property
    def is_disease_specific(self) -> bool:
        return self.status == DiseaseRequestStatus.SUPPORTED


def clean_disease_term(value: Any) -> str:
    """Return display text with surrounding/repeated whitespace removed."""
    if value is None:
        return ""

    try:
        if pd.api.types.is_scalar(value) and bool(pd.isna(value)):
            return ""
    except (TypeError, ValueError):
        pass

    return " ".join(str(value).split())


def normalize_disease_term(value: Any, scope_config: DiseaseGenerationConfig) -> str:
    """Return a conservative exact-match key for a disease term."""
    cleaned = clean_disease_term(value)
    normalized = cleaned.casefold()
    if normalized in scope_config.missing_terms:
        return ""
    return normalized


def _get_node_frame(
    data_state: Mapping[str, pd.DataFrame] | None,
    node_name: str | None,
) -> pd.DataFrame | None:
    if not data_state or not node_name:
        return None

    requested_key = str(node_name).strip().casefold()
    for key, frame in data_state.items():
        if str(key).strip().casefold() == requested_key:
            return frame if isinstance(frame, pd.DataFrame) else None
    return None


def extract_supported_diseases(
    data_state: Mapping[str, pd.DataFrame] | None,
    scope_config: DiseaseGenerationConfig | None,
) -> tuple[str, ...]:
    """Extract deterministic canonical terms using a project's vocabulary mapping."""
    if scope_config is None:
        return ()

    vocabulary_df = _get_node_frame(data_state, scope_config.vocabulary_node)
    vocabulary_property = scope_config.vocabulary_property
    if (
        vocabulary_df is None
        or vocabulary_df.empty
        or vocabulary_property not in vocabulary_df.columns
    ):
        return ()

    variants_by_key: dict[str, Counter[str]] = {}
    for value in vocabulary_df[vocabulary_property]:
        normalized = normalize_disease_term(value, scope_config)
        if not normalized:
            continue
        display = clean_disease_term(value)
        variants_by_key.setdefault(normalized, Counter())[display] += 1

    canonical_terms: list[str] = []
    for variants in variants_by_key.values():
        canonical = sorted(
            variants.items(),
            key=lambda item: (-item[1], item[0].casefold(), item[0]),
        )[0][0]
        canonical_terms.append(canonical)

    return tuple(sorted(canonical_terms, key=lambda term: (term.casefold(), term)))


def resolve_supported_disease(
    requested_disease: Any,
    supported_terms: tuple[str, ...],
    scope_config: DiseaseGenerationConfig,
) -> str | None:
    requested_key = normalize_disease_term(requested_disease, scope_config)
    if not requested_key:
        return None
    return next(
        (
            term
            for term in supported_terms
            if normalize_disease_term(term, scope_config) == requested_key
        ),
        None,
    )


def format_supported_diseases(supported_terms: tuple[str, ...]) -> str:
    if not supported_terms:
        return "None are available in the currently loaded vocabulary data."
    return ", ".join(supported_terms)


def _format_node_counts(node_counts: Mapping[str, int | None]) -> str:
    parts = []
    for node, count in node_counts.items():
        if count is None:
            parts.append(f'{node}: unavailable (no reliable disease linkage)')
        else:
            parts.append(f"{node}: {count}")
    return "; ".join(parts)


def _vocabulary_count(
    data_state: Mapping[str, pd.DataFrame] | None,
    canonical_disease: str,
    scope_config: DiseaseGenerationConfig,
) -> int:
    vocabulary_df = _get_node_frame(data_state, scope_config.vocabulary_node)
    vocabulary_property = scope_config.vocabulary_property
    if (
        vocabulary_df is None
        or vocabulary_df.empty
        or vocabulary_property not in vocabulary_df.columns
    ):
        return 0
    canonical_key = normalize_disease_term(canonical_disease, scope_config)
    return int(
        vocabulary_df[vocabulary_property]
        .map(lambda value: normalize_disease_term(value, scope_config))
        .eq(canonical_key)
        .sum()
    )


def prepare_generation_rows(
    data_state: Mapping[str, pd.DataFrame] | None,
    selected_node: str | None,
    generation_mode: str | None,
    requested_disease: Any = None,
    scope_config: DiseaseGenerationConfig | None = None,
    project_name: str | None = None,
    *,
    min_node_rows: int | None = None,
) -> tuple[DiseaseRequestResult, pd.DataFrame | None]:
    """Validate a request and return only rows proven safe for its generation mode."""
    supported_terms = extract_supported_diseases(data_state, scope_config)
    requested_text = clean_disease_term(requested_disease) or None
    selected_df = _get_node_frame(data_state, selected_node)
    node_name = clean_disease_term(selected_node) or None
    mode = clean_disease_term(generation_mode)

    if not mode:
        result = DiseaseRequestResult(
            status=DiseaseRequestStatus.INVALID_REQUEST,
            requested_disease=requested_text,
            canonical_disease=None,
            selected_node=node_name,
            supported_terms=supported_terms,
            selected_node_row_count=None,
            node_row_counts={},
            message="Choose a generation mode before generating data.",
        )
        return result, None

    disease_specific_mode = (
        scope_config.disease_specific_mode if scope_config is not None else None
    )
    if mode != ALL_LOADED_MODE and mode != disease_specific_mode:
        project_label = clean_disease_term(project_name) or "this project"
        if scope_config is None:
            message = (
                f'Disease-specific generation is not configured for "{project_label}". '
                f'Select "{ALL_LOADED_MODE}" to continue without disease-specific claims.'
            )
        else:
            message = "Choose a valid generation mode before generating data."
        result = DiseaseRequestResult(
            status=DiseaseRequestStatus.INVALID_REQUEST,
            requested_disease=requested_text,
            canonical_disease=None,
            selected_node=node_name,
            supported_terms=supported_terms,
            selected_node_row_count=None,
            node_row_counts={},
            message=message,
        )
        return result, None

    if not node_name:
        result = DiseaseRequestResult(
            status=DiseaseRequestStatus.INVALID_REQUEST,
            requested_disease=requested_text,
            canonical_disease=None,
            selected_node=None,
            supported_terms=supported_terms,
            selected_node_row_count=None,
            node_row_counts={},
            message="Select a node before generating data.",
        )
        return result, None

    if mode == ALL_LOADED_MODE:
        if selected_df is None or selected_df.empty:
            result = DiseaseRequestResult(
                status=DiseaseRequestStatus.INSUFFICIENT_NODE_DATA,
                requested_disease=None,
                canonical_disease=None,
                selected_node=node_name,
                supported_terms=supported_terms,
                selected_node_row_count=0,
                node_row_counts={node_name: 0},
                message=f'No loaded source rows are available for "{node_name}".',
            )
            return result, None

        row_count = len(selected_df)
        result = DiseaseRequestResult(
            status=DiseaseRequestStatus.ALL_LOADED,
            requested_disease=None,
            canonical_disease=None,
            selected_node=node_name,
            supported_terms=supported_terms,
            selected_node_row_count=row_count,
            node_row_counts={node_name: row_count},
            message=(
                f'No disease was requested. The generator will use all {row_count} loaded '
                f'"{node_name}" source rows. The output should not be treated as disease-specific.'
            ),
        )
        return result, selected_df.copy().reset_index(drop=True)

    if not requested_text:
        result = DiseaseRequestResult(
            status=DiseaseRequestStatus.INVALID_REQUEST,
            requested_disease=None,
            canonical_disease=None,
            selected_node=node_name,
            supported_terms=supported_terms,
            selected_node_row_count=None,
            node_row_counts={},
            message="Select or enter a disease for disease-specific generation.",
        )
        return result, None

    # A non-all-loaded mode can reach this point only with a configured project.
    assert scope_config is not None
    canonical_disease = resolve_supported_disease(
        requested_text,
        supported_terms,
        scope_config,
    )
    if canonical_disease is None:
        result = DiseaseRequestResult(
            status=DiseaseRequestStatus.UNSUPPORTED_DISEASE,
            requested_disease=requested_text,
            canonical_disease=None,
            selected_node=node_name,
            supported_terms=supported_terms,
            selected_node_row_count=None,
            node_row_counts={},
            message=(
                f'{scope_config.source_label} does not currently have validated source data for '
                f'"{requested_text}", '
                "so this tool cannot generate disease-specific example files for that disease.\n\n"
                f"Supported {scope_config.source_label}-derived disease terms are: "
                f"{format_supported_diseases(supported_terms)}\n\n"
                "To proceed, choose a supported disease term or submit validated study data first "
                f"so the {scope_config.source_label} vocabulary can be updated."
            ),
        )
        return result, None

    vocabulary_count = _vocabulary_count(data_state, canonical_disease, scope_config)
    node_counts: dict[str, int | None] = {
        scope_config.vocabulary_node: vocabulary_count
    }

    if selected_df is None or selected_df.empty:
        node_counts[node_name] = 0
        result = DiseaseRequestResult(
            status=DiseaseRequestStatus.INSUFFICIENT_NODE_DATA,
            requested_disease=requested_text,
            canonical_disease=canonical_disease,
            selected_node=node_name,
            supported_terms=supported_terms,
            selected_node_row_count=0,
            node_row_counts=node_counts,
            message=(
                f'"{canonical_disease}" exists in the {scope_config.source_label} disease '
                "vocabulary, but there are no "
                f'loaded "{node_name}" rows available for disease-specific generation.\n\n'
                f"Available node support for this disease: {_format_node_counts(node_counts)}."
            ),
        )
        return result, None

    scope_property = scope_config.scope_property_for_node(node_name)
    if scope_property is None or scope_property not in selected_df.columns:
        if node_name.casefold() not in node_counts:
            node_counts[node_name] = None
        result = DiseaseRequestResult(
            status=DiseaseRequestStatus.UNSCOPABLE_NODE,
            requested_disease=requested_text,
            canonical_disease=canonical_disease,
            selected_node=node_name,
            supported_terms=supported_terms,
            selected_node_row_count=None,
            node_row_counts=node_counts,
            message=(
                f'"{canonical_disease}" exists in the {scope_config.source_label} disease '
                "vocabulary, but the loaded "
                f'"{node_name}" rows cannot be reliably associated with that disease. '
                "Disease-specific generation has been declined rather than using all loaded rows.\n\n"
                f"Available node support for this disease: {_format_node_counts(node_counts)}."
            ),
        )
        return result, None

    canonical_key = normalize_disease_term(canonical_disease, scope_config)
    mask = selected_df[scope_property].map(
        lambda value: normalize_disease_term(value, scope_config)
    ).eq(canonical_key)
    scoped_df = selected_df.loc[mask].copy().reset_index(drop=True)
    row_count = len(scoped_df)
    node_counts[node_name] = row_count

    configured_minimum = scope_config.minimum_node_rows
    minimum = max(
        1,
        int(configured_minimum if min_node_rows is None else min_node_rows),
    )
    if row_count < minimum:
        result = DiseaseRequestResult(
            status=DiseaseRequestStatus.INSUFFICIENT_NODE_DATA,
            requested_disease=requested_text,
            canonical_disease=canonical_disease,
            selected_node=node_name,
            supported_terms=supported_terms,
            selected_node_row_count=row_count,
            node_row_counts=node_counts,
            message=(
                f'"{canonical_disease}" exists in the {scope_config.source_label} disease '
                "vocabulary, but there are not "
                f'enough validated "{node_name}" rows associated with that disease to generate '
                f"reliable examples. At least {minimum} rows are required.\n\n"
                f"Available node support for this disease: {_format_node_counts(node_counts)}."
            ),
        )
        return result, None

    result = DiseaseRequestResult(
        status=DiseaseRequestStatus.SUPPORTED,
        requested_disease=requested_text,
        canonical_disease=canonical_disease,
        selected_node=node_name,
        supported_terms=supported_terms,
        selected_node_row_count=row_count,
        node_row_counts=node_counts,
        message=(
            f'Generating {scope_config.source_label}-derived disease-specific examples for '
            f'"{canonical_disease}" '
            f'from {row_count} verified "{node_name}" source rows.'
        ),
    )
    return result, scoped_df
