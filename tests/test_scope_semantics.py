from comfyreview.providers import OutputFileUrlMapper
from services.context_filters import (
    infer_set_key_from_png_path,
    is_empty_character_subdir,
    matches_character_scope,
    matches_set_filter,
    normalize_scope_subdir,
    resolve_assigned_set_key,
)


def test_all_character_scope_excludes_empty():
    assert (
        matches_character_scope(
            item_subdir="playground/Aiko", selected_subdir=""
        )
        is True
    )
    assert (
        matches_character_scope(
            item_subdir="playground/Empty", selected_subdir=""
        )
        is False
    )


def test_explicit_empty_character_scope_is_allowed():
    assert is_empty_character_subdir("playground/Empty") is True
    assert (
        matches_character_scope(
            item_subdir="playground/Empty", selected_subdir="playground/Empty"
        )
        is True
    )


def test_deep_playground_scope_collapses_to_character_scope():
    assert normalize_scope_subdir(r"playground\Aiko\pose") == "playground/Aiko"
    assert (
        matches_character_scope(
            item_subdir="playground/Aiko/pose",
            selected_subdir="playground/Aiko",
        )
        is True
    )


def test_png_path_to_url_uses_real_path_segments(tmp_path):
    p = str(tmp_path / "playground" / "Aiko" / "pose" / "img_1.png")
    mapper = OutputFileUrlMapper(tmp_path)
    assert mapper.to_url(p).endswith("/files/playground/Aiko/pose/img_1.png")


def test_set_assignment_falls_back_to_real_path_when_map_is_missing(tmp_path):
    p = str(tmp_path / "playground" / "Aiko" / "pose" / "img_1.png")
    options = {
        "output_root": tmp_path,
        "allowed_set_keys": ("pose",),
    }
    assert infer_set_key_from_png_path(p, **options) == "pose"
    assert (
        resolve_assigned_set_key(
            png_path=p,
            assigned_set_key=None,
            **options,
        )
        == "pose"
    )
    assert (
        matches_set_filter(
            selected_set_key="pose",
            assigned_set_key=None,
            png_path=p,
            **options,
        )
        is True
    )
    assert (
        matches_set_filter(
            selected_set_key="unsorted",
            assigned_set_key=None,
            png_path=p,
            **options,
        )
        is False
    )


def test_unsorted_filter_stays_visible_for_character_root_images(tmp_path):
    p = str(tmp_path / "playground" / "Aiko" / "img_1.png")
    options = {
        "output_root": tmp_path,
        "allowed_set_keys": ("pose",),
    }
    assert (
        resolve_assigned_set_key(
            png_path=p,
            assigned_set_key=None,
            **options,
        )
        is None
    )
    assert (
        matches_set_filter(
            selected_set_key="unsorted",
            assigned_set_key=None,
            png_path=p,
            **options,
        )
        is True
    )
