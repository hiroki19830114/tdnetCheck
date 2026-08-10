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

    # ★ どんな状態でも、必ず最初にこの「result.txt」を生成させる
    output_file = "result.txt"
    
    with open(output_file, "w", encoding="utf-8") as f_init:
        f_init.write(f"=== 適時開示・決算速報 取得結果 ===\n")
        f_init.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_init.write("==================================================\n\n")

    hit_records = {}

    print("【開始】データ抽出を開始します...")

    for idx, code in enumerate(company_codes, start=1):
        print(f" {idx}/{len(company_codes)} 件目チェック中... (コード: {code})")

        # HTMLタグが変化しても一番安定している「株探の個別銘柄ニュースURL」
        url = f"https://kabutan.jp{code}"

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            
            # 【絶対安全対策】特定のクラス名を指定せず、ページ内のすべてのリンク(aタグ)から情報を抜き取る
            links = soup.find_all("a")
            code_hits = []

            for link in links:
                title_text = link.get_text(strip=True)
                href = link.get_attr_list("href")[0] if link.has_attr("href") else ""
                
                # リンク先が「ニュース詳細ページ」であり、かつ「決算」「短信」「開示」に関するテキストなら抽出
                if "news" in href and any(keyword in title_text for keyword in ["決算", "短信", "開示", "速報"]):
                    full_url = href if href.startswith("http") else "https://kabutan.jp" + href
                    
                    record = f"・{title_text}\n  URL: {full_url}\n"
                    if record not in code_hits:
                        code_hits.append(record)
                    
                    if len(code_hits) >= 5: # 最新の5件でストップ
                        break

            if code_hits:
                hit_records[code] = code_hits

        except Exception as e:
            print(f"【エラー】コード {code} のアクセス/解析に失敗: {e}")

        time.sleep(1)

    # 最終的な結果を、最初に作った「result.txt」の末尾に追記する
    with open(output_file, "a", encoding="utf-8") as f_out:
        if hit_records:
            for code, records in hit_records.items():
                f_out.write(f"=== 証券コード: {code} ===\n")
                for r in records:
                    f_out.write(r)
                f_out.write("\n")
        else:
            f_out.write("条件に一致する最新の開示情報が見つかりませんでした。\n")

    print(f"【完了】すべて終了しました。")

if __name__ == "__main__":
    main()
