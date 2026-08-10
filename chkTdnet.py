import os
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

TXT_FILE = "codes.txt"

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

    # 【修正】GitHub Actionsでの誤判定を防ぐため、出力ファイル名を「result.txt」に完全固定します
    output_file = "result.txt"

    hit_records = {}

    print(
        f"【開始】株探(Kabutan)データから最新の適時開示・決算情報を抽出中..."
    )

    for idx, code in enumerate(company_codes, start=1):
        print(f" {idx}/{len(company_codes)} 件目チェック中... (コード: {code})")

        # 確実にブロックされず、過去ログも保持している株探の適時開示ページ
        url = f"https://kabutan.jp{code}&b=k"

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 適時開示・ニュースの一覧テーブルを取得
            table = soup.find("table", class_="news_list")
            if not table:
                continue

            rows = table.find_all("tr")
            code_hits = []

            # 直近で発表された上位5件をそのまま取得
            count = 0
            for row in rows:
                if count >= 5:  # 最新の5件に絞る
                    break

                time_elem = row.find("time")
                if not time_elem:
                    continue

                time_text = time_elem.get_text(strip=True)

                # タイトルとURL
                td_title = row.find("td", class_="news_title")
                if td_title:
                    a_tag = td_title.find("a")
                    if a_tag:
                        title_text = a_tag.get_text(strip=True)
                        link_url = "https://kabutan.jp" + a_tag["href"]

                        record = f"[{time_text}] {title_text}\n  URL: {link_url}\n"
                        code_hits.append(record)
                        count += 1

            if code_hits:
                hit_records[code] = code_hits

        except Exception as e:
            print(f"【エラー】コード {code} の取得に失敗: {e}")

        time.sleep(1)

    # 結果の書き出し
    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write(f"=== 適時開示・決算速報 取得結果 (確実版) ===\n")
        f_out.write(
            f"実行日時(JST): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        f_out.write("==================================================\n\n")

        if hit_records:
            for code, records in hit_records.items():
                f_out.write(f"=== 証券コード: {code} ===\n")
                for r in records:
                    f_out.write(r)
                f_out.write("\n")
        else:
            f_out.write("監視対象銘柄の開示情報が見つかりませんでした。\n")

    print(f"【完了】すべて終了しました！ 結果ファイル: {output_file}")


if __name__ == "__main__":
    main()
