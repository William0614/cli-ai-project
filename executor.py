import asyncio
import json
from typing import List, Dict, Any, Callable
from tools import available_tools

class Executor:
    def __init__(self, user_confirm_callback: Callable[[str], bool]):
        self.user_confirm_callback = user_confirm_callback

    async def execute_plan(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for i, step in enumerate(plan):
            thought = step.get("thought", "Executing step")
            tool_name = step.get("tool")
            args = step.get("args", {})
            is_critical = step.get("is_critical", False)

            print(f"\n--- Executing Step {i+1}: {thought} ---")
            print(f"Tool: {tool_name}, Args: {args}")

            # Resolve placeholders
            resolved_args = self._resolve_placeholders(args, results)

            if is_critical:
                confirmation_message = (
                    f"Step {i+1} is marked as critical: '{thought}'. "
                    f"It will execute '{tool_name}' with arguments: {resolved_args}. "
                    "Do you want to proceed? (yes/no): "
                )
                if not self.user_confirm_callback(confirmation_message):
                    print(f"Step {i+1} cancelled by user.")
                    results.append({
                        "step": i + 1,
                        "tool": tool_name,
                        "status": "cancelled",
                        "output": "User cancelled critical step."
                    })
                    break # Stop plan execution if a critical step is cancelled
            
            try:
                tool_func = available_tools.get(tool_name)
                if not tool_func:
                    raise ValueError(f"Unknown tool: {tool_name}")

                if asyncio.iscoroutinefunction(tool_func):
                    output = await tool_func(**resolved_args)
                else:
                    output = tool_func(**resolved_args)
                
                status = "success" if "error" not in output else "failed"
                print(f"Output: {output}")

                results.append({
                    "step": i + 1,
                    "tool": tool_name,
                    "status": status,
                    "output": output
                })

                if status == "failed":
                    print(f"Step {i+1} failed. Stopping plan execution.")
                    break # Stop plan execution on first failure

            except Exception as e:
                print(f"Error executing step {i+1}: {e}")
                results.append({
                    "step": i + 1,
                    "tool": tool_name,
                    "status": "error",
                    "output": {"error": str(e)}
                })
                break # Stop plan execution on error
        return results

    def _resolve_placeholders(self, args: Dict[str, Any], previous_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        resolved_args = {}
        for key, value in args.items():
            if isinstance(value, str) and value.startswith("<output_of_step_") and value.endswith(">"):
                try:
                    parts = value[len("<output_of_step_"):-1].split(">", 1)
                    step_index = int(parts[0]) - 1 # 0-indexed
                    
                    if not (0 <= step_index < len(previous_results)):
                        raise IndexError(f"Step index {step_index + 1} out of bounds for previous results.")
                    
                    step_output = previous_results[step_index]["output"]
                    
                    # Handle nested access like <output_of_step_N>['result']['stdout']
                    if len(parts) > 1:
                        path = parts[1].strip()
                        if path.startswith("['") and path.endswith("']"):
                            # Simple case: direct key access
                            key_path = path[2:-2].split("']['")
                            current_value = step_output
                            for k in key_path:
                                if isinstance(current_value, dict) and k in current_value:
                                    current_value = current_value[k]
                                else:
                                    raise KeyError(f"Key '{k}' not found in output of step {step_index + 1}")
                            resolved_args[key] = current_value
                        else:
                            # More complex path, try to evaluate as a Python expression
                            # This is risky and should be handled carefully, or restricted
                            # For now, we'll assume simple dict key access
                            raise ValueError(f"Unsupported placeholder format: {value}. Only direct key access like <output_of_step_N>['key'] is supported.")
                    else:
                        resolved_args[key] = step_output
                except (ValueError, IndexError, KeyError) as e:
                    print(f"Warning: Could not resolve placeholder '{value}'. Error: {e}")
                    resolved_args[key] = value # Keep original if resolution fails
            elif isinstance(value, dict):
                resolved_args[key] = self._resolve_placeholders(value, previous_results)
            elif isinstance(value, list):
                resolved_args[key] = [self._resolve_placeholders_in_item(item, previous_results) for item in value]
            else:
                resolved_args[key] = value
        return resolved_args

    def _resolve_placeholders_in_item(self, item: Any, previous_results: List[Dict[str, Any]]) -> Any:
        if isinstance(item, dict):
            return self._resolve_placeholders(item, previous_results)
        elif isinstance(item, list):
            return [self._resolve_placeholders_in_item(sub_item, previous_results) for sub_item in item]
        elif isinstance(item, str) and item.startswith("<output_of_step_") and item.endswith(">"):
            try:
                parts = item[len("<output_of_step_"):-1].split(">", 1)
                step_index = int(parts[0]) - 1 # 0-indexed
                
                if not (0 <= step_index < len(previous_results)):
                    raise IndexError(f"Step index {step_index + 1} out of bounds for previous results.")
                
                step_output = previous_results[step_index]["output"]
                
                if len(parts) > 1:
                    path = parts[1].strip()
                    if path.startswith("['") and path.endswith("']"):
                        key_path = path[2:-2].split("']['")
                        current_value = step_output
                        for k in key_path:
                            if isinstance(current_value, dict) and k in current_value:
                                current_value = current_value[k]
                            else:
                                raise KeyError(f"Key '{k}' not found in output of step {step_index + 1}")
                        return current_value
                    else:
                        raise ValueError(f"Unsupported placeholder format: {item}. Only direct key access like <output_of_step_N>['key'] is supported.")
                else:
                    return step_output
            except (ValueError, IndexError, KeyError) as e:
                print(f"Warning: Could not resolve placeholder '{item}'. Error: {e}")
                return item # Keep original if resolution fails
        else:
            return item
