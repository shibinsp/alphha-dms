"""Search Service - M13 Search & Semantic Retrieval"""
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import HTTPException

from app.models.document import Document, LifecycleStatus
from app.models.search import SavedSearch, SearchHistory, SearchSuggestion
from app.models.taxonomy import DocumentTag, Tag


class SearchService:
    """Search service with keyword, semantic, and hybrid search capabilities"""

    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        query: str,
        tenant_id: str,
        user_id: str,
        search_type: str = "hybrid",
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20,
        user_clearance_level: str = "PUBLIC",
    ) -> Dict[str, Any]:
        """
        Perform document search with keyword, semantic, or hybrid mode.
        """
        filters = filters or {}
        offset = (page - 1) * page_size

        # Base query with tenant and access control
        base_query = self.db.query(Document).filter(
            Document.tenant_id == tenant_id,
            Document.lifecycle_status != LifecycleStatus.DELETED,
        )

        # Apply access control based on clearance level
        clearance_levels = self._get_accessible_classifications(user_clearance_level)
        base_query = base_query.filter(Document.classification.in_(clearance_levels))

        # Apply filters
        if filters.get("source_type"):
            base_query = base_query.filter(Document.source_type == filters["source_type"])
        if filters.get("document_type_id"):
            base_query = base_query.filter(Document.document_type_id == filters["document_type_id"])
        if filters.get("folder_id"):
            base_query = base_query.filter(Document.folder_id == filters["folder_id"])
        if filters.get("lifecycle_status"):
            base_query = base_query.filter(Document.lifecycle_status == filters["lifecycle_status"])
        if filters.get("date_from"):
            base_query = base_query.filter(Document.created_at >= filters["date_from"])
        if filters.get("date_to"):
            base_query = base_query.filter(Document.created_at <= filters["date_to"])
        if filters.get("customer_id"):
            base_query = base_query.filter(Document.customer_id == filters["customer_id"])
        if filters.get("vendor_id"):
            base_query = base_query.filter(Document.vendor_id == filters["vendor_id"])
        if filters.get("tag_ids"):
            tag_ids = filters["tag_ids"]
            base_query = base_query.join(DocumentTag).filter(DocumentTag.tag_id.in_(tag_ids))

        # Perform search based on type
        if search_type == "keyword":
            results, total = self._keyword_search(base_query, query, offset, page_size)
        elif search_type == "semantic":
            results, total = self._semantic_search(base_query, query, tenant_id, offset, page_size)
        else:  # hybrid
            results, total = self._hybrid_search(base_query, query, tenant_id, offset, page_size)

        # Log search history
        self._log_search(query, search_type, filters, len(results), tenant_id, user_id)

        # Update search suggestions
        self._update_suggestions(query, tenant_id)

        return {
            "items": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "query": query,
            "search_type": search_type,
        }

    def _keyword_search(
        self,
        base_query,
        query: str,
        offset: int,
        limit: int,
    ) -> Tuple[List[Document], int]:
        """Full-text keyword search using SQLite FTS or LIKE fallback"""
        search_terms = query.lower().split()

        # Build search conditions
        conditions = []
        for term in search_terms:
            pattern = f"%{term}%"
            conditions.append(
                or_(
                    Document.title.ilike(pattern),
                    Document.file_name.ilike(pattern),
                    Document.ocr_text.ilike(pattern),
                )
            )

        if conditions:
            base_query = base_query.filter(and_(*conditions))

        total = base_query.count()
        results = (
            base_query
            .order_by(Document.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return results, total

    def _semantic_search(
        self,
        base_query,
        query: str,
        tenant_id: str,
        offset: int,
        limit: int,
    ) -> Tuple[List[Document], int]:
        """
        Semantic search using document embeddings.
        Note: In production, this would use vector similarity search (e.g., sqlite-vss, pgvector).
        This is a simplified implementation.
        """
        # For now, fall back to keyword search
        # In production: Generate query embedding, compute cosine similarity with document embeddings
        return self._keyword_search(base_query, query, offset, limit)

    def _hybrid_search(
        self,
        base_query,
        query: str,
        tenant_id: str,
        offset: int,
        limit: int,
    ) -> Tuple[List[Document], int]:
        """
        Hybrid search combining keyword and semantic results using RRF.
        Reciprocal Rank Fusion: score = sum(1 / (k + rank_i)) for each ranker
        """
        # For now, use keyword search as the basis
        # In production: Combine keyword and semantic rankings using RRF
        return self._keyword_search(base_query, query, offset, limit)

    def _get_accessible_classifications(self, clearance_level: str) -> List[str]:
        """Get classification levels accessible to user based on their clearance"""
        levels = ["PUBLIC"]
        if clearance_level in ["INTERNAL", "CONFIDENTIAL", "RESTRICTED"]:
            levels.append("INTERNAL")
        if clearance_level in ["CONFIDENTIAL", "RESTRICTED"]:
            levels.append("CONFIDENTIAL")
        if clearance_level == "RESTRICTED":
            levels.append("RESTRICTED")
        return levels

    def _log_search(
        self,
        query: str,
        search_type: str,
        filters: Dict[str, Any],
        result_count: int,
        tenant_id: str,
        user_id: Optional[str],
    ) -> None:
        """Log search to history"""
        history = SearchHistory(
            user_id=user_id,
            tenant_id=tenant_id,
            query=query,
            search_type=search_type,
            filters=filters,
            result_count=result_count,
        )
        self.db.add(history)
        self.db.commit()

    def _update_suggestions(self, query: str, tenant_id: str) -> None:
        """Update search suggestions based on query"""
        normalized = query.lower().strip()
        if len(normalized) < 3:
            return

        existing = (
            self.db.query(SearchSuggestion)
            .filter(
                SearchSuggestion.tenant_id == tenant_id,
                SearchSuggestion.normalized == normalized,
            )
            .first()
        )

        if existing:
            existing.search_count += 1
            existing.last_searched_at = datetime.utcnow()
        else:
            suggestion = SearchSuggestion(
                tenant_id=tenant_id,
                suggestion=query,
                normalized=normalized,
            )
            self.db.add(suggestion)

        self.db.commit()

    # Saved Searches
    def save_search(
        self,
        user_id: str,
        tenant_id: str,
        name: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        search_type: str = "hybrid",
        notify_on_new: bool = False,
    ) -> SavedSearch:
        """Save a search for later reuse"""
        saved = SavedSearch(
            user_id=user_id,
            tenant_id=tenant_id,
            name=name,
            query=query,
            filters=filters,
            search_type=search_type,
            notify_on_new_results=notify_on_new,
        )
        self.db.add(saved)
        self.db.commit()
        self.db.refresh(saved)
        return saved

    def get_saved_searches(
        self,
        user_id: str,
        tenant_id: str,
    ) -> List[SavedSearch]:
        """Get user's saved searches"""
        return (
            self.db.query(SavedSearch)
            .filter(
                SavedSearch.user_id == user_id,
                SavedSearch.tenant_id == tenant_id,
            )
            .order_by(SavedSearch.updated_at.desc())
            .all()
        )

    def delete_saved_search(
        self,
        search_id: str,
        user_id: str,
        tenant_id: str,
    ) -> bool:
        """Delete a saved search"""
        saved = (
            self.db.query(SavedSearch)
            .filter(
                SavedSearch.id == search_id,
                SavedSearch.user_id == user_id,
                SavedSearch.tenant_id == tenant_id,
            )
            .first()
        )
        if not saved:
            raise HTTPException(status_code=404, detail="Saved search not found")

        self.db.delete(saved)
        self.db.commit()
        return True

    # Suggestions
    def get_suggestions(
        self,
        prefix: str,
        tenant_id: str,
        limit: int = 10,
    ) -> List[str]:
        """Get search suggestions based on prefix"""
        normalized = prefix.lower().strip()

        suggestions = (
            self.db.query(SearchSuggestion)
            .filter(
                SearchSuggestion.tenant_id == tenant_id,
                SearchSuggestion.normalized.like(f"{normalized}%"),
            )
            .order_by(SearchSuggestion.search_count.desc())
            .limit(limit)
            .all()
        )

        return [s.suggestion for s in suggestions]

    def get_recent_searches(
        self,
        user_id: str,
        tenant_id: str,
        limit: int = 10,
    ) -> List[str]:
        """Get user's recent searches"""
        history = (
            self.db.query(SearchHistory)
            .filter(
                SearchHistory.user_id == user_id,
                SearchHistory.tenant_id == tenant_id,
            )
            .order_by(SearchHistory.searched_at.desc())
            .limit(limit)
            .all()
        )

        # Return unique queries
        seen = set()
        unique = []
        for h in history:
            if h.query not in seen:
                seen.add(h.query)
                unique.append(h.query)
        return unique
