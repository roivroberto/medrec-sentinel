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


def _humanize(text: str) -> str:
    if not text:
        return ""
    return _one_line(text).replace("_", " ").title()


def build_pharmacist_note(flags: list[RiskFlag]) -> str:
    """Build a deterministic pharmacist note from risk flags."""

    parts: list[str] = []
    
    # Header
    parts.append(
        """
        <div class="ehr-container">
            <div class="ehr-header">
                <div class="ehr-title">PHARMACIST NOTE</div>
                <div class="ehr-status">DRAFT - NOT FINAL</div>
            </div>
        """
    )
    
    # Risks Section
    parts.append("<div class='ehr-section'><div class='ehr-section-title'>IDENTIFIED RISKS</div>")
    if not flags:
        parts.append("<div class='ehr-empty'>No risks identified.</div>")
    else:
        for idx, flag in enumerate(flags, start=1):
            severity = _humanize(flag.severity).upper()
            flag_type = _humanize(flag.flag_type)
            summary = _one_line(flag.summary)
            
            # Severity Color Mapping (can be styled in CSS)
            sev_class = "sev-default"
            if "HIGH" in severity:
                sev_class = "sev-high"
            elif "MODERATE" in severity:
                sev_class = "sev-mod"
                
            parts.append(f"""
            <div class="ehr-risk-item">
                <div class="ehr-risk-header">
                    <span class="ehr-severity {sev_class}">{severity}</span>
                    <span class="ehr-risk-type">{flag_type}</span>
                </div>
                <div class="ehr-risk-summary">{idx}. {summary}</div>
            """)
            
            if flag.evidence_spans:
                parts.append("<div class='ehr-evidence-label'>Evidence:</div><ul class='ehr-evidence-list'>")
                for span in flag.evidence_spans:
                    parts.append(f"<li>{_one_line(span.text)}</li>")
                parts.append("</ul>")

            cite_preview_items: list[str] = []
            for cite in flag.citations:
                one = _one_line(cite)
                if one:
                    cite_preview_items.append(one)
            cite_preview_items = _unique_preserve_order(cite_preview_items)
            
            if cite_preview_items:
                cite_preview = ", ".join(cite_preview_items)
                parts.append(f"<div class='ehr-citations'>Refs: {cite_preview}</div>")
                
            parts.append("</div>") # End risk item
            
    parts.append("</div>") # End Risks Section

    # Verification Questions
    parts.append("<div class='ehr-section'><div class='ehr-section-title'>VERIFICATION QUESTIONS</div>")
    questions = []
    for flag in flags:
        flag_type = _humanize(flag.flag_type)
        summary = _one_line(flag.summary)
        questions.append(
            f"Can you verify or clarify for <b>{flag_type}</b>: {summary}?"
        )
    questions = _unique_preserve_order([q for q in questions if q.strip()])
    
    if not questions:
         parts.append("<div class='ehr-empty'>None identified.</div>")
    else:
        parts.append("<ul class='ehr-questions-list'>")
        for q in questions:
            parts.append(f"<li>{q}</li>")
        parts.append("</ul>")
    parts.append("</div>")

    # Disclaimer
    parts.append("""
    <div class="ehr-disclaimer">
        <strong>DISCLAIMER:</strong> This note is not medical advice. It is generated for clinical decision support and 
        must be reviewed and confirmed against the source record and current guidelines.
    </div>
    """)

    # Signoff
    parts.append("""
    <div class="ehr-signoff">
        <div class="signoff-line">
            <span class="signoff-label">Electronically Signed By:</span>
            <span class="signoff-signature">__________________________________________</span>
        </div>
        <div class="signoff-meta">
            DATE: <span class="signoff-date">____/____/________</span> &nbsp;&nbsp; TIME: <span class="signoff-time">____:____</span>
        </div>
    </div>
    </div> <!-- End Container -->
    """)

    return "\n".join(parts)


def build_pharmacist_note_text(flags: list[RiskFlag]) -> str:
    """Build a deterministic plain-text pharmacist note (for export)."""

    lines: list[str] = []
    lines.append("PHARMACIST NOTE (DRAFT)")
    lines.append("")

    lines.append("Identified risks")
    if not flags:
        lines.append("- None identified.")
    else:
        for idx, flag in enumerate(flags, start=1):
            severity = _humanize(flag.severity).upper()
            flag_type = _humanize(flag.flag_type)
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
            flag_type = _humanize(flag.flag_type)
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
