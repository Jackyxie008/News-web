import matplotlib.pyplot as plt
import numpy as np

# 1. 解决中文显示问题
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei'] 
plt.rcParams['axes.unicode_minus'] = False

# 2. 定义热度公式：H = sum(A) / (h + C)^alpha
def calculate_heat(authority_sum, hours, C=2, alpha=1.8):
    return authority_sum / (hours + C)**alpha

# 3. 模拟 24 小时的数据
hours = np.linspace(0, 12, 500)

# 4. 准备三组对比数据 (使用你归一化后的 SCImago 小数权重)
y_global = calculate_heat(89+87+86.75, hours)  # 3家全球媒体
y_reuters = calculate_heat(89, hours)   # 1家路透社
y_macau = calculate_heat(47, hours)    # 1家澳门本地媒体

# 5. 绘图
plt.figure(figsize=(10, 6))
plt.plot(hours, y_global, label='被多家高声誉值媒体报道的新闻（reputation=89+87+86.75）', color='#d62728', linewidth=2)
plt.plot(hours, y_reuters, label='被一家高声誉值媒体报道的新闻（reputation=89）', color='#1f77b4', linewidth=2, linestyle='--')
plt.plot(hours, y_macau, label='被一家中等声誉值媒体报道的新闻（reputation=41.75）', color='#2ca02c', linewidth=2, linestyle=':')

# 6. 图表装饰
plt.title('新闻热度演化图', fontsize=14)
plt.xlabel('距离新闻发布的时间 (小时)', fontsize=12)
plt.ylabel('热度分值', fontsize=12)
plt.grid(True, alpha=0.3)
plt.legend()

plt.show()