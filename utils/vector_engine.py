
import os
from typing import Any, Dict, List, Optional, Union
import httpx

from utils.qdrant_vector import QdrantVector
from utils.postgres_vector import PostgresVector


class VectorEngine:
    def __init__(self) -> None:
        self.ark_api_key = os.getenv("ARK_API_KEY", "")
        self.ark_model = os.getenv("ARK_EMBEDDING_MODEL", "doubao-embedding-vision-251215")
        self.qdrant = QdrantVector()
        self.postgres = PostgresVector()

    async def get_embedding(self, inputs: List[Dict[str, Any]], instructions: str = "") -> List[float]:
        if not self.ark_api_key:
            raise ValueError("ARK_API_KEY未配置")
        url = "https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.ark_api_key}",
        }
        payload = {"model": self.ark_model, "input": inputs, "instructions": instructions}
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        return data.get("data", {}).get("embedding")

    def upsert_vector(self, vector: List[float], payload: Dict[str, Any], collection_name: str, db_type: str = "qdrant") -> str:
        if db_type == "postgresql":
            return self.postgres.upsert(collection_name, vector, payload)
        return self.qdrant.upsert(collection_name, vector, payload)

    def delete_vectors(self, collection_name: str, filter: Dict[str, Any], db_type: str = "qdrant") -> bool:
        if db_type == "postgresql":
            return self.postgres.delete(collection_name, filter)
        return self.qdrant.delete_vectors(collection_name, filter)

    def update_vectors(self, collection_name: str, filter: Dict[str, Any], payload: Dict[str, Any], db_type: str = "qdrant") -> bool:
        if db_type == "postgresql":
            return self.postgres.update(collection_name, filter, payload)
        return self.qdrant.update_vectors(collection_name, filter, payload)

    def delete_collection(self, collection_name: str, db_type: str = "qdrant") -> bool:
        if db_type == "postgresql":
            return self.postgres.delete_collection(collection_name)
        return self.qdrant.delete_collection(collection_name)

    def search_vectors(self, vector: List[float], limit: int = 5, offset: int = 0, collection_name: str = "", filter: Optional[Dict[str, Any]] = None, score_threshold: float = 0.2, db_type: str = "qdrant") -> List[Dict[str, Any]]:
        if db_type == "postgresql":
            return self.postgres.search(collection_name, vector, limit, offset, filter, score_threshold)
        return self.qdrant.search_vectors(vector, limit, offset, collection_name, filter, score_threshold)

    def query_vectors(self, query: Dict[str, Any], limit: int = 5, offset: Union[int, str, None] = None, collection_name: str = "", db_type: str = "qdrant") -> List[Dict[str, Any]]:
        if db_type == "postgresql":
            return self.postgres.query(collection_name, query, limit, offset)
        return self.qdrant.query_vectors(query, limit, offset, collection_name)
