"""Count completed tuning runs."""


def count_runs(log_text: str, mind: str) -> int:
    return sum(line.startswith('- run') and f' mind={mind} ' in line
               for line in log_text.splitlines())


def check_budget(log_text: str, mind: str, budget: int = 20) -> None:
    if count_runs(log_text, mind) >= budget:
        raise ValueError(f'{mind}: tuning budget of {budget} runs exhausted')
