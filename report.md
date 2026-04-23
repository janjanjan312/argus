# ARGUS AI: The Autonomous Agentic Workforce for Institutional-Grade Equity Research

## Introduction

Institutional-grade equity research demands a synthesis of quantitative analysis, qualitative judgment, and verifiable evidence—a task that has traditionally been the exclusive domain of human experts. The core challenge lies in navigating vast, unstructured data sources like SEC filings, integrating them with real-time market data, and maintaining a rigorous, fact-based line of reasoning. ARGUS AI is an advanced system designed to address this challenge by deploying an autonomous, multi-agent workforce. It deconstructs the complex process of equity research into a series of specialized, verifiable tasks executed by a team of AI agents. By combining a robust data foundation, a state-of-the-art retrieval engine, and a collaborative agentic framework, ARGUS aims to produce institutional-grade analysis that is not only insightful but also transparent, auditable, and free from factual hallucination.

## 1. System Architecture

ARGUS is designed as a modular, three-tier system, ensuring a clear separation of concerns between data acquisition, evidence retrieval, and cognitive reasoning. This layered architecture enhances maintainability, scalability, and the verifiability of the final output.

- **The Data Layer** serves as the foundational interface to the outside world. It ingests both structured market data (from sources like `yfinance` and `Finnhub`) and unstructured documents (from `SEC EDGAR`). Its sole responsibility is to fetch, normalize, and provide this information through a standardized set of tools.

- **The RAG Layer** functions as the system's specialized long-term memory. It consumes the unstructured documents from the Data Layer, processes them into an indexed, searchable knowledge base, and exposes this capability to the Agent Layer through a single, powerful retrieval tool.

- **The Agent Layer** is the cognitive core where reasoning occurs. It receives a user query and orchestrates a team of specialized agents to answer it. It consumes structured data directly from the Data Layer's tools and leverages the RAG Layer for citable evidence.

This clear data flow—from ingestion to retrieval to reasoning—is central to the system's design, ensuring that agents operate on a foundation of reliable, traceable information.

## 2. Data Layer

The data layer of ARGUS is designed to provide reliable and standardized inputs for the downstream RAG retrieval layer and agent reasoning layer. Rather than functioning as a static repository of financial information, it serves as an intermediate interface that collects, organizes, and exposes data in a form that can be directly consumed by upper-level modules. Within the scope of this project, the data layer handles two categories of information: structured data, including stock prices, financial statements, valuation indicators, news, and earnings data, and unstructured data, primarily official company filings used for retrieval and citation.

From an implementation perspective, the data layer adopts a **tool-based design**. All data-access functionalities are encapsulated as independent tools and centrally registered in `data_tools/registry.py`. Each tool consists of an executable function together with its corresponding JSON schema for LLM function calling. This design enables the agent layer to invoke appropriate tools automatically without directly interacting with the underlying APIs, thereby improving modularity, maintainability, and extensibility.

At present, the system integrates three principal data sources. First, `yfinance` is used to obtain stock price history, company profile information, financial statements, market index snapshots, valuation indicators, and analyst estimates. Second, `Finnhub` is employed to retrieve company news and quarterly earnings surprise data. Third, `SEC EDGAR` is used to download official filings such as `10-K`, `10-Q`, and `8-K`. In addition to live retrieval, several filing documents are stored locally as an initial knowledge base for the project.

| Category               | Source      | Example Tools                                                   | Purpose                                                    |
| ---------------------- | ----------- | --------------------------------------------------------------- | ---------------------------------------------------------- |
| Structured market data | `yfinance`  | `get_stock_price`, `get_stock_info`, `get_financial_statements` | Retrieve prices, company profile, and financial statements |
| News and event data    | `Finnhub`   | `get_company_news`, `get_earnings_data`                         | Capture recent news and quarterly earnings surprises       |
| Official filings       | `SEC EDGAR` | `download_filing`, `get_risk_factors`                           | Download filings and extract citation-ready evidence       |

For structured data, outputs retrieved from different APIs are converted into normalized Python dictionaries, with response formats specified in data_tools/schemas.py through Pydantic models. For instance, the stock price tool returns historical OHLCV data together with percentage change over a selected period, the financial statement tool returns annual and quarterly statements, and the news tool returns article titles, timestamps, summaries, and URLs. This standardization ensures that downstream modules can consume the data consistently without relying on the raw format of individual sources.

For unstructured documents, the project implements a dedicated filing ingestion pipeline. The function download_filing() retrieves the latest filing from SEC EDGAR and stores it in data/filings/, while parse_filing() processes the document into multiple text chunks. Each chunk preserves key metadata, including ticker, filing type, filing date, accession number, source URL, section title, and page numbers. This mechanism is particularly important because it enables the RAG layer to retrieve evidence with clear provenance and to support citation-backed responses. The current chunking strategy uses a default size of approximately 800 characters with 120 characters of overlap, balancing retrieval granularity with contextual continuity.

Overall, the data layer serves as a standardized bridge between external financial data sources and the higher-level intelligence modules of ARGUS. Its responsibilities extend beyond data acquisition to include basic cleaning, normalization, and interface packaging. Structured outputs are passed directly to agent tools, while parsed filing documents are prepared for embedding and retrieval. In this way, the data layer provides the technical foundation for both real-time financial analysis and citation-based research generation within the system.

## 3. RAG Layer

The Retrieval-Augmented Generation (RAG) layer is a mission-critical component that serves as the interface between the system's unstructured data corpus and the analytical Agent Layer. Its objective is to furnish the `Compliance Analyst` agent with precise, contextually relevant, and citable evidence from financial documents. This is achieved through a multi-stage retrieval pipeline engineered to optimize for both recall and precision, moving decisively beyond simple vector similarity search.

### 3.1. Architectural Design: A Three-Stage Pipeline

The RAG architecture is implemented as a three-stage pipeline designed to progressively refine search results. This approach starts with broad, efficient recall and concludes with high-precision re-ranking, striking an optimal balance between performance and accuracy.

| Stage                    | Component                                     | Primary Goal       |
| :----------------------- | :-------------------------------------------- | :----------------- |
| **1. Query Pre-processing**  | Rule-Based Intent & Query Augmentation        | Enhance Query      |
| **2. Hybrid Recall**     | Dense (FAISS) + Sparse (BM25) Search          | Maximize Recall    |
| **3. Fine-grained Re-ranking** | Cross-Encoder Model                           | Maximize Precision |

### 3.2. Stage 1: Query Pre-processing

Before retrieval, the raw user query is systematically augmented to improve its effectiveness. This is not a complex NLP task but a series of deterministic, rule-based transformations. First, **Intent Detection** is performed using a lightweight keyword-matching system to classify the query's objective (e.g., `risk`, `financial`). Based on the detected intent, a contextual prefix (e.g., "Risk Factors and Potential Challenges:") is prepended during **Query Rewriting** to focus the search on relevant document sections. Finally, a controlled **Query Expansion** appends a small, curated set of high-confidence synonyms for core financial terms. While expansion can introduce noise, its scope is deliberately limited, and any irrelevant results are effectively pruned by the subsequent re-ranking stage.

### 3.3. Stage 2: Hybrid Recall

The recall stage retrieves an initial set of `k=50` candidates by leveraging a hybrid search strategy. This approach synergizes two distinct retrieval paradigms to ensure the system captures both semantic relevance and keyword precision—a capability that neither method can achieve alone.

| Retrieval Method  | Technology                            | Strength                                                              |
| :---------------- | :------------------------------------ | :-------------------------------------------------------------------- |
| **Dense Retrieval** | `sentence-transformers` + `FAISS`     | **Semantic Search:** Understands context and finds conceptually similar results. |
| **Sparse Retrieval**| `BM25`                                | **Keyword Search:** Excels at matching specific, literal terms and acronyms.   |

The final recall score for each document chunk is a weighted linear combination of the normalized scores from both methods: `Score = (α * dense_norm) + ((1-α) * sparse_norm)`. The weighting factor `α` is a configurable hyperparameter that balances the influence of each retrieval method. This combined score ensures that documents relevant in both a semantic and literal sense are prioritized.

### 3.4. Stage 3: Fine-grained Re-ranking

The 50 candidates from the recall stage are passed to a **Cross-Encoder re-ranking model** (specifically, a fine-tuned `ms-marco-MiniLM-L-6-v2`). Unlike the dual-encoder used for recall, the cross-encoder performs full self-attention on the concatenated query and document text. This allows for a much deeper contextual relevance assessment, effectively filtering out false positives from the recall stage. This stage trades higher computational cost for a significant gain in precision. From the re-ranked list, the **top `k=5`** highest-scoring documents are selected as the final evidence set to be passed to the agent.

### 3.5. Integration & Performance

The entire pipeline is encapsulated within a single `retrieve_context` tool, abstracting its complexity from the Agent Layer. This modular design allows the `Compliance Analyst` to leverage the RAG system with a simple, declarative function call. The two-stage architecture ensures low end-to-end latency by performing the expensive re-ranking step on a small, pre-filtered subset of documents. This makes the system responsive enough for interactive analysis while delivering the high-precision, verifiable evidence required for generating reliable financial reports.

## 4. Agent Layer

### 4.1. Architecture Overview

The ARGUS system employs a state-machine architecture combining Directed Acyclic Graphs and cyclic graphs based on LangGraph. Unlike traditional single large language model calls, ARGUS breaks down the complex task of generating equity research reports into multiple specialized agents to achieve process controllability, data accuracy, and logical rigor. Its core design philosophy revolves around the single responsibility principle where each agent processes only specific domain data, a closed-loop verification mechanism with an independent reviewer node for strict fact-checking, and stateful orchestration utilizing LangGraph to maintain the global state and ensure the stability of concurrent executions and multi-turn conversations.

### 4.2. Multi-Agent Workflow

The multi-agent workflow operates on a strict closed-loop execution pipeline that sequentially processes user inputs through rewriting, routing, collection, verification, synthesis, and memory updates. A raw user query is first processed by the query rewriter to resolve ambiguities before being handed to the supervisor for task dispatch. The supervisor dynamically routes tasks to specialized analysts, and all collected evidence must then pass through the reviewer node. If the reviewer rejects the data due to conflicts or hallucinations, the workflow loops back to the supervisor for retries; if the data passes inspection, the verified evidence moves to the synthesizer for final report generation and concludes with the memory manager updating the system's context.

### 4.3. Core Agents & Responsibilities

The system relies on several core agents with distinct responsibilities to execute the research pipeline seamlessly. The Supervisor functions as the brain of the system by analyzing rewritten queries and dynamically routing tasks based on the current collected data and verification feedback. It dispatches tasks to three concurrently operating specialized workers: the Data Analyst focuses on extracting structured financial metrics from corporate fundamentals, the Market Analyst connects to real-time APIs to retrieve stock trends and news, and the Compliance Analyst leverages Retrieval-Augmented Generation technology to analyze risk factors directly from SEC filings. Once data is collected, the Reviewer acts as the quality gatekeeper to detect hallucinations by checking data consistency and relevance, while also gracefully accepting the reality of genuinely unavailable data to prevent infinite retry loops. Finally, the Synthesizer generates the final report using exclusively verified evidence, strictly prohibiting information fabrication by explicitly stating when data is unavailable.

### 4.4. Memory Management and Context Control

To support complex multi-turn follow-up queries and prevent token overflow, the system utilizes a two-level memory structure alongside an automatic clearing mechanism. At the beginning of each new query, the query rewriter stage automatically issues a command to empty the temporary draft data generated in the previous turn, ensuring that the evidence for every research report remains pure and unpolluted by historical interactions. The specific roles of the short-term and long-term memory components are detailed in the following table.

| **Memory Type**                         | **Content**                                | **Purpose**                                                                              |
| --------------------------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------- |
| **Short-Term Memory (`chat_history`)**  | Details of the last 2-3 conversation turns | Supports coreference resolution for pronouns like "it" or "this company".                |
| **Long-Term Memory (`memory_summary`)** | Compressed summary of older conversations  | Retains key context in long sessions while drastically reducing context window pressure. |

### 4.5. Summary of Technical Advantages

The technical advantages of the ARGUS system are defined by its engineering-grade anti-hallucination mechanisms, concurrency capabilities, and contextual robustness. By implementing the reviewer node and the synthesizer's fallback logic, the system structurally prevents the AI from fabricating data. Furthermore, it leverages the fan-out and fan-in mechanisms of LangGraph to enable the parallel execution of multiple analyst nodes, significantly boosting report generation efficiency. Finally, through query rewriting and a sliding window memory manager, the system effortlessly handles complex follow-up questions while maintaining extremely low prompt token costs.

## Conclusion

ARGUS AI demonstrates a significant architectural advancement in the application of agentic AI to the complex domain of financial analysis. Its strength lies not in a single monolithic model, but in its holistic, systems-level design that mirrors the division of labor found in human expert teams.

By systematically integrating a standardized **Data Layer**, a precision-engineered **RAG Layer**, and a collaborative, self-verifying **Agent Layer**, ARGUS creates an analytical workforce that is both powerful and reliable. The system's core design principles—modularity, verifiable evidence, and closed-loop reasoning—directly confront the critical challenges of factual accuracy and transparency that have historically limited the enterprise adoption of large language models.

The result is a system capable of producing institutional-grade equity research that is not only fast and scalable but, most importantly, trustworthy and auditable. ARGUS provides a robust blueprint for building next-generation AI systems that can tackle complex, knowledge-intensive domains with the rigor and dependability required by professional institutions.
