"""Normalise the free-text skill strings the portals emit into one vocabulary.

Portals spell the same thing many ways ("GCP" / "Google Cloud Platform",
"k8s" / "Kubernetes"). Everything here maps to a canonical label grouped
into a category, so the aggregate counts mean something.
"""
from __future__ import annotations

import re

# category -> canonical name -> alias patterns (matched case-insensitively)
VOCAB: dict[str, dict[str, list[str]]] = {
    "Language": {
        "Python": [r"python"],
        "TypeScript": [r"typescript", r"\bts\b"],
        "JavaScript": [r"javascript", r"\bjs\b", r"node\.?js"],
        "Java": [r"\bjava\b"],
        "Go": [r"\bgolang\b", r"\bgo\b"],
        "C++": [r"c\+\+", r"cpp"],
        "C#": [r"c#", r"\.net", r"dotnet"],
        "Rust": [r"\brust\b"],
        "SQL": [r"\bsql\b(?!ite)", r"t-sql", r"pl/sql"],
        "Bash/Shell": [r"\bbash\b", r"\bshell\b", r"powershell"],
    },
    "LLM / GenAI": {
        "LLM (general)": [r"\bllms?\b", r"large language model", r"duże modele j"],
        "Generative AI": [r"generative ai", r"\bgen ?ai\b", r"sztuczn\w+ inteligencj"],
        "OpenAI": [r"openai", r"\bgpt-?\d", r"chatgpt"],
        "Anthropic / Claude": [r"anthropic", r"\bclaude\b"],
        "Azure OpenAI": [r"azure openai", r"azure ai"],
        "AWS Bedrock": [r"bedrock"],
        "Google Vertex AI": [r"vertex ai", r"\bgemini\b"],
        "Hugging Face": [r"hugging ?face", r"\bhf\b"],
        "Prompt engineering": [r"prompt"],
        "Fine-tuning": [r"fine-?tun", r"\bpeft\b", r"\blora\b", r"\brlhf\b"],
        "vLLM / serving": [r"\bvllm\b", r"\bollama\b", r"triton", r"\btgi\b"],
    },
    "RAG / Retrieval": {
        "RAG": [r"\brag\b", r"retrieval[- ]augmented"],
        "Embeddings": [r"embedding", r"wektoryzacj"],
        "Vector DB (generic)": [r"vector (db|database|store)", r"baz\w+ wektorow"],
        "Pinecone": [r"pinecone"],
        "Qdrant": [r"qdrant"],
        "Weaviate": [r"weaviate"],
        "Chroma": [r"chroma ?db", r"\bchroma\b"],
        "pgvector": [r"pgvector"],
        "Milvus": [r"milvus"],
        "FAISS": [r"faiss"],
        "Elasticsearch / OpenSearch": [r"elasticsearch", r"opensearch", r"\belk\b"],
        "Semantic search": [r"semantic search", r"hybrid search", r"re-?rank"],
    },
    "Agents / Tooling": {
        "MCP": [r"\bmcp\b", r"model context protocol"],
        "AI agents": [r"\bagent(s|ic|ow)?\b", r"multi-?agent"],
        "LangChain": [r"langchain"],
        "LlamaIndex": [r"llama-?index"],
        "LangGraph": [r"langgraph"],
        "Semantic Kernel": [r"semantic kernel"],
        "AutoGen / CrewAI": [r"autogen", r"crew ?ai"],
        "Function / tool calling": [r"function calling", r"tool calling", r"tool use"],
        "Copilot / AI coding tools": [r"copilot", r"cursor\b", r"ai coding"],
    },
    "ML Core": {
        "PyTorch": [r"pytorch", r"\btorch\b"],
        "TensorFlow": [r"tensorflow", r"\bkeras\b"],
        "scikit-learn": [r"scikit", r"sklearn"],
        "Transformers": [r"transformers?\b", r"\bbert\b", r"\bnlp\b"],
        "pandas / NumPy": [r"\bpandas\b", r"\bnumpy\b"],
        "Machine learning": [r"machine learning", r"uczenie maszynowe", r"\bml\b"],
        "Deep learning": [r"deep learning", r"neural net", r"sieci neuronow"],
        "Computer vision": [r"computer vision", r"\bopencv\b"],
    },
    "MLOps / Platform": {
        "MLOps / LLMOps": [r"mlops", r"llmops", r"aiops"],
        "MLflow": [r"mlflow"],
        "Kubeflow": [r"kubeflow"],
        "Weights & Biases": [r"weights ?& ?biases", r"\bwandb\b"],
        "LangSmith / Langfuse": [r"langsmith", r"langfuse"],
        "Ray": [r"\bray\b"],
        "Feature store": [r"feature store", r"feast\b"],
        "Model deployment": [r"model (serving|deployment)", r"bentoml", r"seldon", r"kserve"],
    },
    "Evaluation / Quality": {
        "Evals / benchmarking": [r"\bevals?\b", r"evaluation", r"benchmark", r"ewaluacj"],
        "Guardrails / safety": [r"guardrail", r"\bsafety\b", r"responsible ai", r"ai governance"],
        "Observability": [r"observability", r"\btracing\b", r"opentelemetry", r"\botel\b",
                          r"grafana", r"prometheus", r"datadog"],
        "A/B testing": [r"a/b test", r"experimentation"],
        "Hallucination / groundedness": [r"hallucinat", r"groundedness", r"factualit"],
    },
    "Testing (your base)": {
        "pytest": [r"pytest"],
        "Robot Framework": [r"robot ?framework"],
        "Test automation": [r"test automation", r"automatyzacj\w+ test", r"\bqa\b",
                            r"\bsdet\b", r"testy automatyczne"],
        "Selenium": [r"selenium"],
        "Playwright": [r"playwright"],
        "Cypress": [r"cypress"],
        "Performance testing": [r"performance test", r"\bjmeter\b", r"\blocust\b", r"\bk6\b"],
        "Embedded / HW testing": [r"embedded", r"\bhil\b", r"\bcan\b bus", r"hardware.in.the.loop"],
    },
    "Cloud": {
        "AWS": [r"\baws\b", r"amazon web services"],
        "Azure": [r"\bazure\b"],
        "GCP": [r"\bgcp\b", r"google cloud"],
        "SageMaker": [r"sagemaker"],
        "Databricks": [r"databricks"],
        "Snowflake": [r"snowflake"],
        "Cloud (generic)": [r"\bcloud\b", r"chmur"],
    },
    "Infra / DevOps": {
        "Docker": [r"docker", r"konteneryzacj", r"container"],
        "Kubernetes": [r"kubernetes", r"\bk8s\b", r"\bhelm\b", r"openshift"],
        "Terraform / IaC": [r"terraform", r"\biac\b", r"infrastructure as code", r"pulumi"],
        "CI/CD": [r"ci/?cd", r"jenkins", r"github actions", r"gitlab ci", r"azure devops",
                  r"argo ?cd", r"teamcity"],
        "Git": [r"\bgit\b(?!hub actions)"],
        "Linux": [r"\blinux\b", r"\bunix\b"],
    },
    "Backend / Data": {
        "FastAPI": [r"fastapi"],
        "Flask / Django": [r"\bflask\b", r"\bdjango\b"],
        "REST / API design": [r"\brest\b", r"\bapi\b", r"openapi", r"swagger"],
        "GraphQL / gRPC": [r"graphql", r"\bgrpc\b"],
        "Microservices": [r"microservice", r"mikroserwis"],
        "Kafka / streaming": [r"\bkafka\b", r"streaming", r"rabbitmq", r"pub/?sub"],
        "Airflow / orchestration": [r"airflow", r"\bdagster\b", r"\bprefect\b"],
        "dbt / ETL": [r"\bdbt\b", r"\betl\b", r"\belt\b", r"data pipeline"],
        "PostgreSQL": [r"postgres"],
        "NoSQL": [r"mongodb", r"\bredis\b", r"cassandra", r"dynamodb"],
        "Spark": [r"\bspark\b", r"pyspark", r"\bhadoop\b"],
        "BigQuery / Snowflake DW": [r"bigquery", r"redshift", r"synapse"],
    },
}

# pre-compile: (category, canonical, compiled regex)
_COMPILED: list[tuple[str, str, re.Pattern]] = [
    (cat, canon, re.compile("|".join(pats), re.IGNORECASE))
    for cat, items in VOCAB.items()
    for canon, pats in items.items()
]

CANON_CATEGORY: dict[str, str] = {
    canon: cat for cat, items in VOCAB.items() for canon in items
}


def extract(*chunks: str) -> set[str]:
    """Return the canonical technologies mentioned anywhere in `chunks`."""
    blob = " \n ".join(c for c in chunks if c)
    if not blob:
        return set()
    return {canon for _, canon, rx in _COMPILED if rx.search(blob)}


def from_offer(offer) -> set[str]:
    """Skills field is authoritative; description is a weaker secondary signal."""
    return extract(" , ".join(offer.skills), offer.title, offer.text)
