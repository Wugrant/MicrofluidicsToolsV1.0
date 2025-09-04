# Copyright (c) 2025 [Grant]
# Licensed under the MIT License.
# See LICENSE in the project root for license information.
import numpy as np

import matplotlib.pyplot as plt

import matplotlib.patches as mpatches

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

import tkinter as tk

from tkinter import ttk, filedialog, messagebox

from datetime import datetime

import json

import ezdxf

import math

# ────────────────────────── 主工具类 ────────────────────────────

class GeometryTool:
    # ───────────────────────────── 初始化 ─────────────────────────────

    def __init__(self, master: tk.Tk):
        self.master = master

        master.title("直流道几何建模工具 / Straight Microchannel")
        master.geometry("950x750")
        copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 

                                    fg="#555555", bg="#f0f0f0", font=("Arial", 8))
        copyright_label.pack(side=tk.BOTTOM, fill=tk.X, pady=1)
        # ─── 1. 基础可编辑参数 ───

        self.params = {
            "cirDia": tk.StringVar(value="0.40"),  # 圆直径

            "recWid": tk.StringVar(value="0.20"),  # 矩形宽

            "recLen": tk.StringVar(value="17.0"),  # 矩形长

        }
        self.defaults = {k: float(v.get()) for k, v in self.params.items()}

        # ─── 2. 隐含计算参数 ───

        self.calc_params = ["Dx"]          # 圆心水平交点距离

        # ─── 3. 参数中文 / 英文描述 ───

        self.descriptions = {
            "cirDia": "圆直径 / Circle Diameter (mm)",
            "recWid": "矩形宽度 / Rectangle Width (mm)",
            "recLen": "矩形长度 / Rectangle Length (mm)",
        }

        self.editable_params = list(self.params)   # 出现在面板的键

        # ─── 4. 绘图与状态变量 ───

        self.bigFont = ('Helvetica', 12)
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.geoPatch = {k: [] for k in self.params}
        self.stsVar   = tk.StringVar(value="就绪 / Ready")
        self.curHlt   = None

        self.entries  = {}

        # ─── 5. 生成 UI ───

        self.setupUi()
        master.protocol("WM_DELETE_WINDOW", self.quitApplication)
        self.updateModel()

    # ────────────────────────────── UI ──────────────────────────────

    def setupUi(self):
        # 左侧滚动参数框

        paramFrm = ttk.Frame(self.master); paramFrm.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)
        box = ttk.LabelFrame(paramFrm, text="参数 / Parameters"); box.pack(fill=tk.BOTH, expand=True, pady=10)

        canvas = tk.Canvas(box, width=330)
        sb = ttk.Scrollbar(box, orient="vertical", command=canvas.yview)
        self.scroll_content = ttk.Frame(canvas)
        self.scroll_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_content, anchor="nw", width=330)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side='left', fill='both', expand=True); sb.pack(side='right', fill='y')

        self.create_parameter_entries()

        # 按钮

        btnFrm = ttk.Frame(paramFrm); btnFrm.pack(fill=tk.X, pady=15)
        for txt, cmd in [("更新模型 / Update",      self.updateModel),
                         ("导出DXF / Export DXF",  self.exportDxf),
                         ("导出SVG / Export SVG",  self.exportSvg),
                         ("导出JSON / Export JSON",self.exportJson),
                         ("导入JSON / Import JSON",self.importJson)]:
            ttk.Button(btnFrm, text=txt, command=cmd, padding=(10,5)).pack(fill=tk.X, pady=5)

        # 绘图区

        plotFrm = ttk.Frame(self.master); plotFrm.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True,
                                                       padx=10, pady=10)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plotFrm)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self.canvas, plotFrm).update()

        ttk.Label(self.master, textvariable=self.stsVar, relief=tk.SUNKEN,
                  anchor=tk.W, font=self.bigFont).pack(side=tk.BOTTOM, fill=tk.X)

    def create_parameter_entries(self):
        for w in self.scroll_content.winfo_children(): w.destroy()
        for p in self.editable_params:
            fm = ttk.Frame(self.scroll_content); fm.pack(fill=tk.X, pady=6, padx=5)
            ttk.Label(fm, text=self.descriptions[p], font=self.bigFont,
                      wraplength=330).pack(anchor=tk.W, pady=(0,3))
            ent = ttk.Entry(fm, textvariable=self.params[p], font=self.bigFont)
            ent.pack(fill=tk.X)
            ent.bind("<Return>",   lambda e,x=p: self.parameter_changed(x))
            ent.bind("<FocusOut>", lambda e,x=p: self.parameter_changed(x))
            ent.bind("<FocusIn>",  lambda e,x=p: self.highlightComponent(x))
            self.entries[p] = ent

    # ────────────────────────── 参数读写 ────────────────────────────

    def parameter_changed(self, p):
        try:
            float(self.params[p].get())
            self.updateModel()
        except ValueError:
            self.params[p].set(str(self.defaults[p]))
            messagebox.showerror("错误 / Error","无效数字 / Invalid number")

    def getParam(self, name:str)->float:
        if name in self.params:
            return float(self.params[name].get())
        # 计算 Dx = sqrt(R^2 - (W/2)^2)
        if name == "Dx":
            R = self.getParam("cirDia")/2

            W = self.getParam("recWid")
            return math.sqrt(max(R**2 - (W/2)**2, 0))
        return 0.0

    # ─────────────────────────── 高亮 ────────────────────────────

    def highlightComponent(self,key):
        self.curHlt = key

        for patches in self.geoPatch.values():
            for p in patches:
                if hasattr(p,'set_edgecolor'): p.set_edgecolor('blue')
                elif hasattr(p,'set_color'):  p.set_color('blue')
        if key in self.geoPatch:
            for p in self.geoPatch[key]:
                if hasattr(p,'set_edgecolor'): p.set_edgecolor('red')
                elif hasattr(p,'set_color'):  p.set_color('red')
        self.canvas.draw()
        self.stsVar.set(f"已选择 / Selected: {key}")

    # ────────────────────── 几何计算（核心） ─────────────────────

    def calculateGeometry(self):
        # 基本量

        R   = self.getParam("cirDia")/2

        W   = self.getParam("recWid")
        L   = self.getParam("recLen")
        Dx  = self.getParam("Dx")

        # 圆心 X

        xL = -L/2 - R

        xR =  L/2 + R

        # ─── primitives ───

        circles  = [((xL,0), R), ((xR,0), R)]
        arcs     = []                      # 本模型没有圆弧独立对象

        segments = [
            ((xL+Dx,  W/2), (xR-Dx,  W/2)),   # 上边

            ((xL+Dx, -W/2), (xR-Dx, -W/2)),   # 下边

        ]
        return {"circles":circles,"arcs":arcs,"segments":segments,"rectangles":[]}

    # ─────────────────────────── 更新绘图 ───────────────────────────

    def updateModel(self):
        try:
            self.ax.clear()
            self.geoPatch = {k: [] for k in self.params}
            geo = self.calculateGeometry()

            # 画圆

            for ctr,r in geo["circles"]:
                c = mpatches.Circle(ctr,r,fill=False,edgecolor='blue',lw=1.5)
                self.ax.add_patch(c); self.geoPatch["cirDia"].append(c)

            # 画线

            for p0,p1 in geo["segments"]:
                ln = plt.Line2D([p0[0],p1[0]],[p0[1],p1[1]],color='blue',lw=1.5)
                self.ax.add_line(ln)
                self.geoPatch["recWid"].append(ln); self.geoPatch["recLen"].append(ln)

            # autoscale

            xs,ys=[],[]
            for p in self.ax.patches:
                cx,cy=p.center; r=p.radius; xs+=[cx-r,cx+r]; ys+=[cy-r,cy+r]
            for l in self.ax.lines:
                x,y=l.get_data(); xs+=list(x); ys+=list(y)
            if not xs: xs=ys=[-1,1]
            pad=max((max(xs)-min(xs))*0.1,(max(ys)-min(ys))*0.1,1)
            self.ax.set_xlim(min(xs)-pad, max(xs)+pad)
            self.ax.set_ylim(min(ys)-pad, max(ys)+pad)
            self.ax.set_aspect('equal', adjustable='box')
            self.ax.grid(True, linestyle='--', alpha=0.4)
            self.ax.set_title("Straight Microchannel")
            self.ax.set_xlabel("X (mm)"); self.ax.set_ylabel("Y (mm)")
            self.canvas.draw()
            if self.curHlt: self.highlightComponent(self.curHlt)
            self.stsVar.set("模型更新成功 / Model updated successfully")
        except Exception as e:
            messagebox.showerror("错误 / Error", f"模型更新失败: {e}")
            self.stsVar.set(f"失败 / Failed: {e}")

    # ────────────────── 导出 / 导入 / 退出 ──────────────────

    def exportDxf(self):
        try:
            f = filedialog.asksaveasfilename(defaultextension=".dxf",
                                             filetypes=[("DXF","*.dxf")])
            if not f: return

            doc = ezdxf.new('R2010'); msp = doc.modelspace()
            g = self.calculateGeometry()
            for ctr,r in g["circles"]: msp.add_circle(ctr,r)
            for p0,p1 in g["segments"]: msp.add_line(p0,p1)
            doc.saveas(f); self.stsVar.set(f"已导出DXF {f}")
        except Exception as e:
            messagebox.showerror("Error", f"导出DXF失败: {e}")

    def exportSvg(self):
        try:
            f = filedialog.asksaveasfilename(defaultextension=".svg",
                                             filetypes=[("SVG","*.svg")])
            if not f: return

            self.fig.savefig(f, format='svg', bbox_inches='tight')
            self.stsVar.set(f"已导出SVG {f}")
        except Exception as e:
            messagebox.showerror("Error", f"导出SVG失败: {e}")

    def exportJson(self):
        try:
            f = filedialog.asksaveasfilename(defaultextension=".json",
                                             filetypes=[("JSON","*.json")])
            if not f: return

            data = {"model_name": self.ax.get_title(),
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "parameters": {k:v.get() for k,v in self.params.items()}}
            with open(f,'w',encoding='utf-8') as fp: json.dump(data, fp, indent=4, ensure_ascii=False)
            self.stsVar.set(f"已导出JSON {f}")
        except Exception as e:
            messagebox.showerror("Error", f"导出JSON失败: {e}")

    def importJson(self):
        try:
            f = filedialog.askopenfilename(filetypes=[("JSON","*.json"),("All","*.*")])
            if not f: return

            with open(f,'r',encoding='utf-8') as fp: data=json.load(fp)
            for k,v in data.get("parameters",{}).items():
                if k in self.params: self.params[k].set(str(v))
            self.updateModel()
            if "model_name" in data:
                self.ax.set_title(data["model_name"]); self.canvas.draw()
            self.stsVar.set(f"已导入JSON {f}")
        except Exception as e:
            messagebox.showerror("Error", f"导入JSON失败: {e}")

    def quitApplication(self):
        plt.close('all')
        self.master.quit(); self.master.destroy()

# ────────────────────────── 入口 ──────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app  = GeometryTool(root)
    root.mainloop()
