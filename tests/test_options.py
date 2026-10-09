"""Settings survive damage, and presets and single downloads only touch what they may."""

from keepsake.options import (
    BUILT_IN_PRESETS,
    DEFAULTS,
    Options,
    per_job,
    preset_values,
    with_preset,
)


def test_a_damaged_settings_file_costs_only_the_damaged_settings() -> None:
    """Each wrong-typed value keeps its default; everything else loads."""
    loaded = Options.load(
        {
            "quality": "720",
            "concurrency": "5",
            "notify": "yes",
            "retries": True,
            "fragments": 8.0,
            "nonsense": 1,
            "folder": 12,
        }
    )
    assert loaded.quality == "720"
    assert loaded.concurrency == 5
    assert loaded.notify is Options().notify
    assert loaded.retries == Options().retries
    assert loaded.fragments == 8
    assert loaded.folder == Options().folder


def test_anything_that_is_not_a_record_is_the_defaults() -> None:
    """A settings file holding a list, or nothing, gives the defaults."""
    assert Options.load([1, 2]) == Options()
    assert Options.load(None) == Options()


def test_changes_are_checked_like_stored_values() -> None:
    """`but` goes through the same checks as loading."""
    changed = Options().but({"quality": "1080", "sound": "loud"})
    assert changed.quality == "1080"
    assert changed.sound is False


def test_a_preset_shapes_a_download_but_never_moves_it() -> None:
    """A preset may not change where files go or how Keepsake behaves."""
    applied = with_preset(Options(), {"mode": "audio", "folder": "C:/elsewhere", "notify": False})
    assert applied.mode == "audio"
    assert applied.folder == Options().folder
    assert applied.notify is True
    assert "folder" not in preset_values(Options())


def test_every_built_in_preset_is_made_of_real_settings() -> None:
    """A typo in a preset would silently do nothing."""
    for values in BUILT_IN_PRESETS.values():
        assert set(values) <= set(DEFAULTS)


def test_one_download_overrides_only_what_the_preview_offers() -> None:
    """The preview can pick a format or a folder, not turn off notifications."""
    extra = {"format": "22", "rename": "My clip", "notify": False, "concurrency": 9}
    chosen = per_job(Options(), extra)
    assert chosen.format == "22"
    assert chosen.rename == "My clip"
    assert chosen.notify is True
    assert chosen.concurrency == Options().concurrency
    assert per_job(Options(), "not a record") == Options()
