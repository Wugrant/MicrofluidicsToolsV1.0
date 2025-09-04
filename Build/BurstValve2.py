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
        # 前端参数
        self.params = {
            "Length_r1": tk.StringVar(value="5"),
            "Width_r1": tk.StringVar(value="0.2"),
            "Radius_1": tk.StringVar(value="0.4"),
            "Length_r2": tk.StringVar(value="1.7"),
            "Number_v": tk.StringVar(value="5"),
            "Number_r": tk.StringVar(value="3"),
            "Distance_v": tk.StringVar(value="0.05"),
            "Distance_r": tk.StringVar(value="0.15"),
            "Length_3": tk.StringVar(value="0.6"),
            "Radius_2": tk.StringVar(value="0.2"),
            "Angle_1": tk.StringVar(value="60"),
            "Width_r2": tk.StringVar(value="0.1"),
            "Length_r3": tk.StringVar(value="0.3"),
        }
        self.defaults = {k: float(v.get()) if v.get() else 0.0 for k, v in self.params.items()}
        self.descriptions = {
            "Length_r1": "流道距离 Length_r1 (mm)",
            "Width_r1": "流道宽度 Width_r1 (mm)",
            "Radius_1": "打孔半径 Radius_1 (mm)",
            "Length_r2": "阀体直边长度 Length_r2 (mm)",
            "Number_v": "微柱列数 Number_v",
            "Number_r": "微柱行数 Number_r",
            "Distance_v": "列间距 Distance_v (mm)",
            "Distance_r": "行间距 Distance_r (mm)",
            "Length_3": "阀体斜边 Length_3 (mm)",
            "Radius_2": "阀体倒圆角半径 Radius_2 (mm)",
            "Angle_1": "阀体斜边角度 Angle_1 (deg)",
            "Width_r2": "微柱宽度 Width_r2 (mm)",
            "Length_r3": "微柱长度 Length_r3 (mm)",
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
            if "Number" in param and val < 1:
                self.params[param].set("1")
                messagebox.showwarning("警告 / Warning", f"{param} 不能小于1 / {param} cannot be less than 1.")
            self.updateModel()
        except ValueError as e:
            self.params[param].set(str(self.defaults[param]))
            messagebox.showerror("错误 / Error", f"无效的数值 / Invalid number: {e}")

    def getParam(self, name):
        try:
            if name in self.params:
                return float(self.params[name].get())
            elif name == "Angle_1_rad":
                return np.deg2rad(self.getParam("Angle_1"))
            elif name == "Distance_1":
                Radius_1 = self.getParam("Radius_1")
                Width_r1 = self.getParam("Width_r1")
                val = Radius_1**2 - (Width_r1**2)/4

                if val < 0:
                    raise ValueError("Radius_1 必须大于等于 Width_r1/2")
                return Radius_1 - np.sqrt(val)
            elif name == "Length_1":
                Length_3 = self.getParam("Length_3")
                Angle_1_rad = self.getParam("Angle_1_rad")
                return Length_3 * np.cos(Angle_1_rad)
            elif name == "Length_5":
                Length_3 = self.getParam("Length_3")
                Angle_1_rad = self.getParam("Angle_1_rad")
                return 2 * Length_3 * np.sin(Angle_1_rad)
            elif name == "Mov_x":
                Distance_v = self.getParam("Distance_v")
                Length_r3 = self.getParam("Length_r3")
                return Distance_v + Length_r3

            elif name == "Mov_y":
                Distance_r = self.getParam("Distance_r")
                Width_r2 = self.getParam("Width_r2")
                return Distance_r + Width_r2

            else:
                return 0.0

        except Exception as e:
            messagebox.showerror("参数错误 / Parameter Error", f"无法计算或获取参数'{name}': {e}")
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

    def calculateGeometry(self):
        Length_r1 = self.getParam("Length_r1")
        Width_r1 = self.getParam("Width_r1")
        Radius_1 = self.getParam("Radius_1")
        Length_r2 = self.getParam("Length_r2")
        Number_v = int(round(self.getParam("Number_v")))
        Number_r = int(round(self.getParam("Number_r")))
        Distance_v = self.getParam("Distance_v")
        Distance_r = self.getParam("Distance_r")
        Length_3 = self.getParam("Length_3")
        Radius_2 = self.getParam("Radius_2")

        Angle_1 = self.getParam("Angle_1")
        Angle_1_rad = self.getParam("Angle_1_rad")
        Distance_1 = self.getParam("Distance_1")
        Length_1 = self.getParam("Length_1")
        Length_5 = self.getParam("Length_5")
        Mov_x = self.getParam("Mov_x")
        Mov_y = self.getParam("Mov_y")
        Width_r2 = self.getParam("Width_r2")
        Length_r3 = self.getParam("Length_r3")

        # 圆1

        circles = []
        c1 = (-Radius_1, Width_r1/2)
        circles.append((c1, Radius_1))
        # 圆2

        c2 = (Length_r1+2*Length_1+Length_r2+Length_r1+Radius_1, Width_r1/2)
        circles.append((c2, Radius_1))

        # 圆弧

        arcs = []
        arc1_center = (Length_r1+Length_1+Radius_2*np.tan(Angle_1_rad/2), Width_r1+Length_1*np.tan(Angle_1_rad)-Radius_2)
        arcs.append((arc1_center, Radius_2, 90, 90+Angle_1))
        arc2_center = (Length_r1+Length_1+Radius_2*np.tan(Angle_1_rad/2), -Length_1*np.tan(Angle_1_rad)+Radius_2)
        arcs.append((arc2_center, Radius_2, -90-Angle_1, -90))
        arc3_center = (Length_r1+Length_1+Length_r2-Radius_2*np.tan(Angle_1_rad/2), Width_r1+Length_1*np.tan(Angle_1_rad)-Radius_2)
        arcs.append((arc3_center, Radius_2, 90-Angle_1, 90))
        arc4_center = (Length_r1+Length_1+Length_r2-Radius_2*np.tan(Angle_1_rad/2), -Length_1*np.tan(Angle_1_rad)+Radius_2)
        arcs.append((arc4_center, Radius_2, -90, -90+Angle_1))

        # 线段

        segments = []
        seg1_p1 = (-Distance_1, Width_r1)
        seg1_p2 = (Length_r1, Width_r1)
        segments.append((seg1_p1, seg1_p2))
        seg2_p1 = (-Distance_1, 0)
        seg2_p2 = (Length_r1, 0)
        segments.append((seg2_p1, seg2_p2))
        seg3_p1 = (Length_r1, Width_r1)
        seg3_p2 = (Length_r1+Length_1+Radius_2*np.tan(Angle_1_rad/2)-Radius_2*np.sin(Angle_1_rad),
                   Width_r1+Length_1*np.tan(Angle_1_rad)-Radius_2+Radius_2*np.cos(Angle_1_rad))
        segments.append((seg3_p1, seg3_p2))
        seg4_p1 = (Length_r1+Length_1+Radius_2*np.tan(Angle_1_rad/2), Width_r1+Length_1*np.tan(Angle_1_rad))
        seg4_p2 = (Length_r1+Length_1+Length_r2-Radius_2*np.tan(Angle_1_rad/2), Width_r1+Length_1*np.tan(Angle_1_rad))
        segments.append((seg4_p1, seg4_p2))
        seg5_p1 = (Length_r1+2*Length_1+Length_r2, Width_r1)
        seg5_p2 = (Length_r1+Length_1+Length_r2-Radius_2*np.tan(Angle_1_rad/2)+Radius_2*np.sin(Angle_1_rad),
                   Width_r1+Length_1*np.tan(Angle_1_rad)-Radius_2+Radius_2*np.cos(Angle_1_rad))
        segments.append((seg5_p1, seg5_p2))
        seg6_p1 = (Length_r1, 0)
        seg6_p2 = (Length_r1+Length_1+Radius_2*np.tan(Angle_1_rad/2)-Radius_2*np.sin(Angle_1_rad),
                   -Length_1*np.tan(Angle_1_rad)+Radius_2-Radius_2*np.cos(Angle_1_rad))
        segments.append((seg6_p1, seg6_p2))
        seg7_p1 = (Length_r1+Length_1+Radius_2*np.tan(Angle_1_rad/2), -Length_1*np.tan(Angle_1_rad))
        seg7_p2 = (Length_r1+Length_1+Length_r2-Radius_2*np.tan(Angle_1_rad/2), -Length_1*np.tan(Angle_1_rad))
        segments.append((seg7_p1, seg7_p2))
        seg8_p1 = (Length_r1+2*Length_1+Length_r2, 0)
        seg8_p2 = (Length_r1+Length_1+Length_r2-Radius_2*np.tan(Angle_1_rad/2)+Radius_2*np.sin(Angle_1_rad),
                   -Length_1*np.tan(Angle_1_rad)+Radius_2-Radius_2*np.cos(Angle_1_rad))
        segments.append((seg8_p1, seg8_p2))
        seg9_p1 = (Length_r1+2*Length_1+Length_r2, 0)
        seg9_p2 = (Length_r1+2*Length_1+Length_r2+Length_r1+Distance_1, 0)
        segments.append((seg9_p1, seg9_p2))
        seg10_p1 = (Length_r1+2*Length_1+Length_r2, Width_r1)
        seg10_p2 = (Length_r1+2*Length_1+Length_r2+Length_r1+Distance_1, Width_r1)
        segments.append((seg10_p1, seg10_p2))

        # 矩形阵列

        rectangles = []
        rect_x0 = Length_r1+Length_1+Length_r2/2-Length_r3/2-((Number_v-1)*Mov_x/2)
        rect_y0 = Width_r1/2-Width_r2/2-((Number_r-1)*Mov_y/2)
        for i in range(Number_v):
            for j in range(Number_r):
                x = rect_x0 + i*Mov_x

                y = rect_y0 + j*Mov_y

                rectangles.append((x, y, Length_r3, Width_r2))  # 左下角x,y,宽,高

        return {"circles": circles, "arcs": arcs, "segments": segments, "rectangles": rectangles}

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
                self.geoPatch["Radius_2"].append(patch)
            # 线段

            for p0, p1 in geo["segments"]:
                line = plt.Line2D([p0[0], p1[0]], [p0[1], p1[1]], color='blue', lw=1.5)
                self.ax.add_line(line)
                self.geoPatch.setdefault("Length_1", []).append(line)
                self.geoPatch["Length_r1"].append(line)
            # 矩形阵列

            for x, y, w, h in geo["rectangles"]:
                patch = mpatches.Rectangle((x, y), w, h, fill=False, edgecolor='blue', lw=1.5)
                self.ax.add_patch(patch)
                self.geoPatch["Length_r3"].append(patch)
                self.geoPatch["Width_r2"].append(patch)
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
                elif isinstance(patch, mpatches.Rectangle):
                    x0, y0 = patch.get_xy()
                    w, h = patch.get_width(), patch.get_height()
                    all_x.extend([x0, x0+w])
                    all_y.extend([y0, y0+h])
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
            self.ax.set_title("BurstValve2", fontsize=14)
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
            for x, y, w, h in geo["rectangles"]:
                msp.add_lwpolyline([(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)])
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
