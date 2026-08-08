"""Generate manuscript PDF from manuscript.md using weasyprint.

Tables are embedded in the markdown (no CSV build needed). Figures are inserted
from plots/ (the two attention-gap scatter plots). Adapted from the 8th-paper
(kokutai) build pipeline; figure labels are English-only so there are no
CJK-glyph problems in the PDF.

Figure map (must match the Figure Legends section of manuscript.md):
- Figure 1 = presence_by_breadth_and_volume.png (the primary result: what predicts
  having any on-construct study — observed by coverage, observed by literature
  volume, and the adjusted model)
- Figure 2 = attention_gap_all.png (per-food scatter over the primary Tier-1 frame)

The core-only scatter (attention_gap_core.png) is still produced by analysis.py
but is not carried in the manuscript.
"""

import re
from pathlib import Path

import markdown
import weasyprint

PROJECT_DIR = Path(__file__).parent
PLOTS_DIR = PROJECT_DIR / "plots"
PDF_DIR = PROJECT_DIR / "output"
PDF_DIR.mkdir(exist_ok=True)
MANUSCRIPT_MD = PROJECT_DIR / "manuscript.md"

MAIN_FIGURES = {
    "Figure 1": "presence_by_breadth_and_volume.png",
    "Figure 2": "attention_gap_all.png",
}

CSS = """
@page {
    size: A4;
    margin: 2.5cm 2cm;
    @bottom-center { content: counter(page); font-size: 10pt; color: #666; }
}
body {
    font-family: "Times New Roman", "DejaVu Serif", Georgia, serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #111;
}
h1 { font-size: 16pt; margin-top: 0; margin-bottom: 8pt; line-height: 1.3;
     page-break-after: avoid; }
h2 { font-size: 13pt; margin-top: 20pt; margin-bottom: 6pt;
     border-bottom: 1px solid #ccc; padding-bottom: 3pt;
     page-break-after: avoid; }
h3 { font-size: 11.5pt; margin-top: 14pt; margin-bottom: 4pt;
     page-break-after: avoid; }
p { margin: 6pt 0; text-align: justify; widows: 3; orphans: 3; }
ol li, ul li { margin: 6pt 0; widows: 2; orphans: 2; }
sup { font-size: 0.75em; }
table {
    border-collapse: collapse; width: 100%; margin: 10pt 0;
    font-size: 9pt;
    /* Not "avoid": a table taller than one page cannot honour it, and when it
       cannot, the caption above is left stranded on the previous page (Table 4
       did exactly that). Breaking between rows instead keeps the caption with
       the start of its table and repeats the header on each continuation. */
    page-break-inside: auto;
}
thead { display: table-header-group; }
tfoot { display: table-footer-group; }
tr { page-break-inside: avoid; }
th, td {
    border: 1px solid #999; padding: 3pt 5pt; text-align: left;
}
th { background: #e8e8e8; font-weight: bold; }
hr { border: none; border-top: 1px solid #ccc; margin: 16pt 0; }
img { max-width: 100%; height: auto; margin: 10pt 0; }
strong { font-weight: bold; }
em { font-style: italic; }
.figure-block {
    page-break-inside: avoid;
    page-break-before: always;
    margin: 1.5em 0;
    text-align: center;
}
.figure-block img {
    display: block;
    margin: 0 auto;
    max-width: 95%;
    max-height: 78vh;
}
.figure-caption {
    font-size: 10pt;
    text-align: justify;
    margin-top: 0.5em;
}
"""


def extract_figure_legends(md_text: str) -> dict[str, str]:
    """Extract figure legend text from the manuscript's Figure Legends section."""
    legends = {}
    pattern = r"\*\*Figure (\d+)\.\s*(.*?)\*\*\s*(.*?)(?=\n\n\*\*Figure|\n\n---|\Z)"
    for m in re.finditer(pattern, md_text, re.DOTALL):
        fig_num = m.group(1)
        title = m.group(2).strip()
        body = m.group(3).strip().replace("\n", " ")
        legends[f"Figure {fig_num}"] = f"{title} {body}".strip()
    return legends


def _caption_html(caption: str) -> str:
    """Render a legend's inline markdown (bold panel letters, italics) as HTML.

    The legend text is pulled straight out of the markdown source, so dropping
    it into the HTML verbatim prints literal `**(a)**` in the PDF.
    """
    rendered = markdown.markdown(caption)
    return re.sub(r"^<p>|</p>$", "", rendered.strip())


def _render_figure_block(fig_label: str, fig_file: str, caption: str) -> str:
    fig_path = PLOTS_DIR / fig_file
    if not fig_path.exists():
        print(f"[WARN] {fig_path} not found, skipping")
        return ""
    html = '<div class="figure-block">'
    html += f'<img src="file://{fig_path.resolve()}" alt="{fig_label}">'
    html += (f'<p class="figure-caption"><strong>{fig_label}.</strong> '
             f'{_caption_html(caption)}</p></div>\n')
    return html


def build_figures_html(legends: dict[str, str]) -> str:
    html = ""
    for fig_label, fig_file in MAIN_FIGURES.items():
        html += _render_figure_block(fig_label, fig_file, legends.get(fig_label, ""))
    return html


def convert():
    md_text = MANUSCRIPT_MD.read_text(encoding="utf-8")
    legends = extract_figure_legends(md_text)

    # The figure map above is hand-maintained, so it goes stale when the
    # manuscript's figures change — and a stale map silently prints the wrong
    # image under the right caption. Fail instead.
    if set(legends) != set(MAIN_FIGURES):
        raise SystemExit(
            "figure map is out of sync with manuscript.md\n"
            f"  legends in manuscript: {sorted(legends)}\n"
            f"  files in MAIN_FIGURES: {sorted(MAIN_FIGURES)}"
        )

    # Remove the Figure Legends section (rebuilt with actual images below).
    md_text = re.sub(r"## Figure Legends.*?(?=\n## )", "", md_text, flags=re.DOTALL)

    # Convert pandoc-style superscripts ^text^ to <sup>text</sup>.
    md_text = re.sub(r"\^([^^]+?)\^", r"<sup>\1</sup>", md_text)

    html_body = markdown.markdown(md_text, extensions=["tables", "smarty"])
    figures_html = build_figures_html(legends)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>{html_body}{figures_html}</body></html>"""

    out_path = PDF_DIR / "warming-cooling-foods.pdf"
    weasyprint.HTML(string=html, base_url=str(PROJECT_DIR)).write_pdf(str(out_path))
    print(f"[OK] {out_path} ({out_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    convert()
