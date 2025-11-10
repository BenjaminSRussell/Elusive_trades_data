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

        # Search state
        self.searching = False

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
        title_label.grid(row=0, column=0, pady=(0, 20))

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

        # Options frame
        options_frame = ttk.Frame(search_frame)
        options_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky=tk.W)

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
            font=('Courier', 10)
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

    def perform_search(self):
        """Perform the search in a background thread."""
        if self.searching:
            messagebox.showwarning("Search in Progress", "Please wait for the current search to complete.")
            return

        search_value = self.search_entry.get().strip()
        if not search_value:
            messagebox.showwarning("Input Required", "Please enter a part or model number.")
            return

        # Disable search button
        self.search_button.config(state='disabled')
        self.searching = True
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

            if search_type == "part":
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
            # Re-enable search button
            self.root.after(0, lambda: self.search_button.config(state='normal'))
            self.searching = False

    def update_status(self, message):
        """Update status bar (thread-safe)."""
        self.root.after(0, lambda: self.status_var.set(message))

    def display_results(self, search_value, results, enriched=None):
        """Display search results in the text area."""
        self.results_text.delete(1.0, tk.END)

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
        else:
            # Show formatted results
            self._display_formatted_results(search_value, results, enriched)

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
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "ERROR:\n\n")
        self.results_text.insert(tk.END, error_message)
        self.status_var.set("Error occurred")
        messagebox.showerror("Search Error", f"An error occurred:\n\n{error_message}")

    def clear_results(self):
        """Clear the results area."""
        self.results_text.delete(1.0, tk.END)
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
