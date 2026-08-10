import os
import time
from datetime import datetime
import requests

TXT_FILE = "codes.txt"

# 1. 実行した「今日」の日付（JST）を用意
# J-Quantsのデータ形式（YYYY-MM-DD）に合わせます (例: "2026-08-10")
TODAY_STR = datetime.now().strftime("%Y-%m-%d")

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
            # 4桁コードをそのまま格納
            codes.append(clean_line)
    return codes


def main():
    company_codes = load_company_codes(TXT_FILE)
    if not company_codes:
        print("【エラー】codes.txt に有効な証券コードが記載されていません。")
        return

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"result_{now_str}.txt"

    # 日本取引所グループ（東証公式）J-Quants配信の「当日の全適時開示一覧」JSON（最速・リアルタイム）
    url = "https://jquants.co.jp"

    hit_records = {}

    print(
        f"【開始】東証公式J-Quantsデータから本日（{TODAY_STR}）の適時開示を照合中..."
    )

    try:
        # 当日分のデータを一括で取得
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        raw_data = response.json()

        # JSONの配列（全銘柄の開示が1つのリストにまとまっている）を取得
        disclosures = raw_data.get("disclosures", raw_data.get("data", raw_data))
        if not isinstance(disclosures, list):
            # 万が一データが直下にある場合のセーフティ
            disclosures = []

        for item in disclosures:
            if not isinstance(item, dict):
                continue

            # 証券コードの取得（東証公式データは4桁単体か、末尾0付きの5桁）
            raw_code = str(item.get("LocalCode", item.get("code", "")))
            short_code = raw_code[:4]  # 先頭4桁を抽出

            # 監視している証券コードリストに含まれているかチェック
            if short_code in company_codes:
                # 配信日時のチェック
                pub_date = item.get("DisclosedDate", item.get("date", ""))

                # 本日発表分のみに絞り込む
                if TODAY_STR in pub_date:
                    time_str = item.get("DisclosedTime", item.get("time", ""))
                    company_name = item.get(
                        "CompanyName", item.get("name", "企業名不明")
                    )
                    title = item.get("Title", item.get("title", "タイトルなし"))

                    # PDFの閲覧用URL（J-Quantsは開示番号から公式TDnetへ直接リンクさせます）
                    pdf_id = item.get("DisclosureNumber", item.get("id", ""))
                    pdf_url = (
                        f"https://tdnet.info{pdf_id}.pdf"
                        if pdf_id
                        else "URLなし"
                    )

                    record = f"[{time_str}] {company_name}\n  {title}\n  URL: {pdf_url}\n"

                    if short_code not in hit_records:
                        hit_records[short_code] = []
                    hit_records[short_code].append(record)

    except Exception as e:
        print(f"【デバッグエラー】データ取得・解析に失敗: {e}")

    # 結果の書き出し
    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write(f"=== 東証J-Quants公式 適時開示 取得結果 ===\n")
        f_out.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write(f"抽出条件: {TODAY_STR} 発表分\n")
        f_out.write("==================================================\n\n")

        if hit_records:
            for code, records in hit_records.items():
                f_out.write(f"=== 証券コード: {code} ===\n")
                for r in records:
                    f_out.write(r)
                f_out.write("\n")
        else:
            f_out.write(
                f"本日（{TODAY_STR}）、監視対象銘柄の適時開示はありませんでした。\n"
            )

    print(f"【完了】すべて終了しました！ 結果ファイル: {output_file}")


if __name__ == "__main__":
    main()
