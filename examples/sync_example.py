import asyncio
import os
import y_py as Y
from ypy_sqlite import SQLitePersistence


async def simulate_collaboration():
    # Create a temporary database file
    db_path = "sync_example.db"
    
    # Remove the database file if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Initialize the persistence layer
    persistence = await SQLitePersistence.build(db_path)
    
    # Document name for our collaboration
    doc_name = "collaborative-doc"
    
    print("=== Simulating two users collaborating on a document ===")
    
    # User 1: Create initial document
    print("\n--- User 1: Creating initial document ---")
    user1_doc = await persistence.get_ydoc(doc_name)
    
    with user1_doc.begin_transaction() as txn:
        ytext = txn.get_text("shared-text")
        ytext.insert(0, "Hello from User 1! ")
    
    user1_update = Y.encode_state_as_update(user1_doc)
    await persistence.store_update(doc_name, user1_update)
    
    print("User 1 text:", user1_doc.get_text("shared-text").to_string())
    
    # User 2: Get document and make changes
    print("\n--- User 2: Loading document and making changes ---")
    user2_doc = await persistence.get_ydoc(doc_name)
    
    print("Initial text seen by User 2:", user2_doc.get_text("shared-text").to_string())
    
    with user2_doc.begin_transaction() as txn:
        ytext = txn.get_text("shared-text")
        ytext.insert(len(ytext.to_string()), "Hello from User 2!")
    
    user2_update = Y.encode_state_as_update(user2_doc)
    await persistence.store_update(doc_name, user2_update)
    
    print("User 2 text after editing:", user2_doc.get_text("shared-text").to_string())
    
    # User 1: Work offline and make changes
    print("\n--- User 1: Working offline and making changes ---")
    with user1_doc.begin_transaction() as txn:
        ytext = txn.get_text("shared-text")
        # User 1 doesn't see User 2's changes yet
        ytext.insert(len(ytext.to_string()), " User 1 made some offline changes.")
    
    print("User 1 text after offline changes:", user1_doc.get_text("shared-text").to_string())
    
    # User 1: Sync with the server
    print("\n--- User 1: Syncing with the server ---")
    
    # Get state vector for current doc
    user1_sv = Y.encode_state_vector(user1_doc)
    
    # Get the difference from the server
    server_diff = await persistence.get_diff(doc_name, user1_sv)
    
    # Apply the difference
    Y.apply_update(user1_doc, server_diff)
    
    print("User 1 text after syncing:", user1_doc.get_text("shared-text").to_string())
    
    # Store User 1's updates
    user1_update = Y.encode_state_as_update(user1_doc)
    await persistence.store_update(doc_name, user1_update)
    
    # User 2: Sync with the server again
    print("\n--- User 2: Syncing with the server again ---")
    
    # Get state vector for current doc
    user2_sv = Y.encode_state_vector(user2_doc)
    
    # Get the difference from the server
    server_diff = await persistence.get_diff(doc_name, user2_sv)
    
    # Apply the difference
    Y.apply_update(user2_doc, server_diff)
    
    print("User 2 text after syncing:", user2_doc.get_text("shared-text").to_string())
    
    # Verify that both users have the same document
    print("\n--- Verification ---")
    user1_text = user1_doc.get_text("shared-text").to_string()
    user2_text = user2_doc.get_text("shared-text").to_string()
    
    print("User 1 final text:", user1_text)
    print("User 2 final text:", user2_text)
    print("Documents match:", user1_text == user2_text)
    
    # Clean up
    await persistence.destroy()
    
    # Remove the database file
    if os.path.exists(db_path):
        os.remove(db_path)
    
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(simulate_collaboration())