from abc import ABC, abstractmethod
from pathlib import Path
from unittest.mock import patch
import asyncio
import json
import sys
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# Assuming these are available in the same project structure
from main import create_plan, execute_plan, summarize_plan_result, current_working_directory
from terminal_bench.agents.base_agent import BaseAgent, AgentResult, FailureMode, TmuxSession

class Jarvis(BaseAgent):
    @staticmethod
    def name() -> str:
        return "GPT-5-Nano Jarvis"

    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
    ) -> AgentResult:
        """
        This is a synchronous method called by the terminal-bench harness.
        It runs an inner async function to correctly handle your async logic.
        """

        # Define a new ASYNC function that contains your core logic
        async def _run_async_logic():
            # Mocking and history initialization is done inside the async function
            with patch('builtins.input', return_value='yes'):
                with patch('main.get_user_input', return_value=(instruction, False)):
                    history = [f"User: {instruction}"]
                    
                    try:
                        # Step 1: AWAIT the create_plan coroutine
                        decision = await create_plan(history, current_working_directory)

                        if "plan" not in decision:
                            # If no plan is created, handle it and return
                            final_summary = decision.get("text", "No plan generated and no direct text response.")
                            return AgentResult(
                                total_input_tokens=0,
                                total_output_tokens=0,
                                failure_mode=FailureMode.UNSET if "text" not in decision else FailureMode.NONE,
                                timestamped_markers=[(0.0, f"AI: {final_summary}")]
                            )

                        current_plan = decision["plan"]
                        
                        # Step 2: AWAIT the execute_plan coroutine
                        plan_results, plan_halted = await execute_plan(current_plan, history)

                        # Step 3: AWAIT the summarize_plan_result coroutine
                        final_summary = await summarize_plan_result(plan_results)

                        # Determine the final failure mode
                        failure_mode = FailureMode.NONE
                        if plan_halted:
                            failure_mode = FailureMode.UNSET

                        return AgentResult(
                            total_input_tokens=0,
                            total_output_tokens=0,
                            failure_mode=failure_mode,
                            timestamped_markers=[(0.0, f"AI: {final_summary}")]
                        )

                    except Exception as e:
                        # Handle any unexpected errors during execution
                        return AgentResult(
                            total_input_tokens=0,
                            total_output_tokens=0,
                            failure_mode=FailureMode.UNSET,
                            timestamped_markers=[(0.0, f"Error during task execution: {e}")]
                        )
        
        # Use asyncio.run() to create an event loop, run your async logic,
        # and return the final result.
        return asyncio.run(_run_async_logic())

    def _get_network_name(self, container_name: str) -> str:
        # This method is part of BaseAgent but might not be directly relevant
        # for a simple agent that doesn't manage network containers.
        return super()._get_network_name(container_name)

    @property
    def version(self) -> str:
        # You can set a version for your agent
        return "1.0.0"