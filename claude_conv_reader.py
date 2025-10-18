#!/usr/bin/env python3
"""
Claude Conversation Reader - GUI Version
Efficiently parses and displays conversations from Claude export JSON files.
"""

import json
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
from pathlib import Path
import threading


class ConversationReaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Claude Conversation Reader")
        self.root.geometry("1200x800")
        
        self.data = None
        self.conversations = []
        self.all_conversations = []  # Store original unfiltered list
        self.current_conv_index = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open JSON...", command=self.load_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=3)
        main_frame.rowconfigure(1, weight=1)
        
        # Top toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(toolbar, text="Open File", command=self.load_file).pack(side=tk.LEFT, padx=5)
        
        # Navigation buttons
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        self.prev_btn = ttk.Button(toolbar, text="◀ Previous", command=self.goto_previous, state=tk.DISABLED)
        self.prev_btn.pack(side=tk.LEFT, padx=2)
        self.next_btn = ttk.Button(toolbar, text="Next ▶", command=self.goto_next, state=tk.DISABLED)
        self.next_btn.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Label(toolbar, text="Search:").pack(side=tk.LEFT, padx=(5, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(toolbar, text="No file loaded")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        # Left panel - Conversation list
        left_panel = ttk.Frame(main_frame)
        left_panel.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(1, weight=1)
        
        ttk.Label(left_panel, text="Conversations", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(left_panel)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.conv_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=('Monospace', 9))
        scrollbar.config(command=self.conv_listbox.yview)
        
        self.conv_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.conv_listbox.bind('<<ListboxSelect>>', self.on_conversation_select)
        
        # Right panel - Conversation display
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)
        
        # Conversation info
        info_frame = ttk.Frame(right_panel)
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.conv_title_label = ttk.Label(info_frame, text="Select a conversation", font=('Arial', 12, 'bold'))
        self.conv_title_label.pack(anchor=tk.W)
        
        self.conv_info_label = ttk.Label(info_frame, text="", font=('Arial', 9))
        self.conv_info_label.pack(anchor=tk.W)
        
        # Message display
        self.message_display = scrolledtext.ScrolledText(
            right_panel,
            wrap=tk.WORD,
            font=('Arial', 10),
            padx=10,
            pady=10
        )
        self.message_display.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure text tags for formatting
        self.message_display.tag_config('human', foreground='#0066cc', font=('Arial', 10, 'bold'))
        self.message_display.tag_config('assistant', foreground='#cc6600', font=('Arial', 10, 'bold'))
        self.message_display.tag_config('timestamp', foreground='#666666', font=('Arial', 8))
        self.message_display.tag_config('separator', foreground='#cccccc')
        self.message_display.tag_config('highlight', background='#ffff00', foreground='#000000')
        
        self.current_search_query = ""
        
    def load_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Claude Export JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        self.status_label.config(text="Loading...")
        self.root.update()
        
        # Load in a thread to prevent UI freezing
        thread = threading.Thread(target=self.load_file_thread, args=(filepath,))
        thread.daemon = True
        thread.start()
        
    def load_file_thread(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            # Schedule UI update in main thread
            self.root.after(0, self.populate_conversations)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to load file:\n{str(e)}"))
            self.root.after(0, lambda: self.status_label.config(text="Error loading file"))
    
    def populate_conversations(self):
        self.all_conversations = self.data if isinstance(self.data, list) else [self.data]
        # Sort by date (chronological order - oldest to newest for navigation)
        self.all_conversations.sort(key=lambda c: c.get('updated_at', ''))
        # Display sorted by most recent first
        self.conversations = list(reversed(self.all_conversations))
        self.update_conversation_list(self.conversations)
        self.status_label.config(text=f"Loaded {len(self.conversations)} conversation(s) (sorted by most recent)")
        # Enable navigation buttons
        self.prev_btn.config(state=tk.NORMAL)
        self.next_btn.config(state=tk.NORMAL)
        
    def update_conversation_list(self, conversations):
        self.conv_listbox.delete(0, tk.END)
        
        for idx, conv in enumerate(conversations):
            name = conv.get('name', 'Untitled')
            msg_count = len(conv.get('chat_messages', []))
            updated = conv.get('updated_at', '')
            
            try:
                dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                date_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                date_str = 'N/A'
            
            display_text = f"{name} ({msg_count}) - {date_str}"
            self.conv_listbox.insert(tk.END, display_text)
            
            # Store the actual index for later retrieval
            self.conv_listbox.itemconfig(tk.END, {'fg': 'black'})
    
    def on_conversation_select(self, event):
        selection = self.conv_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        # Map display index to actual conversation
        conv = self.conversations[idx]
        # Find this conversation in the full chronological list
        self.current_conv_index = self.all_conversations.index(conv)
        self.display_conversation_by_conv(conv)
        self.update_nav_buttons()
    
    def goto_previous(self):
        """Go to the previous conversation chronologically (older)."""
        if self.current_conv_index is None or self.current_conv_index <= 0:
            return
        
        self.current_conv_index -= 1
        conv = self.all_conversations[self.current_conv_index]
        self.display_conversation_by_conv(conv)
        self.update_nav_buttons()
        self.highlight_in_list(conv)
    
    def goto_next(self):
        """Go to the next conversation chronologically (newer)."""
        if self.current_conv_index is None or self.current_conv_index >= len(self.all_conversations) - 1:
            return
        
        self.current_conv_index += 1
        conv = self.all_conversations[self.current_conv_index]
        self.display_conversation_by_conv(conv)
        self.update_nav_buttons()
        self.highlight_in_list(conv)
    
    def update_nav_buttons(self):
        """Update the enabled/disabled state of navigation buttons."""
        if self.current_conv_index is None:
            self.prev_btn.config(state=tk.DISABLED)
            self.next_btn.config(state=tk.DISABLED)
        else:
            # Previous button (go to older)
            if self.current_conv_index <= 0:
                self.prev_btn.config(state=tk.DISABLED)
            else:
                self.prev_btn.config(state=tk.NORMAL)
            
            # Next button (go to newer)
            if self.current_conv_index >= len(self.all_conversations) - 1:
                self.next_btn.config(state=tk.DISABLED)
            else:
                self.next_btn.config(state=tk.NORMAL)
    
    def highlight_in_list(self, conv):
        """Highlight the current conversation in the listbox."""
        try:
            idx = self.conversations.index(conv)
            self.conv_listbox.selection_clear(0, tk.END)
            self.conv_listbox.selection_set(idx)
            self.conv_listbox.see(idx)
        except ValueError:
            # Conversation not in current filtered list
            pass
    
    def display_conversation_by_conv(self, conv):
        """Display a conversation given the conversation object."""
        # Update title and info
        name = conv.get('name', 'Untitled')
        created = conv.get('created_at', 'N/A')
        updated = conv.get('updated_at', 'N/A')
        msg_count = len(conv.get('chat_messages', []))
        
        # Add position indicator
        position = f"[{self.current_conv_index + 1} of {len(self.all_conversations)}]"
        self.conv_title_label.config(text=f"{name} {position}")
        
        try:
            created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            created_str = created_dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            created_str = created
            
        try:
            updated_dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            updated_str = updated_dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            updated_str = updated
        
        self.conv_info_label.config(
            text=f"Created: {created_str} | Updated: {updated_str} | Messages: {msg_count}"
        )
        
        # Display messages
        self.message_display.config(state=tk.NORMAL)
        self.message_display.delete(1.0, tk.END)
        
        chat_messages = conv.get('chat_messages', [])
        
        for i, msg in enumerate(chat_messages):
            sender = msg.get('sender', 'unknown')
            text = msg.get('text', '')
            timestamp = msg.get('created_at', 'N/A')
            
            try:
                ts_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                ts_str = ts_dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                ts_str = timestamp
            
            # Format sender
            if sender == 'human':
                prefix = "👤 YOU"
                tag = 'human'
            elif sender == 'assistant':
                prefix = "🤖 CLAUDE"
                tag = 'assistant'
            else:
                prefix = f"📝 {sender.upper()}"
                tag = 'human'
            
            # Insert message header
            self.message_display.insert(tk.END, f"{prefix}", tag)
            self.message_display.insert(tk.END, f" [{ts_str}]\n", 'timestamp')
            self.message_display.insert(tk.END, "─" * 80 + "\n", 'separator')
            
            # Insert message text with highlighting
            if self.current_search_query:
                self.insert_text_with_highlight(text, self.current_search_query)
            else:
                self.message_display.insert(tk.END, f"{text}\n\n")
            
            if i < len(chat_messages) - 1:
                self.message_display.insert(tk.END, "═" * 80 + "\n\n", 'separator')
        
        self.message_display.config(state=tk.DISABLED)
        self.message_display.see(1.0)  # Scroll to top
    
    def display_conversation(self, index):
        if index < 0 or index >= len(self.conversations):
            return
        
        conv = self.conversations[index]
        self.current_conv_index = index
        
        # Update title and info
        name = conv.get('name', 'Untitled')
        created = conv.get('created_at', 'N/A')
        updated = conv.get('updated_at', 'N/A')
        msg_count = len(conv.get('chat_messages', []))
        
        self.conv_title_label.config(text=name)
        
        try:
            created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            created_str = created_dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            created_str = created
            
        try:
            updated_dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            updated_str = updated_dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            updated_str = updated
        
        self.conv_info_label.config(
            text=f"Created: {created_str} | Updated: {updated_str} | Messages: {msg_count}"
        )
        
        # Display messages
        self.message_display.config(state=tk.NORMAL)
        self.message_display.delete(1.0, tk.END)
        
        chat_messages = conv.get('chat_messages', [])
        
        for i, msg in enumerate(chat_messages):
            sender = msg.get('sender', 'unknown')
            text = msg.get('text', '')
            timestamp = msg.get('created_at', 'N/A')
            
            try:
                ts_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                ts_str = ts_dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                ts_str = timestamp
            
            # Format sender
            if sender == 'human':
                prefix = "👤 YOU"
                tag = 'human'
            elif sender == 'assistant':
                prefix = "🤖 CLAUDE"
                tag = 'assistant'
            else:
                prefix = f"📝 {sender.upper()}"
                tag = 'human'
            
            # Insert message
            self.message_display.insert(tk.END, f"{prefix}", tag)
            self.message_display.insert(tk.END, f" [{ts_str}]\n", 'timestamp')
            self.message_display.insert(tk.END, "─" * 80 + "\n", 'separator')
            self.message_display.insert(tk.END, f"{text}\n\n")
            
            if i < len(chat_messages) - 1:
                self.message_display.insert(tk.END, "═" * 80 + "\n\n", 'separator')
        
        self.message_display.config(state=tk.DISABLED)
        self.message_display.see(1.0)  # Scroll to top
    
    def insert_text_with_highlight(self, text, query):
        """Insert text with search query highlighted."""
        query_lower = query.lower()
        text_lower = text.lower()
        
        pos = 0
        while pos < len(text):
            # Find next occurrence
            idx = text_lower.find(query_lower, pos)
            
            if idx == -1:
                # No more matches, insert rest of text
                self.message_display.insert(tk.END, text[pos:] + "\n\n")
                break
            
            # Insert text before match
            if idx > pos:
                self.message_display.insert(tk.END, text[pos:idx])
            
            # Insert highlighted match
            self.message_display.insert(tk.END, text[idx:idx+len(query)], 'highlight')
            
            pos = idx + len(query)
        
        if pos >= len(text):
            self.message_display.insert(tk.END, "\n\n")
    
    def on_search_change(self, *args):
        query = self.search_var.get().strip()
        self.current_search_query = query
        
        if not query:
            # Sort by most recent (updated_at) when no search
            sorted_convs = sorted(
                self.all_conversations,
                key=lambda c: c.get('updated_at', ''),
                reverse=True
            )
            self.conversations = sorted_convs
            self.update_conversation_list(sorted_convs)
            self.status_label.config(text=f"{len(self.all_conversations)} conversation(s)")
            return
        
        query_lower = query.lower()
        filtered = []
        
        for conv in self.all_conversations:
            name = conv.get('name', 'Untitled').lower()
            
            # Search in name
            if query_lower in name:
                filtered.append((conv, 'title'))
                continue
            
            # Search in messages
            chat_messages = conv.get('chat_messages', [])
            for msg in chat_messages:
                text = msg.get('text', '').lower()
                if query_lower in text:
                    filtered.append((conv, 'message'))
                    break
        
        # Sort filtered results by date: most recent first (earliest at bottom of display list)
        filtered.sort(key=lambda x: x[0].get('updated_at', ''), reverse=True)
        filtered_convs = [conv for conv, _ in filtered]
        
        self.conversations = filtered_convs
        self.update_conversation_list(filtered_convs)
        
        if len(filtered_convs) == 0:
            self.status_label.config(text=f"No results for '{query}'")
        else:
            self.status_label.config(text=f"Found {len(filtered_convs)} conversation(s) matching '{query}' (sorted by date)")


def main():
    root = tk.Tk()
    app = ConversationReaderGUI(root)
    
    # Load file if provided as argument
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        root.after(100, lambda: app.load_file_thread(filepath))
    
    root.mainloop()


if __name__ == '__main__':
    main()
