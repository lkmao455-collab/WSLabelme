# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Labelme is a Python-based graphical image annotation tool with Qt5 GUI. It supports polygon, rectangle, circle, line, and point annotations for image labeling tasks. The tool includes AI-assisted annotation, video annotation, and training client integration features.

## Build System and Commands

This project uses `uv` for Python package management and `pytest` for testing.

### Development Setup
```bash
# Install dependencies (including dev dependencies)
make setup
# or: uv sync --dev
```

### Running the Application
```bash
# Run labelme directly (standard entry point)
python -m labelme

# Run custom integrated UI wrapper (for local debugging)
python main.py

# Run with specific file
python -m labelme path/to/image.jpg

# Run with options
python -m labelme --labels "label1,label2,label3"
```

### Testing
```bash
# Run all tests
make test
# or: uv run pytest -v tests/

# Run GUI tests (marked with @pytest.mark.gui)
uv run pytest -v tests/ -m gui

# Run a single test file
uv run pytest -v tests/labelme_tests/test_app.py

# Run specific test scripts
python test_training_curve_dock.py
```

### Code Quality
```bash
# Format code with ruff
make format
# or: uv run ruff format && uv run ruff check --fix

# Lint only (check mode)
make lint
# or: uv run ruff format --check && uv run ruff check

# Type checking with mypy
make mypy
# or: uv run mypy --package labelme

# Run all checks
make check
```

### Building
```bash
# Build the package
make build
# or: uv build

# Build Windows executable bundle
powershell -File build.ps1
```

## Architecture Overview

### Core Components

**Main Application (`labelme/app.py`)**
- `MainWindow` class: The primary application window extending `QMainWindow`
- Contains the menu bar, toolbar, status bar, and central widget layout
- Handles file operations, shape management, and user interactions
- Integrates with training client, AI prompt widget, and TCP client

**Entry Point (`labelme/__main__.py`)**
- `main()` function: Parses command-line arguments and initializes the application
- Implements single-instance detection using `QSharedMemory`
- Sets up logging with loguru (logs to stderr and file)
- Configures exception handling to show error dialogs for unhandled exceptions

**Shape System (`labelme/shape.py`)**
- `Shape` class: Base class for all annotation shapes
- Supported shape types: `polygon`, `rectangle`, `circle`, `line`, `point`, `linestrip`, `points`, `mask`
- Handles vertex management, drawing, hit detection, and serialization
- Key methods: `addPoint()`, `popPoint()`, `paint()`, `containsPoint()`, `toDict()`

**Canvas Widget (`labelme/widgets/canvas.py`)**
- `Canvas` class: Main drawing area extending `QWidget`
- Handles mouse/keyboard interactions for shape creation and editing
- Emits signals: `newShape`, `selectionChanged`, `shapeMoved`, `drawingPolygon`, etc.
- Modes: `CREATE` (for drawing new shapes) and `EDIT` (for modifying existing shapes)

**Label File (`labelme/label_file.py`)**
- `LabelFile` class: Handles loading and saving JSON annotation files
- Format includes: version, imagePath, imageData (base64), imageHeight, imageWidth, flags, shapes
- Each shape contains: label, points, shape_type, group_id, flags, description, mask (optional)
- `LabelFileError` exception for file operation errors

### Widget Structure (`labelme/widgets/`)

- `canvas.py`: Main drawing canvas
- `label_dialog.py`: Dialog for entering/editing label names
- `label_list_widget.py`: List widget for managing shape labels
- `ai_prompt_widget.py`: Widget for AI-assisted annotation text input
- `training_dock_widget.py`: Dock widget for training visualization
- `training_curve_widget.py`: Widget for displaying training curves
- `unified_training_widget.py`: Unified interface for training tasks
- `thumbnail_file_list.py`: Thumbnail view of files in current directory
- `zoom_widget.py`: Zoom level display and control

### Configuration System (`labelme/config/`)

- `default_config.yaml`: Default application configuration
- `get_config()`: Merges default config with user config (from `~/.labelmerc` or `.labelmerc`)
- Key config options: labels, validate_label, auto_save, sort_labels, shape_color, etc.

### Utility Modules (`labelme/utils/`)

- `image.py`: Image loading, EXIF orientation handling, format conversion
- `qt.py`: Qt-specific utilities (icon creation, pixmap operations)
- `shape.py`: Shape-related utility functions

### CLI Tools (`labelme/cli/`)

- `draw_json.py`: Draw annotations on images
- `draw_label_png.py`: Generate label visualization PNGs
- `json_to_dataset.py`: Convert JSON annotations to dataset formats
- `export_json.py`: Export JSON annotations

### Training Client (`training_client/`)

- `training_client.py`: Client for communicating with training server
- TCP-based communication protocol for remote training management
- Supports training task creation, monitoring, and result retrieval
- Message protocol uses header (4 bytes) + length (4 bytes) + checksum (4 bytes) + JSON data

### AI Features

- Optional dependency: `osam>=0.2.3` for AI annotation
- AI models supported: YOLO World (text-to-bbox), SAM (segmentation)
- Located in `labelme/_automation/` module

## Testing Structure

Tests are located in `tests/labelme_tests/`:
- `test_app.py`: Application-level tests
- `widgets_tests/`: Widget-specific tests
- `utils_tests/`: Utility function tests

GUI tests are marked with `@pytest.mark.gui` and require a display.

## Key Design Patterns

1. **Qt Signal/Slot**: Extensive use of PyQt5 signals for component communication
2. **Model-View**: Canvas manages shape data; widgets display and interact with it
3. **Command Pattern**: Undo/redo system implemented in MainWindow
4. **Configuration Layering**: Default → file → command-line argument merging

## Important Notes

- Single-instance enforcement: Uses `QSharedMemory` to prevent multiple Labelme instances
- Image data storage: Optional (controlled by `--nodata` flag); stores base64-encoded image data in JSON
- Shape types are stored as strings in JSON; use constants when comparing
- The `osam` module is optional; handle `ImportError` gracefully for AI features
- Log files are stored in `~/.cache/labelme/labelme.log` (Unix) or `%LOCALAPPDATA%/labelme/labelme.log` (Windows)

## Configuration Files Location

App-local configuration files are stored alongside the application:
- `.labelmerc`: Main configuration file
- `.labelme_tcp_config.yaml`: TCP client configuration
- `labelme_config.json`: Default images folder setting
- `labelme.ini`: Window/layout state (delete to reset UI if docks behave oddly)

## Coding Guidelines

- All comments must be in Chinese (UTF-8 encoding)
- Default runtime environment: Windows
- Classes use `CamelCase`, functions and variables use `snake_case`
- UI object names follow Qt Designer conventions (e.g., `layout_canvas`, `label_canvasPlaceholder`)
- Commit messages are typically in Chinese (e.g., "优化模型训练", "修复菜单栏和工具栏显示异常问题")
