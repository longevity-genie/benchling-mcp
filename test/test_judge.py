import json
import pytest
import os
from pathlib import Path

from dotenv import load_dotenv
from just_agents import llm_options
from just_agents.base_agent import BaseAgent
from benchling_mcp.server import BenchlingMCP

# Load environment
load_dotenv(override=True)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
TEST_DIR = PROJECT_ROOT / "test"

# Load judge prompt
with open(TEST_DIR / "judge_prompt.txt", "r", encoding="utf-8") as f:
    JUDGE_PROMPT = f.read().strip()

# System prompt for test agent
SYSTEM_PROMPT = """You are a Benchling assistant that helps scientists manage their biological research data. 
You have access to tools for interacting with the Benchling platform to:
- Retrieve and manage DNA, RNA, and protein sequences
- Access notebook entries and project information
- Search across different entity types
- Download sequence files
- Organize data within projects and folders

Always use the available tools to access Benchling data and provide accurate, helpful responses.
Include details about which tools you used and what data you retrieved in your response."""

# Load reference Q&A data
with open(TEST_DIR / "test_qa.json", "r", encoding="utf-8") as f:
    QA_DATA = json.load(f)

answers_model = {
    "model": "gemini/gemini-2.5-flash-preview-05-20",
    "temperature": 0.0
}

judge_model = {
    "model": "gemini/gemini-2.5-flash-preview-05-20",
    "temperature": 0.0
}

# Initialize agents
@pytest.fixture(scope="session")
def benchling_server():
    """Create BenchlingMCP server instance."""
    api_key = os.getenv("BENCHLING_API_KEY")
    domain = os.getenv("BENCHLING_DOMAIN")
    
    if not api_key or not domain:
        pytest.skip("Missing BENCHLING_API_KEY or BENCHLING_DOMAIN environment variables")
    
    return BenchlingMCP(api_key=api_key, domain=domain)

@pytest.fixture(scope="session")
def test_agent(benchling_server):
    """Create test agent with Benchling tools."""
    tools = [
        benchling_server.get_projects,
        benchling_server.get_dna_sequences,
        benchling_server.get_entries,
        benchling_server.get_folders,
        benchling_server.search_entities,
        benchling_server.get_dna_sequence_by_id,
        benchling_server.get_entry_by_id,
        benchling_server.download_sequence_by_name,
        benchling_server.download_dna_sequence
    ]
    
    return BaseAgent(
        llm_options=answers_model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT
    )

@pytest.fixture(scope="session")
def judge_agent():
    """Create judge agent."""
    return BaseAgent(
        llm_options=judge_model,
        tools=[],
        system_prompt=JUDGE_PROMPT
    )

@pytest.mark.skipif(
    os.getenv("CI") in ("true", "1", "True") or 
    os.getenv("GITHUB_ACTIONS") in ("true", "1", "True") or 
    os.getenv("GITLAB_CI") in ("true", "1", "True") or 
    os.getenv("JENKINS_URL") is not None,
    reason="Skipping expensive LLM tests in CI to save costs. Run locally with: pytest test/test_judge.py"
)
@pytest.mark.parametrize("qa_item", QA_DATA, ids=[f"Q{i+1}" for i in range(len(QA_DATA))])
def test_question_with_judge(qa_item, test_agent, judge_agent):
    """Test each question by generating an answer and evaluating it with the judge."""
    question = qa_item["question"]
    reference_answer = qa_item["answer"]
    reference_tools = qa_item.get("tools_used", [])
    
    # Generate answer
    generated_answer = test_agent.query(question)
    
    # Judge evaluation
    judge_input = f"""
QUESTION: {question}

REFERENCE ANSWER: {reference_answer}

EXPECTED TOOLS USED: {', '.join(reference_tools)}

GENERATED ANSWER: {generated_answer}
"""
    
    judge_result = judge_agent.query(judge_input).strip().upper()
    
    # Print for debugging
    print(f"\nQuestion: {question}")
    print(f"Generated: {generated_answer[:200]}...")
    print(f"Judge: {judge_result}")
    
    if "PASS" not in judge_result:
        print(f"\n=== JUDGE FAILED ===")
        print(f"Question: {question}")
        print(f"Reference Answer: {reference_answer}")
        print(f"Current Answer: {generated_answer}")
        print(f"===================")
    
    assert "PASS" in judge_result, f"Judge failed for question: {question}" 