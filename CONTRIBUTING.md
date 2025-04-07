# Contributing to YPY SQLite

Thank you for considering contributing to YPY SQLite! This document provides guidelines and instructions for contributing to this project.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/ypy-sqlite.git
   cd ypy-sqlite
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

4. Install development dependencies:
   ```bash
   pip install pytest pytest-asyncio black isort mypy
   ```

## Running Tests

Run the tests using:

```bash
python test.py
```

Or using pytest directly:

```bash
pytest ypy_sqlite/tests/
```

## Code Style

We use the following tools for code style and quality:

- **Black** for code formatting
- **isort** for import sorting
- **mypy** for type checking

Format your code using:

```bash
black ypy_sqlite/
isort ypy_sqlite/
mypy ypy_sqlite/
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature-name`)
3. Make your changes
4. Run the tests to ensure they pass
5. Format your code (see Code Style section)
6. Commit your changes (`git commit -m 'Add some feature'`)
7. Push to your branch (`git push origin feature/your-feature-name`)
8. Open a Pull Request

## License

By contributing to this project, you agree that your contributions will be licensed under the project's MIT License.