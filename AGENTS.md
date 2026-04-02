# Repository Guidelines

## Project Structure & Module Organization
- Core application code lives in `labelme/`, with the main UI in `labelme/app.py` and widgets in `labelme/widgets/`.
- Entry points: run the packaged app via `python -m labelme`; the custom UI wrapper is `main.py`.
- Training-related utilities live under `training_client/` and `model_training.py`.
- Tests and sanity checks are in `tests/` and root-level `test_*.py` scripts.
- UI assets and design artifacts include `mainform.ui`, `ui_understanding.html`, and images under `vibe_images/`.

## Build, Test, and Development Commands
- `python -m labelme`: launch the main application using the package entry point.
- `python main.py`: run the custom integrated UI (useful for local debugging).
- `python test_training_curve_dock.py`: quick manual UI test for curve docks.
- `powershell -File build.ps1`: build the application bundle (Windows).

## Coding Style & Naming Conventions
- Python code uses 4-space indentation and UTF-8 source headers.
- Classes use `CamelCase`, functions and variables use `snake_case`.
- UI object names follow Qt Designer conventions (e.g., `layout_canvas`, `label_canvasPlaceholder`).

## Testing Guidelines
- Tests are simple Python scripts and unit tests; filenames typically start with `test_`.
- Prefer running targeted scripts (e.g., `python test_training_curve_dock.py`) before full suites.
- No explicit coverage gate is enforced in this repository.

## Commit & Pull Request Guidelines
- Recent commits use short, descriptive messages in Chinese (e.g., “优化模型训练”, “修复菜单栏和工具栏显示异常问题”).
- Keep commit messages concise and focused on the change.
- PRs should include: a brief description, relevant screenshots for UI changes, and notes on how to verify.

## Configuration & Local Data
- App-local configuration lives alongside the application:
  - `.labelmerc` (main config)
  - `.labelme_tcp_config.yaml` (TCP client config)
  - `labelme_config.json` (default images folder)
  - `labelme.ini` (window/layout state)
- If docks or layout behave oddly, deleting `labelme.ini` will reset the UI state.
