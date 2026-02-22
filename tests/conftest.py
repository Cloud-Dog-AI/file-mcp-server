from pathlib import Path

import pytest
from dotenv import load_dotenv


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--env",
        action="store",
        default=None,
        help="Path to env file (e.g. tests/env-UT)",
    )


@pytest.fixture(scope="session", autouse=True)
def load_env_files(pytestconfig: pytest.Config) -> None:
    env_path = pytestconfig.getoption("--env")
    if not env_path:
        pytest.fail("ERROR: --env parameter REQUIRED (e.g. --env tests/env-UT)")
    path = Path(env_path)
    if not path.exists():
        pytest.fail(f"ERROR: env file not found: {path}")
    load_dotenv(path, override=True)
