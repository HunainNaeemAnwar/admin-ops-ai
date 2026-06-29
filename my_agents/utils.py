from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "library"


def load_prompt(name: str, ctx: dict | None = None) -> str:
    path = PROMPTS_DIR / name
    if not path.suffix:
        path = path.with_suffix(".md")
    content = path.read_text(encoding="utf-8")
    if ctx:
        for k, v in ctx.items():
            content = content.replace("{{" + k + "}}", v)
    return content
