# Copyright (c) 2025 [Grant]
# Licensed under the MIT License.
# See LICENSE in the project root for license information.
import numpy as np

import matplotlib.pyplot as plt

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

import matplotlib.patches as mpatches

import tkinter as tk

from tkinter import ttk, filedialog, messagebox

import json

from datetime import datetime

class MicrochannelTool:
    # ───────────────────────── 初始化 ──────────────────────────

    def __init__(self, master):
        self.master = master

        master.title("微通道几何建模工具")
        master.geometry("1100x700")
        copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 

                                    fg="#555555", bg="#f0f0f0", font=("Arial", 8))
        copyright_label.pack(side=tk.BOTTOM, fill=tk.X, pady=1)
        # ① 纯数值参数（单位 mm，可在面板输入）
        self.params = {
            "Radius_1":   tk.StringVar(value="0.36"),
            "Distance_r1":tk.StringVar(value="2.5"),
            "Length_v2":  tk.StringVar(value="3"),
            "Width_r1":   tk.StringVar(value="0.2"),
            "Width_Or":   tk.StringVar(value="0.1"),
            "Length_Or":  tk.StringVar(value="0.1"),
            "Width_Out":  tk.StringVar(value="0.2"),
            "Length_Out": tk.StringVar(value="0.3"),
            "Length_r2":  tk.StringVar(value="5"),
            "Angle":      tk.StringVar(value="60"),
            "Length_1":   tk.StringVar(value="3"),
            "Length_r3":  tk.StringVar(value="2"),
            "Length_r4":  tk.StringVar(value="3"),
            "Radius_2":   tk.StringVar(value="0.5"),
        }

        # ② 计算参数（界面不显示）
        self.calc_params = ["Distance_1", "Angle_rad"]

        self.defaults = {k: float(v.get()) for k, v in self.params.items()}
        self.descriptions = {
            "Radius_1":   "打孔流道半径 Radius_1 (mm)",
            "Distance_r1":"流道到中间阻管距离 Distance_r1 (mm)",
            "Length_v2":  "中间流道长度 Length_v2 (mm)",
            "Width_r1":   "中间流道宽度 Width_r1 (mm)",
            "Width_Or":   "缩口内径 Width_Or (mm)",
            "Length_Or":  "缩口长度 Length_Or (mm)",
            "Width_Out":  "流阻管宽度 Width_Out (mm)",
            "Length_Out": "缩口出口过渡长 Length_Out (mm)",
            "Length_r2":  "左侧流道长度 Length_r2 (mm)",
            "Angle":      "观察窗角度 Angle (deg)",
            "Length_1":   "观察窗斜边长度 Length_1 (mm)",
            "Length_r3":  "观察窗直边长 Length_r3 (mm)",
            "Length_r4":  "出口流道长 Length_r4 (mm)",
            "Radius_2":   "倒圆角半径 Radius_2 (mm)",
        }
        self.editable_params = list(self.params)

        # 其它通用变量

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

    # ───────────────────────── UI ──────────────────────────────

    def setupUi(self):
        paramFrm = ttk.Frame(self.master); paramFrm.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)
        box = ttk.LabelFrame(paramFrm, text="参数 / Parameters"); box.pack(fill=tk.BOTH, expand=True, pady=10)

        cvs = tk.Canvas(box, width=330)
        bar = ttk.Scrollbar(box, orient="vertical", command=cvs.yview)
        self.scroll_content = ttk.Frame(cvs)
        self.scroll_content.bind("<Configure>", lambda e: cvs.configure(scrollregion=cvs.bbox("all")))
        cvs.create_window((0, 0), window=self.scroll_content, anchor="nw", width=330)
        cvs.configure(yscrollcommand=bar.set)
        cvs.pack(side="left", fill="both", expand=True); bar.pack(side="right", fill="y")
        self.create_parameter_entries()

        btnFrm = ttk.Frame(paramFrm); btnFrm.pack(fill=tk.X, pady=15)
        for txt, cmd in [("更新模型 / Update Model", self.updateModel),
                         ("导出DXF / Export DXF", self.exportDxf),
                         ("导出SVG / Export SVG", self.exportSvg),
                         ("导出JSON / Export JSON", self.exportJson),
                         ("导入JSON / Import JSON", self.importJson)]:
            ttk.Button(btnFrm, text=txt, command=cmd, padding=(10, 5)).pack(fill=tk.X, pady=5)

        plotFrm = ttk.Frame(self.master); plotFrm.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plotFrm); self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self.canvas, plotFrm).update()
        ttk.Label(self.master, textvariable=self.stsVar, relief=tk.SUNKEN, anchor=tk.W, font=self.bigFont)\
            .pack(side=tk.BOTTOM, fill=tk.X)

    def create_parameter_entries(self):
        for w in self.scroll_content.winfo_children(): w.destroy()
        for p in self.editable_params:
            f = ttk.Frame(self.scroll_content); f.pack(fill=tk.X, pady=6, padx=5)
            ttk.Label(f, text=self.descriptions[p], font=self.bigFont, wraplength=330).pack(anchor=tk.W, pady=(0, 3))
            e = ttk.Entry(f, textvariable=self.params[p], font=self.bigFont); e.pack(fill=tk.X)
            e.bind("<Return>", lambda e, x=p: self.parameter_changed(x))
            e.bind("<FocusOut>", lambda e, x=p: self.parameter_changed(x))
            e.bind("<FocusIn>", lambda e, x=p: self.highlightComponent(x))
            self.entries[p] = e

    # ───────────────────────── 参数读取 ──────────────────────────

    def parameter_changed(self, p):
        try:
            float(self.params[p].get()); self.updateModel()
        except ValueError:
            self.params[p].set(str(self.defaults[p])); messagebox.showerror("错误", "无效数字")

    def getParam(self, name):
        if name in self.params:
            return float(self.params[name].get())
        if name == "Distance_1":
            R = self.getParam("Radius_1"); W = self.getParam("Width_r1")
            return R - np.sqrt(max(R**2 - (W**2)/4, 0))
        if name == "Angle_rad":
            return np.deg2rad(self.getParam("Angle"))
        return 0.0

    # ──────────────────────── 高亮 ──────────────────────────────

    def highlightComponent(self, key):
        self.curHlt = key

        for v in self.geoPatch.values():
            for p in v:
                if hasattr(p, 'set_edgecolor'): p.set_edgecolor('blue')
        if key in self.geoPatch:
            for p in self.geoPatch[key]:
                if hasattr(p, 'set_edgecolor'): p.set_edgecolor('red')
        self.canvas.draw(); self.stsVar.set(f"已选择 / Selected: {key}")

    # ──────────────────── 几何计算（核心） ──────────────────────

    def calculateGeometry(self):
        gp = self.getParam

        R1, Dr1, Lv2 = gp("Radius_1"), gp("Distance_r1"), gp("Length_v2")
        Wr1, WOr, LOr = gp("Width_r1"), gp("Width_Or"), gp("Length_Or")
        WOut, LOut, Lr2 = gp("Width_Out"), gp("Length_Out"), gp("Length_r2")
        Angle, L1 = gp("Angle_rad"), gp("Length_1")
        Lr3, Lr4, R2 = gp("Length_r3"), gp("Length_r4"), gp("Radius_2")
        D1 = gp("Distance_1")

        sinA, cosA = np.sin(Angle), np.cos(Angle)

        # ── 圆（4 个）
        circles = [
            ((0, 0), R1),                                           # 圆1

            ((2*R1 + Dr1 + Wr1 + LOr + LOut + Lr2, 0), R1),         # 圆2

            ((0, -Lv2/2 + Wr1/2), R1),                              # 圆3

            ((0,  Lv2/2 - Wr1/2), R1),                              # 圆4

        ]

        # ── 线段（1–20）
        seg = lambda x1,y1,x2,y2: ((x1,y1),(x2,y2))
        segments = [
            seg(R1+Dr1, -Wr1/2, R1-D1, -Wr1/2),                     #1

            seg(R1+Dr1,  Wr1/2, R1-D1,  Wr1/2),                     #2

            seg(R1+Dr1, -Wr1/2, R1+Dr1, -Lv2/2+Wr1),                #3

            seg(R1+Dr1,  Wr1/2, R1+Dr1,  Lv2/2-Wr1),                #4

            seg(R1+Dr1+Wr1, -WOr/2, R1+Dr1+Wr1, -Lv2/2),            #5

            seg(R1+Dr1+Wr1,  WOr/2, R1+Dr1+Wr1,  Lv2/2),            #6

            seg(R1+Dr1+Wr1,  Lv2/2, R1-D1, Lv2/2),                  #7

            seg(R1+Dr1+Wr1,  -Lv2/2, R1-D1, -Lv2/2),                #8  

            seg(R1+Dr1,  Lv2/2-Wr1, R1-D1, Lv2/2-Wr1),                #9

            seg(R1+Dr1, -Lv2/2+Wr1, R1-D1,-Lv2/2+Wr1),              #10

            seg(R1+Dr1+Wr1, -WOr/2, R1+Dr1+Wr1+LOr, -WOr/2),        #15

            seg(R1+Dr1+Wr1,  WOr/2, R1+Dr1+Wr1+LOr,  WOr/2),        #16

            seg(R1+Dr1+Wr1+LOr, -WOr/2, R1+Dr1+Wr1+LOr+LOut, -WOut/2),#17

            seg(R1+Dr1+Wr1+LOr,  WOr/2, R1+Dr1+Wr1+LOr+LOut,  WOut/2),#18

            seg(R1+Dr1+Wr1+LOr+LOut+Lr2+D1,  WOut/2,
                R1+Dr1+Wr1+LOr+LOut, WOut/2),                       #19

            seg(R1+Dr1+Wr1+LOr+LOut+Lr2+D1, -WOut/2,
                R1+Dr1+Wr1+LOr+LOut, -WOut/2),                      #20

        ]

        return {"circles": circles, "arcs": [], "segments": segments, "rectangles": []}

    # ─────────────────── 绘图更新（与原版相同） ──────────────────

    def updateModel(self):
        try:
            self.ax.clear(); self.geoPatch = {k: [] for k in self.params}
            g = self.calculateGeometry()

            for ctr, r in g["circles"]:
                c = mpatches.Circle(ctr, r, fill=False, edgecolor='blue', lw=1.5)
                self.ax.add_patch(c); self.geoPatch.setdefault("Radius_1", []).append(c)

            for p0, p1 in g["segments"]:
                ln = plt.Line2D([p0[0], p1[0]], [p0[1], p1[1]], color='blue', lw=1.5)
                self.ax.add_line(ln); self.geoPatch.setdefault("Length_r2", []).append(ln)

            xs, ys = [], []
            for p in self.ax.patches:
                (cx, cy), r = p.center, p.radius

                xs += [cx - r, cx + r]; ys += [cy - r, cy + r]
            for l in self.ax.lines:
                x, y = l.get_data(); xs += list(x); ys += list(y)
            if not xs: xs = ys = [-1, 1]
            pad = max((max(xs)-min(xs))*0.1, (max(ys)-min(ys))*0.1, 1)
            self.ax.set_xlim(min(xs)-pad, max(xs)+pad); self.ax.set_ylim(min(ys)-pad, max(ys)+pad)
            self.ax.set_aspect('equal'); self.ax.grid(True, linestyle='--', alpha=0.4)
            self.ax.set_title("DdPCR3To1"); self.ax.set_xlabel("X (mm)"); self.ax.set_ylabel("Y (mm)")
            self.canvas.draw()
            if self.curHlt: self.highlightComponent(self.curHlt)
            self.stsVar.set("模型更新成功 / Model updated successfully")
        except Exception as e:
            messagebox.showerror("错误", f"模型更新失败: {e}"); self.stsVar.set(f"失败: {e}")

    # ────────── 导出 / 导入 / 退出（保持原样） ──────────

    def exportDxf(self): pass  # 省略；与原版相同

    def exportSvg(self): pass

    def exportJson(self): pass

    def importJson(self): pass

    def quitApplication(self): plt.close('all'); self.master.quit(); self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk(); app = MicrochannelTool(root); root.mainloop()
