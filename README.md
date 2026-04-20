# DeFi Portfolio Agent

An AI Agent for DeFi portfolio management, built with LangGraph + Claude API + Web3.py.

> Portfolio project targeting AI Agent Architect roles in the Web3 space.

## What it does

- On-chain awareness — queries ETH balance, gas, and Aave V3 positions in real time
- AI reasoning — analyzes health factors and generates risk recommendations
- Transaction preparation — constructs repay/supply transactions (unsigned, user signs locally)
- Human-in-the-loop — all write operations require explicit user confirmation
- Session memory — remembers wallet address across conversation turns

## Architecture
User → LangGraph ReAct Loop
├── agent_node        (Claude / DeepSeek routing)
├── tool_node         (Web3 + price tools)
└── confirmation_node (interrupt for write ops)
│
Redis (session) + Alchemy RPC (chain data)

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Agent framework | LangGraph 0.3 | Native state machine + interrupt support |
| Primary LLM | Claude claude-sonnet-4-20250514 | Best reasoning for DeFi analysis |
| Secondary LLM | DeepSeek | Cost optimization for simple intents |
| Chain interaction | Web3.py 6.x | Most mature Python Ethereum library |
| Session memory | Redis | TTL-based conversation context |
| Frontend | Gradio | Zero-config chat UI |

## Quick start

```bash
git clone https://github.com/mxdu-tech/defi-portfolio-agent.git
cd defi-portfolio-agent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your API keys
python test_day1.py
```

## Roadmap

- [x] Project scaffold
- [x] LangGraph ReAct loop
- [ ] Web3 tools (ETH balance, gas, Aave position)
- [ ] Session memory (Redis)
- [ ] Model routing (Claude / DeepSeek)
- [ ] Transaction confirmation flow
- [ ] Gradio UI
- [ ] Docker + Fly.io deployment

## License

MIT