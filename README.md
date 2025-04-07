# YPY SQLite Persistence Provider

A SQLite persistence provider for [YPY](https://github.com/y-crdt/ypy), the Python bindings for [Yjs](https://github.com/yjs/yjs).

## Installation

```bash
pip install ypy-sqlite
```

## Usage

Here's a basic example of how to use the YPY SQLite persistence provider:

```python
import asyncio
import y_py as Y
from ypy_sqlite import SQLitePersistence

async def example():
    # Initialize the persistence layer
    persistence = await SQLitePersistence.build("data.db", {
        "flush_size": 100,
        "table_name": "my_documents",
        "use_index": True
    })

    # Create and load a document
    doc_name = "example-doc"
    ydoc = await persistence.get_ydoc(doc_name)

    # Make changes
    with ydoc.begin_transaction() as txn:
        ytext = txn.get_text("content")
        ytext.insert(0, "Hello, world!")

    # Get updates for sync
    state_vector = await persistence.get_state_vector(doc_name)

    # Store updates
    update = Y.encode_state_as_update(ydoc)
    await persistence.store_update(doc_name, update)

    # Clean up
    await persistence.destroy()

if __name__ == "__main__":
    asyncio.run(example())
```

## API

### SQLitePersistence

#### `async SQLitePersistence.build(db_path, options=None)`

Initialize the persistence layer with options.

- `db_path`: Path to the SQLite database file
- `options`: Configuration options
  - `flush_size`: Number of updates before flushing (default: 200)
  - `table_name`: Name of the table to store documents (default: "ypy_documents")
  - `use_index`: Whether to use an index on the table (default: True)

#### `async get_ydoc(doc_name)`

Create a Y.Doc instance with the data persisted in SQLite.

#### `async store_update(doc_name, update)`

Store a single document update to the database.

#### `async get_state_vector(doc_name)`

Get the state vector for a document.

#### `async get_diff(doc_name, state_vector)`

Get differences between the current document state and the provided state vector.

#### `async clear_document(doc_name)`

Delete a document and all associated data from the database.

#### `async destroy()`

Clean up resources and close the database connection.

## License

MIT