import json
import os
import time
from datetime import datetime
import requests

TXT_FILE = "codes.txt"

# 1. 実行した「今日」の日付を自動計算
TODAY_HYPHEN = datetime.now().strftime("%Y-%m-%d")
TODAY_SLASH = datetime.now().strftime("%Y/%m/%d")

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
        f_out.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write(f"抽出条件: {TODAY_HYPHEN}（本日発表分のみ）\n")
        f_out.write(f"対象銘柄数: {len(company_codes)} 件\n")
        f_out.write("===============================\n\n")

        print(
            f"【開始】{len(company_codes)}件の銘柄をチェック中...（本日発表分を {output_file} に保存します）"
        )

        for idx, code in enumerate(company_codes, start=1):
            # APIの仕様に合わせ、4桁コードの場合は後ろに0を付与した5桁（例: 8101 -> 81010）を生成
            api_code = f"{code}0" if len(code) == 4 else code

            if idx % 10 == 0 or code == "8101":
                print(f" {idx}/{len(company_codes)} 件目処理中... (コード: {code})")

            # 正しいエンドポイント
            url = f"https://webapi.yanoshin.jp/webapi/tdnet/list/{api_code}.json?limit=15"

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
                        # APIの仕様に合わせて階層を深くチェック（item["Tdnet"]["Tdnet"] などの二重階層対策）
                        if "Tdnet" in item:
                            inner = item["Tdnet"]
                            tdnet_data = inner.get("Tdnet", inner)
                        else:
                            tdnet_data = item

                    # 大文字・小文字どちらのキー名でも取得できるようにフォールバックを設定
                    pub_date_str = tdnet_data.get(
                        "pubdate", tdnet_data.get("PubDate", "")
                    )
                    company_name = tdnet_data.get(
                        "company_name", tdnet_data.get("CompanyName", "企業名不明")
                    )
                    title = tdnet_data.get("title", tdnet_data.get("Title", "タイトルなし"))
                    pdf_url = tdnet_data.get(
                        "document_url", tdnet_data.get("Url", "URLなし")
                    )

                    # 日付チェック
                    if pub_date_str:
                        item_date_prefix = pub_date_str[:10]
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

            except Exception as e:
                # デバッグ用にエラーが起きた場合はコンソールに出力（本番運用時は pass でも可）
                print(f"【デバッグエラー】コード {code} で問題発生: {e}")

            time.sleep(1)

        f_out.write("\n【完了】すべてのチェックが終了しました。\n")

    print(f"\n【完了】すべて終了しました！ 結果ファイル: {output_file}")


if __name__ == "__main__":
    main()
