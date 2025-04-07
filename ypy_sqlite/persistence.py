import y_py as Y
from .sqlite_adapter import SQLiteAdapter
from .utils import (
    flush_document,
    get_current_update_clock,
    get_ydoc_from_db,
    read_state_vector,
    store_update
)

DEFAULT_FLUSH_SIZE = 200
DEFAULT_TABLE_NAME = "ypy_documents"
DEFAULT_USE_INDEX = True


class SQLitePersistence:
    def __init__(self, flush_size, db_adapter):
        """
        Constructor for SQLitePersistence.

        Args:
            flush_size: Number of updates before flushing
            db_adapter: SQLiteAdapter instance
        """
        self.flush_size = flush_size
        self.db = db_adapter
        self.tr = {}  # Transaction queue

    @classmethod
    async def build(cls, db_path, options=None):
        """
        Initialize the persistence layer with options.

        Args:
            db_path: Path to the SQLite database file
            options: Configuration options

        Returns:
            SQLitePersistence instance
        """
        if options is None:
            options = {}
        
        flush_size = options.get("flush_size", DEFAULT_FLUSH_SIZE)
        table_name = options.get("table_name", DEFAULT_TABLE_NAME)
        use_index = options.get("use_index", DEFAULT_USE_INDEX)
        
        # Validate options
        if not isinstance(table_name, str) or not table_name:
            raise ValueError(
                'Constructor option "table_name" is not a valid string. '
                'Either don\'t use this option (default is "ypy_documents") or use a valid string!'
            )
        
        if not isinstance(use_index, bool):
            raise ValueError(
                'Constructor option "use_index" is not a boolean. '
                'Either don\'t use this option (default is True) or use a valid boolean!'
            )
        
        if not isinstance(flush_size, int) or flush_size <= 0:
            raise ValueError(
                'Constructor option "flush_size" is not a valid number. '
                'Either don\'t use this option (default is 200) or use a valid number larger than 0!'
            )
        
        db = await SQLiteAdapter.connect(db_path, table_name, use_index)
        return cls(flush_size, db)

    async def _transact(self, doc_name, func):
        """
        Execute a transaction on a database. This will ensure that other processes are
        currently not writing to the same document.

        Args:
            doc_name: Document name
            func: Function to execute with the database adapter

        Returns:
            Result of the function execution
        """
        # Initialize transaction queue for document if it doesn't exist
        if doc_name not in self.tr:
            self.tr[doc_name] = None
        
        # Wait for previous transaction to complete
        if self.tr[doc_name] is not None:
            await self.tr[doc_name]
        
        # Create a new transaction
        async def transaction():
            try:
                return await func(self.db)
            except Exception as e:
                print(f"Error during transaction: {e}")
                return None
            finally:
                # Once complete, remove from transaction queue
                if doc_name in self.tr:
                    del self.tr[doc_name]
        
        # Add transaction to queue and execute it
        transaction_task = transaction()
        self.tr[doc_name] = transaction_task
        result = await transaction_task
        return result

    async def get_ydoc(self, doc_name):
        """
        Create a Y.Doc instance with the data persisted in SQLite.
        Use this to temporarily create a YDoc to sync changes or extract data.

        Args:
            doc_name: Document name

        Returns:
            Y.YDoc instance
        """
        return await self._transact(doc_name, lambda db: get_ydoc_from_db(db, doc_name, self.flush_size))

    async def store_update(self, doc_name, update):
        """
        Store a single document update to the database.

        Args:
            doc_name: Document name
            update: Binary update data

        Returns:
            ID of the stored update
        """
        return await self._transact(doc_name, lambda db: store_update(db, doc_name, update))

    async def get_state_vector(self, doc_name):
        """
        The state vector (describing the state of the persisted document) is maintained
        in a separate field and constantly updated.

        This allows you to sync changes without actually creating a YDoc.

        Args:
            doc_name: Document name

        Returns:
            Binary state vector
        """
        return await self._transact(doc_name, lambda db: self._get_state_vector(db, doc_name))
        
    async def _get_state_vector(self, db, doc_name):
        # Get the state vector and clock
        state = await read_state_vector(db, doc_name)
        if state["sv"] is not None:
            # Get the current clock to check if it's up to date
            cur_clock = await get_current_update_clock(db, doc_name)
            if state["clock"] == cur_clock:
                # State vector is up to date
                return state["sv"]
        
        # State vector is missing or outdated
        ydoc = await get_ydoc_from_db(db, doc_name, self.flush_size)
        new_sv = Y.encode_state_vector(ydoc)
        await flush_document(db, doc_name, Y.encode_state_as_update(ydoc), new_sv)
        return new_sv

    async def get_diff(self, doc_name, state_vector):
        """
        Get differences directly from the database.
        The same as Y.encode_state_as_update(ydoc, state_vector).

        Args:
            doc_name: Document name
            state_vector: Binary state vector

        Returns:
            Binary update encoding the differences
        """
        ydoc = await self.get_ydoc(doc_name)
        return Y.encode_state_as_update(ydoc, state_vector)

    async def clear_document(self, doc_name):
        """
        Delete a document, and all associated data from the database.

        Args:
            doc_name: Document name
        """
        return await self._transact(doc_name, lambda db: db.delete_document(doc_name))

    async def destroy(self):
        """
        Cleans up the database connection.
        """
        return await self._transact("global", lambda db: db.close())