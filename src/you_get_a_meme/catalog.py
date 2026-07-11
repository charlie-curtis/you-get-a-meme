from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE_PATH = PROJECT_ROOT / "data" / "templates.txt"


IMAGES_DIR = PROJECT_ROOT / "data" / "images"


@dataclass(frozen=True)
class MemeTemplate:
    id: str
    name: str
    description: str
    caption_pattern: str
    box_labels: tuple[str, ...]
    humor_rule: str
    tags: tuple[str, ...]
    box_count: int
    image_url: str = ""
    tone: str = ""
    notes: str = ""

    @property
    def image_path(self) -> Path | None:
        for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            candidate = IMAGES_DIR / f"{self.id}{ext}"
            if candidate.exists():
                return candidate
        return None

    @property
    def embedding_text(self) -> str:
        tags = ", ".join(self.tags)
        parts = [
            f"{self.name}. {self.description}",
            f"Caption pattern: {self.caption_pattern}",
            f"Box labels: {', '.join(self.box_labels)}.",
        ]
        if self.humor_rule:
            parts.append(f"Humor rule: {self.humor_rule}")
        if self.tone:
            parts.append(f"Tone: {self.tone}.")
        parts.append(f"Tags: {tags}. Text boxes: {self.box_count}.")
        return " ".join(parts)

    @property
    def prompt_line(self) -> str:
        parts = [
            f"- {self.name}: {self.description}",
            f"Caption pattern: {self.caption_pattern}",
            f"Box labels, in order: {', '.join(self.box_labels)}.",
        ]
        if self.humor_rule:
            parts.append(f"Humor rule: {self.humor_rule}")
        if self.tone:
            parts.append(f"Tone: {self.tone}.")
        if self.notes:
            parts.append(f"Caption notes: {self.notes}")
        parts.append(f"Text boxes: {self.box_count}. Tags: {', '.join(self.tags)}")
        return " ".join(parts)


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
                humor_rule=section.get("humor_rule", "").strip(),
                tags=tuple(tag.strip() for tag in section.get("tags", "").split(",") if tag.strip()),
                box_count=section.getint("box_count", fallback=2),
                image_url=section.get("image_url", "").strip(),
                tone=section.get("tone", "").strip(),
                notes=section.get("notes", "").strip(),
            )
        )

    return templates
