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
    # ───────────────────────────── 初始化 ─────────────────────────────

    def __init__(self, master):
        self.master = master

        master.title("微通道几何建模工具")
        master.geometry("1100x700")
        copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 

                                    fg="#555555", bg="#f0f0f0", font=("Arial", 8))
        copyright_label.pack(side=tk.BOTTOM, fill=tk.X, pady=1)
        # ─── 纯数值参数（左侧可输入，单位 mm）───

        self.params = {
            "Radius_1":    tk.StringVar(value="0.36"),
            "Distance_r1": tk.StringVar(value="2.5"),
            "Length_v2":   tk.StringVar(value="3"),
            "Length_r1":   tk.StringVar(value="6"),
            "Width_r1":    tk.StringVar(value="0.2"),
            "Width_Or":    tk.StringVar(value="0.1"),
            "Length_Or":   tk.StringVar(value="0.1"),
            "Width_Res":   tk.StringVar(value="0.2"),
            "Length_Out":  tk.StringVar(value="0.3"),
            "Length_r2":   tk.StringVar(value="5"),
            "Angle":       tk.StringVar(value="60"),
            "Length_r4":   tk.StringVar(value="3"),
            "Length_r3":   tk.StringVar(value="0.3"),
            "Length_v3":   tk.StringVar(value="10"),
            "Number":      tk.StringVar(value="10"),
        }

        # ─── 计算参数（不在面板显示）───

        self.calc_params = ["Distance_1", "Distance_2", "Length_v1", "Angle_rad"]

        self.defaults = {k: float(v.get()) for k, v in self.params.items()}
        self.descriptions = {
            "Radius_1":    "打孔流道半径 Radius_1 (mm)",
            "Distance_r1": "流道到中间流阻管距 Distance_r1 (mm)",
            "Length_v2":   "中间流道长度 Length_v2 (mm)",
            "Length_r1":   "右侧流道到中间距 Length_r1 (mm)",
            "Width_r1":    "中间流道宽度 Width_r1 (mm)",
            "Width_Or":    "缩口内径 Width_Or (mm)",
            "Length_Or":   "缩口长度 Length_Or (mm)",
            "Width_Res":   "流阻管宽度 Width_Res (mm)",
            "Length_Out":  "缩口出口过渡长 Length_Out (mm)",
            "Length_r2":   "左侧流道长度 Length_r2 (mm)",
            "Angle":       "观察窗角度 Angle (deg)",
            "Length_r4":   "出口流道长 Length_r4 (mm)",
            "Length_r3":   "液滴出口过渡长 Length_r3 (mm)",
            "Length_v3":   "流阻管纵向总长 Length_v3 (mm)",
            "Number":      "循环次数 Number",
        }
        self.editable_params = list(self.params)

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
        paramFrm.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)
        paramBox = ttk.LabelFrame(paramFrm, text="参数 / Parameters")
        paramBox.pack(fill=tk.BOTH, expand=True, pady=10)

        canvas = tk.Canvas(paramBox, width=330)
        scrollbar = ttk.Scrollbar(paramBox, orient="vertical", command=canvas.yview)
        self.scroll_content = ttk.Frame(canvas)
        self.scroll_content.bind("<Configure>",
                                 lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_content, anchor="nw", width=330)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.create_parameter_entries()

        btnFrm = ttk.Frame(paramFrm)
        btnFrm.pack(fill=tk.X, pady=15)
        for txt, cmd in [("更新模型 / Update Model", self.updateModel),
                         ("导出DXF / Export DXF", self.exportDxf),
                         ("导出SVG / Export SVG", self.exportSvg),
                         ("导出JSON / Export JSON", self.exportJson),
                         ("导入JSON / Import JSON", self.importJson)]:
            ttk.Button(btnFrm, text=txt, command=cmd,
                       padding=(10, 5)).pack(fill=tk.X, pady=5)

        plotFrm = ttk.Frame(self.master); plotFrm.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True,
                                                       padx=10, pady=10)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plotFrm)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self.canvas, plotFrm).update()
        ttk.Label(self.master, textvariable=self.stsVar, relief=tk.SUNKEN,
                  anchor=tk.W, font=self.bigFont).pack(side=tk.BOTTOM, fill=tk.X)

    def create_parameter_entries(self):
        for w in self.scroll_content.winfo_children():
            w.destroy()
        for p in self.editable_params:
            fm = ttk.Frame(self.scroll_content); fm.pack(fill=tk.X, pady=6, padx=5)
            ttk.Label(fm, text=self.descriptions[p], font=self.bigFont,
                      wraplength=330).pack(anchor=tk.W, pady=(0, 3))
            ent = ttk.Entry(fm, textvariable=self.params[p], font=self.bigFont)
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
            messagebox.showerror("错误 / Error", "无效数字 / Invalid number")

    def getParam(self, name):
        if name in self.params:
            return float(self.params[name].get())
        # 计算参数

        if name == "Distance_1":
            R, W = self.getParam("Radius_1"), self.getParam("Width_r1")
            return R - np.sqrt(max(R**2 - (W**2)/4, 0))
        if name == "Distance_2":
            R, W = self.getParam("Radius_1"), self.getParam("Width_Res")
            return R - np.sqrt(max(R**2 - (W**2)/4, 0))
        if name == "Length_v1":
            return self.getParam("Length_v3")/2 - self.getParam("Width_Res")*2

        if name == "Angle_rad":
            return np.deg2rad(self.getParam("Angle"))
        return 0.0

    # ─────────────────────────── 高亮 ────────────────────────────

    def highlightComponent(self, key):
        self.curHlt = key

        for patches in self.geoPatch.values():
            for p in patches:
                if hasattr(p, 'set_edgecolor'): p.set_edgecolor('blue')
                elif hasattr(p, 'set_color'):  p.set_color('blue')
        if key in self.geoPatch:
            for p in self.geoPatch[key]:
                if hasattr(p, 'set_edgecolor'): p.set_edgecolor('red')
                elif hasattr(p, 'set_color'):  p.set_color('red')
        self.canvas.draw()
        self.stsVar.set(f"已选择 / Selected: {key}")

    # ────────────────────── 几何计算（核心） ─────────────────────

    def calculateGeometry(self):
        # 基础参数

        R1   = self.getParam("Radius_1")
        Dr1  = self.getParam("Distance_r1")
        Lv2  = self.getParam("Length_v2")
        Lr1  = self.getParam("Length_r1")
        Wr1  = self.getParam("Width_r1")
        WOr  = self.getParam("Width_Or")
        LOr  = self.getParam("Length_Or")
        WRes = self.getParam("Width_Res")
        LOut = self.getParam("Length_Out")
        Lr2  = self.getParam("Length_r2")
        Lr3  = self.getParam("Length_r3")
        Num  = int(round(self.getParam("Number")))
        D1   = self.getParam("Distance_1")
        D2   = self.getParam("Distance_2")
        Lv1  = self.getParam("Length_v1")

        # 辅助基点

        base_x = R1 + Dr1 + Wr1 + LOr + LOut + Lr3

        y_down = -WRes + Lv1

        y_up   =  WRes - Lv1

        # ─── 圆 ───

        circles = [
            ((0, 0), R1),
            ((R1 + Dr1 - Lr1 - Wr1/2, 0), R1),
            ((base_x + 3*WRes + 4*Num*WRes + WRes + Lr3 + R1 , 0), R1),
        ]

        # ─── 圆弧 ───

        arcs = []

        # (1)(2) 左端第一对圆弧

        c1 = (base_x + 1.5*WRes, y_down)
        arcs += [(c1, 1.5*WRes,   0, 180),  # 大弧

                 (c1, 0.5*WRes,   0, 180)]  # 小弧

        # (3)(4)(5)(6) 及其阵列

        for i in range(Num):
            off = i * 4 * WRes

            # 向上弧（-180 → 0）
            c_up = (base_x + 1.5*WRes + 2*WRes + off, y_up)
            arcs += [(c_up, 1.5*WRes, -180,   0),
                     (c_up, 0.5*WRes, -180,   0)]
            # 向下弧（0 → 180）
            c_dn = (base_x + 1.5*WRes + 4*WRes + off, y_down)
            arcs += [(c_dn, 1.5*WRes,   0, 180),
                     (c_dn, 0.5*WRes,   0, 180)]

        # (7)(8) 左侧最外框

        cL = (base_x - WRes/2, WRes)
        arcs += [(cL, 1.5*WRes, -90,   0),
                 (cL, 0.5*WRes, -90,   0)]

        # (9)(10) 右侧最外框

        cR = (base_x + WRes*3 + WRes*4*Num + WRes/2, WRes)
        arcs += [(cR, 1.5*WRes, 180, 270),
                 (cR, 0.5*WRes, 180, 270)]

        # ─── 直线 ───

        seg = lambda x1, y1, x2, y2: ((x1, y1), (x2, y2))
        segments = [
            seg(R1+Dr1,             -Wr1/2,  R1-D1,               -Wr1/2),   #1

            seg(R1+Dr1,              Wr1/2,  R1-D1,                Wr1/2),   #2

            seg(R1+Dr1,             -Wr1/2,  R1+Dr1,         -Lv2/2+Wr1),    #3

            seg(R1+Dr1,              Wr1/2,  R1+Dr1,          Lv2/2-Wr1),    #4

            seg(R1+Dr1+Wr1,        -WOr/2,   R1+Dr1+Wr1,       -Lv2/2),      #5

            seg(R1+Dr1+Wr1,         WOr/2,   R1+Dr1+Wr1,        Lv2/2),      #6

            seg(R1+Dr1+Wr1,         Lv2/2,   R1+Dr1-Lr1-Wr1,    Lv2/2),      #7

            seg(R1+Dr1+Wr1,        -Lv2/2,   R1+Dr1-Lr1-Wr1,   -Lv2/2),      #8

            seg(R1+Dr1,             Lv2/2-Wr1, R1+Dr1-Lr1,      Lv2/2-Wr1),  #9

            seg(R1+Dr1,            -Lv2/2+Wr1, R1+Dr1-Lr1,    -Lv2/2+Wr1),  #10

            seg(R1+Dr1-Lr1,        -Lv2/2+Wr1, R1+Dr1-Lr1,    -R1+D1),      #11

            seg(R1+Dr1-Lr1-Wr1,    -Lv2/2,   R1+Dr1-Lr1-Wr1,  -R1+D1),      #12

            seg(R1+Dr1-Lr1,         Lv2/2-Wr1, R1+Dr1-Lr1,     R1-D1),      #13

            seg(R1+Dr1-Lr1-Wr1,     Lv2/2,   R1+Dr1-Lr1-Wr1,   R1-D1),      #14

            seg(R1+Dr1+Wr1,        -WOr/2,   R1+Dr1+Wr1+LOr,  -WOr/2),      #15

            seg(R1+Dr1+Wr1,         WOr/2,   R1+Dr1+Wr1+LOr,   WOr/2),      #16

            seg(R1+Dr1+Wr1+LOr,    -WOr/2,   R1+Dr1+Wr1+LOr+LOut, -WRes/2), #17

            seg(R1+Dr1+Wr1+LOr,     WOr/2,   R1+Dr1+Wr1+LOr+LOut,  WRes/2), #18

            seg(R1+Dr1+Wr1+LOr+LOut,  WRes/2,
                R1+Dr1+Wr1+LOr+LOut+Lr3-WRes/2, WRes/2),                    #19

            seg(R1+Dr1+Wr1+LOr+LOut, -WRes/2,
                R1+Dr1+Wr1+LOr+LOut+Lr3-WRes/2,-WRes/2),                    #20

            seg(base_x, y_down, base_x, WRes),                              #21

            seg(base_x+WRes, y_down, base_x+WRes, WRes),                    #22

        ]

        # (23)(24)(25)(26) 及其阵列

        for i in range(Num):
            off = i * 4 * WRes

            segments += [
                seg(base_x + 3*WRes + off, -WRes+Lv1, base_x + 3*WRes + off,  WRes-Lv1),   #23

                seg(base_x + 2*WRes + off, -WRes+Lv1, base_x + 2*WRes + off,  WRes-Lv1),   #24

                seg(base_x + 5*WRes + off,  WRes-Lv1, base_x + 5*WRes + off, -WRes+Lv1),   #25

                seg(base_x + 4*WRes + off,  WRes-Lv1, base_x + 4*WRes + off, -WRes+Lv1),   #26

            ]

        # (27)(28) 阵列右端竖线

        segments += [
            seg(base_x + 3*WRes + 4*Num*WRes - WRes,
                -WRes+Lv1,
                base_x + 3*WRes + 4*Num*WRes - WRes, WRes),                 #27

            seg(base_x + 3*WRes + 4*Num*WRes,
                -WRes+Lv1,
                base_x + 3*WRes + 4*Num*WRes,     WRes),                   #28

        ]
        # (29)(30) 右端水平

        segments += [
            seg(base_x + 3*WRes + 4*Num*WRes + WRes/2,  WRes/2,
                base_x + 3*WRes + 4*Num*WRes + WRes + Lr3 + D2,  WRes/2),  #29

            seg(base_x + 2*WRes + 4*Num*WRes + 1.5*WRes, -WRes/2,
                base_x + 3*WRes + 4*Num*WRes + WRes + Lr3 + D2, -WRes/2),  #30

        ]

        return {"circles": circles, "arcs": arcs,
                "segments": segments, "rectangles": []}

    # ─────────────────────────── 更新绘图 ───────────────────────────

    def updateModel(self):
        try:
            self.ax.clear()
            self.geoPatch = {k: [] for k in self.params}
            geo = self.calculateGeometry()

            # 圆

            for ctr, r in geo["circles"]:
                c = mpatches.Circle(ctr, r, fill=False, edgecolor='blue', lw=1.5)
                self.ax.add_patch(c); self.geoPatch["Radius_1"].append(c)

            # 圆弧

            for ctr, rad, t1, t2 in geo["arcs"]:
                a = mpatches.Arc(ctr, 2*rad, 2*rad, angle=0,
                                 theta1=t1, theta2=t2, edgecolor='blue', lw=1.5)
                self.ax.add_patch(a); self.geoPatch.setdefault("Width_Res", []).append(a)

            # 线段

            for p0, p1 in geo["segments"]:
                ln = plt.Line2D([p0[0], p1[0]], [p0[1], p1[1]],
                                color='blue', lw=1.5)
                self.ax.add_line(ln); self.geoPatch.setdefault("Length_r1", []).append(ln)

            # autoscale

            xs, ys = [], []
            for p in self.ax.patches:
                if isinstance(p, mpatches.Circle):
                    cx, cy = p.center; r = p.radius; xs += [cx-r, cx+r]; ys += [cy-r, cy+r]
                elif isinstance(p, mpatches.Arc):
                    cx, cy = p.center; xs += [cx-p.width/2, cx+p.width/2]; ys += [cy-p.height/2, cy+p.height/2]
            for l in self.ax.lines:
                x, y = l.get_data(); xs += list(x); ys += list(y)
            if not xs: xs = ys = [-1, 1]
            pad = max((max(xs)-min(xs))*0.1, (max(ys)-min(ys))*0.1, 1)
            self.ax.set_xlim(min(xs)-pad, max(xs)+pad)
            self.ax.set_ylim(min(ys)-pad, max(ys)+pad)
            self.ax.set_aspect('equal', adjustable='box')
            self.ax.grid(True, linestyle='--', alpha=0.4)
            self.ax.set_title("CdPCR")
            self.ax.set_xlabel("X (mm)"); self.ax.set_ylabel("Y (mm)")
            self.canvas.draw()
            if self.curHlt: self.highlightComponent(self.curHlt)
            self.stsVar.set("模型更新成功 / Model updated successfully")
        except Exception as e:
            messagebox.showerror("错误 / Error",
                                 f"模型更新失败 / Failed to update model: {e}")
            self.stsVar.set(f"失败 / Failed: {e}")

    # ────────────────── 导出 / 导入 / 退出（保持不变） ──────────────────

    def exportDxf(self):
        try:
            f = filedialog.asksaveasfilename(defaultextension=".dxf",
                                             filetypes=[("DXF", "*.dxf")])
            if not f: return

            import ezdxf

            doc = ezdxf.new('R2010'); msp = doc.modelspace()
            g = self.calculateGeometry()
            for ctr, r in g["circles"]: msp.add_circle(ctr, r)
            for ctr, r, a1, a2 in g["arcs"]: msp.add_arc(ctr, r, a1, a2)
            for p0, p1 in g["segments"]: msp.add_line(p0, p1)
            doc.saveas(f); self.stsVar.set(f"已导出DXF {f}")
        except Exception as e:
            messagebox.showerror("Error", f"导出DXF失败: {e}")

    def exportSvg(self):
        try:
            f = filedialog.asksaveasfilename(defaultextension=".svg",
                                             filetypes=[("SVG", "*.svg")])
            if not f: return

            self.fig.savefig(f, format='svg', bbox_inches='tight')
            self.stsVar.set(f"已导出SVG {f}")
        except Exception as e:
            messagebox.showerror("Error", f"导出SVG失败: {e}")

    def exportJson(self):
        try:
            f = filedialog.asksaveasfilename(defaultextension=".json",
                                             filetypes=[("JSON", "*.json")])
            if not f: return

            data = {"model_name": self.ax.get_title(),
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "parameters": {k: v.get() for k, v in self.params.items()}}
            with open(f, 'w', encoding='utf-8') as fp: json.dump(data, fp, indent=4, ensure_ascii=False)
            self.stsVar.set(f"已导出JSON {f}")
        except Exception as e:
            messagebox.showerror("Error", f"导出JSON失败: {e}")

    def importJson(self):
        try:
            f = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All", "*.*")])
            if not f: return

            with open(f, 'r', encoding='utf-8') as fp: data = json.load(fp)
            for k, v in data.get("parameters", {}).items():
                if k in self.params: self.params[k].set(str(v))
            self.updateModel()
            if "model_name" in data: self.ax.set_title(data["model_name"]); self.canvas.draw()
            self.stsVar.set(f"已导入JSON {f}")
        except Exception as e:
            messagebox.showerror("Error", f"导入JSON失败: {e}")

    def quitApplication(self):
        plt.close('all')
        self.master.quit()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MicrochannelTool(root)
    root.mainloop()
