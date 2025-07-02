import os
from pathlib import Path

memory_file = Path(os.getcwd()).resolve() / ".cli_ai" / "CLI_AI.md"
memory_dir = Path(os.getcwd()).resolve() / ".cli_ai"

def save_memory(fact: str):
    if not fact or not isinstance(fact, str):
        raise ValueError("You must provide a non-empty string as a fact.")

    section_header = "Memories"

    # Ensure the directory exists
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Create the file if it doesn't exist, or load existing content
    if not memory_file.exists():
        with open(memory_file, "w") as f:
            f.write(f"{section_header}\n\n- {fact}\n")
        print(f"Created {memory_file} and added memory.")
        return

    # Read existing content
    with open(memory_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find section header or add it if missing
    if section_header not in "".join(lines):
        lines.append(f"\n{section_header}\n")

    # Insert fact under the section
    new_lines = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if section_header in line and not inserted:
            new_lines.append(f"- {fact}\n")
            inserted = True

    # In case section header was added at the end
    if not inserted:
        new_lines.append(f"- {fact}\n")

    # Write back to file
    with open(memory_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # print(f"Memory saved: {fact}")
