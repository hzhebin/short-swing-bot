
# 📈 撸短策略自动化回测系统（Short-Swing Strategy Backtester）

一个基于 Python + Streamlit 构建的加密货币阶梯挂单策略回测工具，支持 Binance 历史数据拉取、策略参数配置、图形化交易点展示、年化收益与爆仓风险评估。

## 🚀 项目亮点

- 🔗 实时连接 Binance 公共 API 获取历史 K 线
- 🧮 策略模拟挂单交易逻辑（可调杠杆、手续费）
- 📊 输出账户收益、CAGR、爆仓风险频率
- 📈 交易点可视化图表展示
- 💻 可通过 Streamlit 网页端部署，一键运行

---

## ⚙️ 策略逻辑概览

该策略基于市场 **震荡区间套利** 思路，通过在下跌时分批挂单建仓，在上涨时逐级止盈来实现利润最大化。

挂单振幅与权重如下：

| 振幅 | 挂单权重 |
|------|----------|
| -1%  | 36%      |
| -2%  | 32%      |
| -3%  | 21%      |
| -4%  | 9%       |

每上涨1%即止盈1份，对冲波动风险。支持自定义杠杆与手续费。

---

## 🛠️ 使用方法

### 👉 在线体验

点击此链接访问部署好的版本：  
📎 `https://your-streamlit-url.streamlit.app`

### 本地部署

```bash
git clone https://github.com/hzhebin/short-swing-bot.git
cd short-swing-bot
pip install -r requirements.txt
streamlit run app.py
```

---

## 🎛️ 参数说明

| 参数 | 说明 |
|------|------|
| 交易对 | 如 BTCUSDT |
| 时间区间 | 起止时间（注意不能选未来） |
| 杠杆倍数 | 最大50x |
| 每次建仓金额 | 单次挂单占用本金 |
| 衰减因子 | 控制风险调整权重 |
| 手续费率 | 双边手续费，如 0.0005 = 0.05% |

---

## 📦 技术栈

- Streamlit
- Binance API
- Pandas / Matplotlib
- Python 3.9+

---

## 📜 License

MIT License © hzhebin
