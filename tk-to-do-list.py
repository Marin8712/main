import tkinter as tk
from tkinter import messagebox
import json

def to_do_list():
    window = tk.Tk()
    window.title("To-Do List")
    window.geometry("400x400")
    window.configure(bg="#f0f0f0")
   
    task_entry = tk.Entry(window, font=("Arial", 14), width=30)
    task_entry.pack(pady=20)
    
    task_listbox = tk.Listbox(window, font=("Arial", 14), width=30, height=10)
    task_listbox.pack(pady=10)

    def add_task():
        task = task_entry.get()
        if task:
            task_listbox.insert(tk.END, task)
            task_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Warning", "Please enter a task.")

    def delete_task():
        selected_tasks = task_listbox.curselection()
        for index in reversed(selected_tasks):
            task_listbox.delete(index)
    
    add_button = tk.Button(window, text="Add Task", command=add_task, font=("Arial", 12), bg="#4CAF50", fg="white")
    add_button.pack(pady=5)
    
    delete_button = tk.Button(window, text="Delete Task", command=delete_task, font=("Arial", 12), bg="#f44336", fg="white")
    delete_button.pack(pady=5)

    def save_tasks():
        tasks = task_listbox.get(0, tk.END)
        with open("tasks.json", "w") as file:
            json.dump(tasks, file)
        messagebox.showinfo("Saved", "Tasks saved to tasks.json")

    save_button = tk.Button(window, text="Save Tasks", command=save_tasks, font=("Arial", 12), bg="#2196F3", fg="white")
    save_button.pack(pady=5)

    def load_tasks():
        try:
            with open("tasks.json", "r") as file:
                tasks = json.load(file)
                task_listbox.delete(0, tk.END)
                for task in tasks:
                    task_listbox.insert(tk.END, task)
            messagebox.showinfo("Loaded", "Tasks loaded from tasks.json")
        except FileNotFoundError:
            messagebox.showerror("Error", "No saved tasks found.")

    load_button = tk.Button(window, text="Load Tasks", command=load_tasks, font=("Arial", 12), bg="#FF9800", fg="white")
    load_button.pack(pady=5)

    window.mainloop()

to_do_list()
