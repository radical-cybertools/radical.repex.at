# content of conftest.py
import pytest

def pytest_addoption(parser):
    parser.addoption("--cmdopt", action="store", default="type1",
        help="Input file name")

@pytest.fixture
def cmdopt(request):
    return request.config.getoption("--cmdopt")
