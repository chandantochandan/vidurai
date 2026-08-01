from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import json

class CapsuleCategory(str, Enum):
    EVIDENCE = "evidence"
    DECISION = "decision"
    WORKING = "working"
    UNRESOLVED = "unresolved"
    CONTRADICTION = "contradiction"
    INTERPRETATION = "interpretation"
    RECOMMENDATION = "recommendation"

class CapsuleStatus(str, Enum):
    PREVIEW = "preview"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class CapsuleItem:
    item_id: str
    category: CapsuleCategory
    content: str
    source_id: Optional[str] = None
    inclusion_reason: Optional[str] = None
    provenance: Optional[str] = None
    
    def to_dict(self):
        return {
            "item_id": self.item_id,
            "category": self.category.value,
            "content": self.content,
            "source_id": self.source_id,
            "inclusion_reason": self.inclusion_reason,
            "provenance": self.provenance
        }

@dataclass
class CapsuleExcludedItem:
    item_id: str
    exclusion_reason: str

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "exclusion_reason": self.exclusion_reason
        }

@dataclass
class ContextCapsule:
    capsule_id: str
    client_id: str
    project_uuid: str
    branch: Optional[str]
    task: str
    content_hash: str
    status: CapsuleStatus
    items: List[CapsuleItem] = field(default_factory=list)
    excluded_items: List[CapsuleExcludedItem] = field(default_factory=list)
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    delivery_count: int = 0
    
    def to_dict(self):
        return {
            "capsule_id": self.capsule_id,
            "client_id": self.client_id,
            "project_uuid": self.project_uuid,
            "branch": self.branch,
            "task": self.task,
            "content_hash": self.content_hash,
            "status": self.status.value,
            "items": [item.to_dict() for item in self.items],
            "excluded_items": [item.to_dict() for item in self.excluded_items],
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "delivery_count": self.delivery_count
        }

    def compute_hash(self) -> str:
        import hashlib
        items_for_hash = []
        for i in self.items:
            # Exclude item_id as it's randomly generated per preview
            items_for_hash.append({
                "category": i.category.value,
                "content": i.content,
                "source_id": i.source_id,
                "inclusion_reason": i.inclusion_reason,
                "provenance": i.provenance
            })
            
        data = {
            "project_uuid": self.project_uuid,
            "branch": self.branch,
            "task": self.task,
            "items": items_for_hash
        }
        json_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()
