"""Unit tests for configuration manager."""

import json
from pathlib import Path
from ratana_island.config import AppConfig, IslandDimensions


def test_default_config():
    cfg = AppConfig()
    assert cfg.dimensions.compact_width == 280
    assert cfg.dimensions.compact_height == 38
    assert cfg.dimensions.expanded_width == 460
    assert cfg.dimensions.expanded_height == 230
    assert cfg.dimensions.notification_width == 360
    assert cfg.dimensions.notification_height == 44
    assert cfg.dimensions.margin_top == 5
    assert cfg.media.enable_lyrics is True
    assert cfg.media.auto_media_expand is False
    assert cfg.system.volume_step == 5
    assert cfg.appearance.theme == "mac_obsidian"
    assert cfg.appearance.notification_expansion is True
    assert cfg.appearance.double_click_action == "play_pause"


def test_config_save_and_load(tmp_path: Path):
    config_file = tmp_path / "config.json"
    cfg = AppConfig()
    cfg.dimensions.compact_width = 320
    cfg.dimensions.expanded_width = 500
    cfg.media.sync_tolerance_ms = 400
    cfg.appearance.reduced_motion = True

    cfg.save(config_file)
    assert config_file.exists()

    loaded = AppConfig.load(config_file)
    assert loaded.dimensions.compact_width == 320
    assert loaded.dimensions.expanded_width == 500
    assert loaded.media.sync_tolerance_ms == 400
    assert loaded.appearance.reduced_motion is True


def test_config_clamping_and_validation(tmp_path: Path):
    config_file = tmp_path / "bad_config.json"
    bad_data = {
        "dimensions": {
            "compact_width": 99999,  # Should clamp to 800
            "compact_height": 2,     # Should clamp to 24
            "margin_top": -10,       # Should clamp to 0
        },
        "media": {
            "sync_tolerance_ms": 10, # Should clamp to 50
        },
        "system": {
            "volume_step": 100,      # Should clamp to 25
        }
    }
    config_file.write_text(json.dumps(bad_data), encoding="utf-8")

    loaded = AppConfig.load(config_file)
    assert loaded.dimensions.compact_width == 800
    assert loaded.dimensions.compact_height == 24
    assert loaded.dimensions.margin_top == 0
    assert loaded.media.sync_tolerance_ms == 50
    assert loaded.system.volume_step == 25


def test_corrupted_config_fallback(tmp_path: Path):
    config_file = tmp_path / "corrupt.json"
    config_file.write_text("{ not valid json !!! }", encoding="utf-8")

    loaded = AppConfig.load(config_file)
    assert loaded.dimensions.compact_width == 280
