import asyncio

from polymind.models import PolymindOutput, DebateRound, ProviderResponse, StreamEvent
from polymind.config import ProviderConfig
from polymind.providers import get_provider
from polymind.orchestrator import run_provider_stream


async def run_debate(
    first_round: PolymindOutput,
    provider_configs: list[ProviderConfig],
) -> PolymindOutput:
    successful = [r for r in first_round.responses if not r.error]
    if len(successful) < 2:
        first_round.debate = [DebateRound(round=1, responses=first_round.responses)]
        return first_round

    round1 = DebateRound(round=1, responses=first_round.responses)
    critiques: list[ProviderResponse] = []

    tasks = []
    for r in successful:
        other_responses = [sr for sr in successful if sr.provider != r.provider]
        critique_prompt = _build_critique_prompt(
            original_question=first_round.question,
            own_response=r.content,
            other_responses={sr.provider: sr.content for sr in other_responses},
        )
        pc = _find_config(provider_configs, r.provider)
        if pc:
            tasks.append(_critique_task(pc, critique_prompt))

    if tasks:
        results = await asyncio.gather(*tasks)
        critiques = [r for r in results if r is not None]

    round2 = DebateRound(round=2, responses=first_round.responses, critiques=critiques)
    first_round.debate = [round1, round2]
    return first_round


def _build_critique_prompt(
    original_question: str,
    own_response: str,
    other_responses: dict[str, str],
) -> str:
    lines = [
        f"Original question: {original_question}",
        f"\nYour previous answer:\n{own_response[:2000]}",
        "\nOther providers' answers to critique:",
    ]
    for provider, response in other_responses.items():
        lines.append(f"\n--- {provider.upper()} ---\n{response[:2000]}")
    lines.append(
        "\n\nTask: Critique the other providers' answers. For each: "
        "1) What did they get right? 2) What did they miss or get wrong? "
        "3) How does their approach differ from yours? "
        "Be specific and constructive."
    )
    return "\n".join(lines)


def _find_config(configs: list[ProviderConfig], name: str) -> ProviderConfig | None:
    for c in configs:
        if c.name == name:
            return c
    return None


async def _critique_task(pc: ProviderConfig, prompt: str) -> ProviderResponse | None:
    provider = get_provider(pc.name, pc)
    if provider is None:
        return None
    return await provider.run(prompt)
