import os
from datetime import datetime
import xml.etree.ElementTree as ET
import requests

TXT_FILE = "codes.txt"

# 1. 実行した「今日」の日付（JST）を用意
TODAY_STR = datetime.now().strftime("%Y/%m/%d")

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

    # 保存用のファイル名
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"result_{now_str}.txt"

    # 日経新聞の適時開示速報RSS（最新の開示がリアルタイムで配信されます）
    rss_url = "https://nikkei.com"

    try:
        response = requests.get(rss_url, headers=headers)
        response.raise_for_status()
        xml_data = response.content

        # XMLの解析
        root = ET.fromstring(xml_data)

        # RSS内の全開示情報を取得
        # 通常、<item>タグ内に各開示情報が入っています
        items = root.findall(".//item")

        # コードごとの該当開示情報を格納する辞書
        hit_records = {code: [] for code in company_codes}
        has_any_hit = False

        for item in items:
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            pub_date = (
                item.find("pubDate").text
                if item.find("pubDate") is not None
                else ""
            )

            # タイトルやリンクから証券コード（4桁）を特定し、監視リストと照合
            for code in company_codes:
                # 日経RSSはタイトルに「(8101)」や本文リンクにコードが含まれるため、部分一致で判定
                if code in title or code in link:
                    # 簡易的なフォーマット整形
                    record = f"[{pub_date}] \n  {title}\n  URL: {link}\n"
                    hit_records[code].append(record)
                    has_any_hit = True

        # 結果をファイルに書き出し
        with open(output_file, "w", encoding="utf-8") as f_out:
            f_out.write(f"=== TDnet適時開示 取得結果 (日経RSS版) ===\n")
            f_out.write(
                f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            f_out.write(f"監視対象銘柄数: {len(company_codes)} 件\n")
            f_out.write("=========================================\n\n")

            if has_any_hit:
                for code, records in hit_records.items():
                    if records:
                        f_out.write(f"=== 証券コード: {code} ===\n")
                        for r in records:
                            f_out.write(r)
                        f_out.write("\n")
            else:
                f_out.write("本日（直近）の対象銘柄の適時開示はありませんでした。\n")

        print(f"【完了】チェック終了。結果ファイル: {output_file}")

    except Exception as e:
        print(f"【エラー】RSSの取得または解析に失敗しました: {e}")


if __name__ == "__main__":
    main()
