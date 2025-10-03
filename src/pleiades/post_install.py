import os
import subprocess
import sys


def check_sammy_installed():
    """
    Checks if sammy is installed and available in the PATH.

    Removes SAMMY.LPT and SAMMY.IO before and after the check.
    """

    try:
        # Remove existing SAMMY.LPT and SAMMY.IO files
        for filename in ["SAMMY.LPT", "SAMMY.IO"]:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"Removed existing {filename}.")

        # Try to run the SAMMY command
        process = subprocess.Popen(
            ["sammy"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )
        stdout, stderr = process.communicate(input=b"q\n")  # Send 'q' (quit) followed by newline

        # Check for keywords in output indicating successful execution
        if b"SAMMY Version" in stdout or b"What is the name of the INPut file" in stdout:
            print("SAMMY is installed and available in the PATH.")
        else:
            print("SAMMY could not be launched or might not be installed correctly.")
            print(f"STDOUT: {stdout.decode().strip()}")
            print(f"STDERR: {stderr.decode().strip()}")
            sys.exit(1)

        # Remove created SAMMY.LPT and SAMMY.IO files (if any)
        for filename in ["SAMMY.LPT", "SAMMY.IO"]:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"Removed temporary {filename}.")

    except FileNotFoundError:
        print("SAMMY is not installed or not available in the PATH.")
        print("Please install SAMMY and ensure the 'sammy' command is in your PATH.")
        sys.exit(1)


if __name__ == "__main__":
    check_sammy_installed()
