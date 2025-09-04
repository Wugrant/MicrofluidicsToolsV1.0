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
        # ----------------- 1. REPLACED PARAMETERS ------------------
        self.params = {
            "Radius_1": tk.StringVar(value="0.4"),
            "Width_1": tk.StringVar(value="0.2"),
            "Circle": tk.StringVar(value="5"),
            "Distance_3": tk.StringVar(value="0.8"),
            "Length_r1": tk.StringVar(value="0.2"),
            "Length_v1": tk.StringVar(value="0.5"),
            "Angle": tk.StringVar(value="30"),
            "Length_Out": tk.StringVar(value="2.0"),
        }
        self.defaults = {k: float(v.get()) if v.get() else 0.0 for k, v in self.params.items()}

        self.descriptions = {
            "Radius_1": "打孔的半径 (mm) / Hole radius",
            "Width_1": "螺旋的宽度 (mm) / Spiral width",
            "Circle": "圈数 (正整数) / Number of turns (integer)",
            "Distance_3": "螺旋的初始距离 (mm) / Initial spiral distance",
            "Length_r1": "中间打孔流道的长度 (mm) / Middle hole channel length",
            "Length_v1": "中间打孔流道的宽度 (mm) / Middle hole channel width",
            "Angle": "出口流道夹角 (度) / Outlet angle (deg)",
            "Length_Out": "出口流道距离 (mm) / Outlet channel length",
        }
        self.editable_params = [
            "Radius_1", "Width_1", "Circle", "Distance_3", "Length_r1",
            "Length_v1", "Angle", "Length_Out"
        ]
        self.calculated_params = ["Distance_1", "Distance_2"]
        # ----------------- END OF REPLACEMENT ------------------

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
        # --- This section remains unchanged ---
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
        # --- This section remains unchanged ---
        for widget in self.scroll_content.winfo_children():
            widget.destroy()
        for param in self.editable_params:
            self.create_parameter_row(param)

    def create_parameter_row(self, param):
        # --- This section remains unchanged ---
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
        # --- This section remains unchanged ---
        try:
            value = self.params[param].get()
            if param == "Angle":
                angle_value = float(value)
                if angle_value <= 0 or angle_value >= 180:
                    raise ValueError("角度需在0到180度之间 / Angle must be in (0, 180)")
            float(value)
            self.updateModel()
        except ValueError as e:
            self.params[param].set(str(self.defaults[param]))
            messagebox.showerror("错误 / Error", f"无效的数值 / Invalid number: {e}")

    def getParam(self, name):
        # --- This section remains unchanged ---
        try:
            if name == "Distance_1":
                radius_1 = float(self.params["Radius_1"].get())
                width_1 = float(self.params["Width_1"].get())
                v = radius_1**2 - (width_1 / 2)**2
                if v < 0:
                    raise ValueError("Radius_1 must be >= Width_1 / 2")
                return radius_1 - math.sqrt(v)
            elif name == "Distance_2":
                width_1 = float(self.params["Width_1"].get())
                circle = int(float(self.params["Circle"].get()))
                return width_1 * 2 * circle
            elif name == "Angle":
                return math.radians(float(self.params["Angle"].get()))
            else:
                return float(self.params[name].get())
        except (ValueError, tk.TclError) as e:
            messagebox.showerror("参数错误 / Parameter Error", f"无法计算参数'{name}': {e}\n将使用默认值. / Could not calculate parameter '{name}': {e}\nUsing default value.")
            if name in self.defaults:
                self.params[name].set(str(self.defaults[name]))
                return self.defaults[name]
            else:
                return 0.0

    def highlightComponent(self, paramName):
        # --- This section remains unchanged ---
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
        # --- THIS METHOD IS UPDATED WITH THE MISSING LINE ---
        Radius_1 = self.getParam("Radius_1")
        Width_1 = self.getParam("Width_1")
        Circle = int(self.getParam("Circle"))
        Distance_3 = self.getParam("Distance_3")
        Length_r1 = self.getParam("Length_r1")
        Length_v1 = self.getParam("Length_v1")
        Angle = self.getParam("Angle")
        Length_Out = self.getParam("Length_Out")
        Distance_1 = self.getParam("Distance_1")
        Distance_2 = self.getParam("Distance_2")

        c1_center = (0, -Width_1/2 - Length_v1 - Radius_1)
        c2_x = Width_1/2 + Distance_2 + Length_v1 + (Length_Out + Radius_1) * math.cos(Angle) + Width_1 * math.sin(Angle) / 2
        c2_y = Distance_2 + Width_1/2 + (Length_Out + Radius_1) * math.sin(Angle) - Width_1 * math.cos(Angle) / 2
        c2_center = (c2_x, c2_y)
        c3_x = c2_x
        c3_y = Distance_2 - Width_1/2 - (Radius_1 + Length_Out) * math.sin(Angle) + Width_1 * math.cos(Angle) / 2
        c3_center = (c3_x, c3_y)
        c4_center = (Width_1/2 + Distance_2 + Length_v1 + Length_Out + Radius_1, Distance_2)
        circles = [(c1_center, Radius_1), (c2_center, Radius_1), (c3_center, Radius_1), (c4_center, Radius_1)]

        arc_center = (Length_r1/2, -Width_1/2 - Length_v1/2 - Distance_1/2 + (Length_v1 + Distance_1) / 2)
        arc_radius = Width_1
        arc_theta1 = 90
        arc_theta2 = 180
        arcs = [(arc_center, arc_radius, arc_theta1, arc_theta2)]

        segments = []
        seg1_p0 = (Length_r1/2, -Width_1/2 - Length_v1/2 - Distance_1/2 - (Length_v1 + Distance_1) / 2)
        seg1_p1 = (Length_r1/2, -Width_1/2 - Length_v1/2 - Distance_1/2 + (Length_v1 + Distance_1) / 2)
        segments.append((seg1_p0, seg1_p1))
        seg2_p0 = (-Length_r1/2, seg1_p0[1])
        seg2_p1 = (-Length_r1/2, seg1_p1[1])
        segments.append((seg2_p0, seg2_p1))
        seg3_p0 = (Width_1/2, Distance_2 + Width_1/2)
        seg3_p1 = (Width_1/2 + Distance_2 + Length_v1, Distance_2 + Width_1/2)
        segments.append((seg3_p0, seg3_p1))
        seg4_p0 = (Width_1/2, Distance_2 - Width_1/2)
        seg4_p1 = (Width_1/2 + Distance_2 + Length_v1, Distance_2 - Width_1/2)
        segments.append((seg4_p0, seg4_p1))
        seg5_p0 = (Width_1/2 + Distance_2 + Length_v1 + Width_1 / math.sin(Angle), Distance_2 - Width_1/2)
        seg5_p1 = (Width_1/2 + Distance_2 + Length_v1 + Length_Out + Distance_1, Distance_2 - Width_1/2)
        segments.append((seg5_p0, seg5_p1))
        seg6_p0 = (Width_1/2 + Distance_2 + Length_v1 + (Distance_1 + Length_Out) * math.cos(Angle), Distance_2 - Width_1/2 - (Distance_1 + Length_Out) * math.sin(Angle))
        seg6_p1 = (Width_1/2 + Distance_2 + Length_v1, Distance_2 - Width_1/2)
        segments.append((seg6_p0, seg6_p1))
        segments.append((seg6_p1, seg6_p0))
        seg8_p0 = (Width_1/2 + Distance_2 + Length_v1 + Width_1 / math.sin(Angle), Distance_2 + Width_1/2)
        seg8_p1 = (Width_1/2 + Distance_2 + Length_v1 + Length_Out + Distance_1, Distance_2 + Width_1/2)
        segments.append((seg8_p0, seg8_p1))
        seg9_p0 = (Width_1/2 + Distance_2 + Length_v1 + Width_1 / math.sin(Angle), Distance_2 + Width_1/2)
        seg9_p1 = (Width_1/2 + Distance_2 + Length_v1 + (Distance_1 + Length_Out) * math.cos(Angle) + Width_1 * math.sin(Angle), Distance_2 + Width_1/2 + (Distance_1 + Length_Out) * math.sin(Angle) - Width_1 * math.cos(Angle))
        segments.append((seg9_p0, seg9_p1))
        seg10_p0 = (Width_1/2 + Distance_2 + Length_v1 + Width_1 / math.sin(Angle), Distance_2 - Width_1/2)

        seg10_p1 = (Width_1/2 + Distance_2 + Length_v1 + (Distance_1 + Length_Out) * math.cos(Angle) + Width_1 * math.sin(Angle), Distance_2 - Width_1/2 - (Distance_1 + Length_Out) * math.sin(Angle) + Width_1 * math.cos(Angle))
        segments.append((seg10_p0, seg10_p1))

        # *** ADDED MISSING LINE AS PER YOUR REQUEST ***
        missing_line_p0 = (Width_1/2 + Distance_2 + Length_v1, Distance_2 + Width_1/2)
        missing_line_p1 = (Width_1/2 + Distance_2 + Length_v1 + (Distance_1 + Length_Out) * math.cos(Angle), Distance_2 + Width_1/2 + (Distance_1 + Length_Out) * math.sin(Angle))
        segments.append((missing_line_p0, missing_line_p1))
        
        spiral1_pts = []
        spiral2_pts = []
        x_offset = Length_r1 / 2
        y_offset = -Distance_3 - Width_1 / 2
        num_points = max(100, Circle * 50)
        for s in np.linspace(0, 1, num_points):
            t = 2 * math.pi * s * Circle
            r1 = Distance_2 * s + Distance_3 + Width_1
            r2 = Distance_2 * s + Distance_3
            x1 = x_offset + math.sin(t) * r1
            y1 = y_offset + math.cos(t) * r1
            spiral1_pts.append((x1, y1))
            x2 = x_offset + math.sin(t) * r2
            y2 = y_offset + math.cos(t) * r2
            spiral2_pts.append((x2, y2))
            
        return {
            "circles": circles, "arcs": arcs, "segments": segments,
            "spirals": [spiral1_pts, spiral2_pts]
        }

    def updateModel(self):
        # --- This section remains unchanged ---
        try:
            self.ax.clear()
            self.geoPatch = {k: [] for k in self.params}
            geo = self.calculateGeometry()
            for center, radius in geo["circles"]:
                patch = mpatches.Circle(center, radius, fill=False, edgecolor='blue', lw=1.5)
                self.ax.add_patch(patch)
                self.geoPatch["Radius_1"].append(patch)
            for center, radius, t1, t2 in geo["arcs"]:
                patch = mpatches.Arc(center, 2*radius, 2*radius, angle=0, theta1=t1, theta2=t2, edgecolor='blue', lw=1.5)
                self.ax.add_patch(patch)
                self.geoPatch["Width_1"].append(patch)
                self.geoPatch["Length_v1"].append(patch)
            for p0, p1 in geo["segments"]:
                line = plt.Line2D([p0[0], p1[0]], [p0[1], p1[1]], color='blue', lw=1.5)
                self.ax.add_line(line)
                if abs(p0[0]) <= self.getParam("Length_r1")/2 or abs(p1[0]) <= self.getParam("Length_r1")/2:
                    self.geoPatch["Length_r1"].append(line)
                if p0[0] > 0 and p1[0] > 0:
                     self.geoPatch["Length_Out"].append(line)
                     self.geoPatch["Angle"].append(line)
                self.geoPatch["Width_1"].append(line)
            for points in geo["spirals"]:
                if points:
                    x_pts, y_pts = zip(*points)
                    line = plt.Line2D(x_pts, y_pts, color='blue', lw=1.5)
                    self.ax.add_line(line)
                    self.geoPatch["Circle"].append(line)
                    self.geoPatch["Distance_3"].append(line)
            all_x, all_y = [], []
            for patch in self.ax.patches:
                if isinstance(patch, mpatches.Circle):
                    center, r = patch.center, patch.radius
                    all_x.extend([center[0] - r, center[0] + r]); all_y.extend([center[1] - r, center[1] + r])
                elif isinstance(patch, mpatches.Arc):
                    center, w, h = patch.center, patch.width, patch.height
                    all_x.extend([center[0] - w/2, center[0] + w/2]); all_y.extend([center[1] - h/2, center[1] + h/2])
            for line in self.ax.lines:
                x_data, y_data = line.get_data()
                all_x.extend(x_data); all_y.extend(y_data)
            if not all_x or not all_y: all_x, all_y = [-1, 1], [-1, 1]
            pad = max((max(all_x)-min(all_x))*0.1, (max(all_y)-min(all_y))*0.1, 1)
            self.ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
            self.ax.set_ylim(min(all_y) - pad, max(all_y) + pad)

            self.ax.set_aspect('equal', adjustable='box')
            self.ax.grid(True, linestyle='--', alpha=0.5)
            self.ax.set_title("TripleSpiral", fontsize=14)
            self.ax.set_xlabel("X (mm)"); self.ax.set_ylabel("Y (mm)")
            self.canvas.draw()
            if self.curHlt: self.highlightComponent(self.curHlt)
            self.stsVar.set("模型更新成功 / Model updated successfully")
        except Exception as e:
            messagebox.showerror("错误 / Error", f"模型更新失败 / Failed to update model: {e}")
            self.stsVar.set(f"失败 / Failed: {e}")

    def exportDxf(self):
        # --- This section remains unchanged ---
        try:
            filename = filedialog.asksaveasfilename(defaultextension=".dxf", filetypes=[("DXF Files", "*.dxf"), ("All Files", "*.*")], title="保存DXF / Save DXF")
            if not filename: return
            doc = ezdxf.new('R2010'); msp = doc.modelspace()
            geo = self.calculateGeometry()
            for center, radius in geo["circles"]:
                msp.add_circle(center, radius)
            for center, radius, t1, t2 in geo["arcs"]:
                msp.add_arc(center, radius, t1, t2)
            for p0, p1 in geo["segments"]:
                msp.add_line(p0, p1)
            for points in geo["spirals"]:
                if points:
                    msp.add_lwpolyline(points)
            doc.saveas(filename)
            self.stsVar.set(f"已导出DXF / DXF Exported: {filename}")
            messagebox.showinfo("成功 / Success", f"已导出到DXF / Exported to DXF:\n{filename}")
        except Exception as e:
            messagebox.showerror("错误 / Error", f"导出DXF失败 / Failed to export DXF: {e}")
            self.stsVar.set("导出失败 / Export Failed")

    def exportSvg(self):
        # --- This section remains unchanged ---
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
        # --- This section remains unchanged ---
        try:
            filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")], title="保存JSON / Save JSON")
            if not filename: return
            data = {
                "model_name": self.ax.get_title(),
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "parameters": {k: v.get() for k, v in self.params.items()}
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self.stsVar.set(f"已导出JSON / JSON Exported: {filename}")
            messagebox.showinfo("成功 / Success", f"已导出到JSON / Exported to JSON:\n{filename}")
        except Exception as e:
            messagebox.showerror("错误 / Error", f"导出JSON失败 / Failed to export JSON: {e}")
            self.stsVar.set("导出失败 / Export Failed")

    def importJson(self):
        # --- This section remains unchanged ---
        try:
            filename = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")], title="导入JSON / Import JSON")
            if not filename: return
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_params = data.get("parameters", {})
            for key, value in imported_params.items():
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
        # --- This section remains unchanged ---
        plt.close('all')
        self.master.quit()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MicrochannelTool(root)
    root.mainloop()
