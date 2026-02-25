
import os
import uuid
from typing import Any, Dict, List, Optional, Union
import psycopg
from psycopg.types.json import Jsonb
from pgvector.psycopg import register_vector

class PostgresVector:
    def __init__(self) -> None:
        self.url = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

    def _connect(self):
        conn = psycopg.connect(self.url)
        # Register vector type
        register_vector(conn)
        return conn

    def _ensure_table(self, table_name: str, dim: int):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS "{table_name}" (
                        id UUID PRIMARY KEY,
                        embedding vector({dim}),
                        payload JSONB
                    )
                """)
            conn.commit()

    def _table_exists(self, table_name: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, (table_name,))
                return cur.fetchone()[0]

    def upsert(self, collection_name: str, vector: List[float], payload: Dict[str, Any]) -> str:
        self._ensure_table(collection_name, len(vector))
        vid = str(uuid.uuid4())
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO "{collection_name}" (id, embedding, payload)
                    VALUES (%s, %s, %s)
                """, (vid, vector, Jsonb(payload)))
            conn.commit()
        return vid

    def search(self, collection_name: str, vector: List[float], limit: int = 5, offset: int = 0, filter: Optional[Dict[str, Any]] = None, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        if not self._table_exists(collection_name):
            return []
        
        with self._connect() as conn:
            where_clause = ""
            params = [vector]
            
            if filter:
                conditions = []
                for key, value in filter.items():
                    conditions.append(f"payload->>'{key}' = %s")
                    params.append(str(value)) 
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)

            # Cosine distance: 1 - (a . b) / (|a| * |b|)
            # pgvector <=> is cosine distance (1 - cosine similarity)
            # So score = 1 - distance
            
            query = f"""
                SELECT id, payload, 1 - (embedding <=> %s) as score
                FROM "{collection_name}"
                {where_clause}
                ORDER BY embedding <=> %s
                LIMIT %s OFFSET %s
            """
            # We need to pass vector twice
            params.append(vector)
            params.append(limit)
            params.append(offset)

            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
            
        results = []
        for row in rows:
            if row[2] >= score_threshold:
                results.append({
                    "id": str(row[0]),
                    "payload": row[1],
                    "score": row[2]
                })
        return results

    def query(self, collection_name: str, query: Dict[str, Any], limit: int = 5, offset: Union[int, str, None] = None) -> List[Dict[str, Any]]:
        if not self._table_exists(collection_name):
            return []

        with self._connect() as conn:
            where_clause = ""
            params = []
            
            if query:
                conditions = []
                for key, value in query.items():
                    conditions.append(f"payload->>'{key}' = %s")
                    params.append(str(value))
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)

            # Handle offset
            offset_val = 0
            if isinstance(offset, int):
                offset_val = offset
            
            sql = f"""
                SELECT id, payload
                FROM "{collection_name}"
                {where_clause}
                LIMIT %s OFFSET %s
            """
            params.append(limit)
            params.append(offset_val)

            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()

        results = []
        for row in rows:
            results.append({
                "id": str(row[0]),
                "payload": row[1]
            })
        return results

    def delete(self, collection_name: str, filter: Dict[str, Any]) -> bool:
        if not self._table_exists(collection_name):
            return False
        
        if not filter:
            return False

        with self._connect() as conn:
            conditions = []
            params = []
            for key, value in filter.items():
                conditions.append(f"payload->>'{key}' = %s")
                params.append(str(value))
                
            where_clause = " AND ".join(conditions)
            
            with conn.cursor() as cur:
                cur.execute(f"""
                    DELETE FROM "{collection_name}"
                    WHERE {where_clause}
                """, tuple(params))
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def update(self, collection_name: str, filter: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        if not self._table_exists(collection_name):
            return False
            
        if not filter:
            return False

        with self._connect() as conn:
            # Build WHERE clause
            where_conditions = []
            where_params = []
            for key, value in filter.items():
                where_conditions.append(f"payload->>'{key}' = %s")
                where_params.append(str(value))
            where_clause = " AND ".join(where_conditions)

            # Build UPDATE clause - merge payload
            
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE "{collection_name}"
                    SET payload = payload || %s
                    WHERE {where_clause}
                """, (Jsonb(payload), *where_params))
                updated = cur.rowcount > 0
            conn.commit()
        return updated

    def delete_collection(self, collection_name: str) -> bool:
        if not self._table_exists(collection_name):
            return False
        
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f'DROP TABLE IF EXISTS "{collection_name}"')
            conn.commit()
        return True
