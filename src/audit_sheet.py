"""A local worksheet for performing the §10 audit, so that a spreadsheet is not.

This changes how the audit is entered and nothing about what it asks. The sample
is the one `human_audit` drew under the published seed, the five verdicts are the
ones fixed before any row was read, and the files written are the same two the
scorer reads. What it removes is the friction that has nothing to do with
judgment: opening sixty pages instead of eight, hunting for a quotation by eye,
and editing a CSV by hand while doing both.

Three things it does that a spreadsheet cannot:

- **Groups the sample by source.** The sixty rows come from eight pages. Reading
  them page by page means opening each once and judging its rows together, which
  is also the order in which a reader can hold the page's own vocabulary in mind.
- **Links to the sentence, not the page.** Each row's link carries a text
  fragment, so the browser scrolls to the recorded quotation and highlights it.
  A quotation the browser cannot find is a signal worth having, but it is not a
  verdict, and the tool does not treat it as one.
- **Withholds the ledger for the two sources being read end to end.** The
  completeness half is worthless if the reader has already seen what the ledger
  holds, and seven of the sixty precision rows come from those two sources. Those
  rows stay hidden until both reads have been entered.

Run ``python3 -m src.audit_sheet``. It serves on localhost, writes nothing but
the two sheets, and can be closed and reopened without losing work.
"""

from __future__ import annotations

import html
import json
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import pandas as pd

from .human_audit import READS_CSV, RESULTS_CSV, SAMPLE_CSV, VERDICTS, completeness_sources
from .claim_mapping import load_sources

PORT = 8765

# How much of a quotation goes into the link's text fragment. The whole of a long
# quotation rarely matches, because a page's whitespace and soft hyphens need not
# survive extraction; a short prefix usually does.
FRAGMENT_CHARS = 24

VERDICT_LABELS = {
    "supported": "合ってる",
    "wrong-direction": "方向が逆",
    "not-in-source": "書いてない",
    "wrong-food": "食品が違う",
    "unlocatable": "ページが変わった",
}

DIRECTION_LABELS = {"warm": "温", "cool": "冷", "neutral": "平"}


def fragment_link(url: str, quote: str) -> str:
    """A URL that scrolls to the quotation and highlights it, where supported."""
    text = (quote or "").strip()[:FRAGMENT_CHARS]
    if not text:
        return url
    return f"{url}#:~:text={urllib.parse.quote(text, safe='')}"


def load_state() -> dict:
    """The sample, the verdicts entered so far, and the end-to-end reads."""
    sample = pd.read_csv(SAMPLE_CSV, dtype=str).fillna("")
    results = (pd.read_csv(RESULTS_CSV, dtype=str).fillna("")
               if RESULTS_CSV.exists() else pd.DataFrame())
    reads = (pd.read_csv(READS_CSV, dtype=str).fillna("")
             if READS_CSV.exists() else
             pd.DataFrame(columns=["source_id", "food_ja", "direction", "quote"]))
    targets = completeness_sources(load_sources())
    return {"sample": sample, "results": results, "reads": reads, "targets": targets}


def reads_complete(reads: pd.DataFrame, targets: list[str]) -> bool:
    """Whether both end-to-end reads have been entered.

    The gate on the precision rows from those two sources. It is deliberately a
    gate on *having read*, not on having read well: the tool cannot judge the
    second, and a reader who has written their list has already formed it
    without the ledger, which is the property the completeness half needs.
    """
    entered = set(reads["source_id"]) if len(reads) else set()
    return all(target in entered for target in targets)


def _urls() -> dict[str, str]:
    sources = load_sources()
    return dict(zip(sources["source_id"], sources["url"]))


def save_verdict(row: int, verdict: str) -> None:
    """Record one verdict, refusing anything outside the fixed vocabulary.

    The five were written down before any row was read. A sixth entered by
    accident — or a plausible-sounding paraphrase — would be a silent change to
    the instrument, so it is rejected rather than stored and discovered later by
    the scorer.
    """
    if verdict not in VERDICTS:
        raise ValueError(f"unknown verdict {verdict!r}")
    results = pd.read_csv(RESULTS_CSV, dtype=str).fillna("")
    results.loc[int(row), "verdict"] = verdict
    results.to_csv(RESULTS_CSV, index=False)


def save_note(row: int, note: str) -> None:
    results = pd.read_csv(RESULTS_CSV, dtype=str).fillna("")
    results.loc[int(row), "note"] = note
    results.to_csv(RESULTS_CSV, index=False)


def add_read(source_id: str, food_ja: str, direction: str, quote: str = "") -> None:
    """Append one food to an end-to-end read."""
    food = str(food_ja).strip()
    if not food:
        raise ValueError("a read row needs a food name")
    reads = pd.read_csv(READS_CSV, dtype=str).fillna("")
    row = {"source_id": source_id, "food_ja": food,
           "direction": direction, "quote": str(quote).strip()}
    pd.concat([reads, pd.DataFrame([row])], ignore_index=True).to_csv(
        READS_CSV, index=False)


def delete_read(index: int) -> None:
    reads = pd.read_csv(READS_CSV, dtype=str).fillna("")
    reads.drop(index=int(index)).to_csv(READS_CSV, index=False)


def render(state: dict) -> str:
    """The whole worksheet, as one page."""
    sample, results, reads = state["sample"], state["results"], state["reads"]
    targets, urls = state["targets"], _urls()
    unlocked = reads_complete(reads, targets)

    verdicts = list(results["verdict"]) if len(results) else [""] * len(sample)
    notes = list(results["note"]) if len(results) else [""] * len(sample)
    done = sum(1 for v in verdicts if v)

    parts = [_HEAD, f"""
<header>
  <h1>Axis A 人手監査（coding protocol §10）</h1>
  <p class="lede">判定は5つから選ぶだけ。押した瞬間にファイルへ保存される。閉じても続きからやれる。</p>
</header>

<section class="step {'done' if unlocked else 'open'}">
  <h2><span class="n">1</span> 通読 —— {targets[0]} と {targets[1]} を頭から最後まで読む</h2>
  <p class="why">これは <b>AIの見落とし</b>を測る唯一の手段。見落としは結論を「関係なし」側に寄せるので、
     この論文で一番効く。<b>台帳を見ずに</b>やる必要があるから、下の作業2はこれが済むまで一部伏せてある。</p>
"""]

    for target in targets:
        rows = reads[reads["source_id"] == target] if len(reads) else reads
        link = html.escape(urls.get(target, ""))
        parts.append(f"""
  <div class="src">
    <h3><a href="{link}" target="_blank" rel="noreferrer">{html.escape(target)} を開く ↗</a>
        <span class="count">{len(rows)} 件 記入済み</span></h3>
    <form class="readform" data-source="{html.escape(target)}">
      <input name="food_ja" placeholder="食品名（ページの表記のまま）" autocomplete="off" required>
      <select name="direction">
        <option value="warm">温める</option>
        <option value="cool">冷やす</option>
        <option value="neutral">どちらでもない（平）</option>
      </select>
      <input name="quote" placeholder="そう読める根拠の文（任意）" autocomplete="off">
      <button type="submit">追加</button>
    </form>
    <ul class="readlist">""")
        for index, row in rows.iterrows():
            direction = DIRECTION_LABELS.get(row["direction"], row["direction"])
            parts.append(
                f'<li><b>{html.escape(row["food_ja"])}</b> <span class="dir">{direction}</span>'
                f'<span class="q">{html.escape(row["quote"][:40])}</span>'
                f'<button class="del" data-index="{index}">削除</button></li>'
            )
        parts.append("</ul></div>")

    parts.append(f"""
</section>

<section class="step">
  <h2><span class="n">2</span> 答え合わせ —— 台帳の {len(sample)} 件を元ページで確かめる
      <span class="count">{done} / {len(sample)} 判定済み</span></h2>
  <p class="why">リンクを押すと <b>その文まで自動で飛んで光る</b>（Chrome推奨）。同じサイトの行はまとめてあるので、
     開くページは8枚だけ。キーボード <kbd>1</kbd>〜<kbd>5</kbd> でも選べる。</p>
""")

    for source_id, group in sample.groupby("source_id", sort=False):
        hidden = source_id in targets and not unlocked
        filled = sum(1 for i in group.index if verdicts[i])
        parts.append(f"""
  <div class="src {'locked' if hidden else ''}">
    <h3>{html.escape(source_id)} <span class="count">{filled} / {len(group)}</span></h3>""")
        if hidden:
            parts.append('<p class="lock">通読（作業1）を先に済ませてから開く。'
                         'ここを先に見ると通読の独立性が壊れるため。</p></div>')
            continue
        for i, row in group.iterrows():
            link = html.escape(fragment_link(row["url"], row["quote"]))
            direction = DIRECTION_LABELS.get(row["direction"], row["direction"])
            buttons = "".join(
                f'<button class="v {"on" if verdicts[i] == verdict else ""}" '
                f'data-row="{i}" data-verdict="{verdict}">{VERDICT_LABELS[verdict]}</button>'
                for verdict in VERDICTS
            )
            parts.append(f"""
    <div class="row {'judged' if verdicts[i] else ''}" id="row{i}">
      <div class="claim"><b>{html.escape(row["food_ja"])}</b>
        <span class="dir">{direction}</span>
        <a href="{link}" target="_blank" rel="noreferrer">この文へ飛ぶ ↗</a></div>
      <blockquote>{html.escape(row["quote"])}</blockquote>
      <div class="verdicts">{buttons}</div>
      <input class="note" data-row="{i}" placeholder="メモ（任意）"
             value="{html.escape(notes[i])}">
    </div>""")
        parts.append("</div>")

    parts.append(f"""
</section>
<footer>
  <p>両方うまったら、クロコンに「採点して」と言うだけ。
     （中身は <code>data/human_audit_results.csv</code> と
     <code>data/human_audit_source_reads.csv</code> に入っとる）</p>
</footer>
{_SCRIPT}""")
    return "".join(parts)


_HEAD = """<!doctype html><html lang="ja"><meta charset="utf-8">
<title>Axis A 人手監査</title>
<style>
 body{font:15px/1.7 -apple-system,"Hiragino Sans",sans-serif;margin:0;background:#f6f6f4;color:#1c1c1a}
 header,section,footer{max-width:900px;margin:0 auto;padding:0 24px}
 header{padding-top:32px} h1{font-size:22px;margin:0 0 4px}
 .lede{color:#555;margin:0 0 24px}
 .step{background:#fff;border:1px solid #e2e2dd;border-radius:10px;padding:20px 24px;margin:0 auto 24px}
 .step h2{font-size:17px;margin:0 0 6px;display:flex;align-items:center;gap:10px}
 .n{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;
    background:#1c1c1a;color:#fff;font-size:14px}
 .why{color:#555;font-size:14px;margin:0 0 18px}
 .src{border-top:1px solid #eee;padding:16px 0}
 .src h3{font-size:15px;margin:0 0 10px;display:flex;align-items:center;gap:12px}
 .count{font-weight:400;color:#777;font-size:13px;margin-left:auto}
 .row{padding:12px 14px;border:1px solid #ececE6;border-radius:8px;margin-bottom:10px;background:#fcfcfb}
 .row.judged{background:#f2f7f2;border-color:#cfe3cf}
 .claim{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
 .dir{background:#eee;border-radius:4px;padding:1px 7px;font-size:13px}
 blockquote{margin:8px 0;padding:8px 12px;background:#fff;border-left:3px solid #ddd;
            color:#333;font-size:14px}
 .verdicts{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
 button{font:inherit;font-size:13px;padding:5px 12px;border:1px solid #ccc;background:#fff;
        border-radius:6px;cursor:pointer}
 button:hover{background:#f0f0ec}
 .v.on{background:#1c1c1a;color:#fff;border-color:#1c1c1a}
 .note{width:100%;box-sizing:border-box;padding:6px 10px;border:1px solid #ddd;border-radius:6px;font:inherit;font-size:13px}
 .readform{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
 .readform input{flex:1;min-width:150px;padding:6px 10px;border:1px solid #ddd;border-radius:6px;font:inherit}
 .readform select{padding:6px;border:1px solid #ddd;border-radius:6px;font:inherit}
 .readlist{list-style:none;padding:0;margin:0}
 .readlist li{display:flex;align-items:center;gap:10px;padding:5px 0;border-bottom:1px dashed #eee;font-size:14px}
 .readlist .q{color:#888;font-size:13px;flex:1;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
 .locked{opacity:.55} .lock{color:#a33;font-size:14px;margin:0}
 kbd{background:#eee;border:1px solid #ccc;border-bottom-width:2px;border-radius:4px;padding:0 5px;font-size:12px}
 a{color:#0a58ca} footer{color:#777;font-size:13px;padding-bottom:40px}
</style>
"""

_SCRIPT = """
<script>
const post = (path, body) => fetch(path, {method:'POST', body:JSON.stringify(body)})
  .then(r => r.ok ? r.json() : r.text().then(t => Promise.reject(t)));

document.addEventListener('click', async e => {
  const v = e.target.closest('button.v');
  if (v) {
    await post('/verdict', {row:+v.dataset.row, verdict:v.dataset.verdict});
    const box = v.closest('.row');
    box.querySelectorAll('button.v').forEach(b => b.classList.remove('on'));
    v.classList.add('on'); box.classList.add('judged');
    bumpCounts();
    return;
  }
  const d = e.target.closest('button.del');
  if (d) { await post('/read-delete', {index:+d.dataset.index}); location.reload(); }
});

document.addEventListener('submit', async e => {
  if (!e.target.classList.contains('readform')) return;
  e.preventDefault();
  const f = e.target, data = Object.fromEntries(new FormData(f));
  await post('/read', {source_id:f.dataset.source, ...data});
  location.reload();
});

document.addEventListener('change', e => {
  if (e.target.classList.contains('note'))
    post('/note', {row:+e.target.dataset.row, note:e.target.value});
});

// 1-5 pick a verdict for the row the pointer is over, so a page of rows can be
// judged without leaving the keyboard.
let hovered = null;
document.addEventListener('mouseover', e => {
  const row = e.target.closest('.row'); if (row) hovered = row;
});
document.addEventListener('keydown', e => {
  if (!hovered || e.target.tagName === 'INPUT') return;
  const i = '12345'.indexOf(e.key);
  if (i >= 0) hovered.querySelectorAll('button.v')[i].click();
});

function bumpCounts(){
  document.querySelectorAll('.src').forEach(src => {
    const rows = src.querySelectorAll('.row');
    if (!rows.length) return;
    const n = src.querySelectorAll('.row.judged').length;
    const c = src.querySelector('.count'); if (c) c.textContent = `${n} / ${rows.length}`;
  });
  const all = document.querySelectorAll('.row').length;
  const judged = document.querySelectorAll('.row.judged').length;
  const head = document.querySelectorAll('.step h2 .count')[0];
  if (head) head.textContent = `${judged} / ${all} 判定済み`;
}
</script></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, kind: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/", "/index.html"):
            self._send(404, b"not found", "text/plain")
            return
        self._send(200, render(load_state()).encode("utf-8"),
                   "text/html; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        actions = {
            "/verdict": lambda p: save_verdict(p["row"], p["verdict"]),
            "/note": lambda p: save_note(p["row"], p["note"]),
            "/read": lambda p: add_read(p["source_id"], p.get("food_ja", ""),
                                        p.get("direction", "warm"), p.get("quote", "")),
            "/read-delete": lambda p: delete_read(p["index"]),
        }
        if self.path not in actions:
            self._send(404, b"no such action", "text/plain")
            return
        try:
            actions[self.path](payload)
        except ValueError as bad:
            self._send(400, str(bad).encode("utf-8"), "text/plain")
            return
        self._send(200, b'{"ok":true}', "application/json")

    def log_message(self, *args) -> None:
        """Quiet: the terminal is not where the work happens."""


def main() -> None:
    state = load_state()
    print(f"worksheet on http://127.0.0.1:{PORT}/")
    print(f"  precision: {sum(1 for v in state['results'].get('verdict', []) if v)}"
          f"/{len(state['sample'])} judged")
    print(f"  end-to-end reads: {', '.join(state['targets'])} "
          f"({len(state['reads'])} rows entered)")
    print("  ctrl-C to stop; the sheets are written as you go")
    webbrowser.open(f"http://127.0.0.1:{PORT}/")
    try:
        HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
