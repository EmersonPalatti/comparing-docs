from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from io import StringIO
from typing import Callable, Iterable

from src.models import Subject
from src.normalizer import normalize_text
from src.normalizer import normalize_subjects


WORKLOAD_RE = re.compile(r"(?P<hours>\d{1,4})\s*(?:h|horas|hrs)\b", re.IGNORECASE)
CREDITS_RE = re.compile(r"(?P<credits>\d+(?:[,.]\d+)?)\s*(?:cr[eé]ditos?|cred\.?)\b", re.IGNORECASE)
SYLLABUS_RE = re.compile(r"^(?:conte[uú]do|ementa|programa|syllabus)\s*:\s*(?P<value>.+)$", re.IGNORECASE)
SUBJECT_LABEL_RE = re.compile(r"^(?:disciplina|subject|componente curricular)\s*:\s*(?P<value>.+)$", re.IGNORECASE)
CODE_TABLE_RE = re.compile(
    r"^(?P<code>[A-Z]{2,5}\d{2,4})\s+(?P<middle>.*?)\s*(?P<hours>\d{1,4})h\s+"
    r"(?P<semester>\d+º)\s+(?P<grade>-|\d+(?:,\d+)?)\s+(?P<status>Aprovado|A cursar)\b(?P<trailing>.*)$",
    re.IGNORECASE,
)

CONNECTOR_WORDS = {"e", "à", "a", "ao", "de", "da", "do", "das", "dos"}
TABLE_HEADER_MARKERS = {
    "Código Disciplina CH Período Nota Situação",
    "resumida",
    "Ementa",
    "Histórico de disciplinas cursadas",
}
TABLE_END_MARKERS = {
    "Conteúdo programático simplificado",
    "Critérios sugeridos para análise de equivalência",
}
SUBJECT_CODE_RE = re.compile(r"\b[A-Z]{2,5}[-\s]?\d{2,4}\b")


@dataclass(frozen=True)
class ParsedLine:
    text: str
    index: int
    has_subject_code: bool
    has_workload: bool
    has_syllabus_label: bool
    looks_like_title: bool
    is_table_boundary: bool


ParseStrategy = Callable[[str, str], list[Subject]]


def extract_workload(text: str) -> int | None:
    match = WORKLOAD_RE.search(text)
    return int(match.group("hours")) if match else None


def extract_credits(text: str) -> float | None:
    match = CREDITS_RE.search(text)
    if not match:
        return None
    return float(match.group("credits").replace(",", "."))


def clean_subject_name(text: str) -> str:
    value = SUBJECT_LABEL_RE.sub(r"\g<value>", text).strip()
    value = WORKLOAD_RE.sub("", value)
    value = CREDITS_RE.sub("", value)
    value = re.sub(r"\s*[-–—|;]\s*$", "", value)
    value = re.split(r"\s[-–—|]\s", value, maxsplit=1)[0].strip()
    return re.sub(r"\s+", " ", value).strip(" ,-–—|;")


def is_subject_line(line: str) -> bool:
    if SYLLABUS_RE.match(line):
        return False
    return bool(WORKLOAD_RE.search(line) or SUBJECT_LABEL_RE.search(line))


def analyze_lines(text: str) -> list[ParsedLine]:
    return [analyze_line(line, index) for index, line in enumerate(iter_relevant_lines(text))]


def analyze_line(line: str, index: int) -> ParsedLine:
    return ParsedLine(
        text=line,
        index=index,
        has_subject_code=bool(SUBJECT_CODE_RE.search(line)),
        has_workload=bool(WORKLOAD_RE.search(line)),
        has_syllabus_label=bool(SYLLABUS_RE.match(line)),
        looks_like_title=bool(title_prefix(line)),
        is_table_boundary=is_table_end_line(line) or should_skip_table_line(line),
    )


def parse_csv_subjects(text: str, source_document: str) -> list[Subject]:
    try:
        reader = csv.DictReader(StringIO(text))
    except csv.Error:
        return []

    if not reader.fieldnames:
        return []

    field_map = {field.lower().strip(): field for field in reader.fieldnames}
    name_key = next(
        (field_map[key] for key in field_map if key in {"name", "subject", "disciplina", "componente curricular"}),
        None,
    )
    if not name_key:
        return []

    subjects: list[Subject] = []
    for row in reader:
        name = (row.get(name_key) or "").strip()
        if not name:
            continue
        workload = first_present(row, field_map, {"workload_hours", "workload", "carga horaria", "carga_horaria", "horas"})
        credits = first_present(row, field_map, {"credits", "creditos", "créditos"})
        syllabus = first_present(row, field_map, {"syllabus", "ementa", "conteudo", "conteúdo"})
        subjects.append(
            Subject(
                name=name,
                source_document=source_document,
                workload_hours=extract_workload(str(workload)) if workload else extract_workload(",".join(row.values())),
                credits=extract_credits(str(credits)) if credits else extract_credits(",".join(row.values())),
                syllabus=str(syllabus).strip() if syllabus else None,
                raw_text=", ".join(f"{key}: {value}" for key, value in row.items() if value),
            )
        )
    return subjects


def first_present(row: dict[str, str], field_map: dict[str, str], names: set[str]) -> str | None:
    for normalized, original in field_map.items():
        if normalized in names and row.get(original):
            return row[original]
    return None


def parse_text_subjects(text: str, source_document: str) -> list[Subject]:
    subjects: list[Subject] = []
    current: dict[str, object] | None = None

    for line in iter_relevant_lines(text):
        syllabus_match = SYLLABUS_RE.match(line)
        if syllabus_match and current is not None:
            current["syllabus"] = append_text(current.get("syllabus"), syllabus_match.group("value"))
            current["raw_text"] = append_text(current.get("raw_text"), line)
            continue

        if is_subject_line(line):
            if current:
                subjects.append(build_subject(current, source_document))
            current = {
                "name": clean_subject_name(line),
                "workload_hours": extract_workload(line),
                "credits": extract_credits(line),
                "raw_text": line,
            }
            continue

        if current is not None:
            current["raw_text"] = append_text(current.get("raw_text"), line)
            if len(line.split()) > 4:
                current["syllabus"] = append_text(current.get("syllabus"), line)

    if current:
        subjects.append(build_subject(current, source_document))

    return [subject for subject in subjects if subject.name]


def parse_code_table_subjects(text: str, source_document: str) -> list[Subject]:
    parsed_lines = analyze_lines(text)
    lines = [line.text for line in parsed_lines]
    code_rows = [(index, CODE_TABLE_RE.match(line)) for index, line in enumerate(lines)]
    code_rows = [(index, match) for index, match in code_rows if match]
    if not code_rows:
        return []

    subjects: list[Subject] = []
    for row_number, (index, match) in enumerate(code_rows):
        previous_boundary = code_rows[row_number - 1][0] if row_number > 0 else -1
        next_code_boundary = code_rows[row_number + 1][0] if row_number + 1 < len(code_rows) else len(lines)
        next_boundary = min(next_code_boundary, next_table_end_index(lines, index, next_code_boundary))
        before_lines = lines[previous_boundary + 1 : index]
        after_lines = lines[index + 1 : next_boundary]

        name_parts = collect_name_parts(before_lines, match.group("middle"), after_lines)
        name = " ".join(part for part in name_parts if part).strip()
        if not name:
            name = match.group("code")

        syllabus_parts = collect_syllabus_parts(before_lines, match.group("trailing"), after_lines, name_parts)
        grade = None if match.group("grade") == "-" else match.group("grade").replace(",", ".")
        subjects.append(
            Subject(
                name=name,
                source_document=source_document,
                workload_hours=int(match.group("hours")),
                semester=match.group("semester"),
                status=match.group("status"),
                grade=grade,
                syllabus=" ".join(syllabus_parts) or None,
                raw_text=" ".join(lines[previous_boundary + 1 : next_boundary]),
            )
        )

    return subjects


def collect_name_parts(before_lines: list[str], middle: str, after_lines: list[str]) -> list[str]:
    parts: list[str] = []
    before = title_prefix(last_content_line(before_lines))
    middle_name = clean_inline_name(middle)
    after = title_prefix(first_content_line(after_lines))

    should_use_before = not middle_name or len(middle_name.split()) == 1 or middle_name.split()[-1].lower() in CONNECTOR_WORDS
    should_use_after = should_use_before
    if before and should_use_before:
        parts.append(before)
    if middle_name and middle_name not in parts:
        parts.append(middle_name)
    if after and should_use_after and after not in parts:
        parts.append(after)
    return parts


def collect_syllabus_parts(
    before_lines: list[str],
    trailing: str,
    after_lines: list[str],
    name_parts: list[str],
) -> list[str]:
    name_values = set(name_parts)
    parts: list[str] = []
    for line in before_lines + ([trailing.strip()] if trailing.strip() else []) + after_lines:
        if should_skip_table_line(line):
            continue
        prefix = title_prefix(line)
        cleaned = line
        if prefix in name_values:
            cleaned = line[len(prefix) :].strip(" ,-;")
        if cleaned and cleaned not in name_values:
            parts.append(cleaned)
    return parts


def last_content_line(lines: list[str]) -> str:
    for line in reversed(lines):
        if not should_skip_table_line(line):
            prefix = title_prefix(line)
            if prefix:
                return line
    return ""


def first_content_line(lines: list[str]) -> str:
    for line in lines[:3]:
        if not should_skip_table_line(line):
            prefix = title_prefix(line)
            if prefix:
                return line
    return ""


def title_prefix(line: str) -> str:
    words = line.strip().split()
    selected: list[str] = []
    for index, word in enumerate(words):
        cleaned = word.strip(" ,.;:()")
        if not cleaned:
            continue
        starts_upper = cleaned[0].isupper()
        is_connector = cleaned.lower() in CONNECTOR_WORDS
        next_starts_upper = index + 1 < len(words) and words[index + 1].strip(" ,.;:()")[:1].isupper()
        if starts_upper or (selected and is_connector) or (is_connector and next_starts_upper):
            selected.append(cleaned)
            continue
        break
    if not selected:
        return ""
    return " ".join(selected)


def clean_inline_name(value: str) -> str:
    cleaned = value.strip(" ,-;")
    return title_prefix(cleaned) or ""


def should_skip_table_line(line: str) -> bool:
    return not line.strip() or line.strip() in TABLE_HEADER_MARKERS


def next_table_end_index(lines: list[str], start: int, fallback: int) -> int:
    for index in range(start + 1, fallback):
        if is_table_end_line(lines[index]):
            return index
    return fallback


def is_table_end_line(line: str) -> bool:
    normalized = normalize_text(line)
    return any(normalized == normalize_text(marker) for marker in TABLE_END_MARKERS)


def iter_relevant_lines(text: str) -> Iterable[str]:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line:
            yield line


def append_text(existing: object, value: str) -> str:
    if not existing:
        return value.strip()
    return f"{existing} {value.strip()}"


def build_subject(data: dict[str, object], source_document: str) -> Subject:
    return Subject(
        name=str(data.get("name") or "").strip(),
        source_document=source_document,
        workload_hours=data.get("workload_hours") if isinstance(data.get("workload_hours"), int) else None,
        credits=data.get("credits") if isinstance(data.get("credits"), float) else None,
        syllabus=str(data.get("syllabus")).strip() if data.get("syllabus") else None,
        raw_text=str(data.get("raw_text")).strip() if data.get("raw_text") else None,
    )


def parse_subjects(text: str, source_document: str) -> list[Subject]:
    for strategy in PARSE_STRATEGIES:
        subjects = strategy(text, source_document)
        if subjects:
            return normalize_subjects(subjects)
    return []


PARSE_STRATEGIES: tuple[ParseStrategy, ...] = (
    parse_csv_subjects,
    parse_code_table_subjects,
    parse_text_subjects,
)
