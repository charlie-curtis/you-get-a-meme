from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE_PATH = PROJECT_ROOT / "data" / "templates.txt"


@dataclass(frozen=True)
class MemeTemplate:
    id: str
    name: str
    description: str
    caption_pattern: str
    box_labels: tuple[str, ...]
    tags: tuple[str, ...]
    box_count: int

    @property
    def embedding_text(self) -> str:
        tags = ", ".join(self.tags)
        return (
            f"{self.name}. {self.description} "
            f"Caption pattern: {self.caption_pattern} "
            f"Box labels: {', '.join(self.box_labels)}. "
            f"Tags: {tags}. Text boxes: {self.box_count}."
        )

    @property
    def prompt_line(self) -> str:
        return (
            f"- {self.name}: {self.description} "
            f"Caption pattern: {self.caption_pattern} "
            f"Box labels, in order: {', '.join(self.box_labels)}. "
            f"Text boxes: {self.box_count}. Tags: {', '.join(self.tags)}"
        )


def load_templates(path: Path = DEFAULT_TEMPLATE_PATH) -> list[MemeTemplate]:
    parser = configparser.ConfigParser()
    parser.read(path)

    templates = []
    for template_id in parser.sections():
        section = parser[template_id]
        templates.append(
            MemeTemplate(
                id=template_id,
                name=section["name"].strip(),
                description=section["description"].strip(),
                caption_pattern=section["caption_pattern"].strip(),
                box_labels=tuple(
                    label.strip() for label in section.get("box_labels", "").split(",") if label.strip()
                ),
                tags=tuple(tag.strip() for tag in section.get("tags", "").split(",") if tag.strip()),
                box_count=section.getint("box_count", fallback=2),
            )
        )

    return templates
