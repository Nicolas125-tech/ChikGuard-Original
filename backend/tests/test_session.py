from unittest.mock import patch, MagicMock
from src.db.session import get_db

@patch("src.db.session.SessionLocal")
def test_get_db_success(mock_session_local):
    """
    Test the happy path where the db session is yielded and properly closed.
    """
    # Setup mock
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    # get_db is a generator
    db_gen = get_db()

    # Get the db instance yielded
    db = next(db_gen)
    assert db == mock_db

    # Verify close has not been called yet
    mock_db.close.assert_not_called()

    # Resume generator to trigger finally block
    try:
        next(db_gen)
    except StopIteration:
        pass

    # Verify close was called
    mock_db.close.assert_called_once()

@patch("src.db.session.SessionLocal")
def test_get_db_exception(mock_session_local):
    """
    Test the error path where an exception is thrown in the context using the session,
    ensuring the finally block still closes the session.
    """
    # Setup mock
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    # get_db is a generator
    db_gen = get_db()

    # Get the db instance yielded
    db = next(db_gen)
    assert db == mock_db

    # Verify close has not been called yet
    mock_db.close.assert_not_called()

    # Simulate an exception in the calling context
    try:
        db_gen.throw(ValueError("Test exception"))
    except ValueError:
        pass

    # Verify close was STILL called due to the finally block
    mock_db.close.assert_called_once()
