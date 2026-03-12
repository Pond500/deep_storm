"""
Hybrid Wikipedia Retrieval Module
รวม Vector Search + BM25 + Reranking
"""

from typing import List, Dict, Union, Optional
import dspy
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
import numpy as np
import pickle
from pathlib import Path


# Module-level singleton for shared access
_shared_instance: Optional['HybridWikipediaRM'] = None


def get_shared_instance(**kwargs) -> 'HybridWikipediaRM':
    """Get or create a shared HybridWikipediaRM instance (singleton).
    
    Prevents Qdrant local storage file lock errors by ensuring
    only one QdrantClient instance exists at a time.
    """
    global _shared_instance
    if _shared_instance is None:
        _shared_instance = HybridWikipediaRM(**kwargs)
    return _shared_instance


class HybridWikipediaRM(dspy.Retrieve):
    """
    Advanced retrieval module with:
    1. Dense retrieval (vector search - semantic)
    2. Sparse retrieval (BM25 - keyword)
    3. Reciprocal Rank Fusion (RRF merge)
    4. Cross-encoder reranking (optional)
    """
    
    def __init__(
        self,
        vector_store_path: str = "./vector_store",
        collection_name: str = "wikipedia_thai",
        embedding_model: str = "BAAI/bge-m3",
        reranker_model: str = "BAAI/bge-reranker-v2-m3",
        device: str = "mps",
        k: int = 3,
        use_reranking: bool = True,
        rerank_top_k: int = 20,
        alpha: float = 0.5,  # Weight for dense vs sparse (0.5 = balanced)
    ):
        """
        Args:
            vector_store_path: Path to Qdrant vector store
            collection_name: Collection name
            embedding_model: Dense embedding model
            reranker_model: Cross-encoder for reranking
            device: "mps", "cuda", or "cpu"
            k: Final number of results to return
            use_reranking: Enable 2-stage reranking
            rerank_top_k: Number of candidates for reranking (should be > k)
            alpha: Weight for dense (1.0 = pure dense, 0.0 = pure sparse)
        """
        super().__init__(k=k)
        
        self.vector_store_path = vector_store_path
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.reranker_model_name = reranker_model
        self.device = device
        self.k = k
        self.use_reranking = use_reranking
        self.rerank_top_k = max(rerank_top_k, k * 2)  # At least 2x k
        self.alpha = alpha
        
        # Initialize Qdrant client
        print(f"📂 Loading vector store: {vector_store_path}")
        self.client = QdrantClient(path=vector_store_path)
        
        # Load dense embedding model
        print(f"🤖 Loading embedding model: {embedding_model}")
        self.encoder = SentenceTransformer(embedding_model, device=device)
        
        # Load reranker
        if use_reranking:
            print(f"🎯 Loading reranker: {reranker_model}")
            self.reranker = CrossEncoder(reranker_model, device=device)
        else:
            self.reranker = None
        
        # Check collection
        collection_info = self.client.get_collection(collection_name)
        print(f"✅ Collection loaded: {collection_info.points_count:,} documents")
        
        # Load or build BM25 index
        self._load_or_build_bm25_index()
    
    
    def _load_or_build_bm25_index(self):
        """Load BM25 index from cache or build new one"""
        bm25_cache_path = Path(self.vector_store_path) / "bm25_index.pkl"
        
        if bm25_cache_path.exists():
            print(f"📦 Loading BM25 index from cache...")
            with open(bm25_cache_path, 'rb') as f:
                cache = pickle.load(f)
                self.bm25 = cache['bm25']
                self.doc_ids = cache['doc_ids']
                self.doc_metadata = cache['doc_metadata']
            print(f"✅ BM25 index loaded: {len(self.doc_ids):,} documents")
        else:
            print(f"🔨 Building BM25 index (first time only)...")
            self._build_bm25_index()
            
            # Save to cache
            print(f"💾 Saving BM25 index to cache...")
            with open(bm25_cache_path, 'wb') as f:
                pickle.dump({
                    'bm25': self.bm25,
                    'doc_ids': self.doc_ids,
                    'doc_metadata': self.doc_metadata,
                }, f)
            print(f"✅ BM25 index cached")
    
    
    def _build_bm25_index(self):
        """Build BM25 index from all documents"""
        # Fetch all documents
        all_docs = []
        offset = None
        
        while True:
            result = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            
            points, offset = result
            if not points:
                break
            
            all_docs.extend(points)
            
            if offset is None:
                break
        
        print(f"  Fetched {len(all_docs):,} documents")
        
        # Extract texts and metadata
        self.doc_ids = []
        self.doc_metadata = []
        tokenized_corpus = []
        
        for point in all_docs:
            content = point.payload.get('page_content', '')
            metadata = point.payload.get('metadata', {})
            
            # Tokenize (simple word split for now)
            # TODO: Use proper Thai tokenizer for better results
            tokens = content.lower().split()
            
            self.doc_ids.append(point.id)
            self.doc_metadata.append({
                'content': content,
                'title': metadata.get('title', ''),
                'url': metadata.get('url', ''),
                'description': metadata.get('description', ''),
            })
            tokenized_corpus.append(tokens)
        
        # Build BM25 index
        print(f"  Building BM25 index...")
        self.bm25 = BM25Okapi(tokenized_corpus)
        print(f"  ✅ BM25 index built")
    
    
    def _dense_search(self, query: str, top_k: int) -> List[tuple]:
        """
        Dense retrieval (vector search)
        
        Returns:
            List of (doc_id, score, metadata)
        """
        # Encode query
        query_vector = self.encoder.encode(query, convert_to_numpy=True).tolist()
        
        # Search in Qdrant
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
        )
        
        # Format results
        dense_results = []
        for result in results.points:
            metadata = result.payload.get('metadata', {})
            content = result.payload.get('page_content', '')
            
            dense_results.append((
                result.id,
                result.score,
                {
                    'content': content,
                    'title': metadata.get('title', ''),
                    'url': metadata.get('url', ''),
                    'description': metadata.get('description', ''),
                }
            ))
        
        return dense_results
    
    
    def _sparse_search(self, query: str, top_k: int) -> List[tuple]:
        """
        Sparse retrieval (BM25 keyword search)
        
        Returns:
            List of (doc_id, score, metadata)
        """
        # Tokenize query
        query_tokens = query.lower().split()
        
        # BM25 scores
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[-top_k:][::-1]
        
        # Format results
        sparse_results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include non-zero scores
                sparse_results.append((
                    self.doc_ids[idx],
                    float(scores[idx]),
                    self.doc_metadata[idx]
                ))
        
        return sparse_results
    
    
    def _rrf_fusion(
        self,
        dense_results: List[tuple],
        sparse_results: List[tuple],
        k_rrf: int = 60,
    ) -> List[tuple]:
        """
        Reciprocal Rank Fusion (RRF)
        
        Formula: RRF(d) = sum over rankings r: 1 / (k + rank_r(d))
        
        Args:
            dense_results: [(doc_id, score, metadata), ...]
            sparse_results: [(doc_id, score, metadata), ...]
            k_rrf: RRF constant (typically 60)
        
        Returns:
            Fused results sorted by RRF score
        """
        rrf_scores = {}
        doc_metadata = {}
        
        # Add dense ranks (weighted by alpha)
        for rank, (doc_id, score, metadata) in enumerate(dense_results):
            rrf_scores[doc_id] = self.alpha * (1.0 / (k_rrf + rank + 1))
            doc_metadata[doc_id] = metadata
        
        # Add sparse ranks (weighted by 1-alpha)
        for rank, (doc_id, score, metadata) in enumerate(sparse_results):
            if doc_id in rrf_scores:
                rrf_scores[doc_id] += (1 - self.alpha) * (1.0 / (k_rrf + rank + 1))
            else:
                rrf_scores[doc_id] = (1 - self.alpha) * (1.0 / (k_rrf + rank + 1))
                doc_metadata[doc_id] = metadata
        
        # Sort by RRF score
        sorted_results = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Format as list of tuples
        fused_results = [
            (doc_id, rrf_score, doc_metadata[doc_id])
            for doc_id, rrf_score in sorted_results
        ]
        
        return fused_results
    
    
    def _rerank(
        self,
        query: str,
        candidates: List[tuple],
        top_k: int,
    ) -> List[tuple]:
        """
        Rerank candidates using cross-encoder
        
        Args:
            query: Search query
            candidates: [(doc_id, score, metadata), ...]
            top_k: Number of results to return
        
        Returns:
            Reranked results
        """
        if not self.reranker or len(candidates) == 0:
            return candidates[:top_k]
        
        # Prepare query-document pairs
        pairs = []
        for doc_id, score, metadata in candidates:
            content = metadata.get('content', '')[:512]  # Truncate for speed
            pairs.append([query, content])
        
        # Get reranker scores
        rerank_scores = self.reranker.predict(pairs)
        
        # Combine with candidates
        reranked = [
            (doc_id, float(rerank_score), metadata)
            for (doc_id, _, metadata), rerank_score in zip(candidates, rerank_scores)
        ]
        
        # Sort by reranker score
        reranked.sort(key=lambda x: x[1], reverse=True)
        
        return reranked[:top_k]
    
    
    def forward(
        self,
        query_or_queries: Union[str, List[str]],
        exclude_urls: List[str] = None,
    ) -> List[Dict]:
        """
        Hybrid retrieval: Dense + Sparse + RRF + Reranking
        
        Args:
            query_or_queries: Single query or list of queries
            exclude_urls: URLs to exclude (not implemented)
        
        Returns:
            List of dicts with keys: 'description', 'snippets', 'title', 'url', 'score'
        """
        # Handle single query or list
        queries = (
            [query_or_queries]
            if isinstance(query_or_queries, str)
            else query_or_queries
        )
        
        all_results = []
        
        for query in queries:
            # Stage 1a: Dense retrieval
            dense_results = self._dense_search(query, top_k=self.rerank_top_k)
            
            # Stage 1b: Sparse retrieval
            sparse_results = self._sparse_search(query, top_k=self.rerank_top_k)
            
            # Stage 1c: RRF Fusion
            fused_results = self._rrf_fusion(dense_results, sparse_results)
            
            # Stage 2: Reranking (optional)
            if self.use_reranking:
                final_results = self._rerank(query, fused_results, top_k=self.k)
            else:
                final_results = fused_results[:self.k]
            
            # Format results to match STORM's expected format
            for doc_id, score, metadata in final_results:
                formatted_result = {
                    'description': metadata.get('description', metadata.get('content', '')[:200]),
                    'snippets': [metadata.get('content', '')[:500]],
                    'title': metadata.get('title', 'Untitled'),
                    'url': metadata.get('url', ''),
                    'score': score,
                }
                all_results.append(formatted_result)
        
        return all_results
    
    
    def __del__(self):
        """Close client on deletion"""
        if hasattr(self, 'client'):
            self.client.close()
