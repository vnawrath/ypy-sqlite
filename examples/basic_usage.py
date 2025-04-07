import asyncio
import y_py as Y
from ypy_sqlite import SQLitePersistence


async def example():
    # Initialize the persistence layer
    persistence = await SQLitePersistence.build("example.db", {
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
        ytext.insert(txn, 0, "Hello, world!")
        
        ymap = txn.get_map("settings")
        ymap.set(txn, "theme", "dark")
        ymap.set(txn, "fontSize", 16)
        
        yarray = txn.get_array("items")
        yarray.append(txn, ["item1", "item2", "item3"])

    # Get updates for sync
    state_vector = await persistence.get_state_vector(doc_name)
    print(f"State vector size: {len(state_vector)} bytes")

    # Store updates
    update = Y.encode_state_as_update(ydoc)
    doc_id = await persistence.store_update(doc_name, update)
    print(f"Document stored with ID: {doc_id}")

    # Retrieve the document again to verify
    retrieved_doc = await persistence.get_ydoc(doc_name)
    
    # Print the document contents
    with retrieved_doc.begin_transaction() as txn:
        content = str(txn.get_text("content"))
        settings = {k: txn.get_map("settings").get(k) for k in ["theme", "fontSize"]}
        items = list(txn.get_array("items"))
    
    print(f"Retrieved document content: {content}")
    print(f"Retrieved document settings: {settings}")
    print(f"Retrieved document items: {items}")

    # Clean up
    await persistence.destroy()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(example())