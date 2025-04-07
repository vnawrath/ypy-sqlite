import sqlite3
import aiosqlite


class SQLiteAdapter:
    def __init__(self, table_name, connection):
        self.table_name = table_name
        self.connection = connection

    @classmethod
    async def connect(cls, db_path, table_name="ypy_documents", use_index=True):
        """
        Create a SQLiteAdapter instance

        Args:
            db_path: Path to the SQLite database file
            table_name: Name of the table where all documents are stored
            use_index: Whether to use an index for the table

        Returns:
            SQLiteAdapter instance
        """
        connection = await aiosqlite.connect(db_path)
        
        # Create table if it does not exist
        await connection.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                docname TEXT NOT NULL,
                value BLOB NOT NULL,
                version TEXT NOT NULL CHECK (version IN ('v1', 'v1_sv'))
            );
        """)
        
        # Create index on docname if it does not exist
        if use_index:
            await connection.execute(f"""
                CREATE INDEX IF NOT EXISTS {table_name}_docname_idx ON {table_name} (docname);
            """)
        
        await connection.commit()
        return cls(table_name, connection)

    async def find_latest_document_id(self, doc_name):
        """
        Find the latest document id in the table. Returns -1 if no document is found.

        Args:
            doc_name: Document name

        Returns:
            Latest document id or -1 if no document is found
        """
        async with self.connection.execute(
            f"SELECT id FROM {self.table_name} WHERE docname = ? ORDER BY id DESC LIMIT 1",
            (doc_name,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else -1

    async def insert_update(self, doc_name, value):
        """
        Store one update in SQLite.

        Args:
            doc_name: Document name
            value: Binary update data

        Returns:
            Stored document
        """
        async with self.connection.execute(
            f"INSERT INTO {self.table_name} (docname, value, version) VALUES (?, ?, 'v1') RETURNING *",
            (doc_name, value)
        ) as cursor:
            result = await cursor.fetchone()
            await self.connection.commit()
            return {"id": result[0], "docname": result[1], "value": result[2], "version": result[3]}

    async def get_state_vector_buffer(self, doc_name):
        """
        Get the state vector of a document in SQLite.

        Args:
            doc_name: Document name

        Returns:
            State vector buffer or None if no state vector exists
        """
        async with self.connection.execute(
            f"SELECT value FROM {self.table_name} WHERE docname = ? AND version = 'v1_sv' LIMIT 1",
            (doc_name,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

    async def put_state_vector(self, doc_name, value):
        """
        Upsert the state vector for one document in SQLite.

        Args:
            doc_name: Document name
            value: Binary state vector data

        Returns:
            Updated or inserted state vector document
        """
        # Get state vector to check if it exists
        async with self.connection.execute(
            f"SELECT id FROM {self.table_name} WHERE docname = ? AND version = 'v1_sv' LIMIT 1",
            (doc_name,)
        ) as cursor:
            sv = await cursor.fetchone()
        
        if sv:
            # Update existing state vector
            async with self.connection.execute(
                f"UPDATE {self.table_name} SET value = ? WHERE id = ? RETURNING *",
                (value, sv[0])
            ) as cursor:
                result = await cursor.fetchone()
        else:
            # Insert new state vector
            async with self.connection.execute(
                f"INSERT INTO {self.table_name} (docname, value, version) VALUES (?, ?, 'v1_sv') RETURNING *",
                (doc_name, value)
            ) as cursor:
                result = await cursor.fetchone()
        
        await self.connection.commit()
        return {"id": result[0], "docname": result[1], "value": result[2], "version": result[3]}

    async def clear_updates_range(self, doc_name, from_id, to_id):
        """
        Delete all updates of one document in a specific range.

        Args:
            doc_name: Document name
            from_id: Including this id
            to_id: Excluding this id
        """
        await self.connection.execute(
            f"DELETE FROM {self.table_name} WHERE docname = ? AND version = 'v1' AND id >= ? AND id < ?",
            (doc_name, from_id, to_id)
        )
        await self.connection.commit()

    async def read_updates_as_cursor(self, doc_name, callback):
        """
        Get all document updates for a specific document and pass to callback.

        Args:
            doc_name: Document name
            callback: Function to call with update records

        Returns:
            Total number of updates processed
        """
        offset = 0
        limit = 100
        rows_count = 0
        rows = []

        while True:
            async with self.connection.execute(
                f"SELECT id, docname, value, version FROM {self.table_name} "
                f"WHERE docname = ? AND version = 'v1' ORDER BY id LIMIT ? OFFSET ?",
                (doc_name, limit, offset)
            ) as cursor:
                rows = []
                async for row in cursor:
                    rows.append({
                        "id": row[0],
                        "docname": row[1],
                        "value": row[2],
                        "version": row[3]
                    })
            
            rows_count += len(rows)
            if rows:
                callback(rows)
            
            if len(rows) < limit:
                break
                
            offset += limit

        return rows_count

    async def delete_document(self, doc_name):
        """
        Delete a document, and all associated data from the database.

        Args:
            doc_name: Document name

        Returns:
            Deleted document data
        """
        async with self.connection.execute(
            f"DELETE FROM {self.table_name} WHERE docname = ? RETURNING *",
            (doc_name,)
        ) as cursor:
            result = await cursor.fetchone()
            await self.connection.commit()
            return result

    async def close(self):
        """
        Close the connection to the database.
        """
        await self.connection.close()