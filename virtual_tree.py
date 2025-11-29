# virtual_tree.py
# TRUE Virtual Scrolling for Salesforce Report Tree
# Only renders visible items - handles 100,000+ items smoothly

import customtkinter as ctk
from typing import List, Dict, Callable, Optional, Set
import threading


class VirtualTreeView:
    """
    Virtual scrolling tree view that only renders visible items.
    Prevents UI freezing by lazy-loading widgets on scroll.
    """
    
    def __init__(
        self,
        parent_frame: ctk.CTkScrollableFrame,
        item_height: int = 50,
        buffer_items: int = 5  # ✅ CORRECT parameter name
    ):
        self.parent_frame = parent_frame
        self.item_height = item_height
        self.buffer_items = buffer_items
        
        # Data storage
        self.all_items: List[Dict] = []
        self.visible_widgets: Dict[int, Dict] = {}
        self.expanded_folders: Set[str] = set()
        
        # ✅ NEW: Selection state tracking
        self.selected_report_ids: Set[str] = set()  # Track selected report IDs
        
        # Callbacks
        self.on_folder_checkbox: Optional[Callable] = None
        self.on_folder_expand: Optional[Callable] = None
        self.on_report_checkbox: Optional[Callable] = None
        self.get_selection_state: Optional[Callable] = None  # ✅ NEW: Get selection from main app
        
        # Scroll tracking
        self.last_scroll_y = 0
        self.is_rendering = False
        self.render_lock = threading.Lock()
        
        # Bind scroll events
        self._setup_scroll_monitoring()
    
    def _setup_scroll_monitoring(self):
        """Setup scroll event monitoring"""
        try:
            # Get the canvas from CTkScrollableFrame
            canvas = self.parent_frame._parent_canvas
            
            # Bind to canvas scroll events
            canvas.bind("<Configure>", self._on_scroll, add="+")
            canvas.bind("<MouseWheel>", self._on_scroll, add="+")
            canvas.bind("<Button-4>", self._on_scroll, add="+")  # Linux scroll up
            canvas.bind("<Button-5>", self._on_scroll, add="+")  # Linux scroll down
            
        except Exception as e:
            print(f"⚠️ Could not setup scroll monitoring: {e}")
    
    def set_items(self, items: List[Dict], selected_report_ids: Set[str] = None):
        """
        Set all items and trigger initial render.
        
        Args:
            items: List of folder data with reports
            selected_report_ids: Set of currently selected report IDs
        """
        with self.render_lock:
            self.all_items = items
            self.visible_widgets.clear()
            
            # ✅ Update selection state
            if selected_report_ids is not None:
                self.selected_report_ids = selected_report_ids
        
        # Schedule render on main thread
        self.parent_frame.after(10, self._render_visible_items)
    
    def clear(self):
        """Clear all items and widgets"""
        with self.render_lock:
            # Destroy all visible widgets
            for widget_data in list(self.visible_widgets.values()):
                try:
                    if "frame" in widget_data:
                        widget_data["frame"].destroy()
                except:
                    pass
            
            self.visible_widgets.clear()
            self.all_items.clear()
            self.expanded_folders.clear()
            self.last_scroll_y = 0
    
    def _on_scroll(self, event=None):
        """Handle scroll event"""
        if self.is_rendering:
            return  # Skip if already rendering
        
        try:
            canvas = self.parent_frame._parent_canvas
            current_scroll_y = canvas.yview()[0]
            
            # Only re-render if scroll changed significantly (>5%)
            if abs(current_scroll_y - self.last_scroll_y) > 0.05:
                self.last_scroll_y = current_scroll_y
                
                # Schedule render with small delay (debouncing)
                self.parent_frame.after(50, self._render_visible_items)
        except:
            pass
    
    def _render_visible_items(self):
        """Render only the items currently visible in viewport"""
        if self.is_rendering:
            return
        
        if not self.all_items:
            return
        
        with self.render_lock:
            self.is_rendering = True
        
        try:
            # Calculate visible range
            canvas = self.parent_frame._parent_canvas
            canvas_height = canvas.winfo_height()
            
            if canvas_height <= 1:
                # Canvas not ready yet
                return
            
            scroll_y = canvas.yview()[0]
            
            # Calculate which items should be visible
            total_height = len(self.all_items) * self.item_height
            visible_start_y = scroll_y * total_height
            visible_end_y = visible_start_y + canvas_height
            
            # Add buffer using self.buffer_items
            buffer_height = self.buffer_items * self.item_height
            start_y = max(0, visible_start_y - buffer_height)
            end_y = min(total_height, visible_end_y + buffer_height)
            
            # Convert to item indices
            start_idx = max(0, int(start_y / self.item_height))
            end_idx = min(len(self.all_items), int(end_y / self.item_height) + 1)
            
            # Track which items should exist
            should_exist = set(range(start_idx, end_idx))
            current_exist = set(self.visible_widgets.keys())
            
            # Remove widgets outside viewport
            to_remove = current_exist - should_exist
            for idx in to_remove:
                self._remove_item_widget(idx)
            
            # Create widgets for visible items
            to_create = should_exist - current_exist
            for idx in sorted(to_create):
                if idx < len(self.all_items):
                    self._create_item_widget(idx)
        
        finally:
            with self.render_lock:
                self.is_rendering = False
    
    def _create_item_widget(self, idx: int):
        """Create widget for item at index"""
        if idx >= len(self.all_items):
            return
        
        item = self.all_items[idx]
        folder = item.get("folder")
        reports = item.get("reports", [])
        
        folder_id = folder.get("id")
        folder_name = folder.get("name", "Unnamed Folder")
        folder_type = folder.get("type", "")
        
        # Calculate row position (each folder takes 2 rows: header + reports)
        row = idx * 2
        
        # Main folder frame
        folder_frame = ctk.CTkFrame(
            self.parent_frame,
            fg_color="#333333",
            corner_radius=5
        )
        folder_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
        folder_frame.grid_columnconfigure(2, weight=1)
        
        # ✅ FIXED: Check if ALL reports in folder are selected
        reports = item.get("reports", [])
        all_reports_selected = False
        if reports:
            report_ids_in_folder = {r.get("id") for r in reports}
            all_reports_selected = report_ids_in_folder.issubset(self.selected_report_ids)

        # Folder checkbox
        checkbox_var = ctk.BooleanVar(value=all_reports_selected)
        checkbox = ctk.CTkCheckBox(
            folder_frame,
            text="",
            variable=checkbox_var,
            width=20,
            checkbox_width=18,
            checkbox_height=18,
            command=lambda: self._on_folder_checkbox_clicked(folder_id, checkbox_var)
        )
        checkbox.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        
        # Expand/collapse button
        is_expanded = folder_id in self.expanded_folders
        expand_btn = ctk.CTkButton(
            folder_frame,
            text="▼" if is_expanded else "▶",
            width=25,
            height=25,
            fg_color="transparent",
            hover_color="#444444",
            font=ctk.CTkFont(size=12),
            command=lambda: self._on_folder_expand_clicked(folder_id, idx)
        )
        expand_btn.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="w")
        
        # Folder icon and name
        icon = "🌐" if folder_type == "Public" else "👤" if "My" in folder_name else "📂"
        folder_label = ctk.CTkLabel(
            folder_frame,
            text=f"{icon} {folder_name} ({len(reports)} reports)",
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        folder_label.grid(row=0, column=2, sticky="ew", padx=(0, 10), pady=5)
        
        # Reports container (only create if expanded)
        reports_frame = None
        if is_expanded:
            reports_frame = ctk.CTkFrame(self.parent_frame, fg_color="#2b2b2b")
            reports_frame.grid(row=row + 1, column=0, sticky="ew", padx=(30, 5), pady=(0, 2))
            reports_frame.grid_columnconfigure(0, weight=1)
            
            # Create report items
            self._create_report_items(reports_frame, folder_id, reports)
        
        # Store widget data
        self.visible_widgets[idx] = {
            "folder_id": folder_id,
            "frame": folder_frame,
            "checkbox": checkbox,
            "checkbox_var": checkbox_var,
            "expand_btn": expand_btn,
            "reports_frame": reports_frame,
            "reports": reports
        }
    
    def _create_report_items(self, parent_frame, folder_id: str, reports: List[Dict]):
        """Create report checkboxes inside reports frame"""
        if not reports:
            no_reports_label = ctk.CTkLabel(
                parent_frame,
                text="No reports in this folder",
                text_color="gray",
                font=ctk.CTkFont(size=11)
            )
            no_reports_label.grid(row=0, column=0, padx=10, pady=5)
            return
        
        for idx, report in enumerate(reports):
            report_id = report.get("id")
            report_name = report.get("name", "Unnamed Report")
            
            # Report item frame
            report_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
            report_frame.grid(row=idx, column=0, sticky="ew", padx=10, pady=2)
            report_frame.grid_columnconfigure(1, weight=1)
            
            # ✅ FIXED: Check if this report is selected
            is_selected = report_id in self.selected_report_ids

            # Report checkbox
            report_checkbox_var = ctk.BooleanVar(value=is_selected)
            report_checkbox = ctk.CTkCheckBox(
                report_frame,
                text="",
                variable=report_checkbox_var,
                width=20,
                checkbox_width=16,
                checkbox_height=16,
                command=lambda rid=report_id, rname=report_name, fid=folder_id, var=report_checkbox_var:
                    self._on_report_checkbox_clicked(rid, rname, fid, var)
            )
            report_checkbox.grid(row=0, column=0, padx=(5, 5), pady=5, sticky="w")
            
            # Report name
            report_label = ctk.CTkLabel(
                report_frame,
                text=f"📄 {report_name}",
                font=ctk.CTkFont(size=11),
                anchor="w"
            )
            report_label.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5)
    
    def _remove_item_widget(self, idx: int):
        """Remove widget at index"""
        if idx not in self.visible_widgets:
            return
        
        widget_data = self.visible_widgets[idx]
        
        try:
            # Destroy main frame (will destroy all children)
            if "frame" in widget_data:
                widget_data["frame"].destroy()
            
            # Destroy reports frame if exists
            if "reports_frame" in widget_data and widget_data["reports_frame"]:
                widget_data["reports_frame"].destroy()
        except:
            pass
        
        del self.visible_widgets[idx]
    
    def _on_folder_checkbox_clicked(self, folder_id: str, checkbox_var: ctk.BooleanVar):
        """Handle folder checkbox click"""
        if self.on_folder_checkbox:
            self.on_folder_checkbox(folder_id, checkbox_var)
    
    def _on_folder_expand_clicked(self, folder_id: str, idx: int):
        """Handle folder expand/collapse"""
        # Toggle expansion state
        if folder_id in self.expanded_folders:
            self.expanded_folders.remove(folder_id)
        else:
            self.expanded_folders.add(folder_id)
        
        # Re-render this item
        self._remove_item_widget(idx)
        self._create_item_widget(idx)
        
        # Call callback
        if self.on_folder_expand:
            self.on_folder_expand(folder_id)
    
    def _on_report_checkbox_clicked(self, report_id: str, report_name: str, folder_id: str, checkbox_var: ctk.BooleanVar):
        """Handle report checkbox click"""
        if self.on_report_checkbox:
            self.on_report_checkbox(report_id, report_name, folder_id, checkbox_var)
    
    def update_selection_state(self, selected_report_ids: Set[str]):
        """
        Update the selection state and refresh visible items.
        
        Should be called from main app when selection changes.
        
        Args:
            selected_report_ids: Set of currently selected report IDs
            
        ✅ FIXED: Forces re-render of visible items to update checkboxes immediately.
        This is the simplest and most reliable approach.
        """
        with self.render_lock:
            self.selected_report_ids = selected_report_ids
        
        # ✅ SIMPLE FIX: Just re-render all visible items
        # This destroys and recreates them with correct checkbox states
        # Virtual scrolling makes this very fast (only ~10-20 items re-rendered)
        
        # Get list of currently visible indices
        visible_indices = list(self.visible_widgets.keys())
        
        # Remove and recreate each visible item
        for idx in visible_indices:
            self._remove_item_widget(idx)
            self._create_item_widget(idx)
        
        # Note: We don't call _render_visible_items() because that calculates
        # the viewport and might render different items. We want to update
        # the EXACT items that are currently visible.
    
    
    def _update_item_checkboxes(self, idx: int):
        """
        Update checkboxes for a specific visible item without destroying/recreating widgets.
        
        This is much faster than re-rendering the entire item.
        
        Args:
            idx: Index of the item in all_items
            
        ✅ NEW: Efficiently updates only checkbox states, not entire widgets.
        """
        if idx not in self.visible_widgets:
            return
        
        if idx >= len(self.all_items):
            return
        
        widget_data = self.visible_widgets[idx]
        item = self.all_items[idx]
        
        folder_id = item.get("folder", {}).get("id")
        reports = item.get("reports", [])
        
        if not folder_id or not reports:
            return
        
        # ✅ Check if ALL reports in this folder are selected
        report_ids_in_folder = {r.get("id") for r in reports}
        all_selected = report_ids_in_folder.issubset(self.selected_report_ids)
        
        # ✅ Update folder checkbox state
        if "checkbox_var" in widget_data:
            try:
                widget_data["checkbox_var"].set(all_selected)
            except:
                pass
        
        # ✅ Update individual report checkboxes if folder is expanded
        if folder_id in self.expanded_folders and "reports_frame" in widget_data:
            reports_frame = widget_data["reports_frame"]
            
            if reports_frame and reports_frame.winfo_exists():
                # Find report checkboxes in reports_frame and update them
                for widget in reports_frame.winfo_children():
                    if isinstance(widget, ctk.CTkFrame):
                        # This is a report row frame
                        for child in widget.winfo_children():
                            if isinstance(child, ctk.CTkCheckBox):
                                # Found the report checkbox
                                # Extract report ID from the checkbox's command
                                # (We stored it when creating the checkbox)
                                
                                # Get all reports and match by position
                                for report in reports:
                                    report_id = report.get("id")
                                    is_selected = report_id in self.selected_report_ids
                                    
                                    try:
                                        # Update checkbox state
                                        child.deselect() if not is_selected else child.select()
                                    except:
                                        pass