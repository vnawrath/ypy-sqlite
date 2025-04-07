import y_py as Y
from .sqlite_adapter import SQLiteAdapter
import struct


def decode_state_vector_buffer(buffer):
    """
    Decode a state vector buffer.

    Args:
        buffer: Binary state vector buffer

    Returns:
        Dictionary with state vector and clock
    """
    if buffer is None:
        return {"sv": None, "clock": -1}
    
    # First 8 bytes are the clock (as uint64)
    # Remaining bytes are the state vector
    clock = struct.unpack('<Q', buffer[:8])[0]
    sv = buffer[8:]
    
    return {"sv": sv, "clock": clock}


async def read_state_vector(db, doc_name):
    """
    Read and decode a state vector from the database.

    Args:
        db: SQLiteAdapter instance
        doc_name: Document name

    Returns:
        Dictionary with state vector and clock
    """
    sv_buffer = await db.get_state_vector_buffer(doc_name)
    if not sv_buffer:
        # no state vector created yet or no document exists
        return {"sv": None, "clock": -1}
    
    return decode_state_vector_buffer(sv_buffer)


async def write_state_vector(db, doc_name, sv, clock):
    """
    Encode and write a state vector to the database.

    Args:
        db: SQLiteAdapter instance
        doc_name: Document name
        sv: State vector
        clock: Latest document ID

    Returns:
        New state vector document
    """
    # Pack clock as uint64
    clock_bytes = struct.pack('<Q', clock)
    
    # Concatenate clock and state vector
    buffer = clock_bytes + sv
    
    return await db.put_state_vector(doc_name, buffer)


async def get_current_update_clock(db, doc_name):
    """
    Get the latest document ID.

    Args:
        db: SQLiteAdapter instance
        doc_name: Document name

    Returns:
        Latest document ID or -1 if no document exists
    """
    return await db.find_latest_document_id(doc_name)


async def store_update(db, doc_name, update):
    """
    Store an update and handle initial state vector.

    Args:
        db: SQLiteAdapter instance
        doc_name: Document name
        update: Binary update data

    Returns:
        ID of the stored document
    """
    clock = await get_current_update_clock(db, doc_name)
    if clock == -1:
        # make sure that a state vector is always written, so we can search for available documents
        ydoc = Y.YDoc()
        Y.apply_update(ydoc, update)
        sv = Y.encode_state_vector(ydoc)
        await write_state_vector(db, doc_name, sv, 0)
    
    stored_doc = await db.insert_update(doc_name, update)
    return stored_doc["id"]


async def flush_document(db, doc_name, state_as_update, state_vector):
    """
    Merge all records of the same document.

    Args:
        db: SQLiteAdapter instance
        doc_name: Document name
        state_as_update: Document state as update
        state_vector: Document state vector

    Returns:
        Latest document ID
    """
    clock = await store_update(db, doc_name, state_as_update)
    await write_state_vector(db, doc_name, state_vector, clock)
    await db.clear_updates_range(doc_name, 0, clock)
    return clock


async def get_ydoc_from_db(db, doc_name, flush_size):
    """
    Retrieve a document from the database.

    Args:
        db: SQLiteAdapter instance
        doc_name: Document name
        flush_size: Threshold for flushing document

    Returns:
        Y.YDoc instance
    """
    ydoc = Y.YDoc()
    updates_count = 0
    
    def apply_updates(updates):
        nonlocal ydoc
        for update in updates:
            Y.apply_update(ydoc, update["value"])
    
    with ydoc.begin_transaction():
        updates_count = await db.read_updates_as_cursor(doc_name, apply_updates)
    
    if updates_count > flush_size:
        await flush_document(
            db,
            doc_name,
            Y.encode_state_as_update(ydoc),
            Y.encode_state_vector(ydoc)
        )
    
    return ydoc