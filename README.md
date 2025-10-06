# LeetCode Visualizer

A lightweight step-by-step execution helper for experimenting with LeetCode (or any Python) solutions. It wraps your callable with a tracer, highlights the currently executing line, and prints locals so you can follow the algorithm like an interactive debugger.

## Requirements
- Python 3.9 or newer
- Optional but recommended: [`rich`](https://github.com/Textualize/rich) for the full-screen terminal UI (falls back to plain text if Rich is missing)

## Virtual environments 101
A **virtual environment** is a self-contained folder that carries its own Python interpreter and `site-packages` directory. Anything you install while it is active lives inside that folder instead of touching your global Python install -- that is why `pip` warns when you install packages "outside a virtual environment".

### Create one
1. Make sure Python is available:
   ```bash
   python --version
   ```
   On Windows you can also try `py --version`.
2. From the project root, create the environment (this copies Python into `.venv/`):
   ```bash
   python -m venv .venv
   ```
   If you hit `Permission denied ... .venv\Scripts\python.exe`, delete the partial folder and rerun with elevated rights:
   - PowerShell: `Remove-Item -Recurse -Force .venv`
   - Git Bash: `rm -rf .venv`
   Then retry `python -m venv .venv` (PowerShell "Run as administrator" usually fixes the permission issue).

### Working across shells (PowerShell, Command Prompt, Git Bash)
- Git Bash shows Unix-style paths such as `/c/Users/zhang/...`. PowerShell and Command Prompt expect `C:\Users\zhang\...`.
- Quick conversion from Git Bash: `pwd -W` prints the Windows-style path you can paste into PowerShell.
- PowerShell: `Set-Location "C:\Users\zhang\00My Stuff\Coding\Projects\leetcode-visualizer"`
- Command Prompt: `cd "C:\Users\zhang\00My Stuff\Coding\Projects\leetcode-visualizer"`
- Or open File Explorer, navigate to the folder, and choose "Open in Terminal/PowerShell here".

### Activate it
| Shell | Command |
|-------|---------|
| Windows PowerShell | `.\.venv\Scripts\Activate.ps1` |
| Windows Command Prompt | `.\.venv\Scripts\activate.bat` |
| Windows Git Bash / MinGW | `source .venv/Scripts/activate` |
| macOS/Linux | `source .venv/bin/activate` |

When activation succeeds your prompt shows `(.venv)` at the front. Windows environments use the `Scripts/` directory; Unix-like environments use `bin/`, hence the different paths. To exit later, run `deactivate`.

### Install dependencies inside the environment
```bash
python -m pip install --upgrade pip
pip install rich
```

Everything installed while the environment is active stays under `.venv/`; your global Python remains untouched.

## Running the examples
The project ships with two samples under `examples/`. Both expect to be launched **from the project root** so Python can locate the `visualizer` package.

### "Run as a module" (recommended)
Use `python -m package.module`. Python resolves the module inside the current project and automatically adds the project directory to `sys.path`, so imports like `from visualizer.core import ...` work without extra configuration.

```
python -m examples.count_good_subsequences
python -m examples.LC1307_word_arithmetic_problem
```

### Why this avoids `ModuleNotFoundError`
When you run a file directly (`python examples/foo.py`), Python sets `sys.path[0]` to the directory of that file (`examples/`). The `visualizer` package lives one directory higher, so the interpreter cannot find it unless you tweak `PYTHONPATH`. Running "as a module" keeps the project root on the import path automatically, which is why it is the safest option.

### What is `PYTHONPATH`?
`PYTHONPATH` is an environment variable listing extra folders Python should search for modules. You rarely need to modify it manually, but if you do want to run a script file directly you can set it temporarily:
- macOS/Linux:
  ```bash
  PYTHONPATH=. python examples/LC1307_word_arithmetic_problem.py
  ```
- Windows PowerShell:
  ```powershell
  $env:PYTHONPATH = (Get-Location)
  python examples/LC1307_word_arithmetic_problem.py
  ```
  Afterwards you can remove the variable with `Remove-Item Env:PYTHONPATH`.

## Step-by-step: run the LC1307 example
1. Activate your virtual environment (see above).
2. Install Rich if you have not already: `pip install rich`
3. From the project root run:
   ```bash
   python -m examples.LC1307_word_arithmetic_problem
   ```
4. You should see the Rich full-screen UI (or plain text if Rich is missing) showing:
   - syntax-highlighted source for the currently executing lines,
   - live `assignment` and `used_digits` tables,
   - the controls (`Enter` to step, `c` to continue, `q` to quit).

Want to tweak the input? Edit the `run_visualization()` function at the bottom of `examples/LC1307_word_arithmetic_problem.py`, or drive it via the CLI runner described below.

## Use the CLI runner for any script
The helper in `visualize.py` lets you control arguments and watch lists from the command line:

```bash
python visualize.py <path-to-script> "<callable-expression>" --args "(<positional-args>)" --kwargs "{<keyword-args>}" --watch var1,var2
```

**Required arguments**
- `script`: path to the Python file that defines the callable you want to visualize (relative paths resolved from the current working directory).
- `expr`: Python expression evaluated in that module's global scope. Examples: `"Solution().countGoodSubsequences"`, `"solve"`, `"MyClass.helper"`.

**Optional flags**
- `--args`: tuple literal with positional arguments. Defaults to `()`; a single argument like `"('aabc',)"` needs the trailing comma.
- `--kwargs`: dict literal for keyword arguments. Defaults to `{}`.
- `--watch`: comma-separated variable names to highlight. Defaults to an empty list.

Re-run the LC1307 example through the CLI like this:

```bash
python visualize.py examples/LC1307_word_arithmetic_problem.py "Solution().isSolvable" --args "(['SEND','MORE'],'MONEY')" --watch assignment,used_digits,column,word_index,carry
```

## Embedding programmatically
```python
from visualizer.core import RenderSettings, Visualizer

visualizer = Visualizer(settings=RenderSettings(watch=["ans", "bit_mask"]))
solution = Solution()
visualizer.run(solution.countGoodSubsequences, "aabc")
```

To force the classic text output even when Rich is installed, pass `RenderSettings(use_rich=False)`.

## Notes
- By default the tracer prints three lines of context around the current line. Adjust `RenderSettings(context_lines=...)` to change the window size.
- Large values are truncated to keep the output readable. Tweak `RenderSettings(max_value_repr=...)` for wider previews.
- Built-in frames are filtered out: only code from your target script appears so you can focus on your solution.
