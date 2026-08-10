import os
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

TXT_FILE = "codes.txt"

# 今日（JST）の日付を取得（例: "08/10" の形式）
# Yahoo!ファイナンスのニュース日付表示「08/10 14:31」に合わせるため
TODAY_MMDD = datetime.now().strftime("%m/%d")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def load_company_codes(file_path):
    if not os.path.exists(file_path):
        print(f"【エラー】{file_path} が見つかりません。")
        return []

    codes = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            clean_line = line.strip()
            if not clean_line or clean_line.startswith("#"):
                continue
            codes.append(clean_line)
    return codes


def main():
    company_codes = load_company_codes(TXT_FILE)
    if not company_codes:
        print("【エラー】codes.txt に有効な証券コードが記載されていません。")
        return

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"result_{now_str}.txt"

    hit_records = {}

    print(
        f"【開始】{len(company_codes)}件の銘柄のYahoo!ニュースをチェック中...（本日 {TODAY_MMDD} 発表分）"
    )

    for idx, code in enumerate(company_codes, start=1):
        # 4桁のコードをそのまま利用
        print(f" {idx}/{len(company_codes)} 件目処理中... (コード: {code})")

        # Yahoo!ファイナンスの対象銘柄ニュースページURL
        url = f"https://finance.yahoo.co.jp/quote/{code}.T/news"

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            # HTML解析
            soup = BeautifulSoup(response.text, "html.parser")

            # ニュースの各行（aタグでラップされたニュースタイトルと日付の入った要素を探索）
            # Yahooの現在の仕様に合わせ、ニュースリストのアイテム要素を抽出
            articles = soup.find_all("li", class_=lambda x: x and "NewsList_item" in x)

            # 古いデザインや予期せぬ構成向けの汎用フォールバック
            if not articles:
                articles = soup.find_all("li")

            code_hits = []

            for article in articles:
                # タイトルテキストの取得
                title_elem = article.find("h1") or article.find("p") or article
                title_text = title_elem.get_text(strip=True) if title_elem else ""

                # リンクの取得
                a_tag = article.find("a") if hasattr(article, "find") else None
                link_url = a_tag["href"] if a_tag and a_tag.has_attr("href") else url
                if link_url.startswith("/"):
                    link_url = f"https://finance.yahoo.co.jp{link_url}"

                # 配信時間の取得
                time_elem = article.find("time") or article.find(
                    "span", class_=lambda x: x and "time" in x.lower()
                )
                time_text = time_elem.get_text(strip=True) if time_elem else ""

                # 【デバッグ用フォールバック】テキスト全体から時間を探す
                if not time_text:
                    whole_text = article.get_text()
                    # "08/10 14:31" のようなパターンが含まれるか簡易チェック
                    if "/" in whole_text and ":" in whole_text:
                        time_text = whole_text

                # 「今日(TODAY_MMDD)」の日付がニュース時間内に含まれており、かつ「決算」や「開示」に関する速報ならヒット
                if TODAY_MMDD in time_text:
                    if (
                        "決算" in title_text
                        or "速報" in title_text
                        or "開示" in title_text
                        or "短信" in title_text
                    ):
                        record = f"[{time_text}] {title_text}\n  URL: {link_url}\n"
                        # 重複追加を防ぐ
                        if record not in code_hits:
                            code_hits.append(record)

            if code_hits:
                hit_records[code] = code_hits

        except Exception as e:
            print(f"【デバッグエラー】コード {code} の解析に失敗: {e}")

        # 連続アクセス対策で2秒待機
        time.sleep(2)

    # 結果の書き出し
    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write(f"=== TDnet/決算速報 取得結果 (Yahoo直接スクレイピング版) ===\n")
        f_out.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write(f"抽出日条件: {TODAY_MMDD}\n")
        f_out.write("=======================================================\n\n")

        if hit_records:
            for code, records in hit_records.items():
                f_out.write(f"=== 証券コード: {code} ===\n")
                for r in records:
                    f_out.write(r)
                f_out.write("\n")
        else:
            f_out.write(f"本日（{TODAY_MMDD}）に対象銘柄の決算・適時開示速報はありませんでした。\n")

    print(f"【完了】すべて終了しました！ 結果ファイル: {output_file}")


if __name__ == "__main__":
    main()
