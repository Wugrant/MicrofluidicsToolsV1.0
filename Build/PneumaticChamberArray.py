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
        master.title("气腔阵列微通道建模工具")
        master.geometry("1100x700")
        copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 
                             fg="#555555", bg="#f0f0f0")
        copyright_label.pack(side=tk.BOTTOM, fill=tk.X)
        # ----------------- 1. REPLACED PARAMETERS ------------------
        # Parameters, defaults, and descriptions are replaced as per the new model.
        self.params = {
            "Distance_r1": tk.StringVar(value="4.0"),  # 结构和流道的距离
            "Width_r1": tk.StringVar(value="0.2"),     # 水平流道宽度
            "Radius_1": tk.StringVar(value="0.4"),     # 打孔半径
            "Number": tk.StringVar(value="12"),        # 气腔数量
            "Angle": tk.StringVar(value="60"),         # 气腔角度 (Note: Included as requested, but not used in this geometry)
            "Width_1": tk.StringVar(value="0.2"),      # 气腔宽度
            "Length_1": tk.StringVar(value="0.4"),     # 气腔长度
            "Distance_r2": tk.StringVar(value="0.2"),  # 气腔间距
        }
        self.defaults = {k: float(v.get()) if v.get() else 0.0 for k, v in self.params.items()}

        self.descriptions = {
            "Distance_r1": "结构和流道的距离 (mm) / Distance to channel",
            "Width_r1": "水平流道宽度 (mm) / Horizontal channel width",
            "Radius_1": "打孔半径 (mm) / Hole radius",
            "Number": "气腔数量 / Number of chambers",
            "Angle": "气腔角度 (度) / Chamber angle (deg)",
            "Width_1": "气腔宽度 (mm) / Chamber width",
            "Length_1": "气腔长度 (mm) / Chamber length",
            "Distance_r2": "气腔间距 (mm) / Chamber spacing",
        }
        # Editable parameters for the UI. `Distance_h` is excluded as it is calculated.
        self.editable_params = [
            "Distance_r1", "Width_r1", "Radius_1", "Number", "Angle",
            "Width_1", "Length_1", "Distance_r2"
        ]
        # Calculated parameter(s) used internally.
        self.calculated_params = ["Distance_h"]
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
        # --- Updated for the new calculated parameter `Distance_h` ---
        try:
            if name == "Distance_h":
                radius_1 = float(self.params["Radius_1"].get())
                width_r1 = float(self.params["Width_r1"].get())
                v = radius_1**2 - (width_r1 / 2)**2
                if v < 0:
                    raise ValueError("Radius_1 must be >= Width_r1 / 2")
                return radius_1 - math.sqrt(v)
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
        # ----------------- REPLACED GEOMETRY CALCULATION ------------------
        # This method is entirely replaced with the new geometric logic for the chamber array.
        Distance_r1 = self.getParam("Distance_r1")
        Width_r1 = self.getParam("Width_r1")
        Radius_1 = self.getParam("Radius_1")
        Number = int(self.getParam("Number"))
        Width_1 = self.getParam("Width_1")
        Length_1 = self.getParam("Length_1")
        Distance_r2 = self.getParam("Distance_r2")
        Distance_h = self.getParam("Distance_h") # Calculated

        circles = []
        segments = []

        # Circle 1
        circles.append(((0, 0), Radius_1))

        # Total width of the array structure
        array_total_width = Number * (Width_1 + Distance_r2)
        
        # Circle 2
        c2_x = Radius_1 + Distance_r1 + array_total_width + Distance_r1 + Radius_1
        circles.append(((c2_x, 0), Radius_1))

        # Segments 1 & 2 (Inlet channel)
        segments.append(((Radius_1 - Distance_h, -Width_r1 / 2), (Radius_1 + Distance_r1, -Width_r1 / 2)))
        segments.append(((Radius_1 - Distance_h, Width_r1 / 2), (Radius_1 + Distance_r1, Width_r1 / 2)))

        # Chamber Array
        for i in range(Number):
            x_offset = i * (Width_1 + Distance_r2)
            x_base = Radius_1 + Distance_r1 + x_offset

            # Upper chamber part
            segments.append(((x_base, Width_r1 / 2), (x_base, Width_r1 / 2 + Length_1))) # Seg 3

            segments.append(((x_base, Width_r1 / 2 + Length_1), (x_base + Width_1, Width_r1 / 2 + Length_1))) # Seg 4
            segments.append(((x_base + Width_1, Width_r1 / 2), (x_base + Width_1, Width_r1 / 2 + Length_1))) # Seg 5
            
            # Lower chamber part
            segments.append(((x_base, -Width_r1 / 2), (x_base, -Width_r1 / 2 - Length_1))) # Seg 7
            segments.append(((x_base, -Width_r1 / 2 - Length_1), (x_base + Width_1, -Width_r1 / 2 - Length_1))) # Seg 8

            segments.append(((x_base + Width_1, -Width_r1 / 2), (x_base + Width_1, -Width_r1 / 2 - Length_1))) # Seg 9

            # Connecting segments between chambers (if not the last one)
            if i < Number - 1:
                segments.append(((x_base + Width_1, Width_r1 / 2), (x_base + Width_1 + Distance_r2, Width_r1 / 2))) # Seg 6
                segments.append(((x_base + Width_1, -Width_r1 / 2), (x_base + Width_1 + Distance_r2, -Width_r1 / 2))) # Seg 10

        # Segments 12 & 13 (Outlet channel)
        outlet_start_x = Radius_1 + Distance_r1 + array_total_width - Distance_r2
        outlet_end_x = c2_x - (Radius_1 - Distance_h)
        segments.append(((outlet_start_x, Width_r1 / 2), (outlet_end_x, Width_r1 / 2)))
        segments.append(((outlet_start_x, -Width_r1 / 2), (outlet_end_x, -Width_r1 / 2)))

        return { "circles": circles, "segments": segments }
        # ----------------- END OF GEOMETRY REPLACEMENT ------------------

    def updateModel(self):
        # --- Updated to draw the new geometry and assign patches for highlighting ---
        try:
            self.ax.clear()
            self.geoPatch = {k: [] for k in self.params}
            geo = self.calculateGeometry()

            # Draw circles and assign to Radius_1 for highlighting
            for center, radius in geo["circles"]:
                patch = mpatches.Circle(center, radius, fill=False, edgecolor='blue', lw=1.5)
                self.ax.add_patch(patch)
                self.geoPatch["Radius_1"].append(patch)

            # Draw segments and assign for highlighting
            # Simple heuristic for assignment
            inlet_x_limit = self.getParam("Radius_1") + self.getParam("Distance_r1")
            outlet_x_start = inlet_x_limit + self.getParam("Number") * (self.getParam("Width_1") + self.getParam("Distance_r2"))

            for p0, p1 in geo["segments"]:
                line = plt.Line2D([p0[0], p1[0]], [p0[1], p1[1]], color='blue', lw=1.5)
                self.ax.add_line(line)
                # Assign lines to parameters for highlighting
                if p1[0] <= inlet_x_limit or p0[0] >= outlet_x_start:
                    self.geoPatch["Distance_r1"].append(line)
                if abs(p0[1]) == self.getParam("Width_r1")/2 and abs(p1[1]) == self.getParam("Width_r1")/2:
                     self.geoPatch["Width_r1"].append(line)
                if inlet_x_limit < p0[0] < outlet_x_start:
                    self.geoPatch["Number"].append(line)
                    self.geoPatch["Width_1"].append(line)
                    self.geoPatch["Length_1"].append(line)
                    self.geoPatch["Distance_r2"].append(line)

            # Auto-scaling and plot finalization
            all_x, all_y = [], []
            for patch in self.ax.patches:
                center, r = patch.center, patch.radius
                all_x.extend([center[0] - r, center[0] + r]); all_y.extend([center[1] - r, center[1] + r])
            for line in self.ax.lines:
                x_data, y_data = line.get_data()
                all_x.extend(x_data); all_y.extend(y_data)
            if not all_x or not all_y: all_x, all_y = [-1, 1], [-1, 1]
            pad_x = (max(all_x) - min(all_x)) * 0.1
            pad_y = (max(all_y) - min(all_y)) * 0.1
            pad = max(pad_x, pad_y, 1)
            self.ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
            self.ax.set_ylim(min(all_y) - pad, max(all_y) + pad)
            self.ax.set_aspect('equal', adjustable='box')
            self.ax.grid(True, linestyle='--', alpha=0.5)
            self.ax.set_title("PneumaticChamberArray", fontsize=14)
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
