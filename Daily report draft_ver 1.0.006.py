import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from fpdf import FPDF
import json
import os
from datetime import datetime
from tkinterdnd2 import DND_FILES, TkinterDnD

class TaskManager:
    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("Task Manager")
        self.root.geometry("800x600")

        # Initialize drag-and-drop attributes
        self.drag_data = None
        self.drag_source = None
        self.drag_source_index = None

        # Task counter
        self.task_count = 0
        self.accomplished_count = 0  # Initialize accomplished task count
        
        # Initialize undo/redo stacks
        self.undo_stack = []
        self.redo_stack = []

        # Initialize file path
        self.file_path = None

        # Create main containers
        self.create_menu_bar()
        self.create_input_section()
        self.create_task_boxes()
        self.create_action_buttons()  # Add action buttons at the bottom

        # Dictionary to store tasks
        self.tasks = {f"Priority {i}": [] for i in range(1, 5)}

        # Bind keyboard shortcuts
        self.root.bind_all('<Control-o>', lambda e: self.open_file())  # Bind Ctrl+O for open
        self.root.bind_all('<Control-s>', lambda e: self.save_tasks())  # Bind Ctrl+S for save
        self.root.bind('<Control-Shift-L>', lambda e: self.clear_all_accomplished())  # Bind Ctrl+Shift+L for CLA
        self.root.bind('<Delete>', lambda e: self.delete_task())
        self.root.bind('<Control-Shift-E>', lambda e: self.modify_task())
        self.root.bind('<Control-Shift-Up>', lambda e: self.move_up())
        self.root.bind('<Control-Shift-Down>', lambda e: self.move_down())
        self.root.bind('<Control-z>', lambda e: self.undo())  # Bind Ctrl+Z for undo
        self.root.bind('<Control-y>', lambda e: self.redo())  # Bind Ctrl+Y for redo
        self.task_input.bind('<Return>', lambda e: self.prompt_priority())  # Bind Enter in input field
        for listbox in self.task_boxes.values():
            listbox.bind('<Return>', lambda e: self.accomplish_task())  # Bind Enter in task boxes
            listbox.bind('<Double-Return>', lambda e: self.restore_task())  # Bind Double Enter in task boxes

    def create_menu_bar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu, underline=0)  # Set mnemonic for 'File' menu
        file_menu.add_command(label="New", command=self.new_file)
        file_menu.add_command(label="Open", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_tasks, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export to PDF", command=self.export_pdf)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_command(label="CLA", command=self.clear_all_accomplished, accelerator="Ctrl+Shift+L")

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def create_input_section(self):
        # Task counter label
        self.counter_label = tk.Label(self.root, text="Total Tasks: 0")
        self.counter_label.pack(pady=5)

        # Input frame
        input_frame = ttk.Frame(self.root)
        input_frame.pack(pady=10, padx=10, fill='x')

        # Input field
        self.task_input = ttk.Entry(input_frame)
        self.task_input.pack(side='left', expand=True, fill='x', padx=(0, 10))

        # Priority buttons
        for i in range(1, 5):
            btn = ttk.Button(input_frame, 
                           text=f"Priority {i}",
                           command=lambda x=i: self.add_task(x))
            btn.pack(side='left', padx=5)

    def create_task_boxes(self):
        # Create frame for task boxes
        task_frame = ttk.Frame(self.root)
        task_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # Configure grid
        task_frame.grid_columnconfigure(0, weight=1)
        task_frame.grid_columnconfigure(1, weight=1)

        # Define priority labels
        self.priority_labels = {
            1: "Emergency also Important",
            2: "Emergency but not Important",
            3: "Important but not Emergency",
            4: "Not emergency Not Important"
        }

        # Create task boxes
        self.task_boxes = {}
        for i in range(1, 5):
            row = (i-1) // 2
            col = (i-1) % 2
            
            frame = ttk.LabelFrame(task_frame, text=self.priority_labels[i])
            frame.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
            
            listbox = tk.Listbox(frame, height=10, selectmode=tk.SINGLE)
            listbox.pack(expand=True, fill='both', padx=5, pady=5)
            
            # Enable drag and drop for each listbox
            listbox.drop_target_register(DND_FILES)
            listbox.bind('<ButtonPress-1>', self.on_drag_start)  # Left mouse button
            listbox.bind('<B1-Motion>', self.on_drag_motion)     # Left mouse button motion
            listbox.bind('<ButtonRelease-1>', self.on_drag_stop) # Left mouse button release
            
            self.task_boxes[f"Priority {i}"] = listbox

    def on_drag_start(self, event):
        widget = event.widget
        if widget.curselection():
            self.drag_data = widget.get(widget.curselection())
            self.drag_source = widget
            self.drag_source_index = widget.curselection()[0]
            widget.config(cursor="hand2")  # Change cursor to indicate dragging

    def on_drag_motion(self, event):
        event.widget.config(cursor="hand2")  # Change cursor to indicate dragging

    def on_drag_stop(self, event):
        target_listbox = event.widget
        if self.drag_data and self.drag_source != target_listbox:
            # Remove from source
            source_priority = [key for key, value in self.task_boxes.items() if value == self.drag_source][0]
            self.tasks[source_priority].remove(self.drag_data)
            self.drag_source.delete(self.drag_source_index)

            # Add to target
            target_priority = [key for key, value in self.task_boxes.items() if value == target_listbox][0]
            self.tasks[target_priority].append(self.drag_data)
            target_listbox.insert(tk.END, self.drag_data)

            # Update task count
            self.task_count = sum(len(tasks) for tasks in self.tasks.values())
            self.counter_label.config(text=f"Total Tasks: {self.task_count}")

            print(f"Dropped: {self.drag_data} to {target_priority}")
        event.widget.config(cursor="")
        self.drag_data = None
        self.drag_source = None

    def on_drop(self, event):
        # This method is required to handle the drop event
        # It can be used to finalize the drop action if needed
        pass

    def create_action_buttons(self):
        # Create frame for action buttons
        action_frame = ttk.Frame(self.root)
        action_frame.pack(pady=10, padx=10, fill='x', side='bottom')

        # Add action buttons
        ttk.Button(action_frame, text="Delete", command=self.delete_task).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Modify", command=self.modify_task).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Move Up", command=self.move_up).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Move Down", command=self.move_down).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Accomplish", command=self.accomplish_task).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Restore", command=self.restore_task).pack(side='left', padx=5)

    def add_task(self, priority):
        task = self.task_input.get().strip()
        if task:
            self.tasks[f"Priority {priority}"].append(task)
            self.task_boxes[f"Priority {priority}"].insert(tk.END, task)
            self.task_input.delete(0, tk.END)
            self.update_task_counts()  # Update counts
            # Record action for undo
            self.undo_stack.append(('add', priority, task))
            self.redo_stack.clear()  # Clear redo stack on new action

    def prompt_priority(self):
        task = self.task_input.get().strip()
        if not task:
            messagebox.showwarning("Warning", "Please enter a task before categorizing")
            return

        # Ask user for priority
        priority = simpledialog.askstring("Select Priority", "Enter priority (1-4):")
        if priority in ['1', '2', '3', '4']:
            self.add_task(int(priority))
        else:
            messagebox.showwarning("Warning", "Invalid priority. Please enter a number between 1 and 4.")

    def delete_task(self):
        try:
            selected_priority, selected_index = self.get_selected_task()
            task = self.tasks[selected_priority][selected_index]
            self.task_boxes[selected_priority].delete(selected_index)
            del self.tasks[selected_priority][selected_index]
            self.update_task_counts()  # Update counts
            # Record action for undo
            self.undo_stack.append(('delete', selected_priority, task, selected_index))
            self.redo_stack.clear()  # Clear redo stack on new action
        except (IndexError, ValueError):
            return  # Simply return if no task is selected

    def modify_task(self):
        try:
            selected_priority, selected_index = self.get_selected_task()
            old_task = self.tasks[selected_priority][selected_index]
            
            # Prompt user for new task description
            new_task = simpledialog.askstring("Modify Task", "Edit task:", initialvalue=old_task)
            
            if new_task is not None:  # Check if the dialog was not cancelled
                if new_task.strip():  # Check if the new task is not empty
                    # Update the task in the list and refresh the display
                    self.tasks[selected_priority][selected_index] = new_task.strip()
                    self.refresh_task_boxes()
                else:
                    messagebox.showwarning("Warning", "Task description cannot be empty.")
        except (IndexError, ValueError):
            messagebox.showwarning("Warning", "Please select a task to modify")

    def move_up(self):
        try:
            selected_priority, selected_index = self.get_selected_task()
            if selected_index > 0:
                task = self.tasks[selected_priority].pop(selected_index)
                self.tasks[selected_priority].insert(selected_index - 1, task)
                self.refresh_task_boxes()
                self.task_boxes[selected_priority].selection_set(selected_index - 1)
        except (IndexError, ValueError):
            messagebox.showwarning("Warning", "Please select a task to move")

    def move_down(self):
        try:
            selected_priority, selected_index = self.get_selected_task()
            if selected_index < len(self.tasks[selected_priority]) - 1:
                task = self.tasks[selected_priority].pop(selected_index)
                self.tasks[selected_priority].insert(selected_index + 1, task)
                self.refresh_task_boxes()
                self.task_boxes[selected_priority].selection_set(selected_index + 1)
        except (IndexError, ValueError):
            messagebox.showwarning("Warning", "Please select a task to move")

    def accomplish_task(self):
        try:
            selected_priority, selected_index = self.get_selected_task()
            task = self.tasks[selected_priority][selected_index]
            if not task.endswith("(Accomplished)"):
                # Mark the task as accomplished
                self.tasks[selected_priority][selected_index] += " (Accomplished)"
                
                # Move the accomplished task to the first position
                accomplished_task = self.tasks[selected_priority].pop(selected_index)
                self.tasks[selected_priority].insert(0, accomplished_task)
                
                # Refresh the task boxes to reflect changes
                self.refresh_task_boxes()
                
                # Select the newly moved task
                self.task_boxes[selected_priority].selection_set(0)
                
                self.update_task_counts()  # Update counts
        except (IndexError, ValueError):
            messagebox.showwarning("Warning", "Please select a task to accomplish")

    def restore_task(self):
        try:
            selected_priority, selected_index = self.get_selected_task()
            task = self.tasks[selected_priority][selected_index]
            if task.endswith("(Accomplished)"):
                self.tasks[selected_priority][selected_index] = task.replace(" (Accomplished)", "")
                self.refresh_task_boxes()
        except (IndexError, ValueError):
            messagebox.showwarning("Warning", "Please select a task to restore")

    def get_selected_task(self):
        for priority, listbox in self.task_boxes.items():
            if listbox.curselection():
                return priority, listbox.curselection()[0]
        raise ValueError("No task selected")

    def new_file(self):
        for priority in self.tasks:
            self.tasks[priority] = []
            self.task_boxes[priority].delete(0, tk.END)
        self.task_count = 0
        self.counter_label.config(text="Total Tasks: 0")

    def save_tasks(self):
        if self.file_path is None:
            # If no file path is set, act like 'Save As'
            self.save_as()
        else:
            # Save the tasks to the specified file path in plain text format
            with open(self.file_path, 'w') as file:
                for priority, tasks in self.tasks.items():
                    file.write(f"{priority}:\n")
                    for task in tasks:
                        file.write(f"  - {task}\n")

    def save_as(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=4)

    def open_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.tasks = json.load(f)
                self.refresh_task_boxes()

        # Open the tasks from the specified file path
        with open(file_path, 'r') as file:
            self.tasks = {}
            current_priority = None
            for line in file:
                line = line.strip()
                if line.endswith(':'):
                    current_priority = line[:-1]
                    self.tasks[current_priority] = []
                elif line.startswith('- '):
                    task = line[2:]
                    if current_priority is not None:
                        self.tasks[current_priority].append(task)
        self.refresh_task_boxes()
        self.update_task_counts()
        self.file_path = file_path  # Update the file path to the opened file

    def export_pdf(self):
        try:
            # Get current date and day for filename
            current_date = datetime.now()
            day_name = current_date.strftime("%A")
            default_filename = f"Daily report {current_date.strftime('%Y%m%d')}.pdf"

            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialfile=default_filename
            )
            if not file_path:
                return

            # Create PDF object with landscape orientation
            pdf = FPDF(orientation='L')
            pdf.add_page()
            
            # Set font to support Chinese
            pdf.add_font("DejaVu", "", "DejaVuSansCondensed.ttf", uni=True)
            
            # Add title
            pdf.set_font("DejaVu", size=16)
            title = f"Daily Report - {current_date.strftime('%Y-%m-%d')} ({day_name})"
            pdf.cell(0, 8, title, ln=True, align='C')
            pdf.ln(1)  # Minimize space after title

            # Add task counts
            pdf.set_font("DejaVu", size=10)
            task_info = f"Total Tasks: {self.task_count} | Accomplished Tasks: {self.accomplished_count}"
            pdf.cell(0, 6, task_info, ln=True, align='C')
            pdf.ln(1)  # Minimize space after task info

            # Add tasks by priority with labels
            for priority, tasks in self.tasks.items():
                # Add priority header with its label
                pdf.set_font("DejaVu", size=10)
                header = f"{priority} - {self.priority_labels[int(priority.split()[-1])]}"
                pdf.cell(0, 6, header, ln=True)
                
                # Add tasks
                pdf.set_font("DejaVu", size=8)
                if tasks:  # If there are tasks in this priority
                    for task in tasks:
                        pdf.cell(0, 5, f"- {task}", ln=True)
                else:
                    pdf.cell(0, 5, "No tasks", ln=True)
                    
                pdf.ln(1)  # Minimize space between priority sections
            
            # Save PDF
            try:
                pdf.output(file_path)
                messagebox.showinfo("Success", "PDF file has been created successfully!")
                
                # Open the PDF file automatically
                try:
                    import platform
                    if platform.system() == 'Windows':
                        os.startfile(file_path)
                    elif platform.system() == 'Darwin':  # macOS
                        os.system(f'open "{file_path}"')
                    else:  # Linux
                        os.system(f'xdg-open "{file_path}"')
                except Exception as e:
                    print(f"Warning: Could not open PDF automatically: {str(e)}")
                    
            except Exception as e:
                print(f"Error saving PDF: {str(e)}")
                messagebox.showerror("Error", f"Failed to save PDF: {str(e)}")
                
        except Exception as e:
            print(f"Error creating PDF: {str(e)}")
            messagebox.showerror("Error", f"Failed to create PDF: {str(e)}")

    def refresh_task_boxes(self):
        for priority in self.tasks:
            self.task_boxes[priority].delete(0, tk.END)
            for task in self.tasks[priority]:
                self.task_boxes[priority].insert(tk.END, task)
        self.update_task_counts()  # Update counts

    def update_task_counts(self):
        self.task_count = sum(len(tasks) for tasks in self.tasks.values())
        self.accomplished_count = sum(task.endswith("(Accomplished)") for tasks in self.tasks.values() for task in tasks)
        self.counter_label.config(text=f"Total Tasks: {self.task_count} | Accomplished Tasks: {self.accomplished_count}")

    def undo(self):
        if not self.undo_stack:
            messagebox.showinfo("Info", "Nothing to undo")
            return

        action = self.undo_stack.pop()
        if action[0] == 'add':
            priority, task = action[1], action[2]
            self.tasks[f"Priority {priority}"].remove(task)
            self.refresh_task_boxes()
            # Record action for redo
            self.redo_stack.append(('add', priority, task))
        elif action[0] == 'delete':
            priority, task, index = action[1], action[2], action[3]
            self.tasks[priority].insert(index, task)
            self.refresh_task_boxes()
            # Record action for redo
            self.redo_stack.append(('delete', priority, task, index))

    def redo(self):
        if not self.redo_stack:
            messagebox.showinfo("Info", "Nothing to redo")
            return

        action = self.redo_stack.pop()
        if action[0] == 'add':
            priority, task = action[1], action[2]
            self.tasks[f"Priority {priority}"].append(task)
            self.refresh_task_boxes()
            # Record action for undo
            self.undo_stack.append(('add', priority, task))
        elif action[0] == 'delete':
            priority, task, index = action[1], action[2], action[3]
            self.tasks[priority].remove(task)
            self.refresh_task_boxes()
            # Record action for undo
            self.undo_stack.append(('delete', priority, task, index))

    def run(self):
        self.root.mainloop()

    def show_about(self):
        messagebox.showinfo("About", "Daily Tasker\nVersion 1.0.005")

    def clear_all_accomplished(self):
        for priority, tasks in self.tasks.items():
            self.tasks[priority] = [task for task in tasks if not task.endswith("(Accomplished)")]
        self.refresh_task_boxes()
        self.update_task_counts()

if __name__ == "__main__":
    app = TaskManager()
    app.run()