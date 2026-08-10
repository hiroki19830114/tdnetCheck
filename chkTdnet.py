import json
import os
import time
from datetime import datetime
import requests

TXT_FILE = "codes.txt"

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

    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write(f"=== TDnet適時開示 取得結果 ===\n")
        f_out.write(f"実行日時(UTC/環境時間): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write(f"抽出条件: 直近の開示をそのまま取得（反映ラグ・タイムゾーン対策版）\n")
        f_out.write(f"対象銘柄数: {len(company_codes)} 件\n")
        f_out.write("===============================\n\n")

        print(f"【開始】{len(company_codes)}件の銘柄をチェック中... 結果を {output_file} に保存します")

        for idx, code in enumerate(company_codes, start=1):
            api_code = f"{code}0" if len(code) == 4 else code

            if idx % 10 == 0 or code == "8101":
                print(f" {idx}/{len(company_codes)} 件目処理中... (コード: {code})")

            url = f"https://yanoshin.jp{api_code}.json?limit=15"

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
                    if isinstance(item, dict):
                        if "Tdnet" in item:
                            inner = item["Tdnet"]
                            tdnet_data = inner.get("Tdnet", inner)
                        else:
                            tdnet_data = item

                    pub_date_str = tdnet_data.get("pubdate", tdnet_data.get("PubDate", ""))
                    company_name = tdnet_data.get("company_name", tdnet_data.get("CompanyName", "企業名不明"))
                    title = tdnet_data.get("title", tdnet_data.get("Title", "タイトルなし"))
                    pdf_url = tdnet_data.get("document_url", tdnet_data.get("Url", "URLなし"))

                    # 【変更】日付制限を撤回し、取得できた直近の開示をすべてリスト化する
                    filtered_outputs.append(
                        f"[{pub_date_str}] {company_name}\n  {title}\n  URL: {pdf_url}\n"
                    )

                if filtered_outputs:
                    f_out.write(f"=== 証券コード: {code} ===\n")
                    for output in filtered_outputs:
                        f_out.write(output)
                    f_out.write("\n")

            except Exception as e:
                print(f"【デバッグエラー】コード {code} で問題発生: {e}")

            time.sleep(1)

        f_out.write("\n【完了】すべてのチェックが終了しました。\n")

    print(f"\n【完了】すべて終了しました！ 結果ファイル: {output_file}")


if __name__ == "__main__":
    main()
