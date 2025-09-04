# Copyright (c) 2025 [Grant]
# Licensed under the MIT License.
# See LICENSE in the project root for license information.
import numpy as np

import matplotlib.pyplot as plt

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

import matplotlib.patches as mpatches

import tkinter as tk

from tkinter import ttk, filedialog, messagebox

import ezdxf

import math

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
        # ----------------- 1. 参数定义 ------------------
        self.params = {
            "Radius_1": tk.StringVar(value="0.4"),         # 打孔半径

            "Width_1": tk.StringVar(value="0.2"),          # 螺旋宽度

            "Circle": tk.StringVar(value="5"),             # 圈数

            "Distance_3": tk.StringVar(value="0.8"),       # 螺旋初始距离

            "Length_r1": tk.StringVar(value="0.2"),        # 打孔流道长度

            "Length_v1": tk.StringVar(value="0.5"),        # 打孔流道宽度

            "Angle": tk.StringVar(value="30"),             # 出口流道夹角(度)
            "Length_Out": tk.StringVar(value="2.0"),       # 出口流道距离

            # 计算参数不出现在UI，仅后台用

        }
        self.defaults = {k: float(v.get()) if v.get() else 0.0 for k, v in self.params.items()}

        self.descriptions = {
            "Radius_1": "打孔的半径（mm）/ Hole radius",
            "Width_1": "螺旋宽度（mm）/ Spiral width",
            "Circle": "圈数 / Number of turns",
            "Distance_3": "螺旋初始距离（mm）/ Initial spiral distance",
            "Length_r1": "中间打孔流道的长度（mm）/ Middle hole channel length",
            "Length_v1": "中间打孔流道的宽度（mm）/ Middle hole channel width",
            "Angle": "出口流道夹角（度）/ Outlet angle (deg)",
            "Length_Out": "出口流道距离（mm）/ Outlet channel length",
        }
        self.editable_params = [
            "Radius_1", "Width_1", "Circle", "Distance_3", "Length_r1",
            "Length_v1", "Angle", "Length_Out"
        ]
        # 计算参数列表，后台使用，不显示在UI

        self.calculated_params = ["Distance_1", "Distance_2"]

        # ----------------- 2. UI和绘图初始化 ------------------
        self.bigFont = ('Helvetica', 12)
        self.headerFont = ('Helvetica', 12, 'bold')

        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.geoPatch = {k: [] for k in self.params}
        self.stsVar = tk.StringVar(value="就绪 / Ready")
        self.curHlt = None

        self.entries = {}

        self.setupUi()
        master.protocol("WM_DELETE_WINDOW", self.quitApplication)
        self.updateModel()

    def setupUi(self):
        # 左侧参数面板

        paramFrm = ttk.Frame(self.master)
        paramFrm.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y, expand=True)

        # 参数滚动区域

        param_scroll_frame = ttk.LabelFrame(paramFrm, text="参数 / Parameters")
        param_scroll_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        canvas = tk.Canvas(param_scroll_frame, width=330)
        scrollbar = ttk.Scrollbar(param_scroll_frame, orient="vertical", command=canvas.yview)
        self.scroll_content = ttk.Frame(canvas)

        self.scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

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

        statusBar = ttk.Label(self.master, textvariable=self.stsVar,
                             relief=tk.SUNKEN, anchor=tk.W, font=self.bigFont)
        statusBar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_parameter_entries(self):
        for widget in self.scroll_content.winfo_children():
            widget.destroy()
        for param in self.editable_params:  # 只显示可编辑参数

            self.create_parameter_row(param)

    def create_parameter_row(self, param):
        frame = ttk.Frame(self.scroll_content)
        frame.pack(fill=tk.X, pady=8, padx=5)
        ttk.Label(frame, text=self.descriptions[param],
                font=self.bigFont, wraplength=330).pack(anchor=tk.W, pady=(0,5))
        entry = ttk.Entry(frame, textvariable=self.params[param], font=self.bigFont)
        entry.pack(fill=tk.X)
        entry.bind("<Return>", lambda e, p=param: self.parameter_changed(p))
        entry.bind("<FocusOut>", lambda e, p=param: self.parameter_changed(p))
        entry.bind("<FocusIn>", lambda e, p=param: self.highlightComponent(p))
        self.entries[param] = entry

    def parameter_changed(self, param):
        try:
            value = self.params[param].get()
            if param == "Angle":
                angle_value = float(value)
                if angle_value <= 0 or angle_value >= 180:
                    raise ValueError("角度需在0到180度之间 / Angle must be in (0, 180)")
            float(value)
            self.updateModel()
        except ValueError:
            self.params[param].set(str(self.defaults[param]))
            messagebox.showerror("错误 / Error", "无效的数值 / Invalid number")

    def getParam(self, name):
        try:
            if name == "Distance_1":
                radius_1 = float(self.params["Radius_1"].get())
                width_1 = float(self.params["Width_1"].get())
                v = radius_1 ** 2 - (width_1 / 2) ** 2

                if v < 0: return 0.0

                return radius_1 - math.sqrt(v)
            elif name == "Distance_2":
                width_1 = float(self.params["Width_1"].get())
                circle = int(float(self.params["Circle"].get()))
                return width_1 * 2 * circle

            elif name == "Angle":
                return math.radians(float(self.params["Angle"].get()))
            else:
                return float(self.params[name].get())
        except Exception:
            # fallback

            if name in self.defaults:
                self.params[name].set(str(self.defaults[name]))
                return self.defaults[name]
            else:
                return 0.0

    def highlightComponent(self, paramName):
        self.curHlt = paramName

        for patches in self.geoPatch.values():
            for patch in patches:
                if hasattr(patch, 'set_edgecolor'):
                    patch.set_edgecolor('blue')
                elif hasattr(patch, 'set_color'):
                    patch.set_color('blue')
        if paramName in self.geoPatch:
            for patch in self.geoPatch[paramName]:
                if hasattr(patch, 'set_edgecolor'):
                    patch.set_edgecolor('red')
                elif hasattr(patch, 'set_color'):
                    patch.set_color('red')

        self.canvas.draw()
        self.stsVar.set(f"已选择 / Selected: {paramName}")

    def calculateGeometry(self):
        Radius_1 = self.getParam("Radius_1")
        Width_1 = self.getParam("Width_1")
        Circle = int(self.getParam("Circle"))
        Distance_3 = self.getParam("Distance_3")
        Length_r1 = self.getParam("Length_r1")
        Length_v1 = self.getParam("Length_v1")
        Angle = self.getParam("Angle")  # radians

        Length_Out = self.getParam("Length_Out")
        Distance_1 = self.getParam("Distance_1")
        Distance_2 = self.getParam("Distance_2")

        # 圆1

        circle1_center = (0, -Width_1/2-Length_v1-Radius_1)
        circle1_radius = Radius_1

        # 圆2

        x2 = Width_1/2+Distance_2+Length_v1+(Length_Out+Radius_1)*math.cos(Angle)+Width_1*math.sin(Angle)/2

        y2 = Distance_2+Width_1/2+(Length_Out+Radius_1)*math.sin(Angle)-Width_1*math.cos(Angle)/2

        circle2_center = (x2, y2)
        circle2_radius = Radius_1

        # 圆3

        x3 = x2

        y3 = Distance_2-Width_1/2-(Radius_1+Length_Out)*math.sin(Angle)+Width_1*math.cos(Angle)/2

        circle3_center = (x3, y3)
        circle3_radius = Radius_1

        # 圆弧

        arc_center = (Length_r1/2, -Width_1/2-Length_v1/2-Distance_1/2+(Length_v1+Distance_1)/2)
        arc_radius = Width_1

        arc_theta1 = 90

        arc_theta2 = 180

        # 线段

        seg1_p0 = (Length_r1/2, -Width_1/2-Length_v1/2-Distance_1/2-(Length_v1+Distance_1)/2)
        seg1_p1 = (Length_r1/2, -Width_1/2-Length_v1/2-Distance_1/2+(Length_v1+Distance_1)/2)
        seg2_p0 = (-Length_r1/2, seg1_p0[1])
        seg2_p1 = (-Length_r1/2, seg1_p1[1])
        seg3_p0 = (Width_1/2, Distance_2+Width_1/2)
        seg3_p1 = (Width_1/2+Distance_2+Length_v1, Distance_2+Width_1/2)
        seg4_p0 = (Width_1/2, Distance_2-Width_1/2)
        seg4_p1 = (Width_1/2+Distance_2+Length_v1, Distance_2-Width_1/2)
        seg5_p0 = (
            Width_1/2+Distance_2+Length_v1+(Distance_1+Length_Out)*math.cos(Angle),
            Distance_2+Width_1/2+(Distance_1+Length_Out)*math.sin(Angle)
        )
        seg5_p1 = (Width_1/2+Distance_2+Length_v1, Distance_2+Width_1/2)
        seg6_p0 = (
            Width_1/2+Distance_2+Length_v1+(Distance_1+Length_Out)*math.cos(Angle),
            Distance_2-Width_1/2-(Distance_1+Length_Out)*math.sin(Angle)
        )
        seg6_p1 = (Width_1/2+Distance_2+Length_v1, Distance_2-Width_1/2)
        seg7_p0 = (Width_1/2+Distance_2+Length_v1+Width_1/math.sin(Angle), Distance_2+Width_1/2)
        seg7_p1 = (
            Width_1/2+Distance_2+Length_v1+(Distance_1+Length_Out)*math.cos(Angle)+Width_1*math.sin(Angle),
            Distance_2+Width_1/2+(Distance_1+Length_Out)*math.sin(Angle)-Width_1*math.cos(Angle)
        )
        seg8_p0 = (Width_1/2+Distance_2+Length_v1+Width_1/math.sin(Angle), Distance_2-Width_1/2)
        seg8_p1 = (
            Width_1/2+Distance_2+Length_v1+(Distance_1+Length_Out)*math.cos(Angle)+Width_1*math.sin(Angle),
            Distance_2-Width_1/2-(Distance_1+Length_Out)*math.sin(Angle)+Width_1*math.cos(Angle)
        )
        seg9_p0 = (Width_1/2+Distance_2+Length_v1+Width_1/math.sin(Angle), Distance_2+Width_1/2)
        seg9_p1 = (
            Width_1/2+Distance_2+Length_v1+Width_1/math.sin(Angle)-Width_1/2/math.tan(Angle),
            Distance_2

        )
        seg10_p0 = (Width_1/2+Distance_2+Length_v1+Width_1/math.sin(Angle), Distance_2-Width_1/2)
        seg10_p1 = (
            Width_1/2+Distance_2+Length_v1+Width_1/math.sin(Angle)-Width_1/2/math.tan(Angle),
            Distance_2

        )

        # 螺旋

        spiral_points1 = []
        spiral_points2 = []
        s_range = np.linspace(0, 1, 500)
        for s in s_range:
            t = 2*math.pi*s*Circle

            r1 = Distance_2*s+Distance_3+Width_1

            r2 = Distance_2*s+Distance_3

            x0 = Length_r1/2 + math.sin(t)*r1

            y0 = -Distance_3-Width_1/2 + math.cos(t)*r1

            x1 = Length_r1/2 + math.sin(t)*r2

            y1 = -Distance_3-Width_1/2 + math.cos(t)*r2

            spiral_points1.append((x0, y0))
            spiral_points2.append((x1, y1))

        return {
            "circle1": (circle1_center, circle1_radius),
            "circle2": (circle2_center, circle2_radius),
            "circle3": (circle3_center, circle3_radius),
            "arc1": (arc_center, arc_radius, arc_theta1, arc_theta2),
            "segments": [
                (seg1_p0, seg1_p1), (seg2_p0, seg2_p1), (seg3_p0, seg3_p1), (seg4_p0, seg4_p1),
                (seg5_p0, seg5_p1), (seg6_p0, seg6_p1), (seg7_p0, seg7_p1), (seg8_p0, seg8_p1),
                (seg9_p0, seg9_p1), (seg10_p0, seg10_p1)
            ],
            "spiral1": spiral_points1,
            "spiral2": spiral_points2,
        }

    def updateModel(self):
        try:
            # 更新计算参数（但不显示在UI）
            d1 = self.getParam("Distance_1")
            d2 = self.getParam("Distance_2")

            self.ax.clear()
            for key in self.geoPatch:
                self.geoPatch[key] = []

            geo = self.calculateGeometry()

            # 圆

            c1 = mpatches.Circle(geo["circle1"][0], geo["circle1"][1], fill=False, edgecolor='blue', lw=2)
            self.ax.add_patch(c1)
            self.geoPatch["Radius_1"].append(c1)
            c2 = mpatches.Circle(geo["circle2"][0], geo["circle2"][1], fill=False, edgecolor='blue', lw=2)
            self.ax.add_patch(c2)
            self.geoPatch["Radius_1"].append(c2)
            c3 = mpatches.Circle(geo["circle3"][0], geo["circle3"][1], fill=False, edgecolor='blue', lw=2)
            self.ax.add_patch(c3)
            self.geoPatch["Radius_1"].append(c3)

            # 圆弧

            center, radius, theta1, theta2 = geo["arc1"]
            arc = mpatches.Arc(center, 2*radius, 2*radius, angle=0, theta1=theta1, theta2=theta2, edgecolor='blue', lw=2)
            self.ax.add_patch(arc)
            self.geoPatch["Width_1"].append(arc)

            # 线段

            for idx, (p0, p1) in enumerate(geo["segments"], 1):
                line = plt.Line2D([p0[0], p1[0]], [p0[1], p1[1]], color='blue', lw=2)
                self.ax.add_line(line)
                self.geoPatch["Width_1"].append(line)

            # 螺旋

            x_sp1, y_sp1 = zip(*geo["spiral1"])
            x_sp2, y_sp2 = zip(*geo["spiral2"])
            line1 = plt.Line2D(x_sp1, y_sp1, color='blue', lw=2)
            line2 = plt.Line2D(x_sp2, y_sp2, color='blue', lw=2)
            self.ax.add_line(line1)
            self.ax.add_line(line2)
            self.geoPatch["Circle"].extend([line1, line2])

            # 边界自适应

            all_x = []
            all_y = []

            # 螺旋

            if len(geo["spiral1"]) > 0:
                x_sp1, y_sp1 = zip(*geo["spiral1"])
                all_x += list(x_sp1)
                all_y += list(y_sp1)
            else:
                x_sp1 = y_sp1 = []

            if len(geo["spiral2"]) > 0:
                x_sp2, y_sp2 = zip(*geo["spiral2"])
                all_x += list(x_sp2)
                all_y += list(y_sp2)
            else:
                x_sp2 = y_sp2 = []

            # 圆心和半径极值

            for ci in ["circle1", "circle2", "circle3"]:
                cx, cy = geo[ci][0]
                r = geo[ci][1]
                all_x += [cx, cx - r, cx + r]
                all_y += [cy, cy - r, cy + r]

            # 线段端点

            for p0, p1 in geo["segments"]:
                all_x += [p0[0], p1[0]]
                all_y += [p0[1], p1[1]]

            # 弧的圆心极值

            arc_center, arc_radius, _, _ = geo["arc1"]
            all_x += [arc_center[0], arc_center[0] - arc_radius, arc_center[0] + arc_radius]
            all_y += [arc_center[1], arc_center[1] - arc_radius, arc_center[1] + arc_radius]

            pad = 2

            self.ax.set_xlim(min(all_x)-pad, max(all_x)+pad)
            self.ax.set_ylim(min(all_y)-pad, max(all_y)+pad)
            self.ax.set_aspect('equal')
            self.ax.grid(True, linestyle='--', alpha=0.5)

            # 添加标题
            self.ax.set_title("DualSpiral", fontsize=14)
            self.ax.set_xlabel("")
            self.ax.set_ylabel("")

            if self.curHlt:
                self.highlightComponent(self.curHlt)
        except Exception as e:
            messagebox.showerror("错误 / Error", str(e))
            self.stsVar.set("失败 / Failed: {str(e)}")

    # ----------- 这里开始 exportDxf(self): ------------
    def exportDxf(self):
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".dxf",
                filetypes=[("DXF Files", "*.dxf"), ("All Files", "*.*")],
                title="保存DXF / Save DXF"
            )
            if not filename:
                return

            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            geo = self.calculateGeometry()

            # 圆

            msp.add_circle(geo["circle1"][0], geo["circle1"][1])
            msp.add_circle(geo["circle2"][0], geo["circle2"][1])
            msp.add_circle(geo["circle3"][0], geo["circle3"][1])

            # 圆弧

            center, radius, theta1, theta2 = geo["arc1"]
            msp.add_arc(center, radius, theta1, theta2)

            # 线段

            for p0, p1 in geo["segments"]:
                msp.add_line(p0, p1)

            # 螺旋

            # 用多段线近似

            msp.add_lwpolyline(geo["spiral1"])
            msp.add_lwpolyline(geo["spiral2"])

            doc.saveas(filename)
            self.stsVar.set(f"已导出DXF / DXF Exported: {filename}")
            messagebox.showinfo("成功 / Success", f"已导出到DXF / Exported to DXF:\n{filename}")

        except Exception as e:
            messagebox.showerror("错误 / Error", str(e))
            self.stsVar.set("导出失败 / Export Failed")
    def exportSvg(self):
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".svg",
                filetypes=[("SVG Files", "*.svg"), ("All Files", "*.*")],
                title="保存SVG / Save SVG"
            )
            if not filename:
                return

            self.fig.savefig(filename, format='svg', bbox_inches='tight')
            self.stsVar.set(f"已导出SVG / SVG Exported: {filename}")
            messagebox.showinfo("成功 / Success", f"已导出到SVG / Exported to SVG:\n{filename}")
        except Exception as e:
            messagebox.showerror("错误 / Error", str(e))
            self.stsVar.set("导出失败 / Export Failed")

    # 新增JSON导出功能
    def exportJson(self):
        try:
            # 打开文件对话框
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                title="保存JSON / Save JSON"
            )

            if not filename:
                return

            # 获取图形预览数据
            preview_title = self.ax.get_title()

            # 准备要导出的数据
            data = {
                "title": preview_title,  # 图形预览标题
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "parameters": {}
            }

            # 添加所有参数值
            for key, var in self.params.items():
                if var.get():  # 只添加有值的参数
                    data["parameters"][key] = float(var.get())

            # 导出JSON
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            self.stsVar.set(f"已导出JSON / JSON Exported: {filename}")
            messagebox.showinfo("成功 / Success", f"已导出到JSON / Exported to JSON:\n{filename}")

        except Exception as e:
            messagebox.showerror("错误 / Error", str(e))
            self.stsVar.set("导出失败 / Export Failed")

    # 新增JSON导入功能
    def importJson(self):
        try:
            # 打开文件对话框
            filename = filedialog.askopenfilename(
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
                title="导入JSON / Import JSON"
            )

            if not filename:
                return

            # 读取JSON文件
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取图形预览标题
            preview_title = data.get("title", "Asymmetric_Serpentine_Single")

            # 设置图形标题
            self.ax.set_title(preview_title)

            # 更新参数
            params = data.get("parameters", {})

            for key, value in params.items():
                if key in self.params:
                    self.params[key].set(str(value))

            # 更新模型
            self.updateModel()

            self.stsVar.set(f"已导入JSON / JSON Imported: {filename}")
            messagebox.showinfo("成功 / Success", f"已导入JSON / Imported from JSON:\n{filename}")

        except Exception as e:
            messagebox.showerror("错误 / Error", str(e))
            self.stsVar.set("导入失败 / Import Failed")

    def quitApplication(self):
        plt.close('all')
        self.master.quit()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MicrochannelTool(root)
    root.mainloop()
