# checkpoint.py
"""
Checkpoint system for resumable exports.
Saves progress to disk so exports can be resumed after crashes/cancellations.
"""

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime


class ExportCheckpoint:
    """
    Manages checkpoint files for resumable exports.
    
    Format:
    {
        "version": "1.0",
        "created": "2024-11-30T10:30:00",
        "updated": "2024-11-30T10:35:00",
        "output_zip_path": "/path/to/output.zip",
        "total_reports": 5000,
        "completed_reports": ["report_id_1", "report_id_2", ...],
        "failed_reports": [
            {"id": "report_id_x", "name": "Report X", "error": "..."},
            ...
        ],
        "pending_reports": ["report_id_100", "report_id_101", ...],
        "session_info": {
            "session_id": "...",
            "instance_url": "...",
            "username": "..."
        }
    }
    """
    
    CHECKPOINT_VERSION = "1.0"
    
    def __init__(self, checkpoint_path: str):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_path: Path to checkpoint file (.json)
        """
        self.checkpoint_path = Path(checkpoint_path)
        self.lock = threading.Lock()
        
        # In-memory state
        self.data: Dict = {
            "version": self.CHECKPOINT_VERSION,
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "output_zip_path": "",
            "total_reports": 0,
            "completed_reports": [],
            "failed_reports": [],
            "pending_reports": [],
            "session_info": {}
        }
    
    def initialize(
        self,
        output_zip_path: str,
        report_ids: List[str],
        session_info: Dict
    ):
        """
        Initialize a new checkpoint for an export.
        
        Args:
            output_zip_path: Destination ZIP file
            report_ids: List of all report IDs to export
            session_info: Session information for resume
        """
        with self.lock:
            self.data = {
                "version": self.CHECKPOINT_VERSION,
                "created": datetime.now().isoformat(),
                "updated": datetime.now().isoformat(),
                "output_zip_path": output_zip_path,
                "total_reports": len(report_ids),
                "completed_reports": [],
                "failed_reports": [],
                "pending_reports": report_ids.copy(),
                "session_info": {
                    "session_id": session_info.get("session_id", ""),
                    "instance_url": session_info.get("instance_url", ""),
                    "username": session_info.get("user_name", ""),
                    "api_version": session_info.get("api_version", "")
                }
            }
            self._save()
    
    def mark_completed(self, report_id: str):
        """
        Mark a report as successfully completed.
        
        Args:
            report_id: Report ID that was exported
        """
        with self.lock:
            # Remove from pending
            if report_id in self.data["pending_reports"]:
                self.data["pending_reports"].remove(report_id)
            
            # Add to completed (avoid duplicates)
            if report_id not in self.data["completed_reports"]:
                self.data["completed_reports"].append(report_id)
            
            self.data["updated"] = datetime.now().isoformat()
            self._save()
    
    def mark_failed(self, report_id: str, report_name: str, error: str):
        """
        Mark a report as failed.
        
        Args:
            report_id: Report ID that failed
            report_name: Report name
            error: Error message
        """
        with self.lock:
            # Remove from pending
            if report_id in self.data["pending_reports"]:
                self.data["pending_reports"].remove(report_id)
            
            # Add to failed (avoid duplicates)
            existing_ids = {f["id"] for f in self.data["failed_reports"]}
            if report_id not in existing_ids:
                self.data["failed_reports"].append({
                    "id": report_id,
                    "name": report_name,
                    "error": error
                })
            
            self.data["updated"] = datetime.now().isoformat()
            self._save()
    
    def get_pending_reports(self) -> List[str]:
        """Get list of reports still pending export."""
        with self.lock:
            return self.data["pending_reports"].copy()
    
    def get_completed_reports(self) -> List[str]:
        """Get list of successfully exported reports."""
        with self.lock:
            return self.data["completed_reports"].copy()
    
    def get_failed_reports(self) -> List[Dict]:
        """Get list of failed reports with error details."""
        with self.lock:
            return self.data["failed_reports"].copy()
    
    def get_progress(self) -> Dict:
        """
        Get current progress statistics.
        
        Returns:
            Dict with total, completed, failed, pending counts
        """
        with self.lock:
            return {
                "total": self.data["total_reports"],
                "completed": len(self.data["completed_reports"]),
                "failed": len(self.data["failed_reports"]),
                "pending": len(self.data["pending_reports"])
            }
    
    def is_complete(self) -> bool:
        """Check if export is complete (no pending reports)."""
        with self.lock:
            return len(self.data["pending_reports"]) == 0
    
    def _save(self):
        """Save checkpoint to disk (internal, assumes lock held)."""
        try:
            # Ensure parent directory exists
            self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write atomically (write to temp, then rename)
            temp_path = self.checkpoint_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
            
            # Atomic rename
            temp_path.replace(self.checkpoint_path)
            
        except Exception as e:
            print(f"⚠️ Failed to save checkpoint: {e}")
    
    def load(self) -> bool:
        """
        Load checkpoint from disk.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        with self.lock:
            if not self.checkpoint_path.exists():
                return False
            
            try:
                with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                
                # Validate version
                if loaded_data.get("version") != self.CHECKPOINT_VERSION:
                    print(f"⚠️ Checkpoint version mismatch: {loaded_data.get('version')}")
                    return False
                
                self.data = loaded_data
                return True
                
            except Exception as e:
                print(f"⚠️ Failed to load checkpoint: {e}")
                return False
    
    def delete(self):
        """Delete checkpoint file from disk."""
        try:
            if self.checkpoint_path.exists():
                self.checkpoint_path.unlink()
        except Exception as e:
            print(f"⚠️ Failed to delete checkpoint: {e}")
    
    def exists(self) -> bool:
        """Check if checkpoint file exists."""
        return self.checkpoint_path.exists()
    
    def get_session_info(self) -> Dict:
        """Get stored session information for resume."""
        with self.lock:
            return self.data.get("session_info", {}).copy()
    
    def get_output_path(self) -> str:
        """Get the output ZIP path from checkpoint."""
        with self.lock:
            return self.data.get("output_zip_path", "")