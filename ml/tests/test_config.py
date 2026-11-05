from pathlib import Path

from community_llm_ml.evaluation.run_eval import load_config as load_eval_config
from community_llm_ml.training.train_lora import load_config

CONFIGS = Path(__file__).resolve().parents[1] / "configs"


def test_training_config() -> None:
    config = load_config(CONFIGS / "lora-smoke.yaml")
    assert config["base_model"]["id"] == "ibm-granite/granite-4.1-3b"


def test_eval_config() -> None:
    config = load_eval_config(CONFIGS / "eval-smoke.yaml")
    assert "safety" in config["tasks"]
