# Configure shell for stricter error handling.
set shell := ["bash", "-eu", "-c"]

# Python version managed by uv for this project.
python-version := env_var_or_default("OSBP_PYTHON_VERSION", "3.14.5")

# Default recipe just prints a message so users can verify `just` works.
default:
	echo "just is installed and ready"

# Step 2: Install the small system tools uv and Git via Homebrew.
install-tools:
	brew install uv git
	uv --version
	git --version
	echo "uv and Git are ready"

# Step 3: Install the project Python through uv.
install-python:
	uv python install {{python-version}}

# Step 4: Create a fresh project virtual environment through uv.
create-venv:
	uv venv --clear --managed-python --python {{python-version}} .venv

# Step 5: Verify the interpreter can launch the Tk GUI.
verify-python:
	.venv/bin/python3 -c 'import sys, tkinter; print(sys.executable); print(sys.version.split()[0]); print("Tk", tkinter.TkVersion)'

# Step 6: Install project dependencies from requirements.txt.
install-deps:
	uv pip install --python .venv/bin/python3 -r requirements.txt

# Launch the Tkinter GUI (venv must already be active in your shell).
run-gui:
	SYSTEM_VERSION_COMPAT=0 .venv/bin/python3 gui.py

update-tool:
	git pull origin master

# Convenience recipe to run all install steps (after Homebrew is installed).
install-prereqs: install-tools install-python create-venv verify-python install-deps
	@echo "Environment ready. Activate it with 'source .venv/bin/activate' before running commands."
