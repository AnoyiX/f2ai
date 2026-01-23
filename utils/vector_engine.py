import os
from typing import Any, Dict, List
from uuid import uuid4

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


class VectorEngine:
    def __init__(self) -> None:
        self.ark_api_key = os.getenv("ARK_API_KEY", "")
        self.ark_model = os.getenv("ARK_EMBEDDING_MODEL", "doubao-embedding-vision-251215")
        self.qdrant_host = os.getenv("QDRANT_HOST", "http://localhost:6333")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY", None)
        print(self.qdrant_host, self.qdrant_api_key)
        self.qdrant = QdrantClient(url=self.qdrant_host, api_key=self.qdrant_api_key)

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

    def _collection_exists(self, collection_name: str) -> bool:
        cols = self.qdrant.get_collections().collections or []
        names = [c.name for c in cols]
        return collection_name in names

    def ensure_collection(self, size: int, collection_name: str) -> None:
        if self._collection_exists(collection_name):
            return
        self.qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=size, distance=Distance.COSINE),
        )

    def upsert_vector(self, vector: List[float], payload: Dict[str, Any], collection_name: str) -> List[str]:
        self.ensure_collection(len(vector), collection_name)
        vid = str(uuid4())
        points = [PointStruct(id=vid, vector=vector, payload=payload)]
        self.qdrant.upsert(collection_name=collection_name, points=points)
        return vid

    def delete_collection(self, collection_name: str) -> bool:
        if self._collection_exists(collection_name):
            self.qdrant.delete_collection(collection_name=collection_name)
            return True
        return False

    def search_vectors(self, vector: List[float], limit: int = 5, collection_name: str = "") -> List[Dict[str, Any]]:
        self.ensure_collection(len(vector), collection_name)
        res = self.qdrant.search(
            collection_name=collection_name,
            query_vector=vector,
            limit=limit,
            with_payload=True,
        )
        out = []
        for p in res:
            out.append({
                "id": str(p.id),
                "score": p.score,
                "payload": p.payload or {},
            })
        return out
