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

import json

from datetime import datetime

class MicrochannelTool:
    def __init__(self, master):
        self.master = master
        copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 
                             fg="#555555", bg="#f0f0f0")
        copyright_label.pack(side=tk.BOTTOM, fill=tk.X)
        master.title("微通道几何建模工具")
        master.geometry("1100x700")
        # 前端参数

        self.params = {
            "Length_1": tk.StringVar(value="0.4"),
            "Angle": tk.StringVar(value="60"),
            "Width": tk.StringVar(value="0.2"),
            "number": tk.StringVar(value="3"),
            "Length_r1": tk.StringVar(value="1.5"),
            "Radius_1": tk.StringVar(value="0.4"),
        }
        self.defaults = {k: float(v.get()) if v.get() else 0.0 for k, v in self.params.items()}
        self.descriptions = {
            "Length_1": "内侧等腰三角形的边长 (mm)",
            "Angle": "等腰三角形顶角 (deg)",
            "Width": "流道宽度 (mm)",
            "number": "复制的特斯拉阀数量",
            "Length_r1": "接出的管道长度 (mm)",
            "Radius_1": "打孔半径 (mm)",
        }
        self.editable_params = list(self.params)
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
        statusBar = ttk.Label(self.master, textvariable=self.stsVar, relief=tk.SUNKEN, anchor=tk.W, font=self.bigFont)
        statusBar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_parameter_entries(self):
        for widget in self.scroll_content.winfo_children():
            widget.destroy()
        for param in self.editable_params:
            self.create_parameter_row(param)

    def create_parameter_row(self, param):
        frame = ttk.Frame(self.scroll_content)
        frame.pack(fill=tk.X, pady=8, padx=5)
        ttk.Label(frame, text=self.descriptions[param], font=self.bigFont, wraplength=330).pack(anchor=tk.W, pady=(0,5))
        entry = ttk.Entry(frame, textvariable=self.params[param], font=self.bigFont)
        entry.pack(fill=tk.X)
        entry.bind("<Return>", lambda e, p=param: self.parameter_changed(p))
        entry.bind("<FocusOut>", lambda e, p=param: self.parameter_changed(p))
        entry.bind("<FocusIn>", lambda e, p=param: self.highlightComponent(p))
        self.entries[param] = entry

    def parameter_changed(self, param):
        try:
            val = float(self.params[param].get())
            if param == "number" and val < 1:
                 self.params[param].set("1")
                 messagebox.showwarning("警告 / Warning", "复制数量 (number) 不能小于1 / Number cannot be less than 1.")
            self.updateModel()
        except ValueError as e:
            self.params[param].set(str(self.defaults[param]))
            messagebox.showerror("错误 / Error", f"无效的数值 / Invalid number: {e}")

    # -------- 获取参数并统一变量名 ---------
    def getParam(self, name):
        try:
            if name == "Angle_rad":
                return np.deg2rad(float(self.params["Angle"].get()))
            elif name == "cot_Angle":
                Angle = self.getParam("Angle_rad")
                return 1 / np.tan(Angle)
            elif name == "Length_1":
                return float(self.params["Length_1"].get())
            elif name == "Width":
                return float(self.params["Width"].get())
            elif name == "number":
                return int(round(float(self.params["number"].get())))
            elif name == "Length_r1":
                return float(self.params["Length_r1"].get())
            elif name == "Radius_1":
                return float(self.params["Radius_1"].get())
            # 计算参数

            elif name == "Distance_1":
                Radius_1 = self.getParam("Radius_1")
                Width = self.getParam("Width")
                val = Radius_1**2 - (Width**2)/4

                if val < 0:
                    raise ValueError("Radius_1 必须大于等于 Width/2")
                return Radius_1 - np.sqrt(val)
            elif name == "Length_2":
                Length_1 = self.getParam("Length_1")
                Angle = self.getParam("Angle_rad")
                Width = self.getParam("Width")
                return Length_1*np.tan(Angle/2) + Width

            elif name == "x_mov1":
                Length_1 = self.getParam("Length_1")
                Angle = self.getParam("Angle_rad")
                Width = self.getParam("Width")
                Length_2 = self.getParam("Length_2")
                cotA = self.getParam("cot_Angle")
                return (Length_2*(np.sin(Angle)-(1-np.cos(Angle))*cotA)
                        + Length_1-Length_1*np.cos(Angle)
                        + Width*np.sin(Angle)
                        + cotA*(Width+Length_1*np.sin(Angle)+Width*np.cos(Angle)))
            elif name == "x_mov2":
                Angle = self.getParam("Angle_rad")
                x_mov1 = self.getParam("x_mov1")
                return np.cos(Angle)*x_mov1

            elif name == "y_mov2":
                Angle = self.getParam("Angle_rad")
                x_mov1 = self.getParam("x_mov1")
                return np.sin(Angle)*x_mov1

            else:
                return float(self.params[name].get())
        except Exception as e:
            messagebox.showerror("参数错误 / Parameter Error", f"无法计算或获取参数'{name}': {e}\n将使用默认值.")
            if name in self.defaults:
                self.params[name].set(str(self.defaults[name]))
                return self.defaults[name]
            else:
                return 0.0

    def highlightComponent(self, paramName):
        self.curHlt = paramName

        for patches in self.geoPatch.values():
            for patch in patches:
                if hasattr(patch, 'set_edgecolor'): patch.set_edgecolor('blue')
                elif hasattr(patch, 'set_color'): patch.set_color('blue')
        if paramName in self.geoPatch:
            for patch in self.geoPatch[paramName]:
                if hasattr(patch, 'set_edgecolor'): patch.set_edgecolor('red')
                elif hasattr(patch, 'set_color'): patch.set_color('red')
        self.canvas.draw()
        self.stsVar.set(f"已选择 / Selected: {paramName}")

    # ------------ 关键几何函数 -------------
    def calculateGeometry(self):
        # 获取参数

        Length_1 = self.getParam("Length_1")
        Angle = self.getParam("Angle_rad")
        Angle_deg = float(self.params["Angle"].get())
        Width = self.getParam("Width")
        number = self.getParam("number")
        Length_r1 = self.getParam("Length_r1")
        Radius_1 = self.getParam("Radius_1")
        Distance_1 = self.getParam("Distance_1")
        Length_2 = self.getParam("Length_2")
        cot_Angle = self.getParam("cot_Angle")
        x_mov1 = self.getParam("x_mov1")
        x_mov2 = self.getParam("x_mov2")
        y_mov2 = self.getParam("y_mov2")

        circles = []
        arcs = []
        segments = []

        # 圆1

        x_c1 = Length_1*np.cos(Angle) - Width*np.sin(Angle) - cot_Angle*(Width + Length_1*np.sin(Angle) + Width*np.cos(Angle)) - Length_r1 - Radius_1

        y_c1 = -Width/2

        circles.append(((x_c1, y_c1), Radius_1))
        # 圆2

        x_c2 = Length_1 + (x_mov2 + x_mov1)*(number-1) + x_mov2 + Length_r1 + Distance_1 + Radius_1

        y_c2 = y_mov2*number - Width/2

        circles.append(((x_c2, y_c2), Radius_1))

        # =======================
        # 阵列部分

        # =======================
        for i in range(number-1):
            dx = i * (x_mov1 + x_mov2)
            dy = i * y_mov2

            # 圆弧1

            arc1_center = (Length_1 + dx, Length_1 * np.tan(Angle/2) + dy)
            arc1_radius = Length_1 * np.tan(Angle/2)
            arcs.append((arc1_center, arc1_radius, -90, 90+Angle_deg))
            # 圆弧2

            arc2_center = arc1_center

            arc2_radius = arc1_radius + Width

            arcs.append((arc2_center, arc2_radius, -90, 90))
            # 圆弧3

            arc3_center = (Length_1 + x_mov2 + dx, Length_1 * np.tan(Angle/2) + y_mov2 + dy)
            arc3_radius = arc1_radius

            arcs.append((arc3_center, arc3_radius, -90, 90+Angle_deg))
            # 圆弧4

            arc4_center = arc3_center

            arc4_radius = arc3_radius + Width

            arcs.append((arc4_center, arc4_radius, -90+Angle_deg, 90+Angle_deg))
            # 圆弧5

            arc5_center = (Length_1 + x_mov2 + x_mov1 + dx, Length_1 * np.tan(Angle/2) + y_mov2 + dy)
            arc5_radius = arc1_radius + Width

            arcs.append((arc5_center, arc5_radius, -90, 90))
            # 圆弧6

            arc6_center = arc5_center

            arc6_radius = arc1_radius

            arcs.append((arc6_center, arc6_radius, -90, 90+Angle_deg))

            # 线段5

            seg5_p1 = (x_mov2 + dx, y_mov2 + dy)
            seg5_p2 = (Length_1*np.cos(Angle) + x_mov2 + dx, Length_1*np.sin(Angle) + y_mov2 + dy)
            segments.append((seg5_p1, seg5_p2))
            # 线段6

            seg6_p1 = (x_mov2 + dx, y_mov2 + dy)
            seg6_p2 = (Length_1 + x_mov2 + dx, y_mov2 + dy)
            segments.append((seg6_p1, seg6_p2))
            # 线段7

            seg7_p1 = (Length_1*np.cos(Angle)-Width*np.sin(Angle)-cot_Angle*(Width+Length_1*np.sin(Angle)+Width*np.cos(Angle)) + x_mov2 + dx,
                       -Width + y_mov2 + dy)
            seg7_p2 = (Length_1*np.cos(Angle)-Width*np.sin(Angle) + x_mov2 + dx,
                       Length_1*np.sin(Angle)+Width*np.cos(Angle)+y_mov2 + dy)
            segments.append((seg7_p1, seg7_p2))
            # 线段8

            seg8_p1 = (Length_1 + dx, -Width + y_mov2 + dy)
            seg8_p2 = (Length_1 + x_mov2 + x_mov1 + dx, -Width + y_mov2 + dy)
            segments.append((seg8_p1, seg8_p2))
            # 线段9

            seg9_p1 = (x_mov2 + x_mov1 + dx, y_mov2 + dy)
            seg9_p2 = (Length_1*np.cos(Angle) + x_mov2 + x_mov1 + dx, Length_1*np.sin(Angle) + y_mov2 + dy)
            segments.append((seg9_p1, seg9_p2))
            # 线段10

            seg10_p1 = (x_mov2 + x_mov1 + dx, y_mov2 + dy)
            seg10_p2 = (Length_1 + x_mov2 + x_mov1 + dx, y_mov2 + dy)
            segments.append((seg10_p1, seg10_p2))
            # 线段11

            seg11_p1 = (Length_1 + x_mov2 + (Length_1*np.tan(Angle/2)+Width)*np.sin(Angle) + dx,
                        (Length_1)*np.tan(Angle/2)+y_mov2 + dy - (Length_1*np.tan(Angle/2)+Width)*np.cos(Angle))
            seg11_p2 = (Length_1*np.cos(Angle)-Width*np.sin(Angle)-cot_Angle*(Width+Length_1*np.sin(Angle)+Width*np.cos(Angle))
                        + 2*x_mov2 + x_mov1 + dx,
                        -Width + y_mov2*2 + dy)
            segments.append((seg11_p1, seg11_p2))

        # =======================
        # 非阵列部分

        # =======================
        # 圆弧7

        arc7_center = (Length_1 + (x_mov2 + x_mov1)*(number-1) + x_mov2,
                       Length_1 * np.tan(Angle/2) + (y_mov2)*number)
        arc7_radius = Length_1 * np.tan(Angle/2)
        arcs.append((arc7_center, arc7_radius, -90, 90+Angle_deg))
        # 圆弧8

        arc8_center = arc7_center

        arc8_radius = arc7_radius + Width

        theta_start8 = -90 + np.arccos(arc7_radius/arc8_radius)*360/(2*np.pi)
        arcs.append((arc8_center, arc8_radius, theta_start8, 90+Angle_deg))

        # 线段1

        seg1_p1 = (0, 0)
        seg1_p2 = (Length_1*np.cos(Angle), Length_1*np.sin(Angle))
        segments.append((seg1_p1, seg1_p2))
        # 线段2

        seg2_p1 = (0, 0)
        seg2_p2 = (Length_1, 0)
        segments.append((seg2_p1, seg2_p2))
        # 线段3

        seg3_p1 = (Length_1*np.cos(Angle)-Width*np.sin(Angle)-cot_Angle*(Width+Length_1*np.sin(Angle)+Width*np.cos(Angle))+cot_Angle*Width, 0)
        seg3_p2 = (Length_1*np.cos(Angle)-Width*np.sin(Angle)-cot_Angle*(Width+Length_1*np.sin(Angle)+Width*np.cos(Angle))+x_mov2, -Width + y_mov2)
        segments.append((seg3_p1, seg3_p2))
        # 线段4

        seg4_p1 = (Length_1*np.cos(Angle)-Width*np.sin(Angle)-cot_Angle*(Width+Length_1*np.sin(Angle)+Width*np.cos(Angle))+cot_Angle*Width, -Width)
        seg4_p2 = (Length_1, -Width)
        segments.append((seg4_p1, seg4_p2))
        # 线段12

        seg12_p1 = ((x_mov2 + x_mov1)*(number-1)+x_mov2, (y_mov2)*number)
        seg12_p2 = (Length_1*np.cos(Angle)+(x_mov2 + x_mov1)*(number-1)+x_mov2, Length_1*np.sin(Angle)+(y_mov2)*number)
        segments.append((seg12_p1, seg12_p2))
        # 线段13

        seg13_p1 = ((x_mov2 + x_mov1)*(number-1)+x_mov2, (y_mov2)*number)
        seg13_p2 = (Length_1+(x_mov2 + x_mov1)*(number-1)+x_mov2, (y_mov2)*number)
        segments.append((seg13_p1, seg13_p2))
        # 线段14

        seg14_p1 = (Length_1*np.cos(Angle)-Width*np.sin(Angle)-cot_Angle*(Width+Length_1*np.sin(Angle)+Width*np.cos(Angle))+(x_mov2 + x_mov1)*(number-1)+x_mov2,
                    -Width+(y_mov2)*number)
        seg14_p2 = (Length_1*np.cos(Angle)-Width*np.sin(Angle)+(x_mov2 + x_mov1)*(number-1)+x_mov2,
                    Length_1*np.sin(Angle)+Width*np.cos(Angle)+(y_mov2)*number)
        segments.append((seg14_p1, seg14_p2))
        # 线段15

        seg15_p1 = (Length_1+(x_mov2 + x_mov1)*(number-1), -Width+(y_mov2)*number)
        seg15_p2 = (Length_1+(x_mov2 + x_mov1)*(number-1)+x_mov2, -Width+(y_mov2)*number)
        segments.append((seg15_p1, seg15_p2))
        # 线段16

        seg16_p1 = (Length_1+(x_mov2 + x_mov1)*(number-1)+x_mov2+Length_r1+Distance_1, -Width+(y_mov2)*number)
        seg16_p2 = (Length_1+(x_mov2 + x_mov1)*(number-1)+x_mov2, -Width+(y_mov2)*number)
        segments.append((seg16_p1, seg16_p2))
        # 线段17

        seg17_p1 = (Length_1+(x_mov2 + x_mov1)*(number-1)+x_mov2+Length_r1+Distance_1, (y_mov2)*number)
        seg17_p2 = (Length_1+(x_mov2 + x_mov1)*(number-1)+x_mov2+np.sqrt((Length_1*np.tan(Angle/2)+Width)**2-(Length_1*np.tan(Angle/2))**2),
                   (y_mov2)*number)
        segments.append((seg17_p1, seg17_p2))

        # 线段18

        seg18_p1 = (Length_1*np.cos(Angle)-Width*np.sin(Angle)-cot_Angle*(Width+Length_1*np.sin(Angle)+Width*np.cos(Angle))+cot_Angle*Width, -Width)
        seg18_p2 = (Length_1*np.cos(Angle)-Width*np.sin(Angle)-cot_Angle*(Width+Length_1*np.sin(Angle)+Width*np.cos(Angle))-Length_r1-Distance_1, -Width)
        segments.append((seg18_p1, seg18_p2))
        # 线段19

        seg19_p1 = (Length_1*np.cos(Angle)-Width*np.sin(Angle)-cot_Angle*(Width+Length_1*np.sin(Angle)+Width*np.cos(Angle))+cot_Angle*Width, 0)
        seg19_p2 = (Length_1*np.cos(Angle)-Width*np.sin(Angle)-cot_Angle*(Width+Length_1*np.sin(Angle)+Width*np.cos(Angle))-Length_r1-Distance_1, 0)
        segments.append((seg19_p1, seg19_p2))

        return {"circles": circles, "arcs": arcs, "segments": segments}

    def updateModel(self):
        try:
            self.ax.clear()
            self.geoPatch = {k: [] for k in self.params}
            geo = self.calculateGeometry()
            # 圆

            for center, radius in geo["circles"]:
                patch = mpatches.Circle(center, radius, fill=False, edgecolor='blue', lw=1.5)
                self.ax.add_patch(patch)
                self.geoPatch["Radius_1"].append(patch)
            # 圆弧

            for center, radius, t1, t2 in geo["arcs"]:
                patch = mpatches.Arc(center, 2*radius, 2*radius, angle=0, theta1=t1, theta2=t2, edgecolor='blue', lw=1.5)
                self.ax.add_patch(patch)
                self.geoPatch["Width"].append(patch)
            # 线段

            for p0, p1 in geo["segments"]:
                line = plt.Line2D([p0[0], p1[0]], [p0[1], p1[1]], color='blue', lw=1.5)
                self.ax.add_line(line)
                self.geoPatch["Length_1"].append(line)
                self.geoPatch["number"].append(line)
            # autoscale

            all_x, all_y = [], []
            for patch in self.ax.patches:
                if isinstance(patch, mpatches.Circle):
                    center, r = patch.center, patch.radius

                    all_x.extend([center[0] - r, center[0] + r])
                    all_y.extend([center[1] - r, center[1] + r])
                elif isinstance(patch, mpatches.Arc):
                    center, w, h = patch.center, patch.width, patch.height

                    all_x.extend([center[0] - w/2, center[0] + w/2])
                    all_y.extend([center[1] - h/2, center[1] + h/2])
            for line in self.ax.lines:
                x_data, y_data = line.get_data()
                all_x.extend(x_data)
                all_y.extend(y_data)
            if not all_x or not all_y:
                all_x, all_y = [-1, 1], [-1, 1]
            pad = max((max(all_x)-min(all_x))*0.1, (max(all_y)-min(all_y))*0.1, 1)
            self.ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
            self.ax.set_ylim(min(all_y) - pad, max(all_y) + pad)
            self.ax.set_aspect('equal', adjustable='box')
            self.ax.grid(True, linestyle='--', alpha=0.5)
            self.ax.set_title("TeslaValveArray", fontsize=14)
            self.ax.set_xlabel("X (mm)")
            self.ax.set_ylabel("Y (mm)")
            self.canvas.draw()
            if self.curHlt:
                self.highlightComponent(self.curHlt)
            self.stsVar.set("模型更新成功 / Model updated successfully")
        except Exception as e:
            messagebox.showerror("错误 / Error", f"模型更新失败 / Failed to update model: {e}")
            self.stsVar.set(f"失败 / Failed: {e}")

    def exportDxf(self):
        try:
            filename = filedialog.asksaveasfilename(defaultextension=".dxf", filetypes=[("DXF Files", "*.dxf"), ("All Files", "*.*")], title="保存DXF / Save DXF")
            if not filename: return

            import ezdxf

            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            geo = self.calculateGeometry()
            for center, radius in geo["circles"]:
                msp.add_circle(center, radius)
            for center, radius, t1, t2 in geo["arcs"]:
                msp.add_arc(center, radius, t1, t2)
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
            filename = filedialog.asksaveasfilename(defaultextension=".svg", filetypes=[("SVG Files", "*.svg"), ("All Files", "*.*")], title="保存SVG / Save SVG")
            if not filename: return

            self.fig.savefig(filename, format='svg', bbox_inches='tight')
            self.stsVar.set(f"已导出SVG / SVG Exported: {filename}")
            messagebox.showinfo("成功 / Success", f"已导出到SVG / Exported to SVG:\n{filename}")
        except Exception as e:
            messagebox.showerror("错误 / Error", f"导出SVG失败 / Failed to export SVG: {e}")
            self.stsVar.set("导出失败 / Export Failed")

    def exportJson(self):
        try:
            filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")], title="保存JSON / Save JSON")
            if not filename: return

            data = {"model_name": self.ax.get_title(), "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "parameters": {k: v.get() for k, v in self.params.items()}}
            with open(filename, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
            self.stsVar.set(f"已导出JSON / JSON Exported: {filename}")
            messagebox.showinfo("成功 / Success", f"已导出到JSON / Exported to JSON:\n{filename}")
        except Exception as e:
            messagebox.showerror("错误 / Error", f"导出JSON失败 / Failed to export JSON: {e}")
            self.stsVar.set("导出失败 / Export Failed")

    def importJson(self):
        try:
            filename = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")], title="导入JSON / Import JSON")
            if not filename: return

            with open(filename, 'r', encoding='utf-8') as f: data = json.load(f)
            imported_params = data.get("parameters", {})
            for key, value in imported_params.items():
                if key in self.params: self.params[key].set(str(value))
            self.updateModel()
            if "model_name" in data: self.ax.set_title(data["model_name"], fontsize=14); self.canvas.draw()
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
