import uuid
import json
import logging
import asyncio
from typing import List, Dict, Optional, Any
from .models import ContextCapsule, CapsuleItem, CapsuleExcludedItem, CapsuleCategory, CapsuleStatus
from vidurai.storage.database import MemoryDatabase
from datetime import datetime, timedelta

logger = logging.getLogger("vidurai.capsules.service")

class CapsuleService:
    def __init__(self, db: MemoryDatabase):
        self.db = db

    def generate_preview(
        self,
        client_id: str,
        project_uuid: str,
        branch: Optional[str],
        task: str,
        requested_categories: List[CapsuleCategory],
        max_items: int = 50,
        project_path: str = ""
    ) -> ContextCapsule:
        """
        Generate a Context Capsule preview by selecting minimum sufficient truth from the DB.
        """
        project_id = self.db.get_or_create_project(project_path)
        
        with self.db.get_connection_for_reading() as conn:
            mem_rows = conn.execute("SELECT id, event_type, salience, tags, gist FROM memories WHERE project_id = ?", (project_id,)).fetchall()
            
        memories = [dict(r) for r in mem_rows]
        
        items = []
        excluded_items = []
        
        for mem in memories:
            mem_id = mem['id']
            salience = mem['salience'].lower()
            
            cat = CapsuleCategory.EVIDENCE
            if salience == 'high':
                cat = CapsuleCategory.DECISION
            elif salience == 'low':
                cat = CapsuleCategory.WORKING
                
            tags = mem.get('tags') or ''
            if 'contradict' in tags:
                cat = CapsuleCategory.CONTRADICTION
                
            if 'unresolved' in tags:
                cat = CapsuleCategory.UNRESOLVED
                
            if cat in requested_categories:
                if len(items) < max_items:
                    items.append(CapsuleItem(
                        item_id=str(uuid.uuid4()),
                        category=cat,
                        content=mem['gist'],
                        source_id=str(mem_id),
                        inclusion_reason="Matches requested category and project",
                        provenance=f"vidurai://memory/{mem_id}"
                    ))
                else:
                    excluded_items.append(CapsuleExcludedItem(
                        item_id=str(uuid.uuid4()),
                        exclusion_reason="Exceeds requested budget"
                    ))
            else:
                excluded_items.append(CapsuleExcludedItem(
                    item_id=str(uuid.uuid4()),
                    exclusion_reason=f"Category {cat.value} not requested"
                ))
                
        capsule_id = str(uuid.uuid4())
        
        capsule = ContextCapsule(
            capsule_id=capsule_id,
            client_id=client_id,
            project_uuid=project_uuid,
            branch=branch,
            task=task,
            content_hash="",
            status=CapsuleStatus.PREVIEW,
            items=items,
            excluded_items=excluded_items
        )
        capsule.content_hash = capsule.compute_hash()
        
        self._save_capsule(capsule)
        
        return capsule

    def _save_capsule(self, capsule: ContextCapsule):
        future = self.db._enqueue("""
            INSERT OR REPLACE INTO context_capsules 
            (capsule_id, client_id, project_uuid, branch, task, content_hash, status, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            capsule.capsule_id, capsule.client_id, capsule.project_uuid, capsule.branch, 
            capsule.task, capsule.content_hash, capsule.status.value, 
            (datetime.now() + timedelta(hours=1)).isoformat()
        ))
        future.result()
        
        for item in capsule.items:
            future = self.db._enqueue("""
                INSERT OR REPLACE INTO capsule_items
                (capsule_id, item_id, category, source_id, content, inclusion_reason, provenance)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                capsule.capsule_id, item.item_id, item.category.value, item.source_id,
                item.content, item.inclusion_reason, item.provenance
            ))
            future.result()
            
        for excl in capsule.excluded_items:
            future = self.db._enqueue("""
                INSERT OR REPLACE INTO capsule_excluded_items
                (capsule_id, item_id, exclusion_reason)
                VALUES (?, ?, ?)
            """, (
                capsule.capsule_id, excl.item_id, excl.exclusion_reason
            ))
            future.result()

    def get_capsule(self, capsule_id: str) -> Optional[ContextCapsule]:
        with self.db.get_connection_for_reading() as conn:
            row = conn.execute("SELECT * FROM context_capsules WHERE capsule_id = ?", (capsule_id,)).fetchone()
            if not row:
                return None
            
        capsule = ContextCapsule(
            capsule_id=row['capsule_id'],
            client_id=row['client_id'],
            project_uuid=row['project_uuid'],
            branch=row['branch'],
            task=row['task'],
            content_hash=row['content_hash'],
            status=CapsuleStatus(row['status']),
            created_at=row['created_at'],
            expires_at=row['expires_at'],
            delivery_count=row['delivery_count']
        )
        
        with self.db.get_connection_for_reading() as conn:
            for r in conn.execute("SELECT * FROM capsule_items WHERE capsule_id = ?", (capsule_id,)).fetchall():
                capsule.items.append(CapsuleItem(
                    item_id=r['item_id'],
                    category=CapsuleCategory(r['category']),
                    content=r['content'],
                    source_id=r['source_id'],
                    inclusion_reason=r['inclusion_reason'],
                    provenance=r['provenance']
                ))
                
            for r in conn.execute("SELECT * FROM capsule_excluded_items WHERE capsule_id = ?", (capsule_id,)).fetchall():
                capsule.excluded_items.append(CapsuleExcludedItem(
                    item_id=r['item_id'],
                    exclusion_reason=r['exclusion_reason']
                ))
            
        return capsule

    def approve_capsule(self, client_id: str, capsule_id: str) -> bool:
        capsule = self.get_capsule(capsule_id)
        if not capsule or capsule.client_id != client_id or capsule.status != CapsuleStatus.PREVIEW:
            return False
            
        future = self.db._enqueue(
            "UPDATE context_capsules SET status = ? WHERE capsule_id = ?",
            (CapsuleStatus.APPROVED.value, capsule_id)
        )
        future.result()
        return True

    def reject_capsule(self, client_id: str, capsule_id: str) -> bool:
        capsule = self.get_capsule(capsule_id)
        if not capsule or capsule.client_id != client_id or capsule.status != CapsuleStatus.PREVIEW:
            return False
            
        future = self.db._enqueue(
            "UPDATE context_capsules SET status = ? WHERE capsule_id = ?",
            (CapsuleStatus.REJECTED.value, capsule_id)
        )
        future.result()
        return True

    def consume_capsule(self, client_id: str, capsule_id: str) -> Optional[ContextCapsule]:
        capsule = self.get_capsule(capsule_id)
        if not capsule or capsule.client_id != client_id or capsule.status != CapsuleStatus.APPROVED:
            return None
            
        future = self.db._enqueue(
            "UPDATE context_capsules SET delivery_count = delivery_count + 1 WHERE capsule_id = ?",
            (capsule_id,)
        )
        future.result()
        capsule.delivery_count += 1
        return capsule

