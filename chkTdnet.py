import os
import time
from datetime import datetime
import requests

TXT_FILE = "codes.txt"

# 1. 実行した「今日」の日付（JST）を用意 (例: "2026/08/10")
TODAY_SLASH = datetime.now().strftime("%Y/%m/%d")

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
        f"【開始】SBI証券バックエンドから本日（{TODAY_SLASH}）の適時開示を照合中..."
    )

    for idx, code in enumerate(company_codes, start=1):
        print(f" {idx}/{len(company_codes)} 件目チェック中... (コード: {code})")

        # SBI証券が提供している、各銘柄の適時開示情報JSONデータ（ブロックされず確実に最新が取れます）
        url = f"https://sbisec.co.jp_{code}.html"

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            # HTML（内部構造はシンプルなリスト形式）を解析
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")

            # 開示情報の各行を取得
            rows = soup.find_all("tr")
            code_hits = []

            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    # 1列目: 日付と時間 (例: "2026/08/10 14:30")
                    date_time_text = cols[0].get_text(strip=True)
                    # 2列目: タイトルとPDFリンク
                    title_a = cols[1].find("a")

                    if title_a and date_time_text:
                        # 日付部分（先頭10文字）が本日（TODAY_SLASH）と一致するかチェック
                        if date_time_text.startswith(TODAY_SLASH):
                            title_text = title_a.get_text(strip=True)
                            pdf_url = title_a["href"]

                            record = f"[{date_time_text}] \n  {title_text}\n  URL: {pdf_url}\n"
                            if record not in code_hits:
                                code_hits.append(record)

            if code_hits:
                hit_records[code] = code_hits

        except Exception as e:
            print(f"【エラー】コード {code} の取得に失敗: {e}")

        # サーバー負荷軽減のため1秒待機
        time.sleep(1)

    # 結果の書き出し
    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write(f"=== 適時開示 取得結果 (SBIバックエンド版) ===\n")
        f_out.write(
            f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        f_out.write(f"抽出条件: {TODAY_SLASH} 発表分\n")
        f_out.write("==================================================\n\n")

        if hit_records:
            for code, records in hit_records.items():
                f_out.write(f"=== 証券コード: {code} ===\n")
                for r in records:
                    f_out.write(r)
                f_out.write("\n")
        else:
            f_out.write(
                f"本日（{TODAY_SLASH}）、監視対象銘柄の適時開示はありませんでした。\n"
            )

    print(f"【完了】すべて終了しました！ 結果ファイル: {output_file}")


if __name__ == "__main__":
    main()
