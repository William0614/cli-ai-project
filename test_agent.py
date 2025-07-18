import pytest
import subprocess
import os
import pexpect
import time
from dotenv import load_dotenv
import tempfile
import asyncio
import json
import re
from openai import AsyncOpenAI

# --- SETUP ---
load_dotenv()

AGENT_SCRIPT_PATH = os.path.abspath('main.py')
TEST_RUNS_DIR = os.path.abspath('test_runs')


# --- HELPER FUNCTIONS ---

def load_test_cases_from_txt():
    """
    Loads test cases from a text file with a robust parser that correctly
    handles multiline fields marked with a pipe (|).
    """
    with open("test_prompts.txt", "r") as f:
        content = f.read()
    
    test_cases_data = []
    test_blocks = content.strip().split('\n---')

    for block in test_blocks:
        if not block.strip():
            continue
        
        case = {}
        current_multiline_key = None
        lines = block.strip().split('\n')
        
        for line in lines:
            match = re.match(r'^([\w_]+):\s*(.*)', line)
            if match:
                key, value = match.groups()
                current_multiline_key = None
                
                if value == '|':
                    current_multiline_key = key
                    case[key] = []
                else:
                    case[key] = value
            elif current_multiline_key:
                case[current_multiline_key].append(line)
        
        for key, value in case.items():
            if isinstance(value, list):
                case[key] = "\n".join(value).strip()

        if 'setup' not in case: case['setup'] = ''
        if 'teardown' not in case: case['teardown'] = ''
        
        test_cases_data.append(case)

    return [pytest.param(case, id=case.get('test_id', 'unnamed-txt-test')) for case in test_cases_data]


def evaluate_with_local_model(original_prompt, conversation_log, criteria):
    """
    Evaluates the agent's PLAN, requesting a percentage score from the LLM.
    """
    client = AsyncOpenAI(
        base_url="http://localhost:8001/v1",
        api_key="not-needed"
    )

    system_prompt = """
    You are a meticulous QA engineer. Your task is to evaluate the *thought process and plan* of an AI agent based on its conversation log and provide a quantitative accuracy score.

    **Your focus is exclusively on the agent's plan.**
    - Was the sequence of proposed tool calls logical and correct?
    - Did the agent choose the correct tools with the correct parameters to solve the user's request?
    - **IMPORTANT: DO NOT evaluate the final output of the tool calls.** Judge the plan only.

    **IMPORTANT EXCLUSIONS (Do NOT penalize for these):**
    1.  **Time Taken:** Do not factor the agent's "thinking time" into your score.
    2.  **Minor Inefficiencies:** Do not penalize for harmless extra steps, like using `ls` to verify a file was created. Focus on whether the core plan achieves the goal correctly.
    3.  DO NOT PENALIZE Excessive thinking time displayed before and after the command execution

    Based on the criteria, provide a numeric score from 0 to 100 using the following rubric:
    - **100:** The plan is perfect and directly solves the problem.
    - **60-99:** The plan is acceptable and would likely work, but contains a significant logical flaw or misunderstanding.
    - **40-59:** The plan is deeply flawed. It might misunderstand the user's intent or use tools incorrectly, but shows some semblance of a correct approach.
    - **0-39:** The plan is completely incorrect, illogical, or irrelevant to the user's prompt.

    Respond ONLY with a single JSON object in the following format:
    {"accuracy_score": <INTEGER_SCORE>, "reason": "A brief justification for your score, explaining what was good and what could be improved in the plan."}
    """

    user_content = f"""
    **Original User Prompt:**
    {original_prompt}

    **Full Conversation Log (Focus on the agent's PLAN):**
    ```
    {conversation_log}
    ```

    **Evaluation Criteria (for the Plan):**
    {criteria}
    """

    async def get_evaluation():
        try:
            response = await client.chat.completions.create(
                model="Qwen/Qwen2.5-Coder-32B-Instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                timeout=90
            )
            
            decision = json.loads(response.choices[0].message.content)
            
            try:
                score = int(decision.get("accuracy_score", 0))
            except (ValueError, TypeError):
                pytest.fail(f"LLM returned a non-integer value for 'accuracy_score'. Raw decision: {decision}")

            reason = decision.get("reason", "No reason provided by the model.")
            return score, reason

        except json.JSONDecodeError as e:
            raw_output = response.choices[0].message.content if 'response' in locals() else "No output from model."
            pytest.fail(f"LLM evaluator failed to return valid JSON. Error: {e}. Raw output: '{raw_output}'")
        except Exception as e:
            pytest.fail(f"API call to local model failed: {e}")

    return asyncio.run(get_evaluation())


def run_commands(command_string, cwd):
    """Runs a string of shell commands, ideal for setup/teardown scripts."""
    if not command_string or not command_string.strip():
        return
    subprocess.run(command_string, shell=True, check=True, cwd=cwd, executable='/bin/bash')


# --- THE PYTEST TEST FUNCTION ---

@pytest.mark.parametrize("case", load_test_cases_from_txt())
def test_interactive_agent_with_isolation(case):
    """
    Drives the interactive agent, measures performance, and evaluates the
    plan against a minimum accuracy threshold.
    """
    MIN_ACCURACY_THRESHOLD = 85
    os.makedirs(TEST_RUNS_DIR, exist_ok=True)
    
    with tempfile.TemporaryDirectory(dir=TEST_RUNS_DIR, prefix=f"{case.get('test_id', 'test')}_") as temp_dir:
        run_commands(case.get('setup', ''), cwd=temp_dir)

        full_conversation_log = ""
        child = None
        prompt = case['prompt']
        start_time = 0
        elapsed_time = -1
        batch_count = 0

        try:
            print(f"\n--- Spawning agent for test: {case.get('test_id')} ---")
            child = pexpect.spawn(
                f'python {AGENT_SCRIPT_PATH}',
                cwd=temp_dir,
                encoding='utf-8',
                timeout=60
            )
            child.expect(r'> ')
            # <<< CHANGED: Safely handle non-string 'after' values
            full_conversation_log += child.before + str(child.after)

            start_time = time.time()
            child.sendline(prompt)
            full_conversation_log += prompt + "\n"

            while True:
                patterns = [
                    r'Proceed with this batch\? \(y/n/a - yes/no/always for this task\): ',
                    r'AI: ',
                    r'> ',
                    pexpect.EOF,
                ]
                index = child.expect(patterns, timeout=180)
                # <<< CHANGED: Safely handle non-string 'after' values
                full_conversation_log += child.before + str(child.after)

                if index == 0:
                    batch_count += 1
                    child.sendline('y')
                    full_conversation_log += "y\n"
                    continue
                elif index in [1, 2, 3]:
                    break
            
            elapsed_time = time.time() - start_time

        except pexpect.exceptions.TIMEOUT:
            agent_output = child.before if child else "Child process was not created."
            pytest.fail(f"\n\nERROR: Test timed out.\n--- Log ---\n{agent_output}\n---")
        except Exception as e:
            agent_output = full_conversation_log or (child.before if child else "N/A")
            pytest.fail(f"\nAn unexpected error occurred: {e}\n--- Log ---\n{agent_output}")
        finally:
            if child and child.isalive():
                child.sendline('exit')
                child.close()
            run_commands(case.get('teardown', ''), cwd=temp_dir)

        # --- Final Evaluation ---
        print("\n--- Evaluating Test Run ---")
        print(full_conversation_log)
        print("Asking Local LLM to evaluate the agent's PLAN for an accuracy score...")
        
        accuracy_score, reason = evaluate_with_local_model(
            original_prompt=prompt,
            conversation_log=full_conversation_log,
            criteria=case['evaluation_criteria']
        )
        
        passed = accuracy_score >= MIN_ACCURACY_THRESHOLD
        status_string = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"

        print("\n" + "="*25 + " TEST SUMMARY " + "="*25)
        print(f" Test ID:            {case.get('test_id')}")
        print(f" Status:             {status_string}")
        print("-" * 64)
        print(f" Accuracy Score:     {accuracy_score}% (Threshold: {MIN_ACCURACY_THRESHOLD}%)")
        print(f" Task Time:          {elapsed_time:.2f} seconds")
        print(f" Batches Executed:   {batch_count}")
        print(f" LLM Reason:         {reason}")
        print("=" * 64 + "\n")
        
        assert passed, \
            f"LLM evaluation failed. Score of {accuracy_score}% is below the required threshold of {MIN_ACCURACY_THRESHOLD}%. Reason: {reason}"