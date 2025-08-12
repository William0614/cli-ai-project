from abc import ABC, abstractmethod
from pathlib import Path
from unittest.mock import patch
import asyncio
import json
import sys

# Assuming these are available in the same project structure
from main import create_plan, execute_plan, summarize_plan_result, current_working_directory
from terminal_bench.agents.base_agent import BaseAgent, AgentResult, FailureMode, TmuxSession

class TerminalBenchAgent(BaseAgent):
    @staticmethod
    def name() -> str:
        return "GeminiCLIAgent"

    async def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
    ) -> AgentResult:
        # Mock input to automatically approve plans and critical steps
        # This is crucial for non-interactive execution in terminal-bench
        with patch('builtins.input', return_value='yes'):
            # Mock get_user_input to directly use the instruction
            # and avoid the interactive loop in main.py
            with patch('main.get_user_input', return_value=(instruction, False)):
                # Redirect stdout to capture output for summarization if needed
                # For now, we'll rely on the existing print statements in main.py
                # and capture the final summary.

                # Initialize history for the plan creation
                history = [f"User: {instruction}"]
                
                # The main loop in main.py is designed for continuous interaction.
                # We need to adapt it to perform a single task based on the instruction.
                # This means we'll call the core logic directly.

                try:
                    # Step 1: Create the plan
                    decision = await create_plan(history, current_working_directory)

                    if "plan" not in decision:
                        # If no plan is created, it might be a direct text response or an error
                        final_summary = decision.get("text", "No plan generated and no direct text response.")
                        return AgentResult(
                            total_input_tokens=0, # Placeholder, actual token count would require integration with LLM calls
                            total_output_tokens=0, # Placeholder
                            failure_mode=FailureMode.OTHER if "text" not in decision else FailureMode.NONE,
                            timestamped_markers=[(0.0, f"AI: {final_summary}")]
                        )

                    current_plan = decision["plan"]
                    
                    # Step 2: Execute the plan
                    plan_results, plan_halted = await execute_plan(current_plan, history)

                    # Step 3: Summarize the results
                    final_summary = await summarize_plan_result(plan_results)

                    # Determine failure mode
                    failure_mode = FailureMode.NONE
                    if plan_halted:
                        failure_mode = FailureMode.OTHER # Or a more specific failure mode if available

                    return AgentResult(
                        total_input_tokens=0, # Placeholder
                        total_output_tokens=0, # Placeholder
                        failure_mode=failure_mode,
                        timestamped_markers=[(0.0, f"AI: {final_summary}")]
                    )

                except Exception as e:
                    # Handle any unexpected errors during execution
                    return AgentResult(
                        total_input_tokens=0,
                        total_output_tokens=0,
                        failure_mode=FailureMode.OTHER,
                        timestamped_markers=[(0.0, f"Error during task execution: {e}")]
                    )

    def _get_network_name(self, container_name: str) -> str:
        # This method is part of BaseAgent but might not be directly relevant
        # for a simple agent that doesn't manage network containers.
        # Implement it as a pass-through or default.
        return super()._get_network_name(container_name)

    @property
    def version(self) -> str:
        # You can set a version for your agent
        return "1.0.0"

# To run this agent with terminal-bench, you would typically register it
# For example, in a terminal-bench configuration file or script:
# from terminal_bench_agent import TerminalBenchAgent
# agent = TerminalBenchAgent()
# terminal_bench.run_task(agent, "your task instruction")
