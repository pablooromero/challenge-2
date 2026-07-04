from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agent.prompting.catalog import PROMPT_SPECS
from app.agent.prompting.client import get_langfuse_prompt_client


def main() -> None:
    client = get_langfuse_prompt_client()
    if client is None:
        raise SystemExit(
            "Langfuse credentials are not configured. Set LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY and LANGFUSE_HOST."
        )

    for spec in PROMPT_SPECS.values():
        prompt = client.create_prompt(
            name=spec.name,
            prompt=spec.prompt,
            labels=list(spec.labels),
            type=spec.prompt_type,
            commit_message=spec.commit_message,
        )
        print(
            f"Synced prompt {prompt.name} version={prompt.version} labels={','.join(prompt.labels)}"
        )

    client.flush()


if __name__ == "__main__":
    main()
