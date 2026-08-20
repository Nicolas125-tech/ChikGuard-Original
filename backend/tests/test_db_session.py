import pytest
from unittest.mock import MagicMock, patch

import sys
import unittest.mock as mock

# Ensure cv2 is mocked if any imports trigger it (per memory instructions)

from src.db.session import get_db

def test_get_db_yields_session_and_closes():
    with patch("src.db.session.SessionLocal") as mock_session_local:
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        db_gen = get_db()

        db = next(db_gen)

        assert db is mock_session

        mock_session_local.assert_called_once()
        mock_session.close.assert_not_called()

        with pytest.raises(StopIteration):
            next(db_gen)

        mock_session.close.assert_called_once()

def test_get_db_closes_session_on_exception():
    with patch("src.db.session.SessionLocal") as mock_session_local:
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        db_gen = get_db()

        db = next(db_gen)

        with pytest.raises(ValueError, match="Test error"):
            db_gen.throw(ValueError("Test error"))

        mock_session.close.assert_called_once()
