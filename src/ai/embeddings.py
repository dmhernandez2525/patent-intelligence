import numpy as np
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.patent import Patent
from src.utils.logger import logger


class EmbeddingService:
    """Generate and manage patent embeddings using PatentSBERTa."""

    def __init__(self):
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(settings.embedding_model)
            logger.info("embeddings.model_loaded", model=settings.embedding_model)
        return self._model

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        embeddings = self.model.encode(texts, normalize_embeddings=True, batch_size=32)
        return embeddings.tolist()

    def prepare_patent_text(self, patent: Patent) -> str:
        """Prepare patent text for embedding generation."""
        parts = []
        if patent.title:
            parts.append(f"Title: {patent.title}")
        if patent.abstract:
            parts.append(f"Abstract: {patent.abstract}")
        if patent.cpc_codes:
            parts.append(f"Classification: {', '.join(patent.cpc_codes[:5])}")
        return " ".join(parts)

    async def embed_patents(
        self,
        session: AsyncSession,
        patent_ids: list[int] | None = None,
        batch_size: int = 32,
    ) -> int:
        """Generate and store embeddings for patents."""
        query = select(Patent).where(Patent.embedding.is_(None))
        if patent_ids:
            query = query.where(Patent.id.in_(patent_ids))
        query = query.limit(batch_size)

        result = await session.execute(query)
        patents = result.scalars().all()

        if not patents:
            return 0

        texts = [self.prepare_patent_text(p) for p in patents]
        embeddings = self.generate_embeddings_batch(texts)

        for patent, embedding in zip(patents, embeddings):
            patent.embedding = embedding

        await session.flush()

        logger.info("embeddings.generated", count=len(patents))
        return len(patents)

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a_arr = np.array(a)
        b_arr = np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


embedding_service = EmbeddingService()
