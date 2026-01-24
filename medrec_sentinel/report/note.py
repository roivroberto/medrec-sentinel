from __future__ import annotations

from medrec_sentinel.schemas import RiskFlag


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _one_line(text: str) -> str:
    return " ".join(text.split())


def build_pharmacist_note(flags: list[RiskFlag]) -> str:
    """Build a deterministic pharmacist note from risk flags."""

    lines: list[str] = []
    lines.append("PHARMACIST NOTE (DRAFT)")
    lines.append("")

    lines.append("Identified risks")
    if not flags:
        lines.append("- None identified.")
    else:
        for idx, flag in enumerate(flags, start=1):
            severity = _one_line(flag.severity).upper()
            flag_type = _one_line(flag.flag_type)
            summary = _one_line(flag.summary)
            header = f"{idx}. [{severity}] {flag_type}: {summary}".strip()
            lines.append(header)
            if flag.evidence_spans:
                lines.append("   Evidence:")
                for span in flag.evidence_spans:
                    lines.append(f"   - {_one_line(span.text)}")

            cite_preview_items: list[str] = []
            for cite in flag.citations:
                one = _one_line(cite)
                if one:
                    cite_preview_items.append(one)
            cite_preview_items = _unique_preserve_order(cite_preview_items)
            if cite_preview_items:
                cite_preview = ", ".join(cite_preview_items)
                lines.append(f"   Citations: {cite_preview}")

    lines.append("")
    lines.append("Suggested verification questions")
    if not flags:
        lines.append("- None identified.")
    else:
        questions = []
        for flag in flags:
            flag_type = _one_line(flag.flag_type)
            summary = _one_line(flag.summary)
            questions.append(
                f"- Can you verify or clarify for '{flag_type}': {summary}?"
            )
        questions = _unique_preserve_order([q for q in questions if q.strip()])
        if not questions:
            lines.append("- None identified.")
        else:
            lines.extend(questions)

    lines.append("")
    lines.append("Citations")
    citations: list[str] = []
    for flag in flags:
        citations.extend(flag.citations)

    citations_one_line: list[str] = []
    for cite in citations:
        one = _one_line(cite)
        if one:
            citations_one_line.append(one)
    citations_one_line = _unique_preserve_order(citations_one_line)
    if not citations_one_line:
        lines.append("- None provided.")
    else:
        for cite in citations_one_line:
            lines.append(f"- {cite}")

    lines.append("")
    lines.append("Disclaimer")
    lines.append(
        "This note is not medical advice. It is generated for clinical decision support and "
        "must be reviewed and confirmed against the source record and current guidelines."
    )
    lines.append("")
    lines.append("Clinician signoff")
    lines.append("Reviewed by: ____________________   Date/Time: ____________________")

    return "\n".join(lines) + "\n"
