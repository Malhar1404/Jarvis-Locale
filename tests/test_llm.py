from jarvis import config
from jarvis.llm import make_llm


def test_default_model_is_the_instruct_variant():
    assert config.MODEL == "qwen3:4b-instruct"


def test_reasoning_is_unset_by_default():
    assert make_llm().reasoning is None


def test_reasoning_can_be_overridden():
    assert make_llm(reasoning=True).reasoning is True
