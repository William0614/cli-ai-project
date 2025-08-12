import asyncio
from terminal_bench_agent import TerminalBenchAgent
from terminal_bench.agents.base_agent import TmuxSession # Import TmuxSession for mocking
from pathlib import Path

async def run_test():
    agent = TerminalBenchAgent()
    test_instruction = "List all files in the current directory."

    # Create a mock TmuxSession and logging_dir
    # In a real terminal-bench environment, these would be provided.
    mock_session = TmuxSession(session_name="mock_session", socket_path="/tmp/mock_socket")
    mock_logging_dir = Path("./test_logs")
    mock_logging_dir.mkdir(exist_ok=True)

    print(f"\n--- Running test with instruction: {test_instruction} ---")
    result = await agent.perform_task(test_instruction, mock_session, mock_logging_dir)

    print("\n--- Test Result ---")
    print(f"Failure Mode: {result.failure_mode}")
    print(f"Timestamped Markers: {result.timestamped_markers}")
    print(f"Total Input Tokens: {result.total_input_tokens}")
    print(f"Total Output Tokens: {result.total_output_tokens}")

    # You can add assertions here to check the expected behavior
    # For example, assert result.failure_mode == FailureMode.NONE

if __name__ == "__main__":
    asyncio.run(run_test())
