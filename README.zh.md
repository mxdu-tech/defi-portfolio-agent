好的，以下是 Markdown 源码，你可以直接复制。视频已改为嵌入形式。

```markdown
# 🧠 DeFi Portfolio Agent

**AI Agent + DeFi 协议（Aave V3）的智能资产管理系统**

[![Demo](https://img.shields.io/badge/Live_Demo-Vercel-brightgreen)](https://defi-agent.mxdu.me)
[![Chain](https://img.shields.io/badge/Chain-Base_Sepolia-blue)](https://sepolia.basescan.org)
[![Python](https://img.shields.io/badge/Python-3.10+-yellow)](https://www.python.org)

---

## 🎬 项目演示

**在线演示**：https://defi-agent.mxdu.me

**演示视频**：

https://www.youtube.com/watch?v=LcS9avCe8Cs

演示功能包括：Aave V3 仓位查询（抵押/借贷/健康因子）、风险分析与还款建议、链上 repay 交易构造、用户 MetaMask 签名确认、交易上链（Base Sepolia）、交易后仓位自动验证。

---

## ✨ 核心能力

- **多路由 Agent 架构**：意图识别节点自动分流，简单查询走快速模型，DeFi 操作走强推理模型
- **Tool-based 工具系统**：AI 不凭空回答，强制通过链上工具获取数据、构造交易，杜绝幻觉
- **Human-in-the-loop 确认机制**：基于 LangGraph 原生 `interrupt()` 实现交易暂停—确认—继续的安全流程
- **交易安全闭环**：构造交易 → 用户签名 → 链上确认 → 自动验证仓位，形成完整反馈环

---

## 🏗 技术栈

| 层 | 技术 |
|------|------|
| Agent 编排 | LangGraph（StateGraph + MemorySaver） |
| 模型层 | Claude 3.5 Sonnet / DeepSeek Chat（OpenRouter 统一接入） |
| API 服务 | FastAPI |
| 链上交互 | Web3.py |
| 会话持久化 | Redis（双层存储：Session 层 + User 层） |
| 价格数据 | CoinGecko API |
| 网络 | Base Sepolia 测试链 |

---

## 📂 项目结构

```
src/
├── agent/                     # Agent 核心
│   ├── graph.py               # LangGraph 图定义（节点 + 条件路由）
│   ├── nodes.py               # 节点实现（intent / confirmation / execute / save_session 等）
│   ├── state.py               # AgentState 类型定义
│   └── prompts.py             # System Prompt（行为约束 + 强制工具调用规则）
├── tools/                     # 工具集
│   ├── aave.py                # Aave V3 仓位查询 + 风险分析工具
│   ├── price.py               # CoinGecko 价格查询工具
│   ├── transaction.py         # 交易构造工具（approve + repay 双步骤）
│   ├── chain.py               # ETH 余额 + Gas 查询工具
│   └── guards.py              # 交易安全校验（地址/金额/资产白名单）
├── memory/                    # 会话与用户数据持久化
│   └── session.py             # Redis 双层存储实现
└── main.py                    # FastAPI 入口（/chat /confirm /health）
```

---

## 🔁 前后端交互流程

```
用户：Repay 5 USDC
  ↓
前端 POST /chat
  ↓
后端 intent_node 识别意图 → prepare_repay_direct_node
  ↓
prepare_repay_tx 工具：检测 allowance → 构造 approve_tx + repay_tx
  ↓
后端返回含 [ACTION] 标签的响应
  ↓
前端解析 → 弹出 ConfirmationModal（展示交易详情）
  ↓
用户点击确认 → MetaMask 依次签名（approve → 等待链上确认 → repay）
  ↓
前端 POST /confirm（带 tx_hash）
  ↓
后端 execute_node → 确认结果
  ↓
前端自动发送「查看我的 Aave 仓位」→ 验证还款结果 ✅
```

---

## 🧠 架构设计分析

### 一、为什么选择 LangGraph 而不是直接调用 LLM

DeFi 操作是天然的多步骤、有状态的流程。以 repay 为例：

1. 理解用户意图
2. 查询链上仓位数据
3. 分析风险并计算还款金额
4. 构造链上交易
5. **等待用户确认**（状态暂停）
6. 确认后执行
7. 验证执行结果

普通的 LLM 调用是无状态的，无法在步骤 5 处暂停等待用户交互，更无法保证步骤 4 总是先于步骤 6 发生。

LangGraph 的 `StateGraph` 提供了三个关键能力：
- **显式的节点（Node）**：将每个步骤封装为独立节点，职责单一
- **条件路由（Conditional Edge）**：根据状态动态决定下一步走向
- **中断/恢复（interrupt/resume）**：在需要人工决策的节点暂停，等待外部输入后继续

这些能力让 Agent 的行为是可预测、可审计的，而不是黑盒大模型的一次性输出。

### 二、双模型路由策略

项目中配置了两个模型实例，通过 `intent_node` 进行分流：

| 意图类型 | 模型 | 适用场景 |
|----------|------|----------|
| simple | DeepSeek Chat | 问候、帮助、简单币价查询 |
| complex | Claude 3.5 Sonnet | Aave 仓位分析、风险判断、交易构造 |

这样设计的考量：
- **成本与延迟**：简单的对话不需要强大的推理能力，用快速模型响应更快、成本更低
- **工具调用稳定性**：Claude 在 function calling 和多步推理上表现更稳定，适合复杂的 DeFi 场景
- **意图识别前置**：在进入 Agent 循环前就做分流，避免无效的工具绑定和 token 消耗

`intent_node` 的路由逻辑也做了特殊优化：`repay` 意图直接跳过 Agent 思考，进入 `prepare_repay_direct_node`——因为 repay 是明确的单一操作，不需要大模型再做规划，这是一种**意图直通车**的设计，进一步降低延迟和不确定性。

### 三、Tool-based 工具系统设计

项目中的所有链上数据和交易构造都通过 `@tool` 装饰的函数完成，Agent 不直接访问 RPC。

工具按职责分为三类：

**数据查询类**：
- `get_aave_position(address)` — 查询 Aave V3 仓位（collateral、debt、health factor）
- `get_token_price(symbol)` — CoinGecko 实时价格
- `get_eth_balance(address)` — ETH 余额
- `get_gas_price()` — 当前 Gas

**风险分析类**：
- `analyze_aave_risk(total_collateral_usd, total_debt_usd, health_factor)` — 计算达到目标健康因子需要的抵押/还款金额

**交易构造类**：
- `prepare_repay_tx(amount_usdc, user_address)` — 构造 repay 交易计划，**仅构造，不执行**

这种设计的核心原则是：**AI 负责规划和推理，工具负责数据和执行**。每一层职责清晰，便于单独测试和迭代。

### 四、Human-in-the-loop 安全架构

在 DeFi 场景中，AI 的幻觉可能导致错误交易。本项目的核心安全设计是：

**AI 生成交易计划 → 用户确认 → 链上执行**

具体实现依托 LangGraph 的 `interrupt()` 机制：

1. `prepare_repay_tx` 工具构造 approve 和 repay 两笔交易的原始数据
2. 返回值中包含 `[PENDING CONFIRMATION]` 和 `[ACTION]...[/ACTION]` 标签
3. `confirmation_node` 调用 `interrupt()` 暂停整个图执行
4. API 层捕获 `GraphInterrupt` 异常，返回 `awaiting_confirmation: true` + `pending_action`
5. 用户在前端确认后，通过 `/confirm` 端点以 `Command(resume=...)` 恢复图执行
6. `execute_node` 返回确认结果

这个流程确保：
- AI **从不**直接执行链上交易
- 用户始终是交易执行前的最后一道关卡
- 状态在暂停/恢复过程中不丢失

### 五、Allowance 检测与双交易设计

这是对 ERC20 标准理解的一个技术细节。在 Aave V3 中，如果用户要 repay USDC（ERC20），合约需要先从用户钱包划走 USDC。这要求用户先 `approve` 授权给 Pool 合约。

项目在 `prepare_repay_tx` 中做了：
```
query allowance(user, pool)
if allowance < amount:
    approve_tx = build_approve_tx()
repay_tx = build_repay_tx()
```

返回的 `pending_action` 中标记 `need_approve: true/false`，前端根据这个标记决定是否先执行 approve 交易再执行 repay。

这种**服务端构造交易、按需决定是否追加 approve** 的模式，避免了让用户理解 ERC20 授权机制的复杂性，同时保证了交易的完整性。

### 六、Redis 双层的会话与用户存储

项目使用了 Redis 做状态持久化，设计上区分了两个层级：

| 层级 | Key 模式 | 内容 | TTL |
|------|----------|------|-----|
| Session | `session:{id}:messages` / `session:{id}:meta` | 对话历史、关联地址 | 1 小时 |
| User | `user:{address}:meta` / `user:{address}:prefs` | 用户首次出现时间、最后活跃时间、偏好 | 长期保留 |

这样设计的考量：
- Session 层负责临时的对话上下文，短 TTL 自动清理
- User 层按钱包地址关联，跨 Session 保留用户身份和偏好
- 地址在存储前通过 `Web3.to_checksum_address` 做规范化，避免大小写导致的重复

### 七、Provider 模式获取 Aave Pool 地址

Aave V3 在不同网络（Ethereum、Polygon、Base 等）部署的 Pool 合约地址是不同的。项目没有硬编码 Pool 地址，而是通过 `PoolAddressesProvider.getPool()` 动态获取：

```python
provider = w3.eth.contract(address=provider_address, abi=PROVIDER_ABI)
pool_address = provider.functions.getPool().call()
```

这是一个很小的细节，但体现了一个关键设计理念：**不依赖部署常量，依赖链上注册表**。当需要切换到其他网络时，只需更改 Provider 地址，Pool 地址自动跟进。

### 八、System Prompt 的工程化设计

`prompts.py` 中的 System Prompt 不是一段模糊的角色描述，而是一份**行为约束规范**：

- **强制工具调用规则**：定义了触发词集合（repay/borrow/swap/supply/withdraw/send/transfer），出现这些词时必须调用对应工具，禁止用自然语言模拟结果
- **交易流程强制执行**：规定所有交易必须走 prepare → [PENDING CONFIRMATION] → 确认 → 执行 的完整链路
- **禁止虚假输出**：明确禁止伪造交易成功、伪造 tx hash
- **动态地址注入**：如果 state 中有 user_address，自动注入 System Prompt，让 AI 知道当前用户的地址

这种**规则先行**的 Prompt 设计，本质上是在不可靠的 LLM 输出上构建了一套软约束，降低幻觉风险。

---

## 🔮 未来演进方向

### 短期
- **多协议支持**：扩展 `tools/` 目录，接入 Compound、Uniswap 等协议的工具
- **多链支持**：通过环境变量驱动网络切换，让 Provider 模式的价值进一步放大
- **交易历史**：在 Redis User 层记录用户的链上交易历史，提供跨 Session 的操作回顾

### 中期
- **意图理解增强**：将 `intent_node` 从正则匹配升级为轻量级分类模型，提高意图识别准确率
- **风险预警阈值自定义**：在 User 层持久化用户的风险偏好，Aave 仓位分析时自动引用
- **多步交易编排**：支持类似「用 ETH 抵押借 USDC 然后 repay 其他债务」的多步原子操作

### 长期
- **自主 Agent 模式**：在用户设定的风险参数范围内，Agent 可以主动建议仓位调整
- **MEV 保护**：接入 Flashbots 等私有交易池，保护用户交易不被抢跑
- **跨链仓位聚合**：在一个界面内查看用户在多个链上的 DeFi 总仓位

---

## 🚀 本地运行

```bash
git clone <repo-url>
cd defi-portfolio-agent
pip install -r requirements.txt

# 配置环境变量
# OPENROUTER_API_KEY
# ALCHEMY_RPC_URL_BASE_SEPOLIA
# AAVE_POOL_ADDRESSES_PROVIDER_BASE_SEPOLIA
# USDC_ADDRESS_BASE_SEPOLIA
# REDIS_URL

python main.py
```

---

## 🔗 关联项目

**前端仓库**：[defi-agent-frontend](https://github.com/mxdu-tech/defi-agent-frontend)

**在线演示**：https://defi-agent.mxdu.me

---

## 📌 协议与许可

MIT License
