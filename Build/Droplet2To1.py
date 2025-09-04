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
    def __init__(self, master):
        self.master = master

        master.title("微通道几何建模工具")
        master.geometry("1100x700")
        copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 
                             fg="#555555", bg="#f0f0f0")
        copyright_label.pack(side=tk.BOTTOM, fill=tk.X)
        # ───────────────────────────────── 参数 ──────────────────────────────────

        # 纯数值参数（可在界面中输入）
        self.params = {
            "Radius_1":     tk.StringVar(value="0.36"),   # mm

            "Distance_r1":  tk.StringVar(value="2.5"),    # mm

            "Length_v2":    tk.StringVar(value="3"),      # mm

            "Length_r1":    tk.StringVar(value="6"),      # mm

            "Width_r1":     tk.StringVar(value="0.2"),    # mm

            "Width_Or":     tk.StringVar(value="0.1"),    # mm

            "Length_Or":    tk.StringVar(value="0.1"),    # mm

            "Width_Out":    tk.StringVar(value="0.2"),    # mm

            "Length_Out":   tk.StringVar(value="0.3"),    # mm

            "Length_r2":    tk.StringVar(value="5"),      # mm

        }

        # 计算参数（界面不显示）
        self.calc_params = ["Distance_1"]

        self.defaults = {k: float(v.get()) if v.get() else 0.0 for k, v in self.params.items()}
        self.descriptions = {
            "Radius_1":    "打孔流道半径 Radius_1 (mm)",
            "Distance_r1": "流道到中间流阻管的距离 Distance_r1 (mm)",
            "Length_v2":   "中间流道长度 Length_v2 (mm)",
            "Length_r1":   "右侧流道最左端到中间流道的距离 Length_r1 (mm)",
            "Width_r1":    "中间流道宽度 Width_r1 (mm)",
            "Width_Or":    "缩口内径 Width_Or (mm)",
            "Length_Or":   "缩口长度 Length_Or (mm)",
            "Width_Out":   "流阻管宽度 Width_Out (mm)",
            "Length_Out":  "缩口出口过渡横向长 Length_Out (mm)",
            "Length_r2":   "左侧流道长度 Length_r2 (mm)",
        }
        self.editable_params = list(self.params)

        # ─────────────────────────── 其它框架变量 ────────────────────────────────

        self.bigFont = ('Helvetica', 12)
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.geoPatch = {k: [] for k in self.params}          # 基础分组

        self.stsVar = tk.StringVar(value="就绪 / Ready")
        self.curHlt = None

        self.entries = {}

        # UI

        self.setupUi()
        master.protocol("WM_DELETE_WINDOW", self.quitApplication)
        self.updateModel()

    # ──────────────────────────────── UI ──────────────────────────────────────

    def setupUi(self):
        paramFrm = ttk.Frame(self.master)
        paramFrm.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y, expand=True)

        param_scroll_frame = ttk.LabelFrame(paramFrm, text="参数 / Parameters")
        param_scroll_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        canvas = tk.Canvas(param_scroll_frame, width=330)
        scrollbar = ttk.Scrollbar(param_scroll_frame, orient="vertical", command=canvas.yview)
        self.scroll_content = ttk.Frame(canvas)
        self.scroll_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_content, anchor="nw", width=330)
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
        for text, command in buttons:
            ttk.Button(btnFrm, text=text, command=command, padding=(10, 5)).pack(fill=tk.X, pady=5)

        plotFrm = ttk.Frame(self.master)
        plotFrm.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plotFrm)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        toolbarFrame = ttk.Frame(plotFrm)
        toolbarFrame.pack(side=tk.BOTTOM, fill=tk.X)
        NavigationToolbar2Tk(self.canvas, toolbarFrame).update()

        statusBar = ttk.Label(self.master, textvariable=self.stsVar, relief=tk.SUNKEN,
                              anchor=tk.W, font=self.bigFont)
        statusBar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_parameter_entries(self):
        for widget in self.scroll_content.winfo_children():
            widget.destroy()
        for param in self.editable_params:
            frame = ttk.Frame(self.scroll_content)
            frame.pack(fill=tk.X, pady=8, padx=5)
            ttk.Label(frame, text=self.descriptions[param], font=self.bigFont,
                      wraplength=330).pack(anchor=tk.W, pady=(0, 5))
            entry = ttk.Entry(frame, textvariable=self.params[param], font=self.bigFont)
            entry.pack(fill=tk.X)
            entry.bind("<Return>", lambda e, p=param: self.parameter_changed(p))
            entry.bind("<FocusOut>", lambda e, p=param: self.parameter_changed(p))
            entry.bind("<FocusIn>", lambda e, p=param: self.highlightComponent(p))
            self.entries[param] = entry

    # ───────────────────────────── 参数处理 ────────────────────────────────────

    def parameter_changed(self, param):
        try:
            float(self.params[param].get())
            self.updateModel()
        except ValueError:
            self.params[param].set(str(self.defaults[param]))
            messagebox.showerror("错误 / Error", "无效的数值 / Invalid number")

    def getParam(self, name):
        if name in self.params:
            return float(self.params[name].get())
        elif name == "Distance_1":   # 计算参数

            R = self.getParam("Radius_1")
            W = self.getParam("Width_r1")
            val = R**2 - (W**2)/4

            if val < 0:
                raise ValueError("Radius_1 必须大于等于 Width_r1/2")
            return R - np.sqrt(val)
        else:
            return 0.0

    # ────────────────────────────  高亮  ─────────────────────────────────────

    def highlightComponent(self, paramName):
        self.curHlt = paramName

        # 复原

        for patches in self.geoPatch.values():
            for patch in patches:
                if hasattr(patch, 'set_edgecolor'):
                    patch.set_edgecolor('blue')
                elif hasattr(patch, 'set_color'):
                    patch.set_color('blue')
        # 加红

        if paramName in self.geoPatch:
            for patch in self.geoPatch[paramName]:
                if hasattr(patch, 'set_edgecolor'):
                    patch.set_edgecolor('red')
                elif hasattr(patch, 'set_color'):
                    patch.set_color('red')
        self.canvas.draw()
        self.stsVar.set(f"已选择 / Selected: {paramName}")

    # ────────────────────────────  几何计算  ──────────────────────────────────

    def calculateGeometry(self):
        R1   = self.getParam("Radius_1")
        Dr1  = self.getParam("Distance_r1")
        Lv2  = self.getParam("Length_v2")
        Lr1  = self.getParam("Length_r1")
        Wr1  = self.getParam("Width_r1")
        WOr  = self.getParam("Width_Or")
        LOr  = self.getParam("Length_Or")
        WOut = self.getParam("Width_Out")
        LOut = self.getParam("Length_Out")
        Lr2  = self.getParam("Length_r2")
        D1   = self.getParam("Distance_1")

        # 圆 ─────────────

        circles = []
        circles.append(((0, 0), R1))  # 圆1

        circles.append(((R1 + Dr1 - Lr1 - Wr1/2, 0), R1))  # 圆2

        circles.append(((2*R1 + Dr1 + Wr1 + LOr + LOut + Lr2, 0), R1))  # 圆3

        # 线段 ───────────

        seg = lambda x1, y1, x2, y2: ((x1, y1), (x2, y2))
        segments = [
            # 1,2

            seg(R1+Dr1,            -Wr1/2,  R1-D1,               -Wr1/2),
            seg(R1+Dr1,             Wr1/2,  R1-D1,                Wr1/2),
            # 3,4 (竖直)
            seg(R1+Dr1,            -Wr1/2,  R1+Dr1,         -Lv2/2+Wr1),
            seg(R1+Dr1,             Wr1/2,  R1+Dr1,          Lv2/2-Wr1),
            # 5,6 (竖直 at x = R1+Dr1+Wr1)
            seg(R1+Dr1+Wr1,     -WOr/2,     R1+Dr1+Wr1,     -Lv2/2),
            seg(R1+Dr1+Wr1,      WOr/2,     R1+Dr1+Wr1,      Lv2/2),
            # 7,8 (横向最外框)
            seg(R1+Dr1+Wr1,      Lv2/2,     R1+Dr1-Lr1-Wr1,  Lv2/2),
            seg(R1+Dr1+Wr1,     -Lv2/2,     R1+Dr1-Lr1-Wr1, -Lv2/2),
            # 9,10 (横向内框)
            seg(R1+Dr1,          Lv2/2-Wr1, R1+Dr1-Lr1,      Lv2/2-Wr1),
            seg(R1+Dr1,         -Lv2/2+Wr1, R1+Dr1-Lr1,     -Lv2/2+Wr1),
            # 11,12 (右竖内框)
            seg(R1+Dr1-Lr1,     -Lv2/2+Wr1, R1+Dr1-Lr1,     -R1+D1),
            seg(R1+Dr1-Lr1-Wr1, -Lv2/2,     R1+Dr1-Lr1-Wr1, -R1+D1),
            # 13,14 (左竖内框)
            seg(R1+Dr1-Lr1,      Lv2/2-Wr1, R1+Dr1-Lr1,      R1-D1),
            seg(R1+Dr1-Lr1-Wr1,  Lv2/2,     R1+Dr1-Lr1-Wr1,  R1-D1),
            # 15,16 (Or横向)
            seg(R1+Dr1+Wr1,     -WOr/2,     R1+Dr1+Wr1+LOr, -WOr/2),
            seg(R1+Dr1+Wr1,      WOr/2,     R1+Dr1+Wr1+LOr,  WOr/2),
            # 17,18 (Out横向)
            seg(R1+Dr1+Wr1+LOr, -WOr/2,     R1+Dr1+Wr1+LOr+LOut, -WOut/2),
            seg(R1+Dr1+Wr1+LOr,  WOr/2,     R1+Dr1+Wr1+LOr+LOut,  WOut/2),
            # 19,20 (最右)
            seg(R1+Dr1+Wr1+LOr+LOut+Lr2+D1,  WOut/2,
                R1+Dr1+Wr1+LOr+LOut,          WOut/2),
            seg(R1+Dr1+Wr1+LOr+LOut+Lr2+D1, -WOut/2,
                R1+Dr1+Wr1+LOr+LOut,         -WOut/2),
        ]

        return {
            "circles":     circles,
            "arcs":        [],        # 无圆弧

            "segments":    segments,
            "rectangles":  []         # 无矩形阵列

        }

    # ───────────────────────────── 绘制更新 ────────────────────────────────────

    def updateModel(self):
        try:
            self.ax.clear()
            self.geoPatch = {k: [] for k in self.params}

            geo = self.calculateGeometry()

            # 圆

            for center, radius in geo["circles"]:
                patch = mpatches.Circle(center, radius, fill=False,
                                        edgecolor='blue', lw=1.5)
                self.ax.add_patch(patch)
                self.geoPatch["Radius_1"].append(patch)

            # 线段

            for p0, p1 in geo["segments"]:
                line = plt.Line2D([p0[0], p1[0]], [p0[1], p1[1]],
                                  color='blue', lw=1.5)
                self.ax.add_line(line)
                self.geoPatch.setdefault("Length_r1", []).append(line)

            # 自动缩放

            all_x, all_y = [], []
            for patch in self.ax.patches:
                if isinstance(patch, mpatches.Circle):
                    c, r = patch.center, patch.radius

                    all_x.extend([c[0]-r, c[0]+r])
                    all_y.extend([c[1]-r, c[1]+r])
            for line in self.ax.lines:
                xs, ys = line.get_data()
                all_x.extend(xs)
                all_y.extend(ys)
            if not all_x:
                all_x = all_y = [-1, 1]
            pad = max((max(all_x)-min(all_x))*0.1, (max(all_y)-min(all_y))*0.1, 1)
            self.ax.set_xlim(min(all_x)-pad, max(all_x)+pad)
            self.ax.set_ylim(min(all_y)-pad, max(all_y)+pad)
            self.ax.set_aspect('equal', adjustable='box')
            self.ax.grid(True, linestyle='--', alpha=0.5)
            self.ax.set_title("Droplet2To1", fontsize=14)
            self.ax.set_xlabel("X (mm)")
            self.ax.set_ylabel("Y (mm)")
            self.canvas.draw()

            if self.curHlt:
                self.highlightComponent(self.curHlt)

            self.stsVar.set("模型更新成功 / Model updated successfully")
        except Exception as e:
            messagebox.showerror("错误 / Error", f"模型更新失败 / Failed to update model: {e}")
            self.stsVar.set(f"失败 / Failed: {e}")

    # ──────────────────────────── 导出 / 导入 ─────────────────────────────────

    def exportDxf(self):
        try:
            filename = filedialog.asksaveasfilename(defaultextension=".dxf",
                                                    filetypes=[("DXF Files", "*.dxf"), ("All Files", "*.*")],
                                                    title="保存DXF / Save DXF")
            if not filename: return

            import ezdxf

            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            geo = self.calculateGeometry()
            for center, radius in geo["circles"]:
                msp.add_circle(center, radius)
            for p0, p1 in geo["segments"]:
                msp.add_line(p0, p1)
            doc.saveas(filename)
            self.stsVar.set(f"已导出DXF / DXF Exported: {filename}")
            messagebox.showinfo("成功 / Success", f"已导出到DXF / Exported to DXF:\n{filename}")
        except Exception as e:
            messagebox.showerror("错误 / Error", f"导出DXF失败 / Failed to export DXF: {e}")
            self.stsVar.set("导出失败 / Export Failed")

    def exportSvg(self):
        try:
            filename = filedialog.asksaveasfilename(defaultextension=".svg",
                                                    filetypes=[("SVG Files", "*.svg"), ("All Files", "*.*")],
                                                    title="保存SVG / Save SVG")
            if not filename: return

            self.fig.savefig(filename, format='svg', bbox_inches='tight')
            self.stsVar.set(f"已导出SVG / SVG Exported: {filename}")
            messagebox.showinfo("成功 / Success", f"已导出到SVG / Exported to SVG:\n{filename}")
        except Exception as e:
            messagebox.showerror("错误 / Error", f"导出SVG失败 / Failed to export SVG: {e}")
            self.stsVar.set("导出失败 / Export Failed")

    def exportJson(self):
        try:
            filename = filedialog.asksaveasfilename(defaultextension=".json",
                                                    filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                                                    title="保存JSON / Save JSON")
            if not filename: return

            data = {"model_name": self.ax.get_title(),
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "parameters": {k: v.get() for k, v in self.params.items()}}
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self.stsVar.set(f"已导出JSON / JSON Exported: {filename}")
            messagebox.showinfo("成功 / Success", f"已导出到JSON / Exported to JSON:\n{filename}")
        except Exception as e:
            messagebox.showerror("错误 / Error", f"导出JSON失败 / Failed to export JSON: {e}")
            self.stsVar.set("导出失败 / Export Failed")

    def importJson(self):
        try:
            filename = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                                                  title="导入JSON / Import JSON")
            if not filename: return

            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for key, value in data.get("parameters", {}).items():
                if key in self.params:
                    self.params[key].set(str(value))
            self.updateModel()
            if "model_name" in data:
                self.ax.set_title(data["model_name"], fontsize=14)
                self.canvas.draw()
            self.stsVar.set(f"已导入JSON / JSON Imported: {filename}")
            messagebox.showinfo("成功 / Success", f"已导入JSON / Imported from JSON:\n{filename}")
        except Exception as e:
            messagebox.showerror("错误 / Error", f"导入JSON失败 / Failed to import JSON: {e}")
            self.stsVar.set("导入失败 / Import Failed")

    def quitApplication(self):
        plt.close('all')
        self.master.quit()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MicrochannelTool(root)
    root.mainloop()
