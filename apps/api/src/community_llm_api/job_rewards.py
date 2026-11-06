from __future__ import annotations

from community_llm_protocol import JobKind

JOB_REWARDS: dict[JobKind, int] = {
    JobKind.BENCHMARK: 10,
    JobKind.EVAL: 20,
    JobKind.LORA_FINETUNE: 50,
}


def reward_for(kind: str) -> int:
    return JOB_REWARDS[JobKind(kind)]
