// Simple To-Do list using localStorage.
// Features: add, edit, toggle complete, delete, filters, export/import JSON, clear completed.
// Storage key:
const STORAGE_KEY = "todo.tasks.v1";

const taskForm = document.getElementById("task-form");
const taskInput = document.getElementById("task-input");
const listEl = document.getElementById("task-list");
const countEl = document.getElementById("count");
const filters = document.querySelectorAll(".filter");
const emptyEl = document.getElementById("empty");
const clearCompletedBtn = document.getElementById("clear-completed");
const exportBtn = document.getElementById("export-btn");
const importFile = document.getElementById("import-file");

let tasks = [];
let filter = "all";

function uid() {
  if (crypto && crypto.randomUUID) return crypto.randomUUID();
  return String(Date.now()) + "-" + Math.floor(Math.random()*100000);
}

function loadTasks() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    tasks = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(tasks)) tasks = [];
  } catch (e) {
    tasks = [];
  }
}

function saveTasks() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
}

function render() {
  listEl.innerHTML = "";
  const visible = tasks.filter(t => {
    if (filter === "active") return !t.completed;
    if (filter === "completed") return t.completed;
    return true;
  });

  if (visible.length === 0) {
    emptyEl.style.display = "block";
  } else {
    emptyEl.style.display = "none";
  }

  for (const t of visible) {
    const li = document.createElement("li");
    li.className = "task-item";
    li.dataset.id = t.id;

    const chk = document.createElement("button");
    chk.className = "task-checkbox" + (t.completed ? " checked" : "");
    chk.setAttribute("aria-pressed", String(t.completed));
    chk.title = t.completed ? "Mark active" : "Mark completed";
    chk.innerHTML = t.completed ? "✓" : "";
    chk.addEventListener("click", () => toggleComplete(t.id));

    const txt = document.createElement("div");
    txt.className = "task-text" + (t.completed ? " completed" : "");
    txt.textContent = t.text;
    txt.title = "Double click to edit";
    txt.addEventListener("dblclick", () => startEdit(t.id, li));

    const meta = document.createElement("div");
    meta.className = "task-meta";

    const editBtn = document.createElement("button");
    editBtn.className = "icon-btn";
    editBtn.title = "Edit";
    editBtn.innerHTML = "✎";
    editBtn.addEventListener("click", () => startEdit(t.id, li));

    const delBtn = document.createElement("button");
    delBtn.className = "icon-btn";
    delBtn.title = "Delete";
    delBtn.innerHTML = "🗑";
    delBtn.addEventListener("click", () => deleteTask(t.id));

    meta.appendChild(editBtn);
    meta.appendChild(delBtn);

    li.appendChild(chk);
    li.appendChild(txt);
    li.appendChild(meta);
    listEl.appendChild(li);
  }

  countEl.textContent = `${tasks.filter(t=>!t.completed).length} item(s) left`;
}

function addTask(text) {
  const t = {
    id: uid(),
    text: text.trim(),
    completed: false,
    createdAt: new Date().toISOString()
  };
  if (!t.text) return;
  tasks.unshift(t); // new on top
  saveTasks();
  render();
}

function startEdit(id, liEl) {
  const t = tasks.find(x => x.id === id);
  if (!t) return;
  // Replace text element with input
  liEl.querySelectorAll(".task-text, .edit-input").forEach(n => n.remove());
  const input = document.createElement("input");
  input.className = "edit-input";
  input.type = "text";
  input.value = t.text;
  input.setAttribute("aria-label", "Edit task");
  // Save on blur or Enter, cancel on Escape
  const finish = () => {
    const v = input.value.trim();
    if (v) {
      t.text = v;
      t.updatedAt = new Date().toISOString();
      saveTasks();
    }
    render();
  };
  input.addEventListener("blur", finish);
  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") { input.blur(); }
    if (ev.key === "Escape") { render(); }
  });
  // Insert input between checkbox and meta
  const chk = liEl.querySelector(".task-checkbox");
  liEl.insertBefore(input, liEl.querySelector(".task-meta"));
  input.focus();
  // select text
  input.setSelectionRange(0, input.value.length);
}

function toggleComplete(id) {
  const t = tasks.find(x => x.id === id);
  if (!t) return;
  t.completed = !t.completed;
  t.updatedAt = new Date().toISOString();
  saveTasks();
  render();
}

function deleteTask(id) {
  tasks = tasks.filter(x => x.id !== id);
  saveTasks();
  render();
}

function clearCompleted() {
  tasks = tasks.filter(t => !t.completed);
  saveTasks();
  render();
}

function setFilter(f) {
  filter = f;
  filters.forEach(btn=>{
    const is = btn.dataset.filter === f;
    btn.classList.toggle("active", is);
    btn.setAttribute("aria-selected", String(is));
  });
  render();
}

function exportTasks() {
  const data = JSON.stringify(tasks, null, 2);
  const blob = new Blob([data], {type: "application/json"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `todo-export-${new Date().toISOString().slice(0,19).replace(/[:T]/g,"-")}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function importTasksFile(file) {
  const reader = new FileReader();
  reader.onload = (ev) => {
    try {
      const parsed = JSON.parse(ev.target.result);
      if (!Array.isArray(parsed)) throw new Error("Invalid format");
      // Merge: preserve existing IDs, append new ones for any missing id
      const normalized = parsed.map(p=>{
        return {
          id: p.id || uid(),
          text: String(p.text || "").trim(),
          completed: !!p.completed,
          createdAt: p.createdAt || new Date().toISOString(),
          updatedAt: p.updatedAt || null
        };
      }).filter(t=>t.text);
      // Prepend imported items so they appear on top
      tasks = normalized.concat(tasks);
      saveTasks();
      render();
      alert("Import successful");
    } catch (err) {
      alert("Failed to import: " + err.message);
    }
  };
  reader.readAsText(file);
}

/* Event bindings */
document.addEventListener("DOMContentLoaded", () => {
  loadTasks();
  render();

  taskForm.addEventListener("submit", (ev) => {
    ev.preventDefault();
    addTask(taskInput.value);
    taskInput.value = "";
    taskInput.focus();
  });

  filters.forEach(btn => {
    btn.addEventListener("click", () => setFilter(btn.dataset.filter));
  });

  clearCompletedBtn.addEventListener("click", () => {
    if (confirm("Remove all completed tasks?")) clearCompleted();
  });

  exportBtn.addEventListener("click", () => exportTasks());

  importFile.addEventListener("change", (ev) => {
    const f = ev.target.files && ev.target.files[0];
    if (f) importTasksFile(f);
    // reset so same file can be selected again
    importFile.value = "";
  });

  // keyboard shortcut: "n" to focus new task input
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "n" && document.activeElement.tagName.toLowerCase() !== "input" ) {
      taskInput.focus();
      ev.preventDefault();
    }
  });
});