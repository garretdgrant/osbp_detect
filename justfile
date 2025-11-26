# Configure shell for stricter error handling.
set shell := ["bash", "-eu", "-c"]

# Default recipe just prints a message so users can verify `just` works.
default:
	echo "just is installed and ready"

# Step 2: Install Python (with Tk support) & Git via Homebrew.
install-python-and-git:
	brew install python python-tk git
	python3 --version
	git --version
	echo "Python (Tk-enabled) and Git installed successfully"

# Step 3: Create (or reuse) a project virtual environment.
create-venv:
	if [ ! -d .venv ]; then \
	  python3 -m venv .venv; \
	else \
	  echo ".venv already exists, skipping creation"; \
	fi

# Step 4: Upgrade pip inside the virtual environment.
upgrade-pip:
	source .venv/bin/activate && python3 -m pip install --upgrade pip

# Step 5: Install project dependencies from requirements.txt.
install-deps:
	source .venv/bin/activate && python3 -m pip install -r requirements.txt

# Launch the Tkinter GUI (venv must already be active in your shell).
run-gui:
	python3 gui.py

# Convenience recipe to run all install steps (after Homebrew is installed).
install-prereqs: install-python-and-git create-venv upgrade-pip install-deps
	@echo "Environment ready. Activate it with 'source .venv/bin/activate' before running commands."
