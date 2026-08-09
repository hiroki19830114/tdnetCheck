import json
import os
import time
from datetime import datetime
import requests

TXT_FILE = "codes.txt"

# 1. 実行した「今日」の日付を自動計算（例: "2026-08-09" 形式と "2026/08/09" 形式を用意）
TODAY_HYPHEN = datetime.now().strftime("%Y-%m-%d")
TODAY_SLASH = datetime.now().strftime("%Y/%m/%d")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


# ファイルから証券コードのリストを読み込む関数（GitHub用安全版）
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

    # 保存用のファイル名 (例: result_20260809_180000.txt)
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"result_{now_str}.txt"

    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write(f"=== TDnet適時開示 取得結果 ===\n")
        f_out.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write(f"抽出条件: {TODAY_HYPHEN}（本日発表分のみ）\n")
        f_out.write(f"対象銘柄数: {len(company_codes)} 件\n")
        f_out.write("===============================\n\n")

        print(
            f"【開始】{len(company_codes)}件の銘柄をチェック中...（本日発表分を {output_file} に保存します）"
        )

        for idx, code in enumerate(company_codes, start=1):
            if idx % 10 == 0:
                print(f" {idx}/{len(company_codes)} 件目処理中...")

            # 毎日実行であれば、直近の最新「15件」を取得すれば当日の開示はすべてカバーできます
            url = f"https://yanoshin.jp{code}.json?limit=15"

            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 404:
                    continue
                response.raise_for_status()
                raw_data = response.json()

                items = []
                if isinstance(raw_data, dict):
                    items = raw_data.get("items", raw_data.get("item", []))
                elif isinstance(raw_data, list):
                    items = raw_data

                if not items:
                    continue

                filtered_outputs = []

                for item in items:
                    tdnet_data = {}
                    if isinstance(item, str):
                        try:
                            tdnet_data = json.loads(item)
                        except Exception:
                            continue
                    elif isinstance(item, dict):
                        tdnet_data = item.get("Tdnet", item)

                    pub_date_str = tdnet_data.get("pubdate", "")
                    company_name = tdnet_data.get("company_name", "企業名不明")
                    title = tdnet_data.get("title", "タイトルなし")
                    pdf_url = tdnet_data.get("document_url", "URLなし")

                    # 一致チェック：日付文字列の先頭10文字が「今日」かどうか
                    if pub_date_str:
                        item_date_prefix = pub_date_str[:10]
                        # ハイフン形式、またはスラッシュ形式の「今日」でなければスキップ
                        if (item_date_prefix != TODAY_HYPHEN) and (
                            item_date_prefix != TODAY_SLASH
                        ):
                            continue

                    filtered_outputs.append(
                        f"[{pub_date_str}] {company_name}\n  {title}\n  URL: {pdf_url}\n"
                    )

                if filtered_outputs:
                    f_out.write(f"=== 証券コード: {code} ===\n")
                    for output in filtered_outputs:
                        f_out.write(output)
                    f_out.write("\n")

            except Exception:
                pass

            # 1秒待機
            time.sleep(1)

        f_out.write("\n【完了】すべてのチェックが終了しました。\n")

    print(f"\n【完了】すべて終了しました！ 結果ファイル: {output_file}")


if __name__ == "__main__":
    main()
