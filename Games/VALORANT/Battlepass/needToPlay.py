import os
import datetime
from datetime import timezone, timedelta
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from math import ceil

def moscow_today():
    utc_now = datetime.datetime.now(timezone.utc)
    msk = utc_now + timedelta(hours=3)
    return msk.date()

def moscow_weekday():
    return moscow_today().weekday()

def parse_xp_file(filename: str):
    rows = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("("):
                continue
            if ":" in line:
                header, values_part = line.split(":", 1)
                header = header.strip()
                nums = [int(x.strip()) for x in values_part.split(",") if x.strip()]
                if nums:
                    rows.append((header, nums))
    return rows

def rows_to_flat(rows):
    flat = []
    for _, nums in rows:
        flat.extend(nums)
    return flat

def calculate(xp_flat, days_left, lvl_current, xp_lvl_current,
              days_skip, xp_weekly, count_weekly, xp_bonus,
              weekday, today_skipped):
    xp_left = sum(xp_flat) - sum(xp_flat[:lvl_current - 1]) + xp_lvl_current

    effective_days = days_left - days_skip
    if effective_days <= 0:
        return xp_left, None, None, None

    RESET_DAY = 1
    days_until_reset = (RESET_DAY - weekday) % 7
    if days_until_reset == 0:
        days_until_reset = 7

    remaining_days_after = days_left - min(days_left, days_until_reset)
    full_weeks = remaining_days_after // 7

    total_weekly = 0
    if days_left > 0:
        total_weekly += max(0, 3 - count_weekly) * xp_weekly
    for i in range(1, full_weeks + 1):
        total_weekly += 3 * (xp_weekly + 500 * i)

    xp_after_weekly = xp_left - total_weekly

    daily_needed = xp_after_weekly / effective_days
    daily_needed_no_daily = daily_needed - 4000
    daily_needed_no_daily_base = daily_needed_no_daily / (1 + xp_bonus / 100)

    return xp_left, ceil(daily_needed), ceil(daily_needed_no_daily), ceil(daily_needed_no_daily_base)


class SimpleCalendar(tk.Frame):
    MONTHS = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн",
              "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
    WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    def __init__(self, master, highlight_range=None, today_date=None,
                 on_skip_changed=None, **kwargs):
        super().__init__(master, **kwargs)
        self.today = today_date if today_date else datetime.date.today()
        self.current_year = self.today.year
        self.current_month = self.today.month
        self.highlight_range = highlight_range
        self.skipped_dates = set()
        self.on_skip_changed = on_skip_changed

        self._build_ui()
        self._draw_calendar()

    def _build_ui(self):
        top = tk.Frame(self)
        top.pack(fill=tk.X)

        tk.Button(top, text="◀", command=self._prev_month).pack(side=tk.LEFT)
        self.month_label = tk.Label(top, text="", font=("Arial", 9, "bold"))
        self.month_label.pack(side=tk.LEFT, expand=True)
        tk.Button(top, text="▶", command=self._next_month).pack(side=tk.RIGHT)

        self.grid_frame = tk.Frame(self, height=140)
        self.grid_frame.pack(pady=(5,0), fill=tk.BOTH, expand=True)
        self.grid_frame.pack_propagate(False)

    def _prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self._draw_calendar()

    def _next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self._draw_calendar()

    def _draw_calendar(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        self.month_label.config(text=f"{self.MONTHS[self.current_month-1]} {self.current_year}")

        for i, wd in enumerate(self.WEEKDAYS):
            tk.Label(self.grid_frame, text=wd, width=4, anchor=tk.CENTER,
                     font=("Arial", 7, "bold")).grid(row=0, column=i, padx=1, pady=1)

        first_day = datetime.date(self.current_year, self.current_month, 1)
        start_weekday = first_day.weekday()
        if self.current_month == 12:
            next_month_date = datetime.date(self.current_year+1, 1, 1)
        else:
            next_month_date = datetime.date(self.current_year, self.current_month+1, 1)
        last_day = next_month_date - timedelta(days=1)
        days_in_month = last_day.day

        prev_month_last = first_day - timedelta(days=1)
        days_in_prev = prev_month_last.day
        row = 1
        col = 0
        if start_weekday > 0:
            start_prev_day = days_in_prev - start_weekday + 1
            for d in range(start_prev_day, days_in_prev + 1):
                lbl = tk.Label(self.grid_frame, text=str(d), width=4,
                               bg="#D3D3D3", fg="gray", relief=tk.GROOVE)
                lbl.grid(row=row, column=col, padx=1, pady=1)
                col += 1

        for day in range(1, days_in_month + 1):
            date = datetime.date(self.current_year, self.current_month, day)
            bg = "white"
            fg = "black"
            if self.highlight_range:
                start, end = self.highlight_range
                if start <= date <= end:
                    if date in self.skipped_dates:
                        bg = "#FFA07A"
                    else:
                        bg = "#90EE90"

            lbl = tk.Label(self.grid_frame, text=str(day), width=4,
                           bg=bg, fg=fg, relief=tk.GROOVE)
            lbl.grid(row=row, column=col, padx=1, pady=1)
            if self.highlight_range and start <= date <= end:
                lbl.bind("<Button-1>", lambda e, d=date: self._toggle_skip(d))
            col += 1
            if col >= 7:
                col = 0
                row += 1

        next_day = 1
        while row <= 6:
            while col < 7:
                lbl = tk.Label(self.grid_frame, text=str(next_day), width=4,
                               bg="#D3D3D3", fg="gray", relief=tk.GROOVE)
                lbl.grid(row=row, column=col, padx=1, pady=1)
                next_day += 1
                col += 1
            col = 0
            row += 1

    def _toggle_skip(self, date):
        if date in self.skipped_dates:
            self.skipped_dates.discard(date)
        else:
            self.skipped_dates.add(date)
        self._draw_calendar()
        if self.on_skip_changed:
            self.on_skip_changed()

    def set_highlight_range(self, start_date, end_date):
        self.highlight_range = (start_date, end_date)
        self.skipped_dates = {d for d in self.skipped_dates if start_date <= d <= end_date}
        self._draw_calendar()

    def get_skipped_count(self):
        return len(self.skipped_dates)

    def is_today_skipped(self):
        return self.today in self.skipped_dates


class EditorWindow(tk.Toplevel):
    def __init__(self, master, filepath=None, initial_data=None):
        super().__init__(master)
        self.title("Таблица опыта")
        self.filepath = filepath
        self.is_new = filepath is None
        self.dirty = False

        if filepath and os.path.exists(filepath):
            self.data = parse_xp_file(filepath)
        elif initial_data is not None:
            self.data = initial_data
        else:
            self.data = [["Chapter 1", [0]]]

        self.rows = len(self.data)
        self.cols = max((len(row[1]) for row in self.data), default=1)

        self._build_ui()
        self._refresh_table()
        self._autosize_window()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())

    def _build_ui(self):
        main = tk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        toolbar = tk.Frame(main)
        toolbar.pack(fill=tk.X, pady=(0,5))
        tk.Button(toolbar, text="+ Строку", command=self._add_row).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="- Строку", command=self._del_row).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="+ Столбец", command=self._add_col).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="- Столбец", command=self._del_col).pack(side=tk.LEFT, padx=2)

        canvas = tk.Canvas(main, borderwidth=0)
        scrollbar = tk.Scrollbar(main, orient=tk.VERTICAL, command=canvas.yview)
        self.table_frame = tk.Frame(canvas)
        self.table_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=self.table_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        bottom = tk.Frame(self)
        bottom.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(bottom, text="Сохранить", command=self._save).pack(side=tk.RIGHT, padx=5)
        tk.Button(bottom, text="Закрыть", command=self._on_close).pack(side=tk.RIGHT)

    def _autosize_window(self):
        self.update_idletasks()
        col_width = 110
        header_width = 120
        width = header_width + self.cols * col_width + 40
        height = self.rows * 30 + 150
        max_w = self.winfo_screenwidth() - 100
        max_h = self.winfo_screenheight() - 150
        width = min(width, max_w)
        height = min(height, max_h)
        self.geometry(f"{width}x{height}")

    def _refresh_table(self):
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        self.entries = []
        self.header_entries = []

        for i in range(self.rows):
            hdr_var = tk.StringVar(value=self.data[i][0])
            hdr_entry = tk.Entry(self.table_frame, textvariable=hdr_var, width=15)
            hdr_entry.grid(row=i, column=0, padx=1, pady=1, sticky="ew")
            self.header_entries.append(hdr_entry)
            hdr_var.trace_add("write", lambda *a, idx=i: self._mark_dirty(idx, None))

            values = self.data[i][1]
            if len(values) < self.cols:
                values.extend([0] * (self.cols - len(values)))
            elif len(values) > self.cols:
                values = values[:self.cols]
                self.data[i][1] = values

            row_entries = []
            for j in range(self.cols):
                var = tk.StringVar(value=str(values[j]))
                ent = tk.Entry(self.table_frame, textvariable=var, width=10, justify=tk.RIGHT)
                ent.grid(row=i, column=j+1, padx=1, pady=1, sticky="ew")
                ent.bind("<Tab>", lambda e, r=i, c=j: self._tab_nav(r, c))
                ent.bind("<Shift-Tab>", lambda e, r=i, c=j: self._shift_tab_nav(r, c))
                ent.bind("<Return>", lambda e, r=i, c=j: self._enter_nav(r, c))
                ent.bind("<Shift-Return>", lambda e, r=i, c=j: self._shift_enter_nav(r, c))
                var.trace_add("write", lambda *a, r=i, c=j: self._mark_dirty(r, c))
                row_entries.append(ent)
            self.entries.append(row_entries)

        self._autosize_window()

    def _mark_dirty(self, row, col):
        self.dirty = True
        self._sync_model()

    def _sync_model(self):
        for i in range(self.rows):
            self.data[i][0] = self.header_entries[i].get()
            row_values = []
            for j in range(self.cols):
                val_str = self.entries[i][j].get().strip()
                try:
                    row_values.append(int(val_str) if val_str else 0)
                except ValueError:
                    row_values.append(0)
            self.data[i][1] = row_values

    def _tab_nav(self, r, c):
        if c < self.cols - 1:
            self.entries[r][c+1].focus_set()
        elif r < self.rows - 1:
            self.entries[r+1][0].focus_set()
        else:
            self.entries[0][0].focus_set()
        return "break"

    def _shift_tab_nav(self, r, c):
        if c > 0:
            self.entries[r][c-1].focus_set()
        elif r > 0:
            self.entries[r-1][self.cols-1].focus_set()
        else:
            self.entries[self.rows-1][self.cols-1].focus_set()
        return "break"

    def _enter_nav(self, r, c):
        if r < self.rows - 1:
            self.entries[r+1][c].focus_set()
        else:
            next_col = (c + 1) % self.cols
            self.entries[0][next_col].focus_set()
        return "break"

    def _shift_enter_nav(self, r, c):
        if r > 0:
            self.entries[r-1][c].focus_set()
        else:
            prev_col = (c - 1) % self.cols
            self.entries[self.rows-1][prev_col].focus_set()
        return "break"

    def _add_row(self):
        self._sync_model()
        self.data.append([f"Chapter {self.rows+1}", [0]*self.cols])
        self.rows += 1
        self.dirty = True
        self._refresh_table()

    def _del_row(self):
        if self.rows <= 1:
            messagebox.showwarning("Предупреждение", "Должна остаться хотя бы одна строка.")
            return
        self._sync_model()
        self.data.pop()
        self.rows -= 1
        self.dirty = True
        self._refresh_table()

    def _add_col(self):
        self._sync_model()
        for row in self.data:
            row[1].append(0)
        self.cols += 1
        self.dirty = True
        self._refresh_table()

    def _del_col(self):
        if self.cols <= 1:
            messagebox.showwarning("Предупреждение", "Должен остаться хотя бы один столбец.")
            return
        self._sync_model()
        for row in self.data:
            row[1].pop()
        self.cols -= 1
        self.dirty = True
        self._refresh_table()

    def _save(self):
        self._sync_model()
        if self.is_new:
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Сохранить файл как"
            )
            if not path:
                return
            self.filepath = path
            self.is_new = False

        with open(self.filepath, "w", encoding="utf-8") as f:
            for header, nums in self.data:
                nums_str = ", ".join(str(n) for n in nums)
                f.write(f"{header}: {nums_str},\n")
        self.dirty = False
        messagebox.showinfo("Сохранено", "Файл сохранён.")
        self.master._reload_table(self.filepath)
        self.destroy()

    def _on_close(self):
        if self.dirty:
            ans = messagebox.askyesnocancel(
                "Сохранить изменения?",
                "Есть несохранённые изменения. Сохранить перед закрытием?"
            )
            if ans is None:
                return
            if ans:
                self._save()
                return
            else:
                if self.is_new and self.filepath:
                    try:
                        os.remove(self.filepath)
                    except OSError:
                        pass
        else:
            if self.is_new and self.filepath and os.path.exists(self.filepath):
                try:
                    os.remove(self.filepath)
                except OSError:
                    pass
        self.master._reload_table(None)
        self.destroy()


class AddGameDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Игра")
        self.result = None

        tk.Label(self, text="Режим:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.mode_var = tk.StringVar(value="Быстрая игра")
        mode_menu = ttk.Combobox(self, textvariable=self.mode_var,
                                 values=["Быстрая игра", "Установка спайка"],
                                 state="readonly")
        mode_menu.grid(row=0, column=1, padx=5, pady=5)
        mode_menu.bind("<<ComboboxSelected>>", self._on_mode_change)

        self.score_frame = tk.Frame(self)
        self.score_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        tk.Label(self, text="Бонус опыта (%):").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.bonus_var = tk.StringVar(value="0")
        tk.Entry(self, textvariable=self.bonus_var, width=8).grid(row=2, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Добавить", command=self._add).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=self.destroy).pack(side=tk.LEFT, padx=5)

        self._on_mode_change()
        self.grab_set()
        self.wait_window()

    def _on_mode_change(self, event=None):
        for widget in self.score_frame.winfo_children():
            widget.destroy()

        mode = self.mode_var.get()
        if mode == "Быстрая игра":
            tk.Label(self.score_frame, text="Выиграно раундов:").grid(row=0, column=0, padx=2)
            self.win_var = tk.StringVar(value="0")
            tk.Entry(self.score_frame, textvariable=self.win_var, width=5).grid(row=0, column=1, padx=2)
            tk.Label(self.score_frame, text="Проиграно раундов:").grid(row=0, column=2, padx=2)
            self.lose_var = tk.StringVar(value="0")
            tk.Entry(self.score_frame, textvariable=self.lose_var, width=5).grid(row=0, column=3, padx=2)
        else:
            tk.Label(self.score_frame, text="Исход игры:").grid(row=0, column=0, padx=2)
            self.spike_win_var = tk.BooleanVar(value=True)
            tk.Radiobutton(self.score_frame, text="Победа", variable=self.spike_win_var, value=True).grid(row=0, column=1)
            tk.Radiobutton(self.score_frame, text="Поражение", variable=self.spike_win_var, value=False).grid(row=0, column=2)

    def _add(self):
        mode = self.mode_var.get()
        try:
            bonus = int(self.bonus_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректный бонус опыта")
            return

        if mode == "Быстрая игра":
            try:
                wins = int(self.win_var.get())
                losses = int(self.lose_var.get())
            except ValueError:
                messagebox.showerror("Ошибка", "Введите целые числа для счёта")
                return
            if wins < 0 or losses < 0:
                messagebox.showerror("Ошибка", "Счёт не может быть отрицательным")
                return
            base_xp = 300 * wins + 100 * losses
            score_str = f"{wins}-{losses}"
        else:
            win = self.spike_win_var.get()
            base_xp = 1000
            score_str = "Победа" if win else "Поражение"

        total_xp = int(base_xp * (1 + bonus / 100))
        self.result = {
            "mode": mode,
            "score": score_str,
            "bonus": bonus,
            "xp": total_xp
        }
        self.destroy()


class GamesListWindow(tk.Toplevel):
    def __init__(self, master, games_list):
        super().__init__(master)
        self.title("Список игр")
        self.games_list = games_list

        self._build_ui()
        self._refresh_list()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self):
        columns = ("mode", "score", "bonus", "xp")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("mode", text="Режим")
        self.tree.heading("score", text="Счёт")
        self.tree.heading("bonus", text="Бонус (%)")
        self.tree.heading("xp", text="Опыт")
        self.tree.column("mode", width=120)
        self.tree.column("score", width=80)
        self.tree.column("bonus", width=80)
        self.tree.column("xp", width=80)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Добавить игру", command=self._add_game).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Удалить игру", command=self._delete_game).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Подвести итоги дня", command=self._daily_summary).pack(side=tk.LEFT, padx=2)

    def _refresh_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for game in self.games_list:
            self.tree.insert("", tk.END, values=(game["mode"], game["score"], game["bonus"], game["xp"]))

    def _add_game(self):
        dialog = AddGameDialog(self)
        if dialog.result:
            self.games_list.append(dialog.result)
            self._refresh_list()

    def _delete_game(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Не выбрано", "Выберите игру для удаления")
            return
        index = self.tree.index(selected[0])
        del self.games_list[index]
        self._refresh_list()

    def _daily_summary(self):
        total_xp = sum(game["xp"] for game in self.games_list)
        games_count = len(self.games_list)
        top = tk.Toplevel(self)
        top.title("Итоги дня")
        msg = f"Сыграно игр: {games_count}\nВсего получено опыта: {total_xp} XP"
        tk.Label(top, text=msg, font=("Arial", 12), padx=20, pady=20).pack()
        tk.Button(top, text="OK", command=top.destroy).pack(pady=5)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Боевой пропуск")
        self.geometry("1050x680")
        self.minsize(950, 600)

        self.xp_file = None
        self.xp_rows = []
        self.xp_flat = []
        self.selected_level = 1
        self._updating_xp_lvl = False
        self.games_list = []

        self._build_ui()
        self._bind_recalc()

        default_path = os.path.join(os.path.dirname(__file__), "_experiences_bp.txt")
        if os.path.exists(default_path):
            self._load_file(default_path)
        else:
            self._load_file(None)

        self._recalc()


    def _build_ui(self):
        self.main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                                        sashrelief=tk.RAISED, sashwidth=5)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # Левая панель – таблица уровней и кнопки
        left_frame = tk.Frame(self.main_pane)
        self.main_pane.add(left_frame, minsize=200)

        file_buttons = tk.Frame(left_frame)
        file_buttons.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(file_buttons, text="Открыть", command=self._open_file).pack(side=tk.LEFT, padx=2)
        tk.Button(file_buttons, text="Создать", command=self._create_file).pack(side=tk.LEFT, padx=2)
        tk.Button(file_buttons, text="Изменить", command=self._edit_file).pack(side=tk.LEFT, padx=2)

        self.table_canvas = tk.Canvas(left_frame)
        table_scroll = tk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.table_canvas.yview)
        self.table_canvas.configure(yscrollcommand=table_scroll.set)

        self.table_inner = tk.Frame(self.table_canvas)
        self.table_inner.bind("<Configure>", lambda e: self.table_canvas.configure(
            scrollregion=self.table_canvas.bbox("all")))
        self.table_canvas.create_window((0,0), window=self.table_inner, anchor=tk.NW)

        self.table_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        table_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Центральная панель – параметры
        center_frame = tk.Frame(self.main_pane)
        self.main_pane.add(center_frame, minsize=250)

        param_frame = tk.LabelFrame(center_frame, text="Параметры расчёта")
        param_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._add_param(param_frame, "Осталось дней:", "days_left", 0, 100, 1)
        self._add_param(param_frame, "Опыт за еженед. задание:", "xp_weekly", 0, 5000, 2000, show_scale=False)
        self._add_param(param_frame, "Выполнено еженед. заданий:", "count_weekly", 0, 3, 0)
        self._add_param(param_frame, "Бонус опыта (%):", "xp_bonus", 0, 50, 0)

        lvl_frame = tk.Frame(param_frame)
        lvl_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(lvl_frame, text="Уровень:").pack(side=tk.LEFT)
        self.lvl_var = tk.StringVar(value="1")
        tk.Entry(lvl_frame, textvariable=self.lvl_var, width=5).pack(side=tk.LEFT, padx=5)

        xp_frame = tk.Frame(param_frame)
        xp_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(xp_frame, text="Опыт на уровне:").pack(side=tk.LEFT)
        self.xp_lvl_var = tk.StringVar(value="0")
        xp_entry = tk.Entry(xp_frame, textvariable=self.xp_lvl_var, width=8)
        xp_entry.pack(side=tk.LEFT, padx=5)
        xp_entry.bind("<Return>", self._on_xp_lvl_done)
        xp_entry.bind("<FocusOut>", self._on_xp_lvl_done)

        self.xp_lvl_scale = tk.Scale(xp_frame, from_=0, to=1000, orient=tk.HORIZONTAL,
                                     showvalue=False, length=120,
                                     command=self._on_scale_move)
        self.xp_lvl_scale.pack(side=tk.LEFT, padx=5)

        self.xp_lvl_var.trace_add("write", self._sync_xp_scale)

        # Правая панель – календарь и результаты
        right_frame = tk.Frame(self.main_pane)
        self.main_pane.add(right_frame, minsize=300)

        cal_frame = tk.LabelFrame(right_frame, text="Календарь")
        cal_frame.pack(fill=tk.BOTH, padx=5, pady=(5,0))
        self.calendar = SimpleCalendar(cal_frame, today_date=moscow_today(),
                                       on_skip_changed=self._recalc)
        self.calendar.pack(fill=tk.BOTH, expand=True)

        res_frame = tk.LabelFrame(right_frame, text="Результаты")
        res_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.xp_left_var = tk.StringVar()
        self.daily_needed_var = tk.StringVar()
        self.daily_no_daily_var = tk.StringVar()
        self.daily_base_var = tk.StringVar()
        self.opt1_var = tk.StringVar()
        self.opt2_var = tk.StringVar()
        self.opt3_var = tk.StringVar()

        labels = [
            ("Осталось получить XP:", self.xp_left_var),
            ("Ежедневно XP (всего):", self.daily_needed_var),
            ("Ежедневно XP (сверх ежедн.):", self.daily_no_daily_var),
            ("Ежедневно XP (без бонуса):", self.daily_base_var),
            ("Вариант 1 (без побед):", self.opt1_var),
            ("Вариант 2 (победы):", self.opt2_var),
            ("Вариант 3 (спайк):", self.opt3_var),
        ]
        for text, var in labels:
            row = tk.Frame(res_frame)
            row.pack(fill=tk.X, padx=5, pady=2)
            tk.Label(row, text=text, anchor=tk.W).pack(side=tk.LEFT)
            ent = tk.Entry(row, textvariable=var, state="readonly", width=20)
            ent.pack(side=tk.RIGHT)

        tk.Button(right_frame, text="Список игр", command=self.open_games_list).pack(pady=5)

    def _add_param(self, parent, label, attr, from_, to, default, show_scale=True):
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(frame, text=label, width=25, anchor=tk.W).pack(side=tk.LEFT)

        var = tk.StringVar(value=str(default))
        setattr(self, attr + "_var", var)

        ent = tk.Entry(frame, textvariable=var, width=6)
        ent.pack(side=tk.LEFT, padx=5)

        if show_scale:
            scale = tk.Scale(frame, from_=from_, to=to, orient=tk.HORIZONTAL,
                             variable=var, showvalue=False, length=120)
            scale.pack(side=tk.LEFT, padx=5)

    def _bind_recalc(self):
        for attr in ["days_left", "xp_weekly", "count_weekly", "xp_bonus", "lvl", "xp_lvl"]:
            var = getattr(self, attr + "_var", None)
            if var:
                var.trace_add("write", lambda *a: self._recalc())

    def _on_scale_move(self, val):
        if self._updating_xp_lvl:
            return
        self._updating_xp_lvl = True
        self.xp_lvl_var.set(str(int(float(val))))
        self._updating_xp_lvl = False

    def _sync_xp_scale(self, *args):
        if self._updating_xp_lvl:
            return
        s = self.xp_lvl_var.get().strip()
        try:
            val = int(s)
        except ValueError:
            val = 0
        if val >= 0:
            self.xp_lvl_scale.set(val)
        else:
            self.xp_lvl_scale.set(0)

    def _on_xp_lvl_done(self, event=None):
        s = self.xp_lvl_var.get().strip()
        if not s:
            self.xp_lvl_var.set("0")
            return
        try:
            val = int(s)
        except ValueError:
            self.xp_lvl_var.set("0")
            return

        lvl = int(self.lvl_var.get() or 1)
        if 1 <= lvl <= len(self.xp_flat):
            max_xp = self.xp_flat[lvl-1]
        else:
            max_xp = 0

        if val < 0:
            obtained = max(0, max_xp + val)
            self._updating_xp_lvl = True
            self.xp_lvl_var.set(str(obtained))
            self._updating_xp_lvl = False
        elif val > max_xp:
            self._updating_xp_lvl = True
            self.xp_lvl_var.set(str(max_xp))
            self._updating_xp_lvl = False

    def _load_file(self, path):
        if path and os.path.exists(path):
            self.xp_file = path
            self.xp_rows = parse_xp_file(path)
            self.xp_flat = rows_to_flat(self.xp_rows)
        else:
            self.xp_file = None
            self.xp_rows = []
            self.xp_flat = []
        self._redraw_table()
        self._apply_initial_sash()
        self._recalc()

    def _reload_table(self, path=None):
        if path:
            self._load_file(path)
        else:
            if self.xp_file and os.path.exists(self.xp_file):
                self._load_file(self.xp_file)
            else:
                self._load_file(None)

    def _redraw_table(self):
        for w in self.table_inner.winfo_children():
            w.destroy()

        if not self.xp_rows:
            tk.Label(self.table_inner, text="Файл не загружен").pack()
            return

        level_counter = 1
        self.level_widgets = {}

        for i, (header, nums) in enumerate(self.xp_rows):
            tk.Label(self.table_inner, text=header, anchor=tk.W,
                     relief=tk.GROOVE, width=12).grid(row=i, column=0, padx=1, pady=1, sticky="ew")
            for j in range(len(nums)):
                lvl = level_counter
                lbl = tk.Label(self.table_inner, text=str(lvl), relief=tk.GROOVE,
                               width=6, bg="white")
                lbl.grid(row=i, column=j + 1, padx=1, pady=1)
                lbl.bind("<Button-1>", lambda e, l=lvl: self._select_level(l))
                self.level_widgets[lvl] = lbl
                level_counter += 1

        self._highlight_level(self.selected_level)

    def _select_level(self, level):
        self.selected_level = level
        self.lvl_var.set(str(level))
        self._highlight_level(level)
        self._recalc()

    def _highlight_level(self, level):
        for lvl, w in self.level_widgets.items():
            if lvl == level:
                w.configure(bg="#ADD8E6")
            else:
                w.configure(bg="white")

    def _apply_initial_sash(self):
        self.update_idletasks()
        req_width = self.table_inner.winfo_reqwidth()
        if req_width <= 342:
            sash0 = 352
        else:
            sash0 = req_width + 30
        sash1 = 719
        self.main_pane.sash_place(0, sash0, 0)
        self.main_pane.sash_place(1, sash1, 0)

    def _open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Выберите файл с опытом"
        )
        if path:
            self._load_file(path)

    def _create_file(self):
        EditorWindow(self, filepath=None, initial_data=[["Chapter 1", [0]]])

    def _edit_file(self):
        if not self.xp_file or not os.path.exists(self.xp_file):
            messagebox.showwarning("Нет файла", "Сначала откройте или создайте файл.")
            return
        EditorWindow(self, filepath=self.xp_file)

    def _recalc(self, *args):
        if not self.xp_flat:
            for var in [self.xp_left_var, self.daily_needed_var, self.daily_no_daily_var,
                        self.daily_base_var, self.opt1_var, self.opt2_var, self.opt3_var]:
                var.set("–")
            return

        def get_int(var, default=0):
            s = var.get().strip()
            return int(s) if s else default

        days_left = get_int(self.days_left_var)
        days_skip = self.calendar.get_skipped_count()
        today_skipped = self.calendar.is_today_skipped()

        xp_weekly = get_int(self.xp_weekly_var)
        count_weekly = get_int(self.count_weekly_var)
        xp_bonus = get_int(self.xp_bonus_var)
        lvl = get_int(self.lvl_var, 1)
        xp_lvl = get_int(self.xp_lvl_var)
        if xp_lvl < 0:
            xp_lvl = 0

        weekday = moscow_weekday()

        if lvl < 1: lvl = 1
        if lvl > len(self.xp_flat): lvl = len(self.xp_flat)
        self.selected_level = lvl
        self._highlight_level(lvl)

        max_xp = self.xp_flat[lvl-1] if self.xp_flat else 1000
        self.xp_lvl_scale.configure(to=max_xp)
        if xp_lvl > max_xp:
            self.xp_lvl_var.set(str(max_xp))
            xp_lvl = max_xp

        xp_left, daily_needed, daily_no_daily, daily_base = calculate(
            self.xp_flat, days_left, lvl, xp_lvl,
            days_skip, xp_weekly, count_weekly, xp_bonus,
            weekday, today_skipped
        )

        if daily_needed is None:
            self.xp_left_var.set(str(xp_left))
            for v in [self.daily_needed_var, self.daily_no_daily_var, self.daily_base_var,
                      self.opt1_var, self.opt2_var, self.opt3_var]:
                v.set("Невозможно (0 дней)")
        else:
            self.xp_left_var.set(str(xp_left))
            self.daily_needed_var.set(str(daily_needed))
            self.daily_no_daily_var.set(str(daily_no_daily))
            self.daily_base_var.set(str(daily_base))

            raunds1 = ceil(daily_needed / 100)
            games1 = ceil(raunds1 / 5)
            self.opt1_var.set(f"{raunds1} раундов (~{games1} игр)")

            raunds2 = max(ceil(daily_base / 200), 16)
            games2 = ceil(raunds2 / 5)
            self.opt2_var.set(f"{raunds2} раундов (~{games2} игр)")

            games3 = max(ceil(daily_base / 1000), 8)
            self.opt3_var.set(f"{games3} игр")

        today = moscow_today()
        end = today + timedelta(days=max(0, days_left-1))
        self.calendar.set_highlight_range(today, end)

    def open_games_list(self):
        GamesListWindow(self, self.games_list)


if __name__ == "__main__":
    app = App()
    app.mainloop()
