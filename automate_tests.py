from openai import OpenAI
import subprocess
import os
import time

# Initialize the OpenAI client
client = OpenAI(api_key="KEY")

PROGRAM_FILE = "program.lisp"
OUTPUT_FILE = "text.txt"
MAX_LINES = 100
MAX_TOKENS = 5000  # Avoid exceeding token cap


def run_lisp_program():
    """Run the Lisp program and capture output/errors."""
    print("Running the Lisp program...")
    try:
        result = subprocess.run(
            ["python", "main.py", PROGRAM_FILE],
            text=True,
            capture_output=True,
        )
        print("Lisp program executed.")
        return result.stdout, result.stderr
    except Exception as e:
        print(f"Error running program: {e}")
        return "", f"Error running program: {str(e)}"


def call_chatgpt_with_context(program_content, error_log, include_main_py=True):
    """Call ChatGPT with the current program and optional main.py context."""
    print("Calling ChatGPT...")
    try:
        # Optionally include main.py as part of the prompt
        main_py_content = ""
        if include_main_py:
            with open("main.py", "r") as f:
                main_py_content = f.read()

        # Construct the prompt
        prompt = f"""
The following is the Lisp program currently being tested:
{program_content}

The Lisp interpreter implementation (main.py) is as follows:
{main_py_content}

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
        print("Received response from ChatGPT.")
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in ChatGPT call: {e}")
        raise


def update_program_with_tests(new_tests):
    """Append new tests to the Lisp program."""
    print("Updating program with new tests...")
    with open(PROGRAM_FILE, "a") as f:
        f.write("\n" + new_tests + "\n")
    print("Program updated.")


def count_lines_in_file(file_path):
    """Count the number of lines in a file."""
    with open(file_path, "r") as f:
        return sum(1 for _ in f)


def retry_with_backoff(func, *args, max_retries=5, backoff_factor=2, **kwargs):
    """Retry a function with exponential backoff."""
    retries = 0
    while retries < max_retries:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            retries += 1
            wait_time = backoff_factor ** retries
            print(f"Retry {retries}/{max_retries} after error: {e}. Waiting {wait_time} seconds.")
            time.sleep(wait_time)
    raise Exception("Maximum retries reached.")


def chunk_content(content, max_length=MAX_TOKENS):
    """Split content into chunks of approximately max_length."""
    lines = content.split("\n")
    chunks = []
    current_chunk = []

    current_length = 0
    for line in lines:
        line_length = len(line)
        if current_length + line_length > max_length:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_length = 0
        current_chunk.append(line)
        current_length += line_length

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def main():
    while True:
        # Clear the output file
        print("Clearing output file...")
        open(OUTPUT_FILE, "w").close()

        # Run the program
        stdout, stderr = run_lisp_program()

        # Write results to text.txt
        with open(OUTPUT_FILE, "w") as output_file:
            output_file.write("Program Output:\n")
            output_file.write(stdout)
            output_file.write("\nErrors:\n")
            output_file.write(stderr)

        # Check if the program passed all tests
        if not stderr.strip():
            print("All tests passed!")

            # Check the number of lines in the program
            num_lines = count_lines_in_file(PROGRAM_FILE)
            if num_lines >= MAX_LINES:
                print(f"Reached the maximum of {MAX_LINES} lines in {PROGRAM_FILE}.")
                break  # Stop adding tests if line limit is reached

            # Call ChatGPT to generate more tests
            program_content = open(PROGRAM_FILE).read()
            chunks = chunk_content(program_content)

            for chunk in chunks:
                print("Requesting new tests from ChatGPT...")
                new_tests = retry_with_backoff(
                    call_chatgpt_with_context, 
                    chunk, 
                    "",  # No errors to report in this case
                    include_main_py=True
                )
                update_program_with_tests(new_tests)
                print("New tests added. Re-running the program...")
        else:
            # If there are errors, ask ChatGPT to analyze and fix them
            print("Analyzing errors and generating corrections...")
            program_content = open(PROGRAM_FILE).read()
            new_tests = retry_with_backoff(
                call_chatgpt_with_context, 
                program_content, 
                stderr, 
                include_main_py=True
            )
            update_program_with_tests(new_tests)
            print("New tests added to address errors. Re-running the program...")


if __name__ == "__main__":
    main()
