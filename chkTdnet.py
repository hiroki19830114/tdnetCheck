import json
import os
import time
from datetime import datetime
import requests

# 実際のファイル名「code.txt」に合わせました
TXT_FILE = "code.txt"

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
        print("【エラー】code.txt に有効な証券コードが記載されていません。")
        return

    # 保存用のファイル名は固定
    output_file = "result.txt"

    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write(f"=== TDnet適時開示 取得結果 ===\n")
        f_out.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write("抽出条件: 直近の最新開示を表示（タイムゾーン・ラグ対策版）\n")
        f_out.write(f"対象銘柄数: {len(company_codes)} 件\n")
        f_out.write("===============================\n\n")

        print(f"【開始】{len(company_codes)}件の銘柄をチェック中...")

        for idx, code in enumerate(company_codes, start=1):
            # 4桁コードの場合は後ろに0を付与した5桁（例: 8101 -> 81010）を生成
            api_code = f"{code}0" if len(code) == 4 else code

            # 正しいエンドポイントURL
            url = f"https://webapi.yanoshin.jp/webapi/tdnet/list/{api_code}.json?limit=15"

            try:
                response = requests.get(url, headers=headers, timeout=15)
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
                        # APIの二重階層（"Tdnet"の中にさらに"Tdnet"があるケース）に対応
                        if "Tdnet" in item:
                            inner = item["Tdnet"]
                            tdnet_data = inner.get("Tdnet", inner)
                        else:
                            tdnet_data = item

                    # 大文字・小文字どちらのキー名でも取得できるようにフォールバックを設定
                    pub_date_str = tdnet_data.get("pubdate", tdnet_data.get("PubDate", "日付不明"))
                    company_name = tdnet_data.get("company_name", tdnet_data.get("CompanyName", "企業名不明"))
                    title = tdnet_data.get("title", tdnet_data.get("Title", "タイトルなし"))
                    pdf_url = tdnet_data.get("document_url", tdnet_data.get("Url", "URLなし"))

                    # 【修正】日付の厳密な完全一致判定を無くし、直近の発表（最新の決算など）をそのまま残すようにしました
                    filtered_outputs.append(
                        f"[{pub_date_str}] {company_name}\n  {title}\n  URL: {pdf_url}\n"
                    )

                if filtered_outputs:
                    f_out.write(f"=== 証券コード: {code} ===\n")
                    # 最新のものから上位3件〜5件程度をメールに見やすく出力
                    for output in filtered_outputs[:5]: 
                        f_out.write(output)
                    f_out.write("\n")

            except Exception as e:
                # 万が一通信エラーが起きてもプログラムを強制終了させず、ログに書き残してスキップする
                f_out.write(f"=== 証券コード: {code} ===\n  【通信エラー】データの取得に失敗しました: {e}\n\n")

            time.sleep(1)

    print(f"\n【完了】すべて終了しました！ 結果ファイル: {output_file}")

if __name__ == "__main__":
    main()
