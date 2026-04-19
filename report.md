# Data Layer

The data layer of ARGUS is designed to provide reliable and standardized inputs for the downstream RAG retrieval layer and agent reasoning layer. Rather than functioning as a static repository of financial information, it serves as an intermediate interface that collects, organizes, and exposes data in a form that can be directly consumed by upper-level modules. Within the scope of this project, the data layer handles two categories of information: structured data, including stock prices, financial statements, valuation indicators, news, and earnings data, and unstructured data, primarily official company filings used for retrieval and citation.

From an implementation perspective, the data layer adopts a **tool-based design**. All data-access functionalities are encapsulated as independent tools and centrally registered in `data_tools/registry.py`. Each tool consists of an executable function together with its corresponding JSON schema for LLM function calling. This design enables the agent layer to invoke appropriate tools automatically without directly interacting with the underlying APIs, thereby improving modularity, maintainability, and extensibility.

At present, the system integrates three principal data sources. First, `yfinance` is used to obtain stock price history, company profile information, financial statements, market index snapshots, valuation indicators, and analyst estimates. Second, `Finnhub` is employed to retrieve company news and quarterly earnings surprise data. Third, `SEC EDGAR` is used to download official filings such as `10-K`, `10-Q`, and `8-K`. In addition to live retrieval, several filing documents are stored locally as an initial knowledge base for the project.


| Category               | Source      | Example Tools                                                   | Purpose                                                    |
| ---------------------- | ----------- | --------------------------------------------------------------- | ---------------------------------------------------------- |
| Structured market data | `yfinance`  | `get_stock_price`, `get_stock_info`, `get_financial_statements` | Retrieve prices, company profile, and financial statements |
| News and event data    | `Finnhub`   | `get_company_news`, `get_earnings_data`                         | Capture recent news and quarterly earnings surprises       |
| Official filings       | `SEC EDGAR` | `download_filing`, `get_risk_factors`                           | Download filings and extract citation-ready evidence       |

For structured data, outputs retrieved from different APIs are converted into normalized Python dictionaries, with response formats specified in `data_tools/schemas.py` through Pydantic models. For instance, the stock price tool returns historical OHLCV data together with percentage change over a selected period, the financial statement tool returns annual and quarterly statements, and the news tool returns article titles, timestamps, summaries, and URLs. This standardization ensures that downstream modules can consume the data consistently without relying on the raw format of individual sources.

For unstructured documents, the project implements a dedicated filing ingestion pipeline. The function `download_filing()` retrieves the latest filing from SEC EDGAR and stores it in `data/filings/`, while `parse_filing()` processes the document into multiple text chunks. Each chunk preserves key metadata, including ticker, filing type, filing date, accession number, source URL, section title, and page numbers. This mechanism is particularly important because it enables the RAG layer to retrieve evidence with clear provenance and to support citation-backed responses. The current chunking strategy uses a default size of approximately **800 characters** with **120 characters of overlap**, balancing retrieval granularity with contextual continuity.

Overall, the data layer serves as a standardized bridge between external financial data sources and the higher-level intelligence modules of ARGUS. Its responsibilities extend beyond data acquisition to include basic cleaning, normalization, and interface packaging. Structured outputs are passed directly to agent tools, while parsed filing documents are prepared for embedding and retrieval. In this way, the data layer provides the technical foundation for both real-time financial analysis and citation-based research generation within the system.


# Agent Layer

## 1. Architecture Overview

The ARGUS system employs a state-machine architecture combining Directed Acyclic Graphs and cyclic graphs based on LangGraph. Unlike traditional single large language model calls, ARGUS breaks down the complex task of generating equity research reports into multiple specialized agents to achieve process controllability, data accuracy, and logical rigor. Its core design philosophy revolves around the single responsibility principle where each agent processes only specific domain data, a closed-loop verification mechanism with an independent reviewer node for strict fact-checking, and stateful orchestration utilizing LangGraph to maintain the global state and ensure the stability of concurrent executions and multi-turn conversations.

## 2. Multi-Agent Workflow

The multi-agent workflow operates on a strict closed-loop execution pipeline that sequentially processes user inputs through rewriting, routing, collection, verification, synthesis, and memory updates. A raw user query is first processed by the query rewriter to resolve ambiguities before being handed to the supervisor for task dispatch. The supervisor dynamically routes tasks to specialized analysts, and all collected evidence must then pass through the reviewer node. If the reviewer rejects the data due to conflicts or hallucinations, the workflow loops back to the supervisor for retries; if the data passes inspection, the verified evidence moves to the synthesizer for final report generation and concludes with the memory manager updating the system's context.

## 3. Core Agents & Responsibilities

The system relies on several core agents with distinct responsibilities to execute the research pipeline seamlessly. The Supervisor functions as the brain of the system by analyzing rewritten queries and dynamically routing tasks based on the current collected data and verification feedback. It dispatches tasks to three concurrently operating specialized workers: the Data Analyst focuses on extracting structured financial metrics from corporate fundamentals, the Market Analyst connects to real-time APIs to retrieve stock trends and news, and the Compliance Analyst leverages Retrieval-Augmented Generation technology to analyze risk factors directly from SEC filings. Once data is collected, the Reviewer acts as the quality gatekeeper to detect hallucinations by checking data consistency and relevance, while also gracefully accepting the reality of genuinely unavailable data to prevent infinite retry loops. Finally, the Synthesizer generates the final report using exclusively verified evidence, strictly prohibiting information fabrication by explicitly stating when data is unavailable.

## 4. Memory Management and Context Control

To support complex multi-turn follow-up queries and prevent token overflow, the system utilizes a two-level memory structure alongside an automatic clearing mechanism. At the beginning of each new query, the query rewriter stage automatically issues a command to empty the temporary draft data generated in the previous turn, ensuring that the evidence for every research report remains pure and unpolluted by historical interactions. The specific roles of the short-term and long-term memory components are detailed in the following table.


| **Memory Type**                         | **Content**                                | **Purpose**                                                                              |
| --------------------------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------- |
| **Short-Term Memory (`chat_history`)**  | Details of the last 2-3 conversation turns | Supports coreference resolution for pronouns like "it" or "this company".                |
| **Long-Term Memory (`memory_summary`)** | Compressed summary of older conversations  | Retains key context in long sessions while drastically reducing context window pressure. |

## 5. Summary of Technical Advantages

The technical advantages of the ARGUS system are defined by its engineering-grade anti-hallucination mechanisms, concurrency capabilities, and contextual robustness. By implementing the reviewer node and the synthesizer's fallback logic, the system structurally prevents the AI from fabricating data. Furthermore, it leverages the fan-out and fan-in mechanisms of LangGraph to enable the parallel execution of multiple analyst nodes, significantly boosting report generation efficiency. Finally, through query rewriting and a sliding window memory manager, the system effortlessly handles complex follow-up questions while maintaining extremely low prompt token costs.
