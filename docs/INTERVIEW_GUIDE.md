# Kissan AI - Interview Preparation & Architecture Guide

This document is designed to help you confidently present and defend the **Kissan AI** project in technical interviews. It covers the system architecture, key design decisions, trade-offs, and data flow.

---

## 1. Project Overview
**What is Kissan AI?**
Kissan AI is a multilingual, completely offline Retrieval-Augmented Generation (RAG) chatbot designed to assist farmers. It provides contextual advice on crop diseases, fertilizers, and farming practices by retrieving verified agricultural knowledge from local documents.

**Key Features:**
- 100% Offline and Local (No paid APIs, maximum privacy).
- Multilingual Support (English, Hindi, Telugu).
- Extensible architecture designed for future integration with CNN disease prediction models.

---

## 2. Technology Stack & "Why?"

In an interview, you must explain *why* you chose a technology, not just *what* it is.

| Component | Technology | Why we chose it over alternatives |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI** | Faster and more asynchronous than Flask/Django. Built-in data validation via Pydantic. Auto-generates Swagger API documentation. |
| **Vector Database** | **FAISS (CPU)** | Runs entirely locally. Faster than traditional databases for similarity search. We avoided cloud solutions like Pinecone to ensure offline capability. |
| **Embeddings** | **SentenceTransformers (`all-MiniLM-L6-v2`)** | Extremely lightweight (produces 384-dimensional vectors). Fast enough for CPU inference while maintaining high semantic accuracy. |
| **LLM Inference** | **Ollama (`llama3`)** | Allows us to run powerful open-weights models locally. Avoids OpenAI API costs and internet dependency. |
| **Translation** | **Ollama + LangDetect** | Instead of downloading heavy offline translation models (like Helsinki-NLP), we use the existing local LLM via zero-shot prompting to translate non-English queries, saving disk space and memory. |

---

## 3. The RAG Pipeline (Data Flow)

If an interviewer asks: *"Walk me through what happens when a user asks a question in Hindi,"* you should explain this flow:

1. **Language Detection**: The `UserQuery` hits the FastAPI `/chat` endpoint. `langdetect` identifies it as Hindi.
2. **Translation (Inbound)**: The `LocalTranslator` prompts Ollama to translate the Hindi text to English. 
3. **Embedding**: The English query is converted into a 384-dimensional numeric vector by the `SentenceTransformerEmbedding` model.
4. **Vector Search (Retrieval)**: The query vector is passed to `FAISSVectorStore`. FAISS calculates the L2 distance (Euclidean distance) against all document vectors and returns the Top-5 most relevant text chunks.
5. **Prompt Building**: The `AgriPromptBuilder` injects the 5 retrieved chunks into a system prompt alongside the English user query (and placeholder for CNN disease predictions).
6. **LLM Generation**: Ollama receives the massive prompt and generates a contextual, grounded answer in English.
7. **Translation (Outbound)**: The `LocalTranslator` prompts Ollama to translate the English response back to Hindi.
8. **Response**: The final Hindi text is returned to the user via FastAPI.

---

## 4. Key Design Decisions & Trade-Offs

Interviewers love discussing trade-offs. Here is how to defend your architecture:

### A. Modular "Clean" Architecture
- **Decision**: We created abstract Base classes (`BaseLLM`, `BaseVectorStore`, `BaseDocumentLoader`) rather than writing monolithic code.
- **Why**: Dependency Inversion. If we ever want to swap FAISS for Pinecone, or Ollama for OpenAI, we only need to write a new class that implements the base interface. The core `ChatEngine` requires *zero* code changes.

### B. Chunking Strategy
- **Decision**: Overlapping sliding window (1000 characters with 200 character overlap).
- **Why**: Simple fixed-size chunking might cut a sentence in half, destroying context. The 200-character overlap ensures that boundaries don't sever semantic meaning.

### C. Fully Local vs. Cloud APIs
- **Trade-off**: Running locally via Ollama and FAISS limits response speed and model intelligence compared to GPT-4.
- **Defense**: For agricultural use cases in remote areas (India), internet connectivity is unreliable. The offline-first requirement strictly overrides the need for absolute state-of-the-art reasoning.

---

## 5. Future Scalability (How to answer "What's next?")

If asked how you would scale or improve this project, mention these points:

1. **CNN Integration**: The `PromptBuilder` already accepts a `cnn_context` variable. Future scope includes linking a PyTorch CNN that detects tomato diseases from images, passing the result directly into the RAG prompt ("The user uploaded a tomato with 96% Early Blight...").
2. **Memory Upgrades**: Currently, chat history is an `InMemoryHistory` Python dictionary (wiped on server restart). We would implement a `RedisMemory` class to persist sessions globally.
3. **Vector Store Scaling**: If the knowledge base grows to millions of documents, FAISS FlatL2 (exact search) becomes slow. We would swap to `FAISS IVF` (Inverted File Index) or `Milvus` for approximate nearest neighbor (ANN) search.
