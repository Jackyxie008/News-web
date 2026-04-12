import asyncio
import json
import time
import httpx
from dotenv import load_dotenv
from process_grouped_data import PLATFORMS, clean_json_response

load_dotenv()

async def test_single_platform(platform_name, config):
    """测试单个平台API"""
    print(f"\n{'='*60}")
    print(f"🚀 正在测试平台: {platform_name}")
    print(f"📍 模型: {config['model']}")
    print(f"🌐 地址: {config['url']}")
    
    start_time = time.time()
    
    try:
        payload = {
            "model": config['model'],
            "messages": [
                {"role": "user", "content": "测试响应：只返回一个JSON {\"status\": \"ok\"} 不要任何其他内容"}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        
        # 合并平台扩展参数
        if "extra_options" in config:
            payload.update(config["extra_options"])
        
        headers = {"Authorization": f"Bearer {config['key']}"}
        
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(config['url'], headers=headers, json=payload)
            
            elapsed = time.time() - start_time
            
            print(f"⏱️  响应时间: {elapsed:.2f}秒")
            print(f"📡 状态码: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"❌ 请求失败: {resp.text[:500]}")
                return False
            
            result = resp.json()
            content = result["choices"][0]["message"]["content"]
            
            print(f"📤 返回原始内容:\n{content}")
            
            try:
                cleaned = clean_json_response(content)
                json_data = json.loads(cleaned)
                print(f"✅ JSON解析成功: {json_data}")
                print(f"✅ 平台 {platform_name} 测试通过 ✅")
                return True
            except Exception as e:
                print(f"⚠️  JSON解析失败: {e}")
                # 只要返回了200就算API通了
                return True
                
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ 异常: {str(e)}")
        print(f"⏱️  失败耗时: {elapsed:.2f}秒")
        return False

async def main():
    print("\n🔍 大模型API连通性测试工具")
    print(f"共发现 {len(PLATFORMS)} 个已配置平台")
    
    results = {}
    
    for name, config in PLATFORMS.items():
        results[name] = await test_single_platform(name, config)
    
    print("\n" + "="*60)
    print("📊 测试结果汇总:")
    for name, ok in results.items():
        status = "✅ 正常" if ok else "❌ 失败"
        print(f"  {name}: {status}")
    
    print("\n" + "="*60)
    success_count = sum(1 for v in results.values() if v)
    print(f"✅ 总共: {success_count}/{len(PLATFORMS)} 平台可用")
    
    if success_count == len(PLATFORMS):
        print("🎉 所有平台测试通过，可以开始批量处理了！")
    else:
        print("⚠️  部分平台异常，请检查配置后再运行主程序")

if __name__ == "__main__":
    asyncio.run(main())