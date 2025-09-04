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
    # ─────────── 初始化 ──────────────────────────────────────────

    def __init__(self, master):
        self.master = master

        master.title("微通道几何建模工具")
        master.geometry("1100x700")
        copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 

                                    fg="#555555", bg="#f0f0f0", font=("Arial", 8))
        copyright_label.pack(side=tk.BOTTOM, fill=tk.X, pady=1)
        # ① 纯数值参数（左侧可输入，单位 mm）
        self.params = {
            "Radius_1":   tk.StringVar(value="0.36"),
            "Distance_r1":tk.StringVar(value="2.5"),
            "Length_v2":  tk.StringVar(value="3"),
            "Length_r1":  tk.StringVar(value="6"),
            "Width_r1":   tk.StringVar(value="0.2"),
            "Width_Or":   tk.StringVar(value="0.1"),
            "Length_Or":  tk.StringVar(value="0.1"),
            "Width_Out":  tk.StringVar(value="0.2"),
            "Length_Out": tk.StringVar(value="0.3"),
            "Length_r2":  tk.StringVar(value="5"),
            "Radius_2":   tk.StringVar(value="0.2"),
            "Angle":      tk.StringVar(value="60"),
            "Length_1":   tk.StringVar(value="1.0"),
            "Length_r3":  tk.StringVar(value="0.3"),
            "Length_r4":  tk.StringVar(value="3"),
        }

        # ② 计算参数（界面不显示）
        self.calc_params = ["Distance_1", "Angle_rad"]

        self.defaults = {k: float(v.get()) for k, v in self.params.items()}
        self.descriptions = {
            "Radius_1":"打孔流道半径 Radius_1 (mm)",
            "Distance_r1":"流道到中间阻管距 Distance_r1 (mm)",
            "Length_v2":"中间流道长度 Length_v2 (mm)",
            "Length_r1":"右侧流道到中间距 Length_r1 (mm)",
            "Width_r1":"中间流道宽度 Width_r1 (mm)",
            "Width_Or":"缩口内径 Width_Or (mm)",
            "Length_Or":"缩口长度 Length_Or (mm)",
            "Width_Out":"流阻管宽度 Width_Out (mm)",
            "Length_Out":"缩口出口过渡长 Length_Out (mm)",
            "Length_r2":"左侧流道长度 Length_r2 (mm)",
            "Radius_2":"倒圆角半径 Radius_2 (mm)",
            "Angle":"观察窗角度 Angle (deg)",
            "Length_1":"斜边水平投影 Length_1 (mm)",
            "Length_r3":"液滴出口过渡长 Length_r3 (mm)",
            "Length_r4":"出口流道长 Length_r4 (mm)",
        }
        self.editable_params = list(self.params)

        # 其它框架变量

        self.bigFont = ('Helvetica', 12)
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.geoPatch = {k: [] for k in self.params}
        self.stsVar = tk.StringVar(value="就绪 / Ready")
        self.curHlt = None

        self.entries = {}

        self.setupUi()
        master.protocol("WM_DELETE_WINDOW", self.quitApplication)
        self.updateModel()

    # ─────────── UI（保持原样） ──────────────────────────────────

    def setupUi(self):
        paramFrm = ttk.Frame(self.master); paramFrm.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)
        box = ttk.LabelFrame(paramFrm, text="参数 / Parameters"); box.pack(fill=tk.BOTH, expand=True, pady=10)

        cvs = tk.Canvas(box, width=330); bar = ttk.Scrollbar(box, orient="vertical", command=cvs.yview)
        self.scroll_content = ttk.Frame(cvs)
        self.scroll_content.bind("<Configure>", lambda e: cvs.configure(scrollregion=cvs.bbox("all")))
        cvs.create_window((0, 0), window=self.scroll_content, anchor="nw", width=330)
        cvs.configure(yscrollcommand=bar.set); cvs.pack(side="left", fill="both", expand=True); bar.pack(side="right", fill="y")
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
        ttk.Label(self.master, textvariable=self.stsVar, relief=tk.SUNKEN, anchor=tk.W, font=self.bigFont).pack(side=tk.BOTTOM, fill=tk.X)

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

    # ─────────── 参数读取 ─────────────────────────────────────────

    def parameter_changed(self, p):
        try:
            float(self.params[p].get()); self.updateModel()
        except ValueError:
            self.params[p].set(str(self.defaults[p])); messagebox.showerror("错误", "无效数字")

    def getParam(self, name):
        if name in self.params: return float(self.params[name].get())
        R = self.getParam("Radius_1")
        if name == "Distance_1":
            W = self.getParam("Width_r1")
            return R - np.sqrt(max(R**2 - (W**2)/4, 0))
        if name == "Angle_rad":
            return np.deg2rad(self.getParam("Angle"))
        return 0.0

    # ─────────── 高亮 ────────────────────────────────────────────

    def highlightComponent(self, key):
        self.curHlt = key

        for pl in self.geoPatch.values():
            for p in pl:
                if hasattr(p, 'set_edgecolor'): p.set_edgecolor('blue')
        if key in self.geoPatch:
            for p in self.geoPatch[key]:
                if hasattr(p, 'set_edgecolor'): p.set_edgecolor('red')
        self.canvas.draw(); self.stsVar.set(f"已选择 / Selected: {key}")

    # ─────────── 计算几何（核心改动） ─────────────────────────────

    def calculateGeometry(self):
        # 快速取名

        gp = self.getParam

        R1, Dr1, Lv2, Lr1 = gp("Radius_1"), gp("Distance_r1"), gp("Length_v2"), gp("Length_r1")
        Wr1, WOr, LOr, WOut, LOut, Lr2 = gp("Width_r1"), gp("Width_Or"), gp("Length_Or"), gp("Width_Out"), gp("Length_Out"), gp("Length_r2")
        R2, Angle, L1, Lr3, Lr4 = gp("Radius_2"), gp("Angle_rad"), gp("Length_1"), gp("Length_r3"), gp("Length_r4")
        D1 = gp("Distance_1"); sinA, cosA, tanA2 = np.sin(Angle), np.cos(Angle), np.tan(Angle/2)

        # 圆

        circles = [
            ((0, 0), R1),
            ((R1 + Dr1 - Lr1 - Wr1/2, 0), R1),
            ((R1 + Dr1 + Wr1 + LOr + LOut + 2*L1*cosA + Lr3 + Lr4 + R1, 0), R1)
        ]

        # 圆弧

        c1x = R1 + Dr1 + Wr1 + LOr + LOut + L1*cosA + R2*tanA2

        c1y = WOut/2 + L1*sinA - R2

        c3x = R1 + Dr1 + Wr1 + LOr + LOut + L1*cosA + Lr3 - R2*tanA2

        c3y = c1y

        arcs = [
            ((c1x, c1y), R2, 90, 90+np.rad2deg(Angle)),             # arc1

            ((c1x, -c1y), R2, -90-np.rad2deg(Angle), -90),           # arc2

            ((c3x, c3y), R2, 90-np.rad2deg(Angle), 90),              # arc3

            ((c3x, -c3y), R2, -90, -90+np.rad2deg(Angle))            # arc4

        ]

        # 线段

        seg = lambda x1,y1,x2,y2: ((x1,y1),(x2,y2))
        segments = [
            seg(R1+Dr1, -Wr1/2, R1-D1, -Wr1/2),                      #1

            seg(R1+Dr1,  Wr1/2, R1-D1,  Wr1/2),                      #2

            seg(R1+Dr1, -Wr1/2, R1+Dr1, -Lv2/2+Wr1),                 #3

            seg(R1+Dr1,  Wr1/2, R1+Dr1,  Lv2/2-Wr1),                 #4

            seg(R1+Dr1+Wr1, -WOr/2, R1+Dr1+Wr1, -Lv2/2),             #5

            seg(R1+Dr1+Wr1,  WOr/2, R1+Dr1+Wr1,  Lv2/2),             #6

            seg(R1+Dr1+Wr1,  Lv2/2, R1+Dr1-Lr1-Wr1,  Lv2/2),         #7

            seg(R1+Dr1+Wr1, -Lv2/2, R1+Dr1-Lr1-Wr1, -Lv2/2),         #8

            seg(R1+Dr1,  Lv2/2-Wr1, R1+Dr1-Lr1,  Lv2/2-Wr1),         #9

            seg(R1+Dr1, -Lv2/2+Wr1, R1+Dr1-Lr1, -Lv2/2+Wr1),         #10

            seg(R1+Dr1-Lr1, -Lv2/2+Wr1, R1+Dr1-Lr1, -R1+D1),         #11

            seg(R1+Dr1-Lr1-Wr1, -Lv2/2, R1+Dr1-Lr1-Wr1, -R1+D1),     #12

            seg(R1+Dr1-Lr1,  Lv2/2-Wr1, R1+Dr1-Lr1,  R1-D1),         #13

            seg(R1+Dr1-Lr1-Wr1,  Lv2/2, R1+Dr1-Lr1-Wr1,  R1-D1),     #14

            seg(R1+Dr1+Wr1, -WOr/2, R1+Dr1+Wr1+LOr, -WOr/2),         #15

            seg(R1+Dr1+Wr1,  WOr/2, R1+Dr1+Wr1+LOr,  WOr/2),         #16

            seg(R1+Dr1+Wr1+LOr, -WOr/2, R1+Dr1+Wr1+LOr+LOut, -WOut/2),#17

            seg(R1+Dr1+Wr1+LOr,  WOr/2, R1+Dr1+Wr1+LOr+LOut,  WOut/2),#18

            seg(R1+Dr1+Wr1+LOr+LOut,  WOut/2,
                R1+Dr1+Wr1+LOr+LOut+L1*cosA+R2*tanA2 - sinA*R2,
                WOut/2 + L1*sinA - R2 + cosA*R2),                    #19

            seg(R1+Dr1+Wr1+LOr+LOut, -WOut/2,
                R1+Dr1+Wr1+LOr+LOut+L1*cosA+R2*tanA2 - sinA*R2,
                -WOut/2 - L1*sinA + R2 - cosA*R2),                   #20

            seg(c3x, -WOut/2 - L1*sinA, c1x, -WOut/2 - L1*sinA),     #21

            seg(c3x,  WOut/2 + L1*sinA, c1x,  WOut/2 + L1*sinA),     #22

            seg(c3x + sinA*R2,
                -WOut/2 - L1*sinA + R2 - cosA*R2,
                R1+Dr1+Wr1+LOr+LOut+2*L1*cosA+Lr3,
                -WOut/2),                                            #23

            seg(c3x + sinA*R2,
                WOut/2 + L1*sinA - R2 + cosA*R2,
                R1+Dr1+Wr1+LOr+LOut+2*L1*cosA+Lr3,
                WOut/2),                                             #24

            seg(R1+Dr1+Wr1+LOr+LOut+2*L1*cosA+Lr3+Lr4+D1,  WOut/2,
                R1+Dr1+Wr1+LOr+LOut+2*L1*cosA+Lr3,  WOut/2),          #25

            seg(R1+Dr1+Wr1+LOr+LOut+2*L1*cosA+Lr3+Lr4+D1, -WOut/2,
                R1+Dr1+Wr1+LOr+LOut+2*L1*cosA+Lr3, -WOut/2),          #26

        ]

        return {"circles":circles,"arcs":arcs,"segments":segments,"rectangles":[]}

    # ─────────── 绘图刷新（与原程序相同） ─────────────────────────

    def updateModel(self):
        try:
            self.ax.clear(); self.geoPatch = {k: [] for k in self.params}
            g = self.calculateGeometry()
            for ctr,r in g["circles"]:
                c = mpatches.Circle(ctr,r,fill=False,edgecolor='blue',lw=1.5)
                self.ax.add_patch(c); self.geoPatch["Radius_1"].append(c)
            for ctr,r,a1,a2 in g["arcs"]:
                a = mpatches.Arc(ctr,2*r,2*r,angle=0,theta1=a1,theta2=a2,edgecolor='blue',lw=1.5)
                self.ax.add_patch(a); self.geoPatch.setdefault("Radius_2",[]).append(a)
            for p0,p1 in g["segments"]:
                ln = plt.Line2D([p0[0],p1[0]],[p0[1],p1[1]],color='blue',lw=1.5)
                self.ax.add_line(ln); self.geoPatch.setdefault("Length_r1",[]).append(ln)

            xs,ys=[],[]
            for p in self.ax.patches:
                if isinstance(p,mpatches.Circle):
                    (cx,cy),r=p.center,p.radius; xs+=[cx-r,cx+r]; ys+=[cy-r,cy+r]
                elif isinstance(p,mpatches.Arc):
                    cx,cy=p.center; xs+=[cx-p.width/2,cx+p.width/2]; ys+=[cy-p.height/2,cy+p.height/2]
            for l in self.ax.lines:
                x,y=l.get_data(); xs+=list(x); ys+=list(y)
            if not xs: xs=ys=[-1,1]
            pad=max((max(xs)-min(xs))*0.1,(max(ys)-min(ys))*0.1,1)
            self.ax.set_xlim(min(xs)-pad,max(xs)+pad); self.ax.set_ylim(min(ys)-pad,max(ys)+pad)
            self.ax.set_aspect('equal'); self.ax.grid(True,ls='--',alpha=0.4)
            self.ax.set_title("DdPCR2To1"); self.ax.set_xlabel("X (mm)"); self.ax.set_ylabel("Y (mm)")
            self.canvas.draw(); 
            if self.curHlt:self.highlightComponent(self.curHlt)
            self.stsVar.set("模型更新成功 / Model updated successfully")
        except Exception as e:
            messagebox.showerror("错误",f"模型更新失败: {e}"); self.stsVar.set(f"失败: {e}")

    # ─────────── 导出 / 导入 / 退出（保持不变） ───────────────────

    def exportDxf(self):
        try:
            f=filedialog.asksaveasfilename(defaultextension=".dxf",filetypes=[("DXF","*.dxf")]); 
            if not f:return

            import ezdxf;doc=ezdxf.new('R2010');msp=doc.modelspace();g=self.calculateGeometry()
            for c,r in g["circles"]:msp.add_circle(c,r)
            for c,r,a1,a2 in g["arcs"]:msp.add_arc(c,r,a1,a2)
            for p0,p1 in g["segments"]:msp.add_line(p0,p1)
            doc.saveas(f); self.stsVar.set(f"已导出DXF {f}")
        except Exception as e:
            messagebox.showerror("Error",f"导出DXF失败: {e}")

    def exportSvg(self):
        try:
            f=filedialog.asksaveasfilename(defaultextension=".svg",filetypes=[("SVG","*.svg")])
            if not f:return

            self.fig.savefig(f,format='svg',bbox_inches='tight'); self.stsVar.set(f"已导出SVG {f}")
        except Exception as e:
            messagebox.showerror("Error",f"导出SVG失败: {e}")

    def exportJson(self):
        try:
            f=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")]); 
            if not f:return

            data={"model_name":self.ax.get_title(),"date":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                  "parameters":{k:v.get() for k,v in self.params.items()}}
            with open(f,'w',encoding='utf-8') as fp: json.dump(data,fp,indent=4,ensure_ascii=False)
            self.stsVar.set(f"已导出JSON {f}")
        except Exception as e:
            messagebox.showerror("Error",f"导出JSON失败: {e}")

    def importJson(self):
        try:
            f=filedialog.askopenfilename(filetypes=[("JSON","*.json"),("All","*.*")]); 
            if not f:return

            with open(f,'r',encoding='utf-8') as fp:data=json.load(fp)
            for k,v in data.get("parameters",{}).items():
                if k in self.params: self.params[k].set(str(v))
            self.updateModel()
            if "model_name" in data:self.ax.set_title(data["model_name"]); self.canvas.draw()
            self.stsVar.set(f"已导入JSON {f}")
        except Exception as e:
            messagebox.showerror("Error",f"导入JSON失败: {e}")

    def quitApplication(self):
        plt.close('all'); self.master.quit(); self.master.destroy()

if __name__ == "__main__":
    root=tk.Tk(); app=MicrochannelTool(root); root.mainloop()
