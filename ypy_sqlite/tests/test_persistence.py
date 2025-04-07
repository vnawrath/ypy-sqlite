import unittest
import os
import tempfile
import y_py as Y
from ypy_sqlite import SQLitePersistence


class TestSQLitePersistence(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
        self.db_path = self.temp_file.name
        
        # Initialize persistence
        self.persistence = await SQLitePersistence.build(self.db_path)
    
    async def asyncTearDown(self):
        # Clean up
        await self.persistence.destroy()
        os.unlink(self.db_path)
    
    async def test_store_and_retrieve_document(self):
        # Create a document
        doc_name = "test-doc"
        ydoc = Y.YDoc()
        
        # Add some data
        with ydoc.begin_transaction() as txn:
            ytext = txn.get_text("text")
            ytext.insert(txn, 0, "Hello, world!")
            
            ymap = txn.get_map("map")
            ymap.set(txn, "key1", "value1")
            ymap.set(txn, "key2", 42)
        
        # Store the document
        update = Y.encode_state_as_update(ydoc)
        await self.persistence.store_update(doc_name, update)
        
        # Retrieve the document
        retrieved_doc = await self.persistence.get_ydoc(doc_name)
        
        # Check contents
        retrieved_text = str(retrieved_doc.get_text("text"))
        self.assertEqual(retrieved_text, "Hello, world!")
        
        retrieved_map = retrieved_doc.get_map("map")
        self.assertEqual(retrieved_map.get("key1"), "value1")
        self.assertEqual(retrieved_map.get("key2"), 42)
    
    async def test_state_vector_and_diff(self):
        # Create a document
        doc_name = "test-sv"
        ydoc1 = Y.YDoc()
        
        # Add some initial data
        with ydoc1.begin_transaction() as txn:
            ytext = txn.get_text("text")
            ytext.insert(txn, 0, "Hello")
        
        # Store the initial update
        initial_update = Y.encode_state_as_update(ydoc1)
        await self.persistence.store_update(doc_name, initial_update)
        
        # Get the state vector at this point
        sv1 = await self.persistence.get_state_vector(doc_name)
        
        # Make more changes
        with ydoc1.begin_transaction() as txn:
            ytext = txn.get_text("text")
            ytext.insert(txn, 5, ", world!")
        
        # Store the second update
        second_update = Y.encode_state_as_update(ydoc1)
        await self.persistence.store_update(doc_name, second_update)
        
        # Get the diff from the first state vector
        diff = await self.persistence.get_diff(doc_name, sv1)
        
        # Create a new document with the initial state
        ydoc2 = Y.YDoc()
        Y.apply_update(ydoc2, initial_update)
        
        # Apply the diff
        Y.apply_update(ydoc2, diff)
        
        # Check if the documents are synchronized
        text2 = str(ydoc2.get_text("text"))
        self.assertEqual(text2, "Hello, world!")
    
    async def test_clear_document(self):
        # Create a document
        doc_name = "test-clear"
        ydoc = Y.YDoc()
        
        # Add some data
        with ydoc.begin_transaction() as txn:
            ytext = txn.get_text("text")
            ytext.insert(txn, 0, "Hello, world!")
        
        # Store the document
        update = Y.encode_state_as_update(ydoc)
        await self.persistence.store_update(doc_name, update)
        
        # Clear the document
        await self.persistence.clear_document(doc_name)
        
        # Retrieve the document (should be empty)
        retrieved_doc = await self.persistence.get_ydoc(doc_name)
        
        # Check contents
        text = str(retrieved_doc.get_text("text"))
        self.assertEqual(text, "")


if __name__ == '__main__':
    unittest.main()