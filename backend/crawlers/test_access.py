import requests

def test(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    print(f"正在尝试访问: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            print(f"✅ 访问成功！状态码: {response.status_code}")
            print(f"内容预览: {response.text[:100].strip()}...")
        else:
            print(f"❌ 访问受阻。状态码: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("⏰ 访问超时")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 发生错误: {e}")

if __name__ == "__main__":
    target_url = "https://www.bbc.com/news/articles/c4g4xexy4w7o"
    test(target_url)