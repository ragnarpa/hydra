import pytest
import random
import typing


@pytest.fixture
def random_str() -> typing.Callable:
    return lambda: str(random.random())[2:]


@pytest.fixture
def random_int() -> typing.Callable:
    return lambda: random.randint(0, 100000)