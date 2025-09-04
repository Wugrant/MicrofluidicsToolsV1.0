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
        # The window title is updated to reflect the new model.
        master.title("微通道几何建模工具")
        master.geometry("1100x700")
        copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 
                             fg="#555555", bg="#f0f0f0")
        copyright_label.pack(side=tk.BOTTOM, fill=tk.X)
        # ----------------- 1. REPLACED PARAMETERS ------------------
        # Parameters, defaults, and descriptions are replaced for the single valve model.
        self.params = {
            "Length_r1": tk.StringVar(value="5.0"),
            "Width_r1": tk.StringVar(value="0.2"),
            "Radius_1": tk.StringVar(value="0.4"),
            "Angle_1": tk.StringVar(value="60"),
            "Length_r2": tk.StringVar(value="1.7"),
            "Length_3": tk.StringVar(value="0.6"),
            "Radius_2": tk.StringVar(value="0.2"),
        }
        self.defaults = {k: float(v.get()) if v.get() else 0.0 for k, v in self.params.items()}

        self.descriptions = {
            "Length_r1": "流道距离 (mm) / Channel distance",
            "Width_r1": "流道宽度 (mm) / Channel width",
            "Radius_1": "打孔半径 (mm) / Hole radius",
            "Angle_1": "阀体夹角 (度) / Valve angle (deg)",
            "Length_r2": "阀体直边长度 (mm) / Valve straight edge length",
            "Length_3": "阀体斜边边长 (mm) / Valve hypotenuse length",
            "Radius_2": "阀体倒圆角半径 (mm) / Valve fillet radius",
        }
        # Editable parameters for the UI.
        self.editable_params = [
            "Length_r1", "Width_r1", "Radius_1", "Angle_1",
            "Length_r2", "Length_3", "Radius_2"
        ]
        # Calculated parameters used internally.
        self.calculated_params = ["Distance_1", "Length_1", "Length_5"]
        # ----------------- END OF REPLACEMENT ------------------

        # --- Unchanged UI and Plotting Initialization ---
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
            float(self.params[param].get())
            self.updateModel()
        except ValueError as e:
            self.params[param].set(str(self.defaults[param]))
            messagebox.showerror("错误 / Error", f"无效的数值 / Invalid number: {e}")

    def getParam(self, name):
        # --- Updated for the new calculated parameters ---
        try:
            if name == "Angle_1_deg": # Keep degrees for plot
                return float(self.params["Angle_1"].get())
            elif name == "Angle_1": # Radians for math
                return math.radians(float(self.params["Angle_1"].get()))
            elif name == "Distance_1":
                radius_1 = float(self.params["Radius_1"].get())
                width_r1 = float(self.params["Width_r1"].get())
                v = radius_1**2 - (width_r1 / 2)**2
                if v < 0: raise ValueError("Radius_1 must be >= Width_r1 / 2")
                return radius_1 - math.sqrt(v)
            elif name == "Length_1": # Calculated from Length_3
                angle_rad = math.radians(float(self.params["Angle_1"].get()))
                length_3 = float(self.params["Length_3"].get())
                return length_3 * math.cos(angle_rad)
            elif name == "Length_5": # Calculated from Length_3
                angle_rad = math.radians(float(self.params["Angle_1"].get()))
                length_3 = float(self.params["Length_3"].get())
                return 2 * length_3 * math.sin(angle_rad)
            else:
                return float(self.params[name].get())
        except (ValueError, tk.TclError) as e:
            messagebox.showerror("参数错误 / Parameter Error", f"无法计算参数'{name}': {e}\n将使用默认值.")
            if name in self.defaults:
                self.params[name].set(str(self.defaults[name]))
                return self.defaults[name]
            else: return 0.0

    def highlightComponent(self, paramName):
        # --- This section remains unchanged ---
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
        # ----------------- REPLACED GEOMETRY CALCULATION ------------------
        # This method is entirely replaced with the new single valve logic.
        Length_r1 = self.getParam("Length_r1")
        Width_r1 = self.getParam("Width_r1")
        Radius_1 = self.getParam("Radius_1")
        Angle_1_rad = self.getParam("Angle_1")
        Angle_1_deg = self.getParam("Angle_1_deg")
        Length_r2 = self.getParam("Length_r2")
        Length_3 = self.getParam("Length_3")
        Radius_2 = self.getParam("Radius_2")
        Distance_1 = self.getParam("Distance_1")
        Length_1 = self.getParam("Length_1")
        
        circles, arcs, segments = [], [], []

        # Circles
        c1_center = (-Radius_1, Width_r1 / 2)
        c2_x = Length_r1 + 2 * Length_1 + Length_r2 + Length_r1 + Radius_1
        c2_center = (c2_x, Width_r1 / 2)
        circles.extend([(c1_center, Radius_1), (c2_center, Radius_1)])

        # Arcs
        y_valve_top = Width_r1 + Length_3 * math.sin(Angle_1_rad)
        y_valve_bottom = -Length_3 * math.sin(Angle_1_rad)
        
        arc1_center = (Length_r1 + Length_1 + Radius_2 * math.tan(Angle_1_rad/2), y_valve_bottom + Radius_2)
        arcs.append((arc1_center, Radius_2, -90 - Angle_1_deg, -90))
        
        arc2_center = (Length_r1 + Length_1 + Radius_2 * math.tan(Angle_1_rad/2), y_valve_top - Radius_2)
        arcs.append((arc2_center, Radius_2, 90, 90 + Angle_1_deg)) # Corrected angle direction
        
        arc3_center = (Length_r1 + Length_1 + Length_r2 - Radius_2 * math.tan(Angle_1_rad/2), y_valve_top - Radius_2)
        arcs.append((arc3_center, Radius_2, 90 - Angle_1_deg, 90))
        
        arc4_center = (Length_r1 + Length_1 + Length_r2 - Radius_2 * math.tan(Angle_1_rad/2), y_valve_bottom + Radius_2)
        arcs.append((arc4_center, Radius_2, -90, -90 + Angle_1_deg))

        # Line Segments
        segments.append(((-Distance_1, Width_r1), (Length_r1, Width_r1))) # seg 1
        segments.append(((-Distance_1, 0), (Length_r1, 0))) # seg 2

        # Connect inlet to top valve corner
        p3_end_x = arc2_center[0] - Radius_2 * math.sin(Angle_1_rad)
        p3_end_y = arc2_center[1] + Radius_2 * math.cos(Angle_1_rad)
        segments.append(((Length_r1, Width_r1), (p3_end_x, p3_end_y))) # seg 3

        # Top horizontal part of valve
        segments.append(((arc2_center[0], arc2_center[1] + Radius_2), (arc3_center[0], arc3_center[1] + Radius_2))) # seg 4

        # Connect top valve corner to outlet
        p5_start_x = arc3_center[0] + Radius_2 * math.sin(Angle_1_rad)
        p5_start_y = arc3_center[1] + Radius_2 * math.cos(Angle_1_rad)
        segments.append(((p5_start_x, p5_start_y), (Length_r1 + 2 * Length_1 + Length_r2, Width_r1))) # seg 5

        # Connect inlet to bottom valve corner
        p6_end_x = arc1_center[0] - Radius_2 * math.sin(Angle_1_rad)
        p6_end_y = arc1_center[1] - Radius_2 * math.cos(Angle_1_rad)
        segments.append(((Length_r1, 0), (p6_end_x, p6_end_y))) # seg 6

        # Bottom horizontal part of valve
        segments.append(((arc1_center[0], arc1_center[1] - Radius_2), (arc4_center[0], arc4_center[1] - Radius_2))) # seg 7
        
        # Connect bottom valve corner to outlet
        p9_start_x = arc4_center[0] + Radius_2 * math.sin(Angle_1_rad)
        p9_start_y = arc4_center[1] - Radius_2 * math.cos(Angle_1_rad)
        segments.append(((p9_start_x, p9_start_y), (Length_r1 + 2 * Length_1 + Length_r2, 0))) # seg 9
        
        # Outlet channels
        segments.append(((Length_r1 + 2 * Length_1 + Length_r2, 0), (c2_center[0] - Radius_1 + Distance_1, 0))) # seg 8
        segments.append(((Length_r1 + 2 * Length_1 + Length_r2, Width_r1), (c2_center[0] - Radius_1 + Distance_1, Width_r1))) # seg 10

        return {"circles": circles, "arcs": arcs, "segments": segments}
        # ----------------- END OF GEOMETRY REPLACEMENT ------------------

    def updateModel(self):
        # --- Updated to draw the new geometry ---
        try:
            self.ax.clear()
            self.geoPatch = {k: [] for k in self.params}
            geo = self.calculateGeometry()

            for center, radius in geo["circles"]:
                patch = mpatches.Circle(center, radius, fill=False, edgecolor='blue', lw=1.5)
                self.ax.add_patch(patch); self.geoPatch["Radius_1"].append(patch)

            for center, radius, t1, t2 in geo["arcs"]:
                patch = mpatches.Arc(center, 2*radius, 2*radius, angle=0, theta1=t1, theta2=t2, edgecolor='blue', lw=1.5)
                self.ax.add_patch(patch); self.geoPatch["Radius_2"].append(patch)

            for p0, p1 in geo["segments"]:
                line = plt.Line2D([p0[0], p1[0]], [p0[1], p1[1]], color='blue', lw=1.5)
                self.ax.add_line(line)
                # Simple heuristic for highlighting
                if p0[1] == p1[1]: self.geoPatch["Length_r1"].append(line); self.geoPatch["Length_r2"].append(line)
                else: self.geoPatch["Length_3"].append(line); self.geoPatch["Angle_1"].append(line)
                self.geoPatch["Width_r1"].append(line)

            # Auto-scaling and plot finalization
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
            self.ax.set_title("Chamber", fontsize=14)
            self.ax.set_xlabel("X (mm)"); self.ax.set_ylabel("Y (mm)")
            self.canvas.draw()
            if self.curHlt: self.highlightComponent(self.curHlt)
            self.stsVar.set("模型更新成功 / Model updated successfully")
        except Exception as e:
            messagebox.showerror("错误 / Error", f"模型更新失败 / Failed to update model: {e}")
            self.stsVar.set(f"失败 / Failed: {e}")

    def exportDxf(self):
        # --- Updated to export the new geometry ---
        try:
            filename = filedialog.asksaveasfilename(defaultextension=".dxf", filetypes=[("DXF Files", "*.dxf"), ("All Files", "*.*")], title="保存DXF / Save DXF")
            if not filename: return
            doc = ezdxf.new('R2010'); msp = doc.modelspace()
            geo = self.calculateGeometry()

            for center, radius in geo["circles"]: msp.add_circle(center, radius)
            for center, radius, t1, t2 in geo["arcs"]: msp.add_arc(center, radius, t1, t2)
            for p0, p1 in geo["segments"]: msp.add_line(p0, p1)

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
            data = {"model_name": self.ax.get_title(), "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "parameters": {k: v.get() for k, v in self.params.items()}}
            with open(filename, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)
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
        # --- This section remains unchanged ---
        plt.close('all')
        self.master.quit()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MicrochannelTool(root)
    root.mainloop()
