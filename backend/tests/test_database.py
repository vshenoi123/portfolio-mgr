import os
import pytest
import duckdb


class TestDatabase:
    def test_get_connection_returns_duckdb_conn(self, test_db_path):
        from app.database import get_connection
        conn = get_connection(test_db_path)
        assert isinstance(conn, duckdb.DuckDBPyConnection)
        conn.close()

    def test_get_connection_creates_db_file(self, test_db_path):
        from app.database import get_connection
        conn = get_connection(test_db_path)
        conn.close()
        assert os.path.exists(test_db_path)

    def test_get_connection_cache_reuses_conn(self, test_db_path):
        from app.database import get_connection
        conn1 = get_connection(test_db_path)
        conn2 = get_connection(test_db_path)
        assert conn1 is conn2
        conn1.close()

    def test_close_connection_removes_cache(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        close_connection(test_db_path)
        conn2 = get_connection(test_db_path)
        assert conn2 is not conn
        conn2.close()
