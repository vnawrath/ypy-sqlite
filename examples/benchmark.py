import asyncio
import os
import time
import y_py as Y
from ypy_sqlite import SQLitePersistence


async def run_benchmark():
    # Create a temporary database file
    db_path = "benchmark.db"
    
    # Remove the database file if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    print("=== YPY SQLite Persistence Benchmark ===")
    
    # Initialize the persistence layer
    start_time = time.time()
    persistence = await SQLitePersistence.build(db_path)
    end_time = time.time()
    print(f"Initialization time: {(end_time - start_time) * 1000:.2f} ms")
    
    doc_name = "benchmark-doc"
    
    # Benchmark document creation
    start_time = time.time()
    ydoc = await persistence.get_ydoc(doc_name)
    end_time = time.time()
    print(f"Empty document load time: {(end_time - start_time) * 1000:.2f} ms")
    
    # Benchmark small update
    with ydoc.begin_transaction() as txn:
        ytext = txn.get_text("text")
        ytext.insert(0, "Hello, world!")
    
    update = Y.encode_state_as_update(ydoc)
    
    start_time = time.time()
    await persistence.store_update(doc_name, update)
    end_time = time.time()
    print(f"Small update store time: {(end_time - start_time) * 1000:.2f} ms")
    
    # Benchmark document load with content
    start_time = time.time()
    ydoc2 = await persistence.get_ydoc(doc_name)
    end_time = time.time()
    print(f"Document load time with content: {(end_time - start_time) * 1000:.2f} ms")
    
    # Benchmark state vector retrieval
    start_time = time.time()
    sv = await persistence.get_state_vector(doc_name)
    end_time = time.time()
    print(f"State vector retrieval time: {(end_time - start_time) * 1000:.2f} ms")
    
    # Benchmark large document
    print("\n--- Large Document Test ---")
    large_doc_name = "large-benchmark-doc"
    large_doc = await persistence.get_ydoc(large_doc_name)
    
    # Create a document with many operations
    with large_doc.begin_transaction() as txn:
        ytext = txn.get_text("text")
        for i in range(1000):
            ytext.insert(len(ytext.to_string()), f"Line {i}: This is a test line with some content.\n")
    
    large_update = Y.encode_state_as_update(large_doc)
    print(f"Large update size: {len(large_update)} bytes")
    
    start_time = time.time()
    await persistence.store_update(large_doc_name, large_update)
    end_time = time.time()
    print(f"Large update store time: {(end_time - start_time) * 1000:.2f} ms")
    
    start_time = time.time()
    large_doc2 = await persistence.get_ydoc(large_doc_name)
    end_time = time.time()
    print(f"Large document load time: {(end_time - start_time) * 1000:.2f} ms")
    
    # Check if flush happened due to large document size
    print(f"Document size exceeded flush threshold: {persistence.flush_size}")
    
    # Clean up
    await persistence.destroy()
    
    # Remove the database file
    if os.path.exists(db_path):
        os.remove(db_path)
    
    print("\nBenchmark completed!")


if __name__ == "__main__":
    asyncio.run(run_benchmark())