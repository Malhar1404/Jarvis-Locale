import jarvis
from jarvis import config


def test_package_imports():
    assert jarvis.__version__


def test_default_model_is_set():
    assert config.MODEL
