import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.plugins.manager import PluginManager, LoadedPlugin

def test_plugin_discovery_error():
    mock_logger = MagicMock()
    manager = PluginManager(plugins_root="/tmp/fake_plugins_dir", logger=mock_logger)

    with patch("os.path.isdir", return_value=True):
        with patch("os.listdir", return_value=["test_plugin"]):
            with patch("os.path.isfile", return_value=True):
                with patch("importlib.util.spec_from_file_location", side_effect=Exception("Import failed")):
                    manager.load_all({"some": "context"})

                    assert len(manager._plugins) == 1
                    assert manager._plugins[0].enabled == False
                    assert manager._plugins[0].error == "Import failed"
                    mock_logger.exception.assert_called_once()
