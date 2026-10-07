#!/usr/bin/env python3
"""
Lightweight GUI for HVAC Parts Search System

Simple tkinter-based interface for searching part and model numbers.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from phase1_acquisition.orchestrator import APIOrchestrator
from phase2_matching.enricher import PartEnricher
from phase3_index.parts_index import PartsIndex
import os
import subprocess
import webbrowser


class HVACSearchGUI:
    """Lightweight GUI for HVAC parts search."""

    def __init__(self, root):
        """Initialize the GUI."""
        self.root = root
        self.root.title("HVAC Parts Search")
        self.root.geometry("800x600")

        # Initialize components
        self.orchestrator = APIOrchestrator()
        self.enricher = PartEnricher()
        self.fts_db = Path(os.environ.get("PARTS_INDEX_DB", "data/parts_index.sqlite"))
        self.parts_index = None
        if self.fts_db.exists():
            try:
                self.parts_index = PartsIndex(self.fts_db)
            except Exception as exc:
                print(f"FTS index unavailable: {exc}")

        # Search state
        self.searching = False
        self._last_fts_hits = []

        # Create GUI elements
        self.create_widgets()

    def create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="HVAC Parts Search System",
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, pady=(0, 10))

        self.index_banner = ttk.Label(main_frame, text=self._index_banner_text(), foreground="#333")
        self.index_banner.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Search frame
        search_frame = ttk.LabelFrame(main_frame, text="Search", padding="10")
        search_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        search_frame.columnconfigure(1, weight=1)

        # Search type selection
        ttk.Label(search_frame, text="Search Type:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        self.search_type = tk.StringVar(value="part")
        type_frame = ttk.Frame(search_frame)
        type_frame.grid(row=0, column=1, sticky=tk.W)

        ttk.Radiobutton(
            type_frame,
            text="Part Number",
            variable=self.search_type,
            value="part"
        ).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Radiobutton(
            type_frame,
            text="Model Number",
            variable=self.search_type,
            value="model"
        ).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Radiobutton(
            type_frame,
            text="FTS Index",
            variable=self.search_type,
            value="fts"
        ).pack(side=tk.LEFT)

        # Input field
        ttk.Label(search_frame, text="Enter Number:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))

        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10, 0))
        self.search_entry.bind('<Return>', lambda e: self.perform_search())

        # Buttons frame
        button_frame = ttk.Frame(search_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))

        self.search_button = ttk.Button(
            button_frame,
            text="Search",
            command=self.perform_search
        )
        self.search_button.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="Clear",
            command=self.clear_results
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="Save Results",
            command=self.save_results
        ).pack(side=tk.LEFT)

        # Progress bar frame
        progress_frame = ttk.Frame(search_frame)
        progress_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
        progress_frame.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='indeterminate'
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # Options frame
        options_frame = ttk.Frame(search_frame)
        options_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky=tk.W)

        self.enrich_data = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Enrich data (Phase 2)",
            variable=self.enrich_data
        ).pack(side=tk.LEFT, padx=(0, 20))

        self.show_raw = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Show raw JSON",
            variable=self.show_raw
        ).pack(side=tk.LEFT)

        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        results_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        # Results text area
        self.results_text = scrolledtext.ScrolledText(
            results_frame,
            wrap=tk.WORD,
            width=80,
            height=20,
            font=('Courier', 10),
            state='disabled'
        )
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # Store current results
        self.current_results = None


    def _index_banner_text(self) -> str:
        """Index freshness banner for FTS DB (#5)."""
        if not self.fts_db.exists():
            return "FTS index: missing (run phase3_index.parts_index ingest)"
        mtime = datetime.fromtimestamp(self.fts_db.stat().st_mtime)
        age_h = (datetime.now() - mtime).total_seconds() / 3600
        stale = " STALE" if age_h > 24 else ""
        docs = "?"
        if self.parts_index is not None:
            try:
                row = self.parts_index.conn.execute("SELECT COUNT(*) FROM documents").fetchone()
                docs = row[0]
            except Exception:
                pass
        return (
            f"FTS index: {self.fts_db} | docs={docs} | "
            f"mtime={mtime.isoformat(timespec='seconds')}{stale}"
        )

    def _fts_search(self, query: str) -> dict:
        if self.parts_index is None:
            return {"status": "error", "error": "FTS index not available", "hits": []}
        hits = self.parts_index.search(query, limit=50)
        self._last_fts_hits = hits
        return {"status": "ok", "source": "fts", "hits": hits, "count": len(hits)}

    def _open_pdf_at_page(self, document: str, page_ref):
        """Best-effort jump-to-page via system viewer (#5)."""
        path = Path(document)
        if not path.exists():
            messagebox.showinfo("PDF", f"Document not found locally: {document}")
            return
        page = int(page_ref) if page_ref is not None else 1
        for cmd in (
            ["evince", f"--page-index={page}", str(path)],
            ["okular", "-p", str(page), str(path)],
            ["xdg-open", str(path)],
        ):
            try:
                subprocess.Popen(cmd)
                return
            except FileNotFoundError:
                continue
        webbrowser.open(path.as_uri())

    def _display_fts_results(self, results: dict):
        """Render FTS hits (#5)."""
        hits = results.get("hits") or []
        self.results_text.insert(tk.END, f"FTS hits: {len(hits)}\n")
        self.results_text.insert(
            tk.END, "(Select a hit line and press Ctrl+O to open PDF at page)\n\n"
        )
        for i, h in enumerate(hits, 1):
            line = (
                f"{i}. {h.get('part_number')}  page={h.get('page_ref')}  "
                f"{h.get('description') or ''}  [{h.get('document')}]\n"
            )
            self.results_text.insert(tk.END, line)
        self.results_text.bind("<Control-o>", self._on_open_selected_hit)
        self.status_var.set(f"FTS: {len(hits)} hits")

    def _on_open_selected_hit(self, event=None):
        try:
            line_no = int(self.results_text.index("insert").split(".")[0])
        except Exception:
            return
        idx = line_no - 3
        if idx < 0 or idx >= len(self._last_fts_hits):
            return
        hit = self._last_fts_hits[idx]
        self._open_pdf_at_page(hit.get("document") or "", hit.get("page_ref"))

    def perform_search(self):
        """Perform the search in a background thread."""
        if self.searching:
            messagebox.showwarning("Search in Progress", "Please wait for the current search to complete.")
            return

        search_value = self.search_entry.get().strip()
        if not search_value:
            messagebox.showwarning("Input Required", "Please enter a part or model number.")
            return

        # Disable search button and start progress bar
        self.search_button.config(state='disabled')
        self.searching = True
        self.progress_bar.start()
        self.status_var.set("Searching...")

        # Run search in background thread
        thread = threading.Thread(target=self._search_thread, args=(search_value,))
        thread.daemon = True
        thread.start()

    def _search_thread(self, search_value):
        """Background thread for searching."""
        try:
            search_type = self.search_type.get()

            # Phase 1: API search
            self.update_status(f"Phase 1: Searching APIs for {search_value}...")

            if search_type == "fts":
                results = self._fts_search(search_value)
                enriched = None
                self.root.after(0, self.display_results, search_value, results, enriched)
                return
            elif search_type == "part":
                results = self.orchestrator.search_all_apis(search_value)
            else:  # model
                results = self.orchestrator.search_by_model_all_apis(search_value)

            # Phase 2: Enrichment (if enabled)
            enriched = None
            if self.enrich_data.get() and search_type == "part":
                self.update_status(f"Phase 2: Enriching data for {search_value}...")
                try:
                    enriched = self.enricher.enrich_part(search_value)
                except Exception as e:
                    print(f"Enrichment error (non-critical): {e}")

            # Display results
            self.root.after(0, self.display_results, search_value, results, enriched)

        except Exception as e:
            self.root.after(0, self.display_error, str(e))

        finally:
            # Dispatch UI state reset via root.after() to ensure thread safety
            self.root.after(0, self._on_search_finished)


    def _maybe_show_mock_banner(self, results):
        """Show a visible MOCK DATA banner when any payload is mock-sourced."""
        payloads = []
        if isinstance(results, dict):
            for v in results.values():
                if isinstance(v, dict):
                    payloads.append(v)
                elif isinstance(v, list):
                    payloads.extend([x for x in v if isinstance(x, dict)])
        mockish = any(
            (p.get("source") == "mock") or p.get("live_fallback")
            for p in payloads
        )
        if mockish:
            self.results_text.insert(tk.END, "\n*** MOCK DATA — not live vendor prices/stock ***\n\n")

    def update_status(self, message):
        """Update status bar (thread-safe)."""
        self.root.after(0, lambda: self.status_var.set(message))

    def _on_search_finished(self):
        """Handle UI state reset when search completes (called via root.after for thread safety)."""
        self.search_button.config(state='normal')
        self.progress_bar.stop()
        self.searching = False

    def display_results(self, search_value, results, enriched=None):
        """Display search results in the text area."""
        # Temporarily enable text widget for insertion
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self._maybe_show_mock_banner(results)

        # Store results
        self.current_results = {
            "search_value": search_value,
            "timestamp": datetime.now().isoformat(),
            "api_results": results,
            "enriched": enriched
        }

        if self.show_raw.get():
            # Show raw JSON
            self.results_text.insert(tk.END, json.dumps(self.current_results, indent=2))
        elif isinstance(results, dict) and results.get("source") == "fts":
            self._display_fts_results(results)
        else:
            # Show formatted results
            self._display_formatted_results(search_value, results, enriched)

        # Disable text widget to prevent user editing
        self.results_text.config(state='disabled')
        self.status_var.set(f"Search complete for: {search_value}")

    def _display_formatted_results(self, search_value, results, enriched):
        """Display formatted (human-readable) results."""
        # Header
        self.results_text.insert(tk.END, "=" * 70 + "\n")
        self.results_text.insert(tk.END, f"  Search Results for: {search_value}\n")
        self.results_text.insert(tk.END, "=" * 70 + "\n\n")

        # Phase 1 Results
        self.results_text.insert(tk.END, "PHASE 1: API SEARCH RESULTS\n")
        self.results_text.insert(tk.END, "-" * 70 + "\n\n")

        if 'results' in results:
            for api_name, api_result in results['results'].items():
                status = api_result.get('status', 'unknown')
                self.results_text.insert(tk.END, f"  {api_name.upper()}:\n")
                self.results_text.insert(tk.END, f"    Status: {status}\n")

                if status == 'success' and 'data' in api_result:
                    data = api_result['data']

                    # Extract key information
                    if 'data' in data and isinstance(data['data'], dict):
                        part_data = data['data']

                        if 'description' in part_data:
                            self.results_text.insert(tk.END, f"    Description: {part_data['description']}\n")

                        if 'manufacturer' in part_data:
                            self.results_text.insert(tk.END, f"    Manufacturer: {part_data['manufacturer']}\n")

                        if 'price' in part_data:
                            self.results_text.insert(tk.END, f"    Price: ${part_data['price']}\n")

                        if 'in_stock' in part_data:
                            stock_status = "Yes" if part_data['in_stock'] else "No"
                            self.results_text.insert(tk.END, f"    In Stock: {stock_status}\n")

                        if 'specifications' in part_data:
                            self.results_text.insert(tk.END, f"    Specifications:\n")
                            for key, value in part_data['specifications'].items():
                                self.results_text.insert(tk.END, f"      - {key}: {value}\n")

                self.results_text.insert(tk.END, "\n")

        # Phase 2 Results (if available)
        if enriched:
            self.results_text.insert(tk.END, "\n" + "=" * 70 + "\n")
            self.results_text.insert(tk.END, "PHASE 2: ENRICHED DATA\n")
            self.results_text.insert(tk.END, "-" * 70 + "\n\n")

            # Status
            if 'status' in enriched:
                status = enriched['status']
                self.results_text.insert(tk.END, "  Part Status:\n")
                self.results_text.insert(tk.END, f"    Deprecated: {status.get('is_deprecated', 'Unknown')}\n")
                self.results_text.insert(tk.END, f"    Has Replacement: {status.get('has_replacement', 'Unknown')}\n")

                if status.get('deprecation_confidence'):
                    confidence = status['deprecation_confidence']
                    self.results_text.insert(tk.END, f"    Deprecation Confidence: {confidence:.1%}\n")

            # Relationships
            if 'relationships' in enriched:
                relationships = enriched['relationships']

                cross_refs = relationships.get('cross_references', [])
                if cross_refs:
                    self.results_text.insert(tk.END, f"\n  Cross-References ({len(cross_refs)}):\n")
                    for ref in cross_refs[:5]:  # Show first 5
                        if isinstance(ref, dict):
                            mfr = ref.get('manufacturer', 'Unknown')
                            pn = ref.get('part_number', 'Unknown')
                            self.results_text.insert(tk.END, f"    - {mfr}: {pn}\n")

                replacements = relationships.get('replacements', [])
                if replacements:
                    self.results_text.insert(tk.END, f"\n  Replacements ({len(replacements)}):\n")
                    for rep in replacements[:5]:  # Show first 5
                        if isinstance(rep, dict):
                            pn = rep.get('part_number', 'Unknown')
                            self.results_text.insert(tk.END, f"    - {pn}\n")

            # Confidence Scores
            if 'confidence_scores' in enriched:
                scores = enriched['confidence_scores']
                self.results_text.insert(tk.END, "\n  Confidence Scores:\n")
                for key, value in scores.items():
                    self.results_text.insert(tk.END, f"    {key}: {value:.1%}\n")

        # Data sources
        self.results_text.insert(tk.END, "\n" + "=" * 70 + "\n")
        self.results_text.insert(tk.END, "DATA LOCATIONS\n")
        self.results_text.insert(tk.END, "-" * 70 + "\n")
        self.results_text.insert(tk.END, f"  Raw API data: data/raw/\n")
        if enriched:
            self.results_text.insert(tk.END, f"  Processed data: data/processed/{search_value}/\n")

    def display_error(self, error_message):
        """Display error message."""
        # Temporarily enable text widget for error insertion
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "ERROR:\n\n")
        self.results_text.insert(tk.END, error_message)
        # Disable text widget to prevent user editing
        self.results_text.config(state='disabled')
        self.status_var.set("Error occurred")
        messagebox.showerror("Search Error", f"An error occurred:\n\n{error_message}")

    def clear_results(self):
        """Clear the results area."""
        # Temporarily enable text widget to clear it
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        # Keep it disabled after clearing
        self.results_text.config(state='disabled')
        self.search_entry.delete(0, tk.END)
        self.current_results = None
        self.status_var.set("Ready")

    def save_results(self):
        """Save current results to file."""
        if not self.current_results:
            messagebox.showwarning("No Results", "No results to save. Perform a search first.")
            return

        # Save to tests/output directory
        output_dir = Path("tests/output")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        search_value = self.current_results['search_value']
        filename = f"gui_search_{search_value}_{timestamp}.json"
        filepath = output_dir / filename

        try:
            with open(filepath, 'w') as f:
                json.dump(self.current_results, f, indent=2)

            self.status_var.set(f"Results saved to: {filepath}")
            messagebox.showinfo("Saved", f"Results saved to:\n{filepath}")

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save results:\n{e}")


def main():
    """Main entry point for GUI."""
    root = tk.Tk()
    app = HVACSearchGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
