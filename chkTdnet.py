import os
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

TXT_FILE = "codes.txt"

# 東証TDnetの仕様に合わせ、今日（JST）の日付を取得
# 本日（2026/08/10）の場合、TDnet上は「08/10」または「2026/08/10」で表示されます
TODAY_MMDD = datetime.now().strftime("%m/%d")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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

    # 東証公式の適時開示一覧ページ（当日分を含む直近データがすべて載っているページ）
    url = "https://tdnet.info"

    hit_records = {}

    print(
        f"【開始】東証公式TDnetから本日（{TODAY_MMDD}）の開示情報を照合中..."
    )

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # 文字化け対策（東証はShift_JISで書かれているため明示的に変換）
        response.encoding = "shift_jis"

        soup = BeautifulSoup(response.text, "html.parser")

        # 開示情報のテーブル（表）の行をすべて取得
        # TDnetは1つの開示情報が1つの<tr>タグにまとまっています
        rows = soup.find_all("tr")

        for row in rows:
            row_text = row.get_text()

            # 監視している証券コード（4桁）がその行に含まれているかチェック
            for code in company_codes:
                if code in row_text:
                    # その行から「時間」「会社名」「タイトル」「PDFのURL」を抽出
                    time_elem = row.find("td", class_="yjSt")
                    time_text = (
                        time_elem.get_text(strip=True) if time_elem else ""
                    )

                    # 本日の日付データ、または時間の記述があるか確認
                    # TDnetの仕様上、当日分は「14:30」のように時間だけ表示されます
                    title_a = row.find("a", class_="kaijiTitle")
                    if title_a:
                        title_text = title_a.get_text(strip=True)
                        pdf_link = "https://tdnet.info" + title_a["href"]

                        company_elem = row.find("td", class_="yjM")
                        company_name = (
                            company_elem.get_text(strip=True)
                            if company_elem
                            else "企業名不明"
                        )

                        record = f"[{time_text}] {company_name}\n  {title_text}\n  URL: {pdf_link}\n"

                        if code not in hit_records:
                            hit_records[code] = []
                        if record not in hit_records[code]:
                            hit_records[code].append(record)

    except Exception as e:
        print(f"【エラー】TDnetの解析に失敗しました: {e}")

    # 結果の書き出し
    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write(f"=== 東証公式 TDnet適時開示 取得結果 ===\n")
        f_out.write(
            f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        f_out.write("==================================================\n\n")

        if hit_records:
            for code, records in hit_records.items():
                f_out.write(f"=== 証券コード: {code} ===\n")
                for r in records:
                    f_out.write(r)
                f_out.write("\n")
        else:
            f_out.write(
                f"本日、監視対象銘柄（{', '.join(company_codes)}）の適時開示はありませんでした（または発表時間外です）。\n"
            )

    print(f"【完了】すべて終了しました！ 結果ファイル: {output_file}")


if __name__ == "__main__":
    main()
