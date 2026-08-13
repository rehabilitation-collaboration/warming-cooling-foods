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

from .definitions import DATA_DIR
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

# One worked example per verdict, so the choice is made against a case rather
# than against a definition. The five are the protocol's; the examples are
# illustrations of them and are not claims that any of these errors is present.
VERDICT_EXAMPLES = {
    "supported": ("ページがその食品をその向きで書いとる",
                  "行「しょうが・温」／ページ「しょうがは体を温める代表格」"),
    "wrong-direction": ("食品は載っとるが、向きが逆",
                        "行「緑茶・温」／ページ「温活で控えた方がよい：緑茶」→ 実際は冷"),
    "not-in-source": ("その食品に温冷をひとことも与えてへん",
                      "行「ココア・温」／ページはレシピで名前を挙げるだけで、温冷を言うてない"),
    "wrong-food": ("引用の文が指しとるのは別の食品",
                   "行「ねぎ・温」／引用文をよう見たら「玉ねぎ」の話やった"),
    "unlocatable": ("8/3 の取得後にページが変わって確かめられん",
                    "リンクが404／記事が別内容に差し替わっとる（AIのせいやないので集計から外れる）"),
}

DIRECTION_LABELS = {"warm": "温", "cool": "冷", "neutral": "平"}

# The direction vocabulary of protocol §3, for the reader's reference. Both
# halves of the audit need it: the end-to-end read has to recognise a direction
# to write one down, and the precision check has to recognise the one the ledger
# recorded. Reproduced rather than paraphrased.
DIRECTION_VOCABULARY = [
    ("温", "温める／体を温める／温性／熱性／陽性／陽"),
    ("冷", "冷やす／体を冷やす／涼性／寒性／陰性／陰"),
    ("平", "平／どちらでもない／中庸"),
    ("温（温活）", "温活向き／温活食材／温活におすすめ／温活に適している／温活に役立つ"),
    ("冷（温活）", "温活で控えたい／温活中は避けたい／温活の妨げになる"),
]

# A worked example of the end-to-end read: an invented page, and the rows it
# should produce. Invented rather than excerpted, because the two sources being
# read are the two the reader must not see first, and quoting a third would
# reveal part of the precision sample for that source. Every row names the §3
# term that licenses it, and a test reads those terms back against the protocol.
READ_EXAMPLE_PAGE = """■ 体を温める食材
　根菜類（にんじん、ごぼう）、しょうが、シナモン

■ 五性でみると
　なつめは温性、きゅうりは寒性にあたります。

■ 温活向きの飲み物
　ほうじ茶は温活向き。逆に緑茶は温活で控えた方がよいでしょう。

■ 温活レシピ
　しょうが焼きの作り方はこちら

　※ 冷たい飲み物は体を冷やすので控えめに"""

READ_EXAMPLE_ROWS = [
    ("根菜類", "warm", "体を温める食材：根菜類", "体を温める",
     "クラス名もそのまま1件。食品名やないから飛ばす、はせん"),
    ("にんじん", "warm", "体を温める食材：根菜類（にんじん、ごぼう）", "体を温める",
     "括りとは別に、個別に名前が出とるので別の1件"),
    ("ごぼう", "warm", "同上", "体を温める", ""),
    ("しょうが", "warm", "体を温める食材：しょうが", "体を温める", ""),
    ("シナモン", "warm", "体を温める食材：シナモン", "体を温める", ""),
    ("なつめ", "warm", "なつめは温性", "温性", "五性の語も §3 の表で温になる"),
    ("きゅうり", "cool", "きゅうりは寒性", "寒性", ""),
    ("ほうじ茶", "warm", "ほうじ茶は温活向き", "温活向き",
     "温活でも、食品を味方側に置いとる文なら向きになる"),
    ("緑茶", "cool", "緑茶は温活で控えた方がよい", "温活で控えた方がよい",
     "同じ温活でも、控える側に置かれとるので冷"),
]

READ_EXAMPLE_SKIPPED = [
    ("「温活レシピ」の見出し", "食品をどっち側にも置いてへん。温活は活動の名前"),
    ("しょうが焼き",
     "見出しが「温活レシピ」で、作り方の案内をしとるだけ。"
     "ただし「しょうが焼きは体を温める」と書いてあったら、料理でも1件として書く"),
    ("「冷たい飲み物は体を冷やす」", "出す温度の話で、食品そのものの性質やない"),
]

# The cases §3 names where something that looks like a direction is not one.
NOT_A_DIRECTION = [
    ("「温活レシピ」「温活商品」など",
     "食品をどっち側にも置いてへん。温活は活動の名前であって向きやない"),
    ("「冷たい飲み物」など",
     "出す温度の話で、食品そのものの性質やない（§3 が名指しで区別しとる）"),
    ("自分の知識で補うこと",
     "ページが言うてへん向きは書かん。「一般に生姜は温めるから」は根拠にせん"),
]


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

    vocab = "".join(f"<tr><td class=dir>{d}</td><td>{html.escape(words)}</td></tr>"
                    for d, words in DIRECTION_VOCABULARY)
    not_dir = "".join(f"<li><b>{html.escape(what)}</b> — {html.escape(why)}</li>"
                      for what, why in NOT_A_DIRECTION)
    example_page = html.escape(READ_EXAMPLE_PAGE)
    n_rows = len(READ_EXAMPLE_ROWS)
    example_rows = "".join(
        f"<tr><td><b>{html.escape(food)}</b></td>"
        f'<td class="dir">{DIRECTION_LABELS[direction]}</td>'
        f"<td>{html.escape(quote)}</td>"
        f'<td class="ex">{html.escape(why)}</td></tr>'
        for food, direction, quote, _term, why in READ_EXAMPLE_ROWS)
    example_skipped = "".join(
        f"<li><b>{html.escape(what)}</b> — {html.escape(why)}</li>"
        for what, why in READ_EXAMPLE_SKIPPED)

    parts = [_HEAD, f"""
<header>
  <h1>Axis A 人手監査（coding protocol §10）</h1>
  <p class="lede">やることは2つ。<b>ページを読んで書き出す</b>のと、<b>台帳を元ページで確かめる</b>。
     押した瞬間にファイルへ保存されるので、いつ閉じてもええ。</p>
  <div class="map">
    <div><span class="tag now">先にやる</span> <b>通読</b> ——
         AIが<b>落とした</b>ものを探す。2ページ。</div>
    <div><span class="tag later">通読のあと</span> <b>答え合わせ</b> ——
         AIが<b>書いた</b>ことを確かめる。{len(sample)}件。</div>
    <p class="mapwhy">この2つは逆のミスを測っとる。答え合わせでは<b>見落としは原理的に1件も出てこん</b>
       （台帳に載っとるものしか見んから）。査読者が刺しとるのは見落としの方やから、通読が本丸にゃ。</p>
  </div>
</header>

<details class="guide" open>
  <summary>どの言葉が「温／冷」になるか（protocol §3・両方の作業で使う）</summary>
  <table class="vocab">{vocab}</table>
  <p class="sub">向きに<b>ならん</b>もの:</p>
  <ul>{not_dir}</ul>
  <p class="sub">2列の表（温めるもの｜冷やすもの）は、近くの文やなく<b>列の見出し</b>で決める。
     生と加熱で分かれとったら<b>両方</b>書く。</p>
</details>

<section class="step {'done' if unlocked else 'open'}">
  <h2><span class="tag now">先にやる</span> 通読 —— {targets[0]} と {targets[1]} を頭から最後まで読む</h2>
  <p class="why">ページを最初から最後まで読んで、<b>温か冷かが付いとる食品を全部</b>書き出す。
     <b>台帳は見んと</b>やる —— 見てもうたら「AIが挙げた分を確認する作業」になって、
     見落としが永久に出てこんくなる。だから答え合わせ側はこれが済むまで一部伏せてある。</p>
  <details class="guide" open>
    <summary>やってみせる —— 架空のページを1枚読んだら、こう書き出す</summary>
    <div class="demo">
      <div class="demopage">
        <p class="demolabel">架空の例ページ（実在のソースやない）</p>
        <pre>{example_page}</pre>
      </div>
      <div class="demoout">
        <p class="demolabel">→ 書き出す（{n_rows} 件）</p>
        <table class="ex">
          <tr><th>食品名</th><th>向き</th><th>根拠の文</th><th>なんで</th></tr>
          {example_rows}
        </table>
        <p class="demolabel skip">→ 書かへんもの</p>
        <ul class="skiplist">{example_skipped}</ul>
      </div>
    </div>
  </details>
  <details class="guide">
    <summary>何を書き出す？ 迷った時は？</summary>
    <ul>
      <li><b>クラス名も書く</b> —— 「葉物野菜」「香辛料」みたいな括りも、ページがそう言うてるなら1件。
          食品名やないから飛ばす、はせんといて</li>
      <li><b>食品名はページの表記のまま</b> —— 「しょうが」を「生姜」に直さんでええ。
          表記が違うだけの分はうちが後で突き合わせる</li>
      <li><b>根拠の文は任意</b>やけど、迷った時ほど入れといてほしい。判断はうちが引き取れる</li>
      <li><b>迷ったら書く</b> —— 余分に書いた分は「台帳になし」として出てくるけど、それはうちが見て裁く。
          逆に<b>書かんかったものは誰も気づけん</b></li>
    </ul>
  </details>
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

    examples = "".join(
        f'<tr><td><span class="v sample">{VERDICT_LABELS[v]}</span></td>'
        f"<td>{html.escape(VERDICT_EXAMPLES[v][0])}</td>"
        f'<td class="ex">{html.escape(VERDICT_EXAMPLES[v][1])}</td></tr>'
        for v in VERDICTS)

    parts.append(f"""
</section>

<section class="step">
  <h2><span class="tag later">通読のあと</span> 答え合わせ —— 台帳の {len(sample)} 件を元ページで確かめる
      <span class="count">{done} / {len(sample)} 判定済み</span></h2>
  <p class="why">1行ずつ「このページ、ほんまにこの食品をこの向きで書いてる？」を見るだけ。
     リンクを押すと <b>その文まで自動で飛んで光る</b>（Chrome推奨）。同じサイトの行はまとめてあるので、
     開くページは8枚だけ。マウスを行に乗せて <kbd>1</kbd>〜<kbd>5</kbd> でも押せる。</p>
  <details class="guide" open>
    <summary>どれを選ぶ？（解答例つき）</summary>
    <table class="ex"><tr><th>選ぶやつ</th><th>こういう時</th><th>例</th></tr>{examples}</table>
    <p class="sub">★ <b>飛んだ先に引用文が見つからん</b>のは、それ自体は判定やない。
       ページ内を探しても本当に無いのか、ページが書き換わったのかを見てから決めてにゃ。<br>
       ★ 迷ったら<b>メモ欄</b>に一言だけ残しといて。後でうちが読む。</p>
  </details>
  <label class="filter"><input type="checkbox" id="hidejudged"> 判定済みを隠す</label>
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
  <p>この画面は<b>起動した時のコード</b>で動いとる。作りを直してもろたら、再読み込みやなく
     ターミナルで <kbd>Ctrl</kbd>+<kbd>C</kbd> → <code>python3 -m src.audit_sheet</code> を叩き直す。</p>
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
 .step h2{font-size:17px;margin:0 0 6px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
 .tag{font-size:12px;font-weight:600;padding:2px 9px;border-radius:20px;white-space:nowrap}
 .tag.now{background:#1c1c1a;color:#fff}
 .tag.later{background:#e8e8e2;color:#555}
 .map{background:#fff;border:1px solid #e2e2dd;border-radius:10px;padding:14px 18px;margin-bottom:24px}
 .map>div{display:flex;align-items:center;gap:10px;padding:4px 0;font-size:14px}
 .mapwhy{color:#555;font-size:13px;margin:8px 0 0;padding-top:8px;border-top:1px solid #eee}
 .guide{background:#fff;border:1px solid #e2e2dd;border-radius:10px;padding:0 18px;margin:0 auto 18px;
        max-width:900px;font-size:14px}
 .step .guide{margin:0 0 18px;max-width:none}
 .guide summary{cursor:pointer;padding:12px 0;font-weight:600;font-size:14px}
 .guide[open] summary{border-bottom:1px solid #eee;margin-bottom:12px}
 .guide ul{margin:0 0 14px;padding-left:20px} .guide li{margin-bottom:5px;color:#333}
 .guide .sub{color:#555;font-size:13px;margin:0 0 12px}
 table.vocab,table.ex{border-collapse:collapse;width:100%;margin-bottom:12px;font-size:13.5px}
 table.vocab td,table.ex td,table.ex th{border-bottom:1px solid #eee;padding:7px 10px;text-align:left;
                                        vertical-align:top}
 table.ex th{color:#777;font-weight:600;font-size:12.5px}
 table.vocab td.dir{width:90px;font-weight:600;white-space:nowrap}
 table.ex td.ex,td.ex{color:#555}
 .v.sample{display:inline-block;border:1px solid #ccc;border-radius:6px;padding:3px 10px;
           background:#fff;font-size:12.5px;white-space:nowrap}
 .filter{display:block;color:#666;font-size:13px;margin-bottom:12px;cursor:pointer}
 .demo{display:grid;grid-template-columns:minmax(230px,1fr) 1.6fr;gap:18px;margin-bottom:14px}
 @media(max-width:820px){.demo{grid-template-columns:1fr}}
 .demopage pre{background:#fbfbf8;border:1px solid #e6e6df;border-radius:8px;padding:12px 14px;
               margin:0;font:13px/1.9 "Hiragino Sans",monospace;white-space:pre-wrap}
 .demolabel{font-size:12.5px;color:#777;margin:0 0 6px;font-weight:600}
 .demolabel.skip{margin-top:14px;color:#a33}
 .skiplist{list-style:none;padding:0;margin:0;font-size:13px}
 .skiplist li{padding:5px 0;border-bottom:1px dashed #eee;color:#444}
 .demoout table.ex td{padding:5px 8px;font-size:13px}
 .why{color:#555;font-size:14px;margin:0 0 14px}
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
 body.hide-judged .row.judged{display:none}
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

document.addEventListener('change', e => {
  if (e.target.id !== 'hidejudged') return;
  document.body.classList.toggle('hide-judged', e.target.checked);
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
