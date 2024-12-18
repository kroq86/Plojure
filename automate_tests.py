import subprocess
import os
from openai import OpenAI

client = OpenAI(api_key="KEY")

PROGRAM_FILE = "program.lisp"
ERROR_LOG = "error.log"
MAX_LINES = 100

def run_lisp_program():
    """Run the Lisp program and capture output/errors."""
    try:
        result = subprocess.run(
            ["python", "main.py", PROGRAM_FILE],
            text=True,
            capture_output=True,
        )
        return result.stdout, result.stderr
    except Exception as e:
        return "", f"Error running program: {str(e)}"


def call_chatgpt_with_context(program_content, error_log):
    """Call ChatGPT to generate new tests or fixes."""
    try:
        prompt = f"""
The following is the Lisp program currently being tested:
{program_content}

The program encountered the following errors:
{error_log}

Please provide additional or corrected tests for the Lisp program to address these errors.
Only respond with valid Lisp code. Do not include any comments, explanations, or additional text. Provide only the Lisp code block, formatted properly for direct inclusion in `program.lisp`.
"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert Lisp programmer."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"Error in ChatGPT call: {e}")


def update_program_with_tests(new_tests):
    """Append new tests to the Lisp program."""
    with open(PROGRAM_FILE, "a") as f:
        f.write("\n" + new_tests + "\n")


def count_lines_in_file(file_path):
    """Count the number of lines in a file."""
    with open(file_path, "r") as f:
        return sum(1 for _ in f)


def main():
    while True:
        # Run the program
        stdout, stderr = run_lisp_program()

        # Check the number of lines in the program
        num_lines = count_lines_in_file(PROGRAM_FILE)

        if num_lines >= MAX_LINES:
            print(f"Reached the maximum of {MAX_LINES} lines in {PROGRAM_FILE}. Stopping.")
            break

        if not stderr.strip():
            print("All tests passed! Generating more tests to reach the target line count...")
            program_content = open(PROGRAM_FILE).read()
            new_tests = call_chatgpt_with_context(program_content, "")
            update_program_with_tests(new_tests)
        else:
            print("Errors detected. Adding fixes...")
            program_content = open(PROGRAM_FILE).read()
            new_tests = call_chatgpt_with_context(program_content, stderr)
            update_program_with_tests(new_tests)

        print("Re-running the program with updated tests...\n")


if __name__ == "__main__":
    main()
