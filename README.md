# DeFi Portfolio Agent

**An intelligent asset management system combining AI Agents with the Aave V3 protocol.**

[![Demo](https://img.shields.io/badge/Live_Demo-Vercel-brightgreen)](https://defi-agent.mxdu.me)
[![Chain](https://img.shields.io/badge/Chain-Base_Sepolia-blue)](https://sepolia.basescan.org)
[![Python](https://img.shields.io/badge/Python-3.10+-yellow)](https://www.python.org)

---

🌐 Language: English | [中文](./README_CN.md)

> An intelligent portfolio management system combining AI Agents with the Aave V3 protocol—featuring natural language interaction, on-chain data analysis, and transaction execution with a mandatory user confirmation layer.

## 🎬 Demo

**Live Demo**: https://defi-agent.mxdu.me

**Video Walkthrough**:

[![Demo Video](https://img.youtube.com/vi/LcS9avCe8Cs/0.jpg)](https://www.youtube.com/watch?v=LcS9avCe8Cs)

The demo covers Aave V3 position queries (collateral, debt, and health factor), risk analysis and repayment recommendations, on-chain repay transaction construction, MetaMask signature confirmation, transaction execution on Base Sepolia, and automatic post-transaction position verification.

---

## ✨ Core Capabilities

- **Multi-Route Agent Architecture**: An intent classification node automatically routes simple queries to a fast model and complex DeFi operations to a strong reasoning model.
- **Tool-Based System**: The AI is forced to use on-chain tools for data and transaction construction—eliminating hallucinations from pure text generation.
- **Human-in-the-Loop Confirmation**: Leverages LangGraph's native `interrupt()` mechanism to create a secure *pause-confirm-proceed* flow for all transactions.
- **Closed-Loop Transaction Safety**: Construct transaction → User signs → On-chain confirmation → Automatic position verification, creating a complete feedback loop.

---

## 🏗 Tech Stack

| Layer | Technology |
|---|---|
| Agent Orchestration | LangGraph (StateGraph + MemorySaver) |
| Model Layer | Claude 3.5 Sonnet / DeepSeek Chat (via OpenRouter) |
| API Service | FastAPI |
| Blockchain Interaction | Web3.py |
| Session Persistence | Redis (Dual-layer: Session + User) |
| Price Data | CoinGecko API |
| Network | Base Sepolia Testnet |

---

## 📂 Project Structure

```
src/
├── agent/                     # Agent Core
│   ├── graph.py               # LangGraph graph definition (nodes + conditional edges)
│   ├── nodes.py               # Node implementations (intent, confirmation, execute, save_session, etc.)
│   ├── state.py               # AgentState type definitions
│   └── prompts.py             # System Prompt (behavioral constraints + mandatory tool-call rules)
├── tools/                     # Tool Set
│   ├── aave.py                # Aave V3 position query + risk analysis tools
│   ├── price.py               # CoinGecko price query tool
│   ├── transaction.py         # Transaction construction tools (dual-step approve + repay)
│   ├── chain.py               # ETH balance + gas query tools
│   └── guards.py              # Transaction safety guards (address, amount, asset whitelist)
├── memory/                    # Session & User Data Persistence
│   └── session.py             # Redis dual-layer storage implementation
└── main.py                    # FastAPI entry point (/chat, /confirm, /health)
```

---

## 🔁 Frontend-Backend Interaction Flow

```
User: "Repay 5 USDC"
  ↓
Frontend POST /chat
  ↓
Backend intent_node classifies intent → prepare_repay_direct_node
  ↓
prepare_repay_tx tool: checks allowance → builds approve_tx + repay_tx
  ↓
Backend returns response containing [ACTION] tag
  ↓
Frontend parses it → displays ConfirmationModal with transaction details
  ↓
User clicks confirm → MetaMask signs sequentially (approve → wait for confirmation → repay)
  ↓
Frontend POST /confirm (with tx_hash)
  ↓
Backend execute_node → confirmation result
  ↓
Frontend automatically sends "Check my updated Aave position" → verifies the repayment
```

---

## 🧠 Architecture Analysis

### 1. Why LangGraph Over a Simple LLM Call?

DeFi operations are inherently multi-step and stateful. Take `repay` as an example:

1.  Understand user intent.
2.  Query on-chain position data.
3.  Analyze risk and calculate the repayment amount.
4.  Construct the on-chain transaction.
5.  **Wait for user confirmation** (state paused).
6.  Execute after confirmation.
7.  Verify the execution result.

A single LLM call is stateless; it cannot pause at step 5 to wait for user input, nor can it guarantee step 4 always happens before step 6.

LangGraph's `StateGraph` provides three critical capabilities:
- **Explicit Nodes**: Encapsulate each step as an independent, single-responsibility node.
- **Conditional Edges**: Dynamically decide the next step based on state.
- **Interrupt/Resume**: Pause execution at decision-critical nodes and wait for external input.

These capabilities make the Agent's behavior predictable and auditable, rather than being a black-box, one-off LLM output.

### 2. Dual-Model Routing Strategy

Two model instances are configured in the project, routed through `intent_node`:

| Intent Type | Model | Use Case |
|---|---|---|
| `simple` | DeepSeek Chat | Greetings, help, simple price queries |
| `complex` | Claude 3.5 Sonnet | Aave position analysis, risk assessment, transaction construction |

Design Considerations:
- **Cost & Latency**: Simple conversations don't need powerful reasoning. A faster model provides quicker, cheaper responses.
- **Tool-Call Stability**: Claude is more stable with function calling and multi-step reasoning, making it suitable for complex DeFi scenarios.
- **Pre-Routing**: Classifying intent before entering the Agent loop avoids unnecessary tool binding and token consumption.

The routing logic also has a special optimization: a `repay` intent bypasses the Agent entirely and goes to `prepare_repay_direct_node`. Since a repay is a single, explicit action, it needs no further LLM planning—a **direct-to-action path** that reduces both latency and uncertainty.

### 3. Tool-Based System Design

All on-chain data access and transaction construction is handled by functions decorated with `@tool`. The Agent never touches an RPC endpoint directly.

Tools are split into three categories:

**Data Query**:
- `get_aave_position(address)` — Query Aave V3 position.
- `get_token_price(symbol)` — Fetch real-time price via CoinGecko.
- `get_eth_balance(address)` — Query ETH balance.
- `get_gas_price()` — Fetch current gas price.

**Risk Analysis**:
- `analyze_aave_risk(total_collateral_usd, total_debt_usd, health_factor)` — Calculate required collateral/debt repayment to reach a target health factor.

**Transaction Construction**:
- `prepare_repay_tx(amount_usdc, user_address)` — Build a repay transaction plan. **Builds only; does not execute.**

The core principle: **The AI is responsible for planning and reasoning, while tools handle data and execution.** Each layer has a clear responsibility, making them easy to test and iterate independently.

### 4. Human-in-the-Loop Security Architecture

In DeFi, AI hallucinations can lead to costly errors. This project's core safety design is:

**AI generates a transaction plan → User confirms → Execute on-chain.**

Implementation relies on LangGraph's `interrupt()`:

1.  `prepare_repay_tx` builds raw payloads for approve and repay transactions.
2.  The return value includes `[PENDING CONFIRMATION]` and `[ACTION]...[/ACTION]` tags.
3.  `confirmation_node` calls `interrupt()` to pause the entire graph.
4.  The API layer catches the `GraphInterrupt` exception and returns `awaiting_confirmation: true` + `pending_action`.
5.  After the user confirms on the frontend, the `/confirm` endpoint resumes the graph with `Command(resume=...)`.
6.  `execute_node` returns the final result.

The flow guarantees that the AI **never** directly executes a transaction, the user is always the final arbiter, and the graph's state is preserved during the pause/resume cycle.

### 5. Allowance Checking and Dual-Transaction Design

This reflects a technical understanding of the ERC20 standard. For a user to repay USDC on Aave V3, the contract needs to pull USDC from their wallet, which requires a prior `approve` call.

`prepare_repay_tx` handles this by checking the allowance first and conditionally building an approval transaction if it's insufficient. The returned `pending_action` includes a `need_approve: true/false` flag, allowing the frontend to be dumb about the logic—it simply follows the plan. This server-side transaction construction model abstracts away the complexity of ERC20 mechanics from the user.

### 6. Two-Tier Redis Storage for Sessions and Users

Redis is used for state persistence, with a design that distinguishes between two levels:

| Tier | Key Pattern | Content | TTL |
|---|---|---|---|
| **Session** | `session:{id}:messages` / `session:{id}:meta` | Chat history, linked wallet address | 1 hour |
| **User** | `user:{address}:meta` / `user:{address}:prefs` | First seen, last active, user preferences | Long-term |

Design considerations:
- The Session layer handles temporary conversational context with automatic cleanup via a short TTL.
- The User layer, keyed by wallet address, persists identity and preferences across sessions.
- Addresses are normalized using `Web3.to_checksum_address` before storage to prevent case-sensitivity duplicates.

### 7. Provider Pattern for Aave Pool Address

Aave V3 deploys different Pool contract addresses across various networks. The project avoids hardcoding and instead fetches it dynamically via `PoolAddressesProvider.getPool()`.

This is a small detail that reflects a core design philosophy: **rely on on-chain registries, not deployment constants.** Switching to a new network only requires changing the Provider address, and the Pool address follows automatically.

### 8. Engineering the System Prompt

The System Prompt in `prompts.py` is not a generic role description but a strict **behavioral constraint specification**:

- **Mandatory Tool-Call Rules**: Defines a set of trigger words (repay, borrow, swap, etc.). The AI *must* call a corresponding tool when they appear, and is forbidden from simulating results in natural language.
- **Strict Transaction Flow**: Mandates the complete prepare → [PENDING CONFIRMATION] → user confirmation → execute pathway.
- **No Fake Outputs**: Explicitly forbids fabricating successful transactions or tx hashes.
- **Dynamic Address Injection**: Appends the user's wallet address to the system prompt at runtime when available, making the AI context-aware.

This **rules-first** prompt design builds a set of soft constraints on top of an inherently unreliable LLM, effectively reducing the risk of hallucination.

---

## 🔮 Future Roadmap

### Short-term
- **Multi-Protocol Support**: Expand the `tools/` directory with integrations for Compound, Uniswap, etc.
- **Multi-Chain Support**: Drive network switching via environment variables to fully unlock the value of the Provider pattern.
- **Transaction History**: Record user transaction history in the Redis User layer for cross-session review.

### Mid-term
- **Enhanced Intent Understanding**: Upgrade `intent_node` from regex matching to a lightweight classification model for higher accuracy.
- **Custom Risk Thresholds**: Persist user-defined risk preferences in the User layer for personalized Aave position analysis.
- **Multi-Step Transaction Orchestration**: Support atomic, multi-step actions like "deposit ETH as collateral, borrow USDC, and repay another debt."

### Long-term
- **Autonomous Agent Mode**: The Agent could proactively suggest portfolio adjustments within user-defined risk parameters.
- **MEV Protection**: Integrate private transaction pools like Flashbots to protect user trades from front-running.
- **Cross-Chain Portfolio Aggregation**: View a user's total DeFi positions across multiple chains from a single interface.

---

## 🚀 Local Development

```bash
git clone <repo-url>
cd defi-portfolio-agent
pip install -r requirements.txt

# Configure environment variables
# OPENROUTER_API_KEY
# ALCHEMY_RPC_URL_BASE_SEPOLIA
# AAVE_POOL_ADDRESSES_PROVIDER_BASE_SEPOLIA
# USDC_ADDRESS_BASE_SEPOLIA
# REDIS_URL

python main.py
```

---

## 🔗 Related Projects

**Frontend Repository**: [defi-agent-frontend](https://github.com/mxdu-tech/defi-agent-frontend)

**Live Demo**: https://defi-agent.mxdu.me

---

## 📌 License

MIT License
