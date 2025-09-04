# Copyright (c) 2025 [Grant]
# Licensed under the MIT License.
# See LICENSE in the project root for license information.import numpy as np

import matplotlib.pyplot as plt

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

import matplotlib.patches as mpatches

import numpy as np

import tkinter as tk

from tkinter import ttk, filedialog, messagebox

import json

from datetime import datetime

class MicrochannelTool:
    # ───────────────────────────── 初始化 ─────────────────────────────

    def __init__(self, master):
        self.master = master

        master.title("微通道几何建模工具")
        master.geometry("1100x700")
        copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 
                             fg="#555555", bg="#f0f0f0")
        copyright_label.pack(side=tk.BOTTOM, fill=tk.X)
        # 可输入的纯数值参数（单位 mm）
        self.params = {
            "Radius_1":    tk.StringVar(value="0.36"),
            "Distance_r1": tk.StringVar(value="2.5"),
            "Length_v2":   tk.StringVar(value="3"),
            "Width_r1":    tk.StringVar(value="0.2"),
            "Width_Or":    tk.StringVar(value="0.1"),
            "Length_Or":   tk.StringVar(value="0.1"),
            "Width_Out":   tk.StringVar(value="0.2"),
            "Length_Out":  tk.StringVar(value="0.3"),
            "Length_r2":   tk.StringVar(value="5"),
        }
        # 计算参数（不显示）
        self.calc_params = ["Distance_1"]

        self.defaults = {k: float(v.get()) if v.get() else 0.0

                         for k, v in self.params.items()}
        self.descriptions = {
            "Radius_1":    "打孔流道半径 Radius_1 (mm)",
            "Distance_r1": "流道到中间流阻管距离 Distance_r1 (mm)",
            "Length_v2":   "中间流道长度 Length_v2 (mm)",
            "Width_r1":    "中间流道宽度 Width_r1 (mm)",
            "Width_Or":    "缩口内径 Width_Or (mm)",
            "Length_Or":   "缩口长度 Length_Or (mm)",
            "Width_Out":   "流阻管宽度 Width_Out (mm)",
            "Length_Out":  "缩口出口过渡横向长 Length_Out (mm)",
            "Length_r2":   "左侧流道长度 Length_r2 (mm)",
        }
        self.editable_params = list(self.params)

        # 其它界面变量

        self.bigFont = ('Helvetica', 12)
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.geoPatch = {k: [] for k in self.params}
        self.stsVar = tk.StringVar(value="就绪 / Ready")
        self.curHlt = None

        self.entries = {}

        # UI

        self.setupUi()
        master.protocol("WM_DELETE_WINDOW", self.quitApplication)
        self.updateModel()

    # ────────────────────────────── UI ──────────────────────────────

    def setupUi(self):
        paramFrm = ttk.Frame(self.master)
        paramFrm.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y, expand=True)

        paramBox = ttk.LabelFrame(paramFrm, text="参数 / Parameters")
        paramBox.pack(fill=tk.BOTH, expand=True, pady=10)

        canvas = tk.Canvas(paramBox, width=330)
        scrollbar = ttk.Scrollbar(paramBox, orient="vertical",
                                  command=canvas.yview)
        self.scroll_content = ttk.Frame(canvas)
        self.scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_content,
                             anchor="nw", width=330)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.create_parameter_entries()

        btnFrm = ttk.Frame(paramFrm)
        btnFrm.pack(fill=tk.X, pady=15)
        buttons = [
            ("更新模型 / Update Model", self.updateModel),
            ("导出DXF / Export DXF", self.exportDxf),
            ("导出SVG / Export SVG", self.exportSvg),
            ("导出JSON / Export JSON", self.exportJson),
            ("导入JSON / Import JSON", self.importJson),
        ]
        for text, cmd in buttons:
            ttk.Button(btnFrm, text=text, command=cmd,
                       padding=(10, 5)).pack(fill=tk.X, pady=5)

        plotFrm = ttk.Frame(self.master)
        plotFrm.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True,
                     padx=10, pady=10)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plotFrm)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        tbarFrame = ttk.Frame(plotFrm)
        tbarFrame.pack(side=tk.BOTTOM, fill=tk.X)
        NavigationToolbar2Tk(self.canvas, tbarFrame).update()

        status = ttk.Label(self.master, textvariable=self.stsVar,
                           relief=tk.SUNKEN, anchor=tk.W, font=self.bigFont)
        status.pack(side=tk.BOTTOM, fill=tk.X)

    def create_parameter_entries(self):
        for w in self.scroll_content.winfo_children():
            w.destroy()
        for p in self.editable_params:
            frame = ttk.Frame(self.scroll_content)
            frame.pack(fill=tk.X, pady=8, padx=5)
            ttk.Label(frame, text=self.descriptions[p], font=self.bigFont,
                      wraplength=330).pack(anchor=tk.W, pady=(0, 5))
            ent = ttk.Entry(frame, textvariable=self.params[p],
                            font=self.bigFont)
            ent.pack(fill=tk.X)
            ent.bind("<Return>", lambda e, x=p: self.parameter_changed(x))
            ent.bind("<FocusOut>", lambda e, x=p: self.parameter_changed(x))
            ent.bind("<FocusIn>", lambda e, x=p: self.highlightComponent(x))
            self.entries[p] = ent

    # ────────────────────────── 参数读写 ────────────────────────────

    def parameter_changed(self, p):
        try:
            float(self.params[p].get())
            self.updateModel()
        except ValueError:
            self.params[p].set(str(self.defaults[p]))
            messagebox.showerror("错误 / Error", "无效数值 / Invalid number")

    def getParam(self, name):
        if name in self.params:
            return float(self.params[name].get())
        elif name == "Distance_1":
            R, W = self.getParam("Radius_1"), self.getParam("Width_r1")
            val = R**2 - (W**2)/4

            if val < 0:
                raise ValueError("Radius_1 必须大于 Width_r1/2")
            return R - np.sqrt(val)
        return 0.0

    # ─────────────────────────── 高亮 ────────────────────────────

    def highlightComponent(self, key):
        self.curHlt = key

        # 先洗成蓝色

        for patches in self.geoPatch.values():
            for p in patches:
                if hasattr(p, 'set_edgecolor'):
                    p.set_edgecolor('blue')
                elif hasattr(p, 'set_color'):
                    p.set_color('blue')
        # 再染红

        if key in self.geoPatch:
            for p in self.geoPatch[key]:
                if hasattr(p, 'set_edgecolor'):
                    p.set_edgecolor('red')
                elif hasattr(p, 'set_color'):
                    p.set_color('red')
        self.canvas.draw()
        self.stsVar.set(f"已选择 / Selected: {key}")

    # ────────────────────── 几何计算（核心改动） ─────────────────────

    def calculateGeometry(self):
        # 取参数

        R1 = self.getParam("Radius_1")
        Dr1 = self.getParam("Distance_r1")
        Lv2 = self.getParam("Length_v2")
        Wr1 = self.getParam("Width_r1")
        WOr = self.getParam("Width_Or")
        LOr = self.getParam("Length_Or")
        WOut = self.getParam("Width_Out")
        LOut = self.getParam("Length_Out")
        Lr2 = self.getParam("Length_r2")
        D1 = self.getParam("Distance_1")

        # ─────────── 圆 ───────────

        circles = [
            ((0, 0), R1),
            ((2*R1 + Dr1 + Wr1 + LOr + LOut + Lr2, 0), R1),
            ((0, -Lv2/2 + Wr1/2), R1),
            ((0,  Lv2/2 - Wr1/2), R1),
        ]

        # 辅助函数

        seg = lambda x1, y1, x2, y2: ((x1, y1), (x2, y2))

        # ─────────── 线段 (20) ───────────

        segments = [
            seg(R1+Dr1,             -Wr1/2,      R1-D1,               -Wr1/2),   #1

            seg(R1+Dr1,              Wr1/2,      R1-D1,                Wr1/2),   #2

            seg(R1+Dr1,             -Wr1/2,      R1+Dr1,         -Lv2/2+Wr1),    #3

            seg(R1+Dr1,              Wr1/2,      R1+Dr1,          Lv2/2-Wr1),    #4

            seg(R1+Dr1+Wr1,        -WOr/2,       R1+Dr1+Wr1,       -Lv2/2),      #5

            seg(R1+Dr1+Wr1,         WOr/2,       R1+Dr1+Wr1,        Lv2/2),      #6

            seg(R1+Dr1+Wr1,         Lv2/2,       R1-D1,              Lv2/2),     #7

            seg(R1+Dr1+Wr1,        -Lv2/2,       R1-D1,             -Lv2/2),     #8

            seg(R1+Dr1,             Lv2/2-Wr1,   R1-D1,              Lv2/2-Wr1), #9

            seg(R1+Dr1,            -Lv2/2+Wr1,   R1-D1,             -Lv2/2+Wr1), #10

            seg(R1+Dr1+Wr1,        -WOr/2,       R1+Dr1+Wr1+LOr,    -WOr/2),     #15

            seg(R1+Dr1+Wr1,         WOr/2,       R1+Dr1+Wr1+LOr,     WOr/2),     #16

            seg(R1+Dr1+Wr1+LOr,    -WOr/2,       R1+Dr1+Wr1+LOr+LOut, -WOut/2),  #17

            seg(R1+Dr1+Wr1+LOr,     WOr/2,       R1+Dr1+Wr1+LOr+LOut,  WOut/2),  #18

            seg(R1+Dr1+Wr1+LOr+LOut+Lr2+D1,  WOut/2,
                R1+Dr1+Wr1+LOr+LOut,          WOut/2),                         #19

            seg(R1+Dr1+Wr1+LOr+LOut+Lr2+D1, -WOut/2,
                R1+Dr1+Wr1+LOr+LOut,         -WOut/2),                         #20

        ]

        return {"circles": circles,
                "arcs": [],            # 无圆弧

                "segments": segments,
                "rectangles": []}      # 无矩形阵列

    # ─────────────────────────── 更新绘图 ───────────────────────────

    def updateModel(self):
        try:
            self.ax.clear()
            self.geoPatch = {k: [] for k in self.params}
            geo = self.calculateGeometry()

            # 圆

            for ctr, r in geo["circles"]:
                c = mpatches.Circle(ctr, r, fill=False,
                                    edgecolor='blue', lw=1.5)
                self.ax.add_patch(c)
                self.geoPatch["Radius_1"].append(c)

            # 线段

            for p0, p1 in geo["segments"]:
                ln = plt.Line2D([p0[0], p1[0]], [p0[1], p1[1]],
                                color='blue', lw=1.5)
                self.ax.add_line(ln)
                self.geoPatch.setdefault("Length_r2", []).append(ln)

            # 自动缩放

            xs, ys = [], []
            for p in self.ax.patches:
                if isinstance(p, mpatches.Circle):
                    c, r = p.center, p.radius

                    xs += [c[0]-r, c[0]+r]
                    ys += [c[1]-r, c[1]+r]
            for l in self.ax.lines:
                x, y = l.get_data()
                xs += list(x); ys += list(y)
            if not xs:
                xs = ys = [-1, 1]
            pad = max((max(xs)-min(xs))*0.1, (max(ys)-min(ys))*0.1, 1)
            self.ax.set_xlim(min(xs)-pad, max(xs)+pad)
            self.ax.set_ylim(min(ys)-pad, max(ys)+pad)
            self.ax.set_aspect('equal', adjustable='box')
            self.ax.grid(True, linestyle='--', alpha=0.5)
            self.ax.set_title("Droplet3To1")
            self.ax.set_xlabel("X (mm)")
            self.ax.set_ylabel("Y (mm)")
            self.canvas.draw()

            if self.curHlt:
                self.highlightComponent(self.curHlt)
            self.stsVar.set("模型更新成功 / Model updated successfully")
        except Exception as e:
            messagebox.showerror("错误 / Error",
                                 f"模型更新失败 / Failed to update model: {e}")
            self.stsVar.set(f"失败 / Failed: {e}")

    # ────────────────────── 导出 / 导入 / 退出 ─────────────────────

    def exportDxf(self):
        try:
            name = filedialog.asksaveasfilename(defaultextension=".dxf",
                                                filetypes=[("DXF", "*.dxf")])
            if not name:
                return

            import ezdxf

            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            geo = self.calculateGeometry()
            for ctr, r in geo["circles"]:
                msp.add_circle(ctr, r)
            for p0, p1 in geo["segments"]:
                msp.add_line(p0, p1)
            doc.saveas(name)
            self.stsVar.set(f"已导出DXF / DXF Exported: {name}")
            messagebox.showinfo("成功 / Success",
                                f"已导出到DXF / Exported to DXF:\n{name}")
        except Exception as e:
            messagebox.showerror("错误 / Error",
                                 f"导出DXF失败 / Failed to export DXF: {e}")
            self.stsVar.set("导出失败 / Export Failed")

    def exportSvg(self):
        try:
            name = filedialog.asksaveasfilename(defaultextension=".svg",
                                                filetypes=[("SVG", "*.svg")])
            if not name:
                return

            self.fig.savefig(name, format='svg', bbox_inches='tight')
            self.stsVar.set(f"已导出SVG / SVG Exported: {name}")
            messagebox.showinfo("成功 / Success",
                                f"已导出到SVG / Exported to SVG:\n{name}")
        except Exception as e:
            messagebox.showerror("错误 / Error",
                                 f"导出SVG失败 / Failed to export SVG: {e}")
            self.stsVar.set("导出失败 / Export Failed")

    def exportJson(self):
        try:
            name = filedialog.asksaveasfilename(defaultextension=".json",
                                                filetypes=[("JSON", "*.json")])
            if not name:
                return

            data = {"model_name": self.ax.get_title(),
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "parameters": {k: v.get() for k, v in self.params.items()}}
            with open(name, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self.stsVar.set(f"已导出JSON / JSON Exported: {name}")
            messagebox.showinfo("成功 / Success",
                                f"已导出到JSON / Exported to JSON:\n{name}")
        except Exception as e:
            messagebox.showerror("错误 / Error",
                                 f"导出JSON失败 / Failed to export JSON: {e}")
            self.stsVar.set("导出失败 / Export Failed")

    def importJson(self):
        try:
            name = filedialog.askopenfilename(
                filetypes=[("JSON", "*.json"), ("All files", "*.*")])
            if not name:
                return

            with open(name, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for k, v in data.get("parameters", {}).items():
                if k in self.params:
                    self.params[k].set(str(v))
            self.updateModel()
            if "model_name" in data:
                self.ax.set_title(data["model_name"])
                self.canvas.draw()
            self.stsVar.set(f"已导入JSON / JSON Imported: {name}")
            messagebox.showinfo("成功 / Success",
                                f"已导入JSON / Imported from JSON:\n{name}")
        except Exception as e:
            messagebox.showerror("错误 / Error",
                                 f"导入JSON失败 / Failed to import JSON: {e}")
            self.stsVar.set("导入失败 / Import Failed")

    def quitApplication(self):
        plt.close('all')
        self.master.quit()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MicrochannelTool(root)
    root.mainloop()

