"""Synonym helpers and GOST patterns for price-row matching."""

from __future__ import annotations

import json
from pathlib import Path

GOST_PATTERNS: list[str] = [
    r"ГОСТ(?:\s)?\d+-\d+",
    r"ГОСТ(?:\s)?Р(?:\s)?\d+-\d+",
    r"ТУ(?:\s)?\d+-\d+-\d+-\d+",
    r"\bОСТ(?:\s)?(?:\d+ )?[\.\d\-]+",
]

SYN: list[list[str]] = [
    ["лист", "прокат"],
    ["пруток", "круг"],
    ["ткань", "стеклоткань"],
    ["нить", "филамент"],
    ["Ст10", "10-", "10сп", "10пс"],
    ["Ст20", "20-", "20сп", "20пс"],
    ["Ст25", "25-", "25сп", "25пс"],
    ["Ст30", "30-", "30сп", "30пс"],
    ["Ст35", "35-", "35сп", "35пс"],
    ["Ст40", "40-", "40сп", "40пс"],
    ["Ст45", "45-", "45сп", "45пс"],
    ["65Г", "65Г-"],
    ["Т10", "Т-10"],
    ["Т11", "Т-11"],
    ["Т13", "Т-13"],
    ["Т15", "Т-15"],
    ["Т23", "Т-23"],
    ["Т25", "Т-25"],
    ["Т64", "Т-64"],
    ["ТС-8/3-К", "ТС8/3к"],
    ["КТ11", "КТ-11"],
    ["м", "п/м", "пог. м"],
]


def get_casefolded_syn_list(word: str, synonyms: list[list[str]] | None = None) -> list[str]:
    synonyms = synonyms or SYN
    word_ = word.casefold()
    templates: list[str] = [word_]
    synonyms_ = [[i.casefold() for i in sg] for sg in synonyms]
    for syn_group in synonyms_:
        if word_ in syn_group:
            templates += syn_group
    return list(dict.fromkeys(templates))


def add_comma_point_syns(word_list: list[str]) -> list[str]:
    res: list[str] = []
    for t in word_list:
        res.append(t)
        if "," in t:
            res.append(t.replace(",", "."))
        if "." in t:
            res.append(t.replace(".", ","))
    return res


def load_gost_forms() -> dict[str, dict[str, str]]:
    path = Path(__file__).resolve().parent / "data" / "gost_by_form.json"
    with path.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    return {
        form.casefold(): {
            std.replace(" ", "").casefold(): desc for std, desc in forms.items()
        }
        for form, forms in raw.items()
    }
