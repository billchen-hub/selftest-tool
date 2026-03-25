import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def simple_script(fixtures_dir):
    return fixtures_dir / "simple_script.py"


@pytest.fixture
def branching_script(fixtures_dir):
    return fixtures_dir / "branching_script.py"


@pytest.fixture
def random_script(fixtures_dir):
    return fixtures_dir / "random_script.py"


@pytest.fixture
def multi_function_script(fixtures_dir):
    return fixtures_dir / "multi_function_script.py"
