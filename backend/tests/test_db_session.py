import sys

if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import sys
import unittest.mock as mock
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.db.session import get_db

# Ensure cv2 is mocked if any imports trigger it (per memory instructions)
sys.modules["cv2"] = mock.MagicMock()




def test_get_db_yields_session_and_closes():
    with patch("src.infrastructure.db.session.SessionLocal") as mock_session_local:
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
    with patch("src.infrastructure.db.session.SessionLocal") as mock_session_local:
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        db_gen = get_db()

        next(db_gen)

        with pytest.raises(ValueError, match="Test error"):
            db_gen.throw(ValueError("Test error"))

        mock_session.close.assert_called_once()
