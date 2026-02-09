import os
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams, Filter, FieldCondition, MatchValue


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

    def delete_vectors(self, collection_name: str, filter: Dict[str, Any]) -> bool:
        if not self._collection_exists(collection_name):
            return False

        conditions = []
        for key, value in filter.items():
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

        if not conditions:
            return False

        q_filter = Filter(must=conditions)
        self.qdrant.delete(
            collection_name=collection_name,
            points_selector=q_filter
        )
        return True

    def update_vectors(self, collection_name: str, filter: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        if not self._collection_exists(collection_name):
            return False

        conditions = []
        for key, value in filter.items():
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

        if not conditions:
            return False

        q_filter = Filter(must=conditions)
        self.qdrant.set_payload(
            collection_name=collection_name,
            payload=payload,
            points=q_filter
        )
        return True

    def delete_collection(self, collection_name: str) -> bool:
        if self._collection_exists(collection_name):
            self.qdrant.delete_collection(collection_name=collection_name)
            return True
        return False

    def search_vectors(self, vector: List[float], limit: int = 5, offset: int = 0, collection_name: str = "", filter: Optional[Dict[str, Any]] = None, score_threshold: float = 0.2) -> List[Dict[str, Any]]:
        self.ensure_collection(len(vector), collection_name)

        q_filter = None
        if filter:
            conditions = []
            for key, value in filter.items():
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            if conditions:
                q_filter = Filter(must=conditions)

        res = self.qdrant.search(
            collection_name=collection_name,
            query_vector=vector,
            query_filter=q_filter,
            limit=limit,
            offset=offset,
            with_payload=True,
            score_threshold=score_threshold,
        )
        out = []
        for p in res:
            out.append({
                "id": str(p.id),
                "score": p.score,
                "payload": p.payload or {},
            })
        return out

    def query_vectors(self, query: Dict[str, Any], limit: int = 5, offset: Union[int, str, None] = None, collection_name: str = "") -> List[Dict[str, Any]]:
        if not self._collection_exists(collection_name):
            return []

        conditions = []
        for key, value in query.items():
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

        q_filter = Filter(must=conditions) if conditions else None

        # Handle offset
        scroll_offset = None
        if isinstance(offset, int) and offset > 0:
            # If offset is int, it means we want to skip 'offset' items.
            # We need to scroll to find the cursor.
            _, scroll_offset = self.qdrant.scroll(
                collection_name=collection_name,
                scroll_filter=q_filter,
                limit=offset,
                with_payload=False,
                with_vectors=False
            )
            if scroll_offset is None:
                return []
        elif isinstance(offset, str):
            # If offset is str, it's a cursor (Point ID).
            scroll_offset = offset

        res, _ = self.qdrant.scroll(
            collection_name=collection_name,
            scroll_filter=q_filter,
            limit=limit,
            offset=scroll_offset,
            with_payload=True,
            with_vectors=False
        )

        out = []
        for p in res:
            out.append({
                "id": str(p.id),
                "payload": p.payload or {},
            })
        return out
