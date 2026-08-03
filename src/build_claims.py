"""Build data/claims.csv from hand-coded warm/cool attributions.

Each row is one (food, source, direction) claim coded BY HAND from the fetched
source text under ``data/sources_raw/{source_id}.txt``, following
``data/coding_protocol.md``. ``food_en`` is the canonical aggregation key;
``food_ja`` and ``quote`` (source's own label + section/location) preserve
traceability. Directions use the source's own vocabulary mapped to the binary
lay axis per protocol §3 (warm / cool / neutral).

Running this script regenerates claims.csv deterministically. It is the audit
trail of the manual coding: to re-check any row, open the cited source txt.
"""

from __future__ import annotations

import pandas as pd

from .definitions import CLAIMS_CSV

COLUMNS = ["food_en", "food_ja", "source_id", "direction", "quote", "condition"]

# (food_en, food_ja, source_id, direction, quote, condition)
# food_en is the canonical key kept consistent across sources (e.g. きゅうり /
# キュウリ / 胡瓜 all -> "cucumber"). food_ja is the source's verbatim label.
CLAIMS: list[tuple[str, str, str, str, str, str]] = [
    # ==================================================================
    # yomeishu (Tier 1) 養命酒製造 健康コラム
    #   東洋医学: 陽性=warm / 陰性=cool。温=「体を温める食べ物」節+見分け方。
    #   冷=「体を冷やす食べ物」節(陰性リスト)+見分け方(白米)。
    # ==================================================================
    # -- warm (陽性) --
    ("ginger", "生姜", "yomeishu", "warm", "体を温める食べ物: 生姜", ""),
    ("green onion", "ねぎ", "yomeishu", "warm", "体を温める食べ物: ねぎ", ""),
    ("chicken", "鶏むね肉", "yomeishu", "warm", "体を温める食べ物: 鶏むね肉(むね肉→chickenに一般化)", ""),
    ("pumpkin", "かぼちゃ", "yomeishu", "warm", "体を温める食べ物: かぼちゃ", ""),
    ("mandarin orange", "みかん", "yomeishu", "warm", "体を温める食べ物: みかん", ""),
    ("pork liver", "豚レバー", "yomeishu", "warm", "体を温める食べ物: 豚レバー", ""),
    ("carrot", "人参", "yomeishu", "warm", "見分け方: 人参などの根菜類は陽性", ""),
    ("burdock", "ごぼう", "yomeishu", "warm", "見分け方: ごぼうなどの根菜類は陽性", ""),
    ("miso", "味噌", "yomeishu", "warm", "見分け方: 味噌など色が濃いものは陽性", ""),
    ("brown rice", "玄米", "yomeishu", "warm", "見分け方: 色が濃い玄米は陽性", ""),
    ("brown sugar", "黒糖", "yomeishu", "warm", "見分け方: 黒糖は陽性", ""),
    ("beet sugar", "てんさい糖", "yomeishu", "warm", "見分け方: てんさい糖は陽性", ""),
    ("honey", "ハチミツ", "yomeishu", "warm", "見分け方: ハチミツは陽性", ""),
    # -- cool (陰性) 穀物・豆類 --
    ("wheat", "小麦", "yomeishu", "cool", "体を冷やす食べ物＞穀物・豆類: 小麦", ""),
    ("barley", "大麦", "yomeishu", "cool", "体を冷やす食べ物＞穀物・豆類: 大麦", ""),
    ("buckwheat", "そば", "yomeishu", "cool", "体を冷やす食べ物＞穀物・豆類: そば", ""),
    ("edamame", "枝豆", "yomeishu", "cool", "体を冷やす食べ物＞穀物・豆類: 枝豆", ""),
    ("tofu", "豆腐", "yomeishu", "cool", "体を冷やす食べ物＞穀物・豆類: 豆腐", ""),
    ("mung bean", "緑豆", "yomeishu", "cool", "体を冷やす食べ物＞穀物・豆類: 緑豆", ""),
    ("konjac", "こんにゃく", "yomeishu", "cool", "体を冷やす食べ物＞穀物・豆類: こんにゃく", ""),
    # -- cool 肉 --
    ("horse meat", "馬肉", "yomeishu", "cool", "体を冷やす食べ物＞肉: 馬肉", ""),
    ("duck meat", "鴨肉", "yomeishu", "cool", "体を冷やす食べ物＞肉: 鴨肉", ""),
    ("animal fat", "動物性脂肪", "yomeishu", "cool", "体を冷やす食べ物＞肉: 動物性脂肪", ""),
    # -- cool 魚介類 --
    ("oyster", "牡蠣", "yomeishu", "cool", "体を冷やす食べ物＞魚介類: 牡蠣", ""),
    ("asari clam", "あさり", "yomeishu", "cool", "体を冷やす食べ物＞魚介類: あさり", ""),
    ("shijimi clam", "しじみ", "yomeishu", "cool", "体を冷やす食べ物＞魚介類: しじみ", ""),
    ("hamaguri clam", "はまぐり", "yomeishu", "cool", "体を冷やす食べ物＞魚介類: はまぐり", ""),
    ("crab", "カニ", "yomeishu", "cool", "体を冷やす食べ物＞魚介類: カニ", ""),
    ("octopus", "タコ", "yomeishu", "cool", "体を冷やす食べ物＞魚介類: タコ", ""),
    ("wakame", "わかめ", "yomeishu", "cool", "体を冷やす食べ物＞魚介類: わかめ", ""),
    ("hijiki", "ひじき", "yomeishu", "cool", "体を冷やす食べ物＞魚介類: ひじき", ""),
    ("nori", "のり", "yomeishu", "cool", "体を冷やす食べ物＞魚介類: のり", ""),
    # -- cool 野菜 --
    ("cucumber", "きゅうり", "yomeishu", "cool", "体を冷やす食べ物＞野菜: きゅうり", ""),
    ("tomato", "トマト", "yomeishu", "cool", "体を冷やす食べ物＞野菜: トマト", ""),
    ("chinese cabbage", "白菜", "yomeishu", "cool", "体を冷やす食べ物＞野菜: 白菜", ""),
    ("eggplant", "なす", "yomeishu", "cool", "体を冷やす食べ物＞野菜: なす", ""),
    ("bitter melon", "ゴーヤ", "yomeishu", "cool", "体を冷やす食べ物＞野菜: ゴーヤ", ""),
    ("spinach", "ほうれん草", "yomeishu", "cool", "体を冷やす食べ物＞野菜: ほうれん草", ""),
    ("bok choy", "チンゲン菜", "yomeishu", "cool", "体を冷やす食べ物＞野菜: チンゲン菜", ""),
    # celery added 2026-08-04 after inter-coder reconciliation: coder 1 missed
    # it though it is listed verbatim in the 野菜 cooling line (protocol §3).
    ("celery", "セロリ", "yomeishu", "cool", "体を冷やす食べ物＞野菜: セロリ", ""),
    ("radish sprouts", "かいわれ大根", "yomeishu", "cool", "体を冷やす食べ物＞野菜: かいわれ大根", ""),
    ("winter melon", "冬瓜", "yomeishu", "cool", "体を冷やす食べ物＞野菜: 冬瓜", ""),
    # -- cool 果物 --
    ("strawberry", "いちご", "yomeishu", "cool", "体を冷やす食べ物＞果物: いちご", ""),
    ("banana", "バナナ", "yomeishu", "cool", "体を冷やす食べ物＞果物: バナナ", ""),
    ("watermelon", "スイカ", "yomeishu", "cool", "体を冷やす食べ物＞果物: スイカ", ""),
    ("persimmon", "柿", "yomeishu", "cool", "体を冷やす食べ物＞果物: 柿", ""),
    ("pear", "梨", "yomeishu", "cool", "体を冷やす食べ物＞果物: 梨", ""),
    ("melon", "メロン", "yomeishu", "cool", "体を冷やす食べ物＞果物: メロン", ""),
    ("kiwi", "キウイ", "yomeishu", "cool", "体を冷やす食べ物＞果物: キウイ", ""),
    ("mango", "マンゴー", "yomeishu", "cool", "体を冷やす食べ物＞果物: マンゴー", ""),
    # -- cool 調味料 --
    ("vinegar", "酢", "yomeishu", "cool", "体を冷やす食べ物＞調味料: 酢", ""),
    ("white sugar", "白砂糖", "yomeishu", "cool", "体を冷やす食べ物＞調味料: 白砂糖", ""),
    ("sesame oil", "ごま油", "yomeishu", "cool", "体を冷やす食べ物＞調味料: ごま油", ""),
    ("rapeseed oil", "菜種油", "yomeishu", "cool", "体を冷やす食べ物＞調味料: 菜種油", ""),
    ("oyster sauce", "オイスターソース", "yomeishu", "cool", "体を冷やす食べ物＞調味料: オイスターソース", ""),
    # -- cool 見分け方 --
    ("white rice", "白米", "yomeishu", "cool", "見分け方: 白米は色が薄く体を冷やす", ""),

    # ==================================================================
    # esse (Tier 1) ESSEonline (扶桑社) 管理栄養士監修
    #   ＜温食材＞=warm / ＜冷食材＞=cool の2区分リスト。
    # ==================================================================
    # -- warm ＜温食材＞ --
    ("carrot", "ニンジン", "esse", "warm", "＜温食材＞野菜: ニンジン", ""),
    ("burdock", "ゴボウ", "esse", "warm", "＜温食材＞野菜: ゴボウ(根菜類)", ""),
    ("pumpkin", "カボチャ", "esse", "warm", "＜温食材＞野菜: カボチャ", ""),
    ("brown rice", "玄米", "esse", "warm", "＜温食材＞炭水化物: 玄米", ""),
    ("buckwheat", "そば", "esse", "warm", "＜温食材＞炭水化物: そば", ""),
    ("whole grain bread", "全粒粉パン", "esse", "warm", "＜温食材＞炭水化物: 全粒粉パン", ""),
    ("salt", "塩", "esse", "warm", "＜温食材＞調味料: 塩", ""),
    ("miso", "みそ", "esse", "warm", "＜温食材＞調味料: みそ", ""),
    ("soy sauce", "しょうゆ", "esse", "warm", "＜温食材＞調味料: しょうゆ", ""),
    ("brown sugar", "黒砂糖", "esse", "warm", "＜温食材＞調味料: 黒砂糖", ""),
    ("umeboshi", "梅干し", "esse", "warm", "＜温食材＞調味料: 梅干し", ""),
    ("red meat and fish", "赤身（肉·魚）", "esse", "warm", "＜温食材＞タンパク質: 赤身（肉·魚）", ""),
    ("shrimp", "エビ", "esse", "warm", "＜温食材＞タンパク質: エビ", ""),
    ("octopus", "タコ", "esse", "warm", "＜温食材＞タンパク質: タコ", ""),
    ("shellfish", "貝類", "esse", "warm", "＜温食材＞タンパク質: 貝類", ""),
    ("small fish", "小魚", "esse", "warm", "＜温食材＞タンパク質: 小魚", ""),
    ("natto", "納豆", "esse", "warm", "＜温食材＞タンパク質: 納豆", ""),
    ("black tea", "紅茶", "esse", "warm", "＜温食材＞飲み物: 紅茶", ""),
    ("cocoa", "ココア", "esse", "warm", "＜温食材＞飲み物: ココア", ""),
    ("sake", "日本酒", "esse", "warm", "＜温食材＞飲み物: 日本酒", ""),
    ("red wine", "赤ワイン", "esse", "warm", "＜温食材＞飲み物: 赤ワイン", ""),
    ("apple", "リンゴ", "esse", "warm", "＜温食材＞果物: リンゴ", ""),
    ("cherry", "サクランボ", "esse", "warm", "＜温食材＞果物: サクランボ", ""),
    ("grape", "ブドウ", "esse", "warm", "＜温食材＞果物: ブドウ", ""),
    ("prune", "プルーン", "esse", "warm", "＜温食材＞果物: プルーン", ""),
    # -- cool ＜冷食材＞ --
    ("leafy greens", "葉野菜", "esse", "cool", "＜冷食材＞野菜: 葉野菜", ""),
    ("eggplant", "ナス", "esse", "cool", "＜冷食材＞野菜: ナス", ""),
    ("cucumber", "キュウリ", "esse", "cool", "＜冷食材＞野菜: キュウリ", ""),
    ("tomato", "トマト", "esse", "cool", "＜冷食材＞野菜: トマト", ""),
    ("bean sprouts", "モヤシ", "esse", "cool", "＜冷食材＞野菜: モヤシ", ""),
    ("pasta", "パスタ", "esse", "cool", "＜冷食材＞炭水化物: パスタ", ""),
    ("udon", "うどん", "esse", "cool", "＜冷食材＞炭水化物: うどん", ""),
    ("white rice", "白米", "esse", "cool", "＜冷食材＞炭水化物: 白米", ""),
    ("white bread", "白パン", "esse", "cool", "＜冷食材＞炭水化物: 白パン", ""),
    ("mayonnaise", "マヨネーズ", "esse", "cool", "＜冷食材＞調味料: マヨネーズ", ""),
    ("ketchup", "ケチャップ", "esse", "cool", "＜冷食材＞調味料: ケチャップ", ""),
    ("vinegar", "酢", "esse", "cool", "＜冷食材＞調味料: 酢", ""),
    ("white sugar", "白砂糖", "esse", "cool", "＜冷食材＞調味料: 白砂糖", ""),
    ("white fish", "白身の魚", "esse", "cool", "＜冷食材＞タンパク質: 白身の魚", ""),
    ("fatty meat", "脂身", "esse", "cool", "＜冷食材＞タンパク質: 脂身", ""),
    ("tofu", "豆腐", "esse", "cool", "＜冷食材＞タンパク質: 豆腐", ""),
    ("white sesame", "白ゴマ", "esse", "cool", "＜冷食材＞タンパク質: 白ゴマ", ""),
    ("green tea", "緑茶", "esse", "cool", "＜冷食材＞飲み物: 緑茶", ""),
    ("coffee", "コーヒー", "esse", "cool", "＜冷食材＞飲み物: コーヒー", ""),
    ("milk", "牛乳", "esse", "cool", "＜冷食材＞飲み物: 牛乳", ""),
    ("beer", "ビール", "esse", "cool", "＜冷食材＞飲み物: ビール", ""),
    ("white wine", "白ワイン", "esse", "cool", "＜冷食材＞飲み物: 白ワイン", ""),
    ("banana", "バナナ", "esse", "cool", "＜冷食材＞果物: バナナ", ""),
    ("pineapple", "パイナップル", "esse", "cool", "＜冷食材＞果物: パイナップル", ""),
    ("mango", "マンゴー", "esse", "cool", "＜冷食材＞果物: マンゴー", ""),
    ("kiwi", "キウイ", "esse", "cool", "＜冷食材＞果物: キウイ", ""),
    ("melon", "メロン", "esse", "cool", "＜冷食材＞果物: メロン", ""),
    ("grapefruit", "グレープフルーツ", "esse", "cool", "＜冷食材＞果物: グレープフルーツ", ""),

    # ==================================================================
    # macaroni (Tier 1) macaroni (トラストリッジ) 管理栄養士執筆
    #   五性ベース。体を「温める」一覧=warm / 体を「冷やす」一覧=cool。
    # ==================================================================
    # -- warm 温める野菜 --
    ("carrot", "にんじん", "macaroni", "warm", "体を温める野菜: にんじん", ""),
    ("burdock", "ごぼう", "macaroni", "warm", "体を温める野菜: ごぼう", ""),
    ("lotus root", "れんこん", "macaroni", "warm", "体を温める野菜: れんこん", ""),
    ("pumpkin", "かぼちゃ", "macaroni", "warm", "体を温める野菜: かぼちゃ", ""),
    ("green onion", "ねぎ", "macaroni", "warm", "体を温める野菜: ねぎ", ""),
    ("onion", "たまねぎ", "macaroni", "warm", "体を温める野菜: たまねぎ", ""),
    ("ginger", "しょうが", "macaroni", "warm", "体を温める野菜: しょうが", ""),
    # -- warm 温める果物 --
    ("apple", "りんご", "macaroni", "warm", "体を温める果物: りんご", ""),
    ("cherry", "さくらんぼ", "macaroni", "warm", "体を温める果物: さくらんぼ", ""),
    ("grape", "ぶどう", "macaroni", "warm", "体を温める果物: ぶどう", ""),
    ("prune", "プルーン", "macaroni", "warm", "体を温める果物: プルーン", ""),
    ("orange", "オレンジ", "macaroni", "warm", "体を温める果物: オレンジ", ""),
    # -- warm そのほか(温) --
    ("chili pepper", "唐辛子", "macaroni", "warm", "体を温めるそのほか: 唐辛子", ""),
    ("spices", "香辛料", "macaroni", "warm", "体を温めるそのほか: 香辛料", ""),
    ("miso", "みそ", "macaroni", "warm", "体を温めるそのほか: みそ(発酵食品)", ""),
    ("black tea", "紅茶", "macaroni", "warm", "体を温めるそのほか: 紅茶(発酵食品)", ""),
    ("sake", "日本酒", "macaroni", "warm", "体を温めるそのほか: 日本酒(発酵食品)", ""),
    # -- cool 冷やす野菜 --
    ("lettuce", "レタス", "macaroni", "cool", "体を冷やす野菜: レタス", ""),
    ("cabbage", "キャベツ", "macaroni", "cool", "体を冷やす野菜: キャベツ", ""),
    ("chinese cabbage", "白菜", "macaroni", "cool", "体を冷やす野菜: 白菜", ""),
    ("spinach", "ほうれんそう", "macaroni", "cool", "体を冷やす野菜: ほうれんそう", ""),
    ("komatsuna", "小松菜", "macaroni", "cool", "体を冷やす野菜: 小松菜", ""),
    ("cucumber", "きゅうり", "macaroni", "cool", "体を冷やす野菜: きゅうり", ""),
    ("tomato", "トマト", "macaroni", "cool", "体を冷やす野菜: トマト", ""),
    ("eggplant", "なす", "macaroni", "cool", "体を冷やす野菜: なす", ""),
    # -- cool 冷やす果物 --
    ("mango", "マンゴー", "macaroni", "cool", "体を冷やす果物: マンゴー", ""),
    ("banana", "バナナ", "macaroni", "cool", "体を冷やす果物: バナナ", ""),
    ("pineapple", "パイナップル", "macaroni", "cool", "体を冷やす果物: パイナップル", ""),
    ("watermelon", "スイカ", "macaroni", "cool", "体を冷やす果物(本文): スイカも夏が旬", ""),
    ("melon", "メロン", "macaroni", "cool", "体を冷やす果物(本文): メロンも夏が旬", ""),
    # -- cool そのほか(冷) --
    ("vinegar", "酢", "macaroni", "cool", "体を冷やすそのほか: 酢", ""),
    ("mayonnaise", "マヨネーズ", "macaroni", "cool", "体を冷やすそのほか: マヨネーズ", ""),
    ("beer", "ビール", "macaroni", "cool", "体を冷やすそのほか: ビール", ""),
    ("coffee", "コーヒー", "macaroni", "cool", "体を冷やすそのほか: コーヒー", ""),
    ("green tea", "緑茶", "macaroni", "cool", "体を冷やすそのほか: 緑茶", ""),
    ("white sugar", "白砂糖", "macaroni", "cool", "チョコレートの項: 白砂糖は体を冷やす食材", ""),

    # ==================================================================
    # oitr (Tier 1) いつでもオイテル (IBGメディア)
    #   薬膳「陽性食品」=warm(6カテゴリ表)。体を冷やしやすい食材=cool。
    #   「冷たい飲み物・アイス」は提供温度カテゴリなので除外(protocol §3)。
    # ==================================================================
    # -- warm 根菜・冬野菜 --
    ("carrot", "にんじん", "oitr", "warm", "体を温める食材(陽性)＞根菜・冬野菜: にんじん", ""),
    ("burdock", "ごぼう", "oitr", "warm", "体を温める食材(陽性)＞根菜・冬野菜: ごぼう", ""),
    ("lotus root", "れんこん", "oitr", "warm", "体を温める食材(陽性)＞根菜・冬野菜: れんこん", ""),
    ("pumpkin", "かぼちゃ", "oitr", "warm", "体を温める食材(陽性)＞根菜・冬野菜: かぼちゃ", ""),
    ("sweet potato", "さつまいも", "oitr", "warm", "体を温める食材(陽性)＞根菜・冬野菜: さつまいも", ""),
    ("daikon", "大根", "oitr", "warm", "体を温める食材(陽性)＞根菜・冬野菜: 大根", ""),
    # -- warm 薬味・香味野菜 --
    ("ginger", "生姜", "oitr", "warm", "体を温める食材(陽性)＞薬味・香味野菜: 生姜", ""),
    ("garlic", "にんにく", "oitr", "warm", "体を温める食材(陽性)＞薬味・香味野菜: にんにく", ""),
    ("green onion", "ねぎ", "oitr", "warm", "体を温める食材(陽性)＞薬味・香味野菜: ねぎ", ""),
    ("onion", "玉ねぎ", "oitr", "warm", "体を温める食材(陽性)＞薬味・香味野菜: 玉ねぎ", ""),
    ("nira", "にら", "oitr", "warm", "体を温める食材(陽性)＞薬味・香味野菜: にら", ""),
    ("myoga", "みょうが", "oitr", "warm", "体を温める食材(陽性)＞薬味・香味野菜: みょうが", ""),
    # -- warm 発酵食品 --
    ("miso", "味噌", "oitr", "warm", "体を温める食材(陽性)＞発酵食品: 味噌", ""),
    ("natto", "納豆", "oitr", "warm", "体を温める食材(陽性)＞発酵食品: 納豆", ""),
    ("amazake", "甘酒", "oitr", "warm", "体を温める食材(陽性)＞発酵食品: 甘酒", ""),
    ("kimchi", "キムチ", "oitr", "warm", "体を温める食材(陽性)＞発酵食品: キムチ", ""),
    ("nukazuke", "ぬか漬け", "oitr", "warm", "体を温める食材(陽性)＞発酵食品: ぬか漬け", ""),
    ("shio koji", "塩麹", "oitr", "warm", "体を温める食材(陽性)＞発酵食品: 塩麹", ""),
    # -- warm スパイス・調味料 --
    ("cinnamon", "シナモン", "oitr", "warm", "体を温める食材(陽性)＞スパイス・調味料: シナモン", ""),
    ("chili pepper", "唐辛子", "oitr", "warm", "体を温める食材(陽性)＞スパイス・調味料: 唐辛子", ""),
    ("pepper", "こしょう", "oitr", "warm", "体を温める食材(陽性)＞スパイス・調味料: こしょう", ""),
    ("curry powder", "カレー粉", "oitr", "warm", "体を温める食材(陽性)＞スパイス・調味料: カレー粉", ""),
    ("sansho", "山椒", "oitr", "warm", "体を温める食材(陽性)＞スパイス・調味料: 山椒", ""),
    ("sesame", "ごま", "oitr", "warm", "体を温める食材(陽性)＞スパイス・調味料: ごま", ""),
    # -- warm たんぱく質 --
    ("chicken", "鶏肉", "oitr", "warm", "体を温める食材(陽性)＞たんぱく質: 鶏肉", ""),
    ("pork", "豚肉", "oitr", "warm", "体を温める食材(陽性)＞たんぱく質: 豚肉", ""),
    ("mackerel", "サバ", "oitr", "warm", "体を温める食材(陽性)＞たんぱく質: サバ", ""),
    ("sardine", "イワシ", "oitr", "warm", "体を温める食材(陽性)＞たんぱく質: イワシ", ""),
    ("egg", "卵", "oitr", "warm", "体を温める食材(陽性)＞たんぱく質: 卵", ""),
    ("tofu", "豆腐", "oitr", "warm", "体を温める食材(陽性)＞たんぱく質: 大豆製品(豆腐)", ""),
    # -- warm 寒冷地の果物・ナッツ --
    ("apple", "りんご", "oitr", "warm", "体を温める食材(陽性)＞寒冷地の果物・ナッツ: りんご", ""),
    ("grape", "ぶどう", "oitr", "warm", "体を温める食材(陽性)＞寒冷地の果物・ナッツ: ぶどう", ""),
    ("jujube", "なつめ", "oitr", "warm", "体を温める食材(陽性)＞寒冷地の果物・ナッツ: なつめ", ""),
    ("walnut", "くるみ", "oitr", "warm", "体を温める食材(陽性)＞寒冷地の果物・ナッツ: くるみ", ""),
    ("almond", "アーモンド", "oitr", "warm", "体を温める食材(陽性)＞寒冷地の果物・ナッツ: アーモンド", ""),
    ("black sesame", "黒ごま", "oitr", "warm", "体を温める食材(陽性)＞寒冷地の果物・ナッツ: 黒ごま", ""),
    # -- cool 体を冷やしやすい食材 --
    ("tomato", "トマト", "oitr", "cool", "体を冷やしやすい食材＞夏野菜: トマト", ""),
    ("cucumber", "きゅうり", "oitr", "cool", "体を冷やしやすい食材＞夏野菜: きゅうり", ""),
    ("eggplant", "なす", "oitr", "cool", "体を冷やしやすい食材＞夏野菜: なす", ""),
    ("bitter melon", "ゴーヤ", "oitr", "cool", "体を冷やしやすい食材＞夏野菜: ゴーヤ", ""),
    ("banana", "バナナ", "oitr", "cool", "体を冷やしやすい食材＞南国の果物(陰性): バナナ", ""),
    ("mango", "マンゴー", "oitr", "cool", "体を冷やしやすい食材＞南国の果物(陰性): マンゴー", ""),
    ("pineapple", "パイナップル", "oitr", "cool", "体を冷やしやすい食材＞南国の果物(陰性): パイナップル", ""),
    ("kiwi", "キウイ", "oitr", "cool", "体を冷やしやすい食材＞南国の果物(陰性): キウイ", ""),
    ("white sugar", "白砂糖", "oitr", "cool", "体を冷やしやすい食材: 白砂糖・精製食品", ""),

    # ==================================================================
    # kawashimaya (Tier 1) かわしま屋 Food for Well-being
    #   体を温める食材一覧(表)=warm。体を冷やしやすい食べ物一覧(表)=cool。
    #   「冷たい食べ物」(アイス/かき氷/そうめん等)は提供温度カテゴリなので除外。
    # ==================================================================
    # -- warm 根菜類などの冬野菜 --
    ("carrot", "にんじん", "kawashimaya", "warm", "体を温める食べ物一覧＞根菜類などの冬野菜: にんじん", ""),
    ("burdock", "ごぼう", "kawashimaya", "warm", "体を温める食べ物一覧＞根菜類などの冬野菜: ごぼう", ""),
    ("lotus root", "れんこん", "kawashimaya", "warm", "体を温める食べ物一覧＞根菜類などの冬野菜: れんこん", ""),
    ("daikon", "だいこん", "kawashimaya", "warm", "体を温める食べ物一覧＞根菜類などの冬野菜: だいこん", ""),
    ("pumpkin", "かぼちゃ", "kawashimaya", "warm", "体を温める食べ物一覧＞根菜類などの冬野菜: かぼちゃ", ""),
    # -- warm たんぱく質が多い食材 --
    ("chicken", "鶏肉", "kawashimaya", "warm", "体を温める食べ物一覧＞たんぱく質: 鶏肉", ""),
    ("beef", "牛肉", "kawashimaya", "warm", "体を温める食べ物一覧＞たんぱく質: 牛肉", ""),
    ("pork", "豚肉", "kawashimaya", "warm", "体を温める食べ物一覧＞たんぱく質: 豚肉", ""),
    ("lamb", "羊肉", "kawashimaya", "warm", "体を温める食べ物一覧＞たんぱく質: 羊肉", ""),
    ("salmon", "鮭", "kawashimaya", "warm", "体を温める食べ物一覧＞たんぱく質: 鮭", ""),
    ("mackerel", "サバ", "kawashimaya", "warm", "体を温める食べ物一覧＞たんぱく質: サバ", ""),
    ("horse mackerel", "アジ", "kawashimaya", "warm", "体を温める食べ物一覧＞たんぱく質: アジ", ""),
    ("sardine", "イワシ", "kawashimaya", "warm", "体を温める食べ物一覧＞たんぱく質: イワシ", ""),
    ("tuna", "マグロ", "kawashimaya", "warm", "体を温める食べ物一覧＞たんぱく質: マグロ", ""),
    ("egg", "卵", "kawashimaya", "warm", "体を温める食べ物一覧＞たんぱく質: 卵", ""),
    ("tofu", "豆腐", "kawashimaya", "warm", "体を温める食べ物一覧＞たんぱく質: 豆腐", ""),
    ("atsuage", "厚揚げ", "kawashimaya", "warm", "体を温める食べ物一覧＞たんぱく質: 厚揚げ", ""),
    # -- warm 香味野菜・スパイス --
    ("ginger", "しょうが", "kawashimaya", "warm", "体を温める食べ物一覧＞香味野菜・スパイス: しょうが", ""),
    ("garlic", "にんにく", "kawashimaya", "warm", "体を温める食べ物一覧＞香味野菜・スパイス: にんにく", ""),
    ("green onion", "ねぎ", "kawashimaya", "warm", "体を温める食べ物一覧＞香味野菜・スパイス: ねぎ", ""),
    ("chili pepper", "唐辛子", "kawashimaya", "warm", "体を温める食べ物一覧＞香味野菜・スパイス: 唐辛子", ""),
    ("cinnamon", "シナモン", "kawashimaya", "warm", "体を温める食べ物一覧＞香味野菜・スパイス: シナモン", ""),
    # -- warm 発酵食品 --
    ("natto", "納豆", "kawashimaya", "warm", "体を温める食べ物一覧＞発酵食品: 納豆", ""),
    ("miso", "味噌", "kawashimaya", "warm", "体を温める食べ物一覧＞発酵食品: 味噌", ""),
    ("soy sauce", "醤油", "kawashimaya", "warm", "体を温める食べ物一覧＞発酵食品: 醤油", ""),
    ("tsukemono", "漬物", "kawashimaya", "warm", "体を温める食べ物一覧＞発酵食品: 漬物", ""),
    ("kimchi", "キムチ", "kawashimaya", "warm", "体を温める食べ物一覧＞発酵食品: キムチ", ""),
    # -- warm 寒冷地の果物 --
    ("apple", "りんご", "kawashimaya", "warm", "体を温める食べ物一覧＞寒冷地の果物: りんご", ""),
    ("grape", "ぶどう", "kawashimaya", "warm", "体を温める食べ物一覧＞寒冷地の果物: ぶどう", ""),
    ("cherry", "さくらんぼ", "kawashimaya", "warm", "体を温める食べ物一覧＞寒冷地の果物: さくらんぼ", ""),
    ("peach", "もも", "kawashimaya", "warm", "体を温める食べ物一覧＞寒冷地の果物: もも", ""),
    ("apricot", "あんず", "kawashimaya", "warm", "体を温める食べ物一覧＞寒冷地の果物: あんず", ""),
    # -- cool 夏野菜 --
    ("cucumber", "きゅうり", "kawashimaya", "cool", "体を冷やしやすい食べ物一覧＞夏野菜: きゅうり", ""),
    ("tomato", "トマト", "kawashimaya", "cool", "体を冷やしやすい食べ物一覧＞夏野菜: トマト", ""),
    ("eggplant", "ナス", "kawashimaya", "cool", "体を冷やしやすい食べ物一覧＞夏野菜: ナス", ""),
    ("lettuce", "レタス", "kawashimaya", "cool", "体を冷やしやすい食べ物一覧＞夏野菜: レタス", ""),
    ("bell pepper", "ピーマン", "kawashimaya", "cool", "体を冷やしやすい食べ物一覧＞夏野菜: ピーマン", ""),
    ("zucchini", "ズッキーニ", "kawashimaya", "cool", "体を冷やしやすい食べ物一覧＞夏野菜: ズッキーニ", ""),
    # -- cool 南国の果物 --
    ("banana", "バナナ", "kawashimaya", "cool", "体を冷やしやすい食べ物一覧＞南国の果物: バナナ", ""),
    ("pineapple", "パイナップル", "kawashimaya", "cool", "体を冷やしやすい食べ物一覧＞南国の果物: パイナップル", ""),
    ("mango", "マンゴー", "kawashimaya", "cool", "体を冷やしやすい食べ物一覧＞南国の果物: マンゴー", ""),
    ("watermelon", "スイカ", "kawashimaya", "cool", "体を冷やしやすい食べ物一覧＞南国の果物: スイカ", ""),
    ("melon", "メロン", "kawashimaya", "cool", "体を冷やしやすい食べ物一覧＞南国の果物: メロン", ""),

    # ==================================================================
    # basefood (Tier 1) BASE FOOD HEALTH MAGAZINE
    #   陽=warm / 陰=cool(色・産地・形状・水分量の表)。個別食材+飲み物節。
    #   コーヒー=cool を「温活で控えた方がよい飲み物」で明記(coffee確認源)。
    # ==================================================================
    # -- warm 根菜類 --
    ("carrot", "ニンジン", "basefood", "warm", "効率的に体を温める食べ物＞根菜類: ニンジン", ""),
    ("pumpkin", "カボチャ", "basefood", "warm", "効率的に体を温める食べ物＞根菜類: カボチャ", ""),
    ("burdock", "ゴボウ", "basefood", "warm", "効率的に体を温める食べ物＞根菜類: ゴボウ", ""),
    ("lotus root", "れんこん", "basefood", "warm", "効率的に体を温める食べ物＞根菜類: れんこん", ""),
    ("potato", "ジャガイモ", "basefood", "warm", "効率的に体を温める食べ物＞根菜類: ジャガイモ", ""),
    ("taro", "サトイモ", "basefood", "warm", "効率的に体を温める食べ物＞根菜類: サトイモ", ""),
    # -- warm 発酵食品 --
    ("miso", "味噌", "basefood", "warm", "効率的に体を温める食べ物＞発酵食品: 味噌(赤味噌)", ""),
    ("natto", "納豆", "basefood", "warm", "効率的に体を温める食べ物＞発酵食品: 納豆", ""),
    ("kimchi", "キムチ", "basefood", "warm", "効率的に体を温める食べ物＞発酵食品: キムチ", ""),
    # -- warm たんぱく質 --
    ("beef", "牛肉", "basefood", "warm", "効率的に体を温める食べ物＞たんぱく質: 牛肉", ""),
    ("chicken", "鶏肉", "basefood", "warm", "効率的に体を温める食べ物＞たんぱく質: 鶏肉", ""),
    ("pork", "豚肉", "basefood", "warm", "効率的に体を温める食べ物＞たんぱく質: 豚肉", ""),
    ("salmon", "鮭", "basefood", "warm", "効率的に体を温める食べ物＞たんぱく質: 鮭", ""),
    ("tuna", "マグロ", "basefood", "warm", "効率的に体を温める食べ物＞たんぱく質: マグロ", ""),
    ("bonito", "カツオ", "basefood", "warm", "効率的に体を温める食べ物＞たんぱく質: カツオ", ""),
    ("egg", "卵", "basefood", "warm", "効率的に体を温める食べ物＞たんぱく質: 卵", ""),
    # -- warm スパイス・薬味 --
    ("ginger", "生姜", "basefood", "warm", "効率的に体を温める食べ物＞スパイス・薬味: 生姜", ""),
    ("chili pepper", "唐辛子", "basefood", "warm", "効率的に体を温める食べ物＞スパイス・薬味: 唐辛子", ""),
    ("cinnamon", "シナモン", "basefood", "warm", "効率的に体を温める食べ物＞スパイス・薬味: シナモン", ""),
    ("garlic", "ニンニク", "basefood", "warm", "効率的に体を温める食べ物＞スパイス・薬味: ニンニク", ""),
    ("green onion", "ネギ", "basefood", "warm", "効率的に体を温める食べ物＞スパイス・薬味: ネギ", ""),
    # -- warm フルーツ(冬が旬) --
    ("apple", "リンゴ", "basefood", "warm", "フルーツの選び方: リンゴなど冬が旬のものは体を冷やしにくい", ""),
    ("grape", "ブドウ", "basefood", "warm", "フルーツの選び方: ブドウなど冬が旬のものは体を冷やしにくい", ""),
    ("prune", "プルーン", "basefood", "warm", "フルーツの選び方: プルーンなど冬が旬のものは体を冷やしにくい", ""),
    # -- warm 飲み物(発酵茶) --
    ("hojicha", "ほうじ茶", "basefood", "warm", "飲み物の選び方: 温活向き ほうじ茶", ""),
    ("black tea", "紅茶", "basefood", "warm", "飲み物の選び方: 発酵茶(紅茶)は体を温めやすい", ""),
    ("oolong tea", "ウーロン茶", "basefood", "warm", "飲み物の選び方: 発酵茶(ウーロン茶)は体を温めやすい", ""),
    ("cocoa", "ココア", "basefood", "warm", "飲み物の選び方: 温活向き ココア", ""),
    # NOTE: てんさい糖/はちみつ/玄米/そば were previously coded warm here but
    # DROPPED after inter-coder reconciliation (2026-08-04, kappa pass): the
    # source (L172-173 "白い食べ物と糖質対策") only recommends them as
    # substitutes for white sugar/refined flour ("置き換えるのも有効") and does
    # NOT assign them a warming nature. Coding them warm violated protocol §3
    # (do not infer a direction the source does not state). Coder 2 correctly
    # omitted them.
    # -- cool 南国系フルーツ --
    ("banana", "バナナ", "basefood", "cool", "フルーツの選び方: バナナなど南国系は体の熱を落ち着かせる", ""),
    ("mango", "マンゴー", "basefood", "cool", "フルーツの選び方: マンゴーなど南国系は体の熱を落ち着かせる", ""),
    ("pineapple", "パイナップル", "basefood", "cool", "フルーツの選び方: パイナップルなど南国系は体の熱を落ち着かせる", ""),
    # -- cool 飲み物 --
    ("coffee", "コーヒー", "basefood", "cool", "飲み物の選び方: 温活で控えた方がよい=コーヒー(体を冷やしやすい)", ""),
    ("green tea", "緑茶", "basefood", "cool", "飲み物の選び方: 温活で控えた方がよい=緑茶(体を冷やしやすい)", ""),
    ("mugicha", "麦茶", "basefood", "cool", "飲み物の選び方: 温活で控えた方がよい=麦茶(体を冷やしやすい)", ""),
    # -- cool 白い食べ物 --
    ("white sugar", "白砂糖", "basefood", "cool", "白い食べ物と糖質対策: 白砂糖は冷えを感じやすくする", ""),
]


def main() -> None:
    df = pd.DataFrame(CLAIMS, columns=COLUMNS)
    df.to_csv(CLAIMS_CSV, index=False)
    print(f"wrote {len(df)} claims to {CLAIMS_CSV}")


if __name__ == "__main__":
    main()
