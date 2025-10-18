import subprocess
import sys
import os

def main():
    here = os.path.dirname(__file__)
    app_path = os.path.join(here, "app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", app_path]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
