import pytest
import httpx
import respx


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_httpx():
    """Activate respx router for mocking httpx calls."""
    with respx.mock(assert_all_called=False) as router:
        yield router
