# Copyright (c) 2025 [Grant]
# Licensed under the MIT License.
# See LICENSE in the project root for license information.
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.patches as mpatches
from matplotlib.path import Path
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
        master.geometry("1100x900")
        copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 

                                    fg="#555555", bg="#f0f0f0", font=("Arial", 8))
        copyright_label.pack(side=tk.BOTTOM, fill=tk.X, pady=1)
        # 初始化参数
        self.params = {
            "Length_r1": tk.StringVar(value="1.0"),      # 直流道的长度
            "Width_r1": tk.StringVar(value="0.2"),       # 直流道的宽度
            "Radius_1": tk.StringVar(value="0.4"),       # 打孔半径
            "Radius_2": tk.StringVar(value="0.1"),       # 不对称半圆小圆内半径
            "Radius_4": tk.StringVar(value="0.8"),       # 不对称半圆大圆内半径
            "Angle": tk.StringVar(value="120"),           # 不对称半圆内角度
            "Radius_5": tk.StringVar(value=""),          # 不对称半圆大圆外半径 (计算值)
            "number": tk.StringVar(value="5"),           # 不对称结构的循环数
            "Length_r2": tk.StringVar(value="1.0"),      # 直流道的出口长度
        }

        # 默认值备份 
        self.defaults = {k: float(v.get()) if v.get() else 0.0 for k, v in self.params.items()}

        # 参数描述 
        self.descriptions = {
            "Length_r1": "直流道的长度（mm） / Channel Length", 
            "Width_r1": "直流道的宽度（mm） / Channel Width",
            "Radius_1": "打孔半径（mm） / Hole Radius",
            "Radius_2": "不对称半圆小圆内半径（mm） / Small inner radius",
            "Radius_4": "不对称半圆大圆内半径（mm） / Large inner radius",
            "Angle": "不对称半圆内角度（Degree） / Inner angle",
            "Radius_5": "不对称半圆大圆外半径（mm） / Large outer radius",
            "number": "不对称结构的循环数 / Number of cycles",
            "Length_r2": "直流道的出口长度（mm） / Outlet length",
        }
        # 可编辑参数列表 (排除计算参数)
        self.editable_params = [
            "Length_r1", "Width_r1", "Radius_1", 
            "Radius_2", "Radius_4", "Angle", "number", "Length_r2"
        ]

        # 计算参数列表 (后台计算，不显示在UI中)
        self.calculated_params = ["Radius_5"]

        # 配置字体和样式
        self.bigFont = ('Helvetica', 12)
        self.headerFont = ('Helvetica', 12, 'bold')

        # 创建图形和相关变量
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

        # 创建滚动画布
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

        # 添加所有可编辑参数到滚动区域
        self.create_parameter_entries()

        # 按钮区域
        btnFrm = ttk.Frame(paramFrm)
        btnFrm.pack(fill=tk.X, pady=15)

        buttons = [
            ("更新模型 / Update Model", self.updateModel),
            ("导出DXF / Export DXF", self.exportDxf),
            ("导出SVG / Export SVG", self.exportSvg),
            ("导出JSON / Export JSON", self.exportJson),  # 新增导出JSON按钮
            ("导入JSON / Import JSON", self.importJson),  # 新增导入JSON按钮
        ]

        for text, command in buttons:
            ttk.Button(btnFrm, text=text, command=command, padding=(10, 5)).pack(fill=tk.X, pady=5)

        # 绘图区域
        plotFrm = ttk.Frame(self.master)
        plotFrm.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = FigureCanvasTkAgg(self.fig, master=plotFrm)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 添加导航工具栏
        toolbarFrame = ttk.Frame(plotFrm)
        toolbarFrame.pack(side=tk.BOTTOM, fill=tk.X)
        NavigationToolbar2Tk(self.canvas, toolbarFrame).update()

        # 状态栏
        statusBar = ttk.Label(self.master, textvariable=self.stsVar, 
                             relief=tk.SUNKEN, anchor=tk.W, font=self.bigFont)
        statusBar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_parameter_entries(self):
        # 清除现有控件
        for widget in self.scroll_content.winfo_children():
            widget.destroy()

        # 添加所有可编辑参数
        for param in self.editable_params:
            self.create_parameter_row(param)

    def create_parameter_row(self, param):
        frame = ttk.Frame(self.scroll_content)
        frame.pack(fill=tk.X, pady=8, padx=5)

        # 参数描述（移除参数名，只保留中英文描述）
        ttk.Label(frame, text=self.descriptions[param], 
                font=self.bigFont, wraplength=330).pack(anchor=tk.W, pady=(0,5))

        # 参数值输入框
        entry = ttk.Entry(frame, textvariable=self.params[param], font=self.bigFont)
        entry.pack(fill=tk.X)

        # 绑定事件
        entry.bind("<Return>", lambda e, p=param: self.parameter_changed(p))
        entry.bind("<FocusOut>", lambda e, p=param: self.parameter_changed(p))
        entry.bind("<FocusIn>", lambda e, p=param: self.highlightComponent(p))

        self.entries[param] = entry

    def parameter_changed(self, param):
        try:
            # 验证输入
            value = self.params[param].get()

            # 特殊处理Angle参数
            if param == "Angle":
                angle_value = float(value)
                if angle_value >= 180:
                    raise ValueError("角度必须小于180度 / Angle must be less than 180 degrees")

            float(value)  # 尝试转换为浮点数来验证
            # 更新模型
            self.updateModel()
        except ValueError:
            # 恢复默认值
            self.params[param].set(str(self.defaults[param]))
            messagebox.showerror("错误 / Error", "无效的数值 / Invalid number")

    def getParam(self, name):
        try:
            # 计算Distance_1
            if name == "Distance_1":
                radius_1 = self.getParam("Radius_1")
                width_r1 = self.getParam("Width_r1")
                # 计算 Distance_1 = Radius_1 - sqrt(Radius_1^2 - (Width_r1/2)^2)
                discriminant = radius_1**2 - (width_r1/2)**2
                if discriminant < 0:
                    return 0.0  # 避免负值
                return radius_1 - math.sqrt(discriminant)

            # 计算Radius_5
            elif name == "Radius_5":
                # 计算Radius_5 = Radius_4*sin(Angle*2*pi/360) + Width_r1
                angle_rad = self.getParam("Angle")  * math.pi / 360
                return self.getParam("Radius_4") * math.sin(angle_rad) + self.getParam("Width_r1")

            # 其他参数
            return float(self.params[name].get())
        except:
            self.params[name].set(str(self.defaults[name]))
            return self.defaults[name]

    def highlightComponent(self, paramName):
        self.curHlt = paramName
        # 将所有元素设为蓝色
        for patches in self.geoPatch.values():
            for patch in patches:
                if hasattr(patch, 'set_edgecolor'):
                    patch.set_edgecolor('blue')
                elif hasattr(patch, 'set_color'):
                    patch.set_color('blue')

        # 将选中参数对应的元素设为红色
        if paramName in self.geoPatch:
            for patch in self.geoPatch[paramName]:
                if hasattr(patch, 'set_edgecolor'):
                    patch.set_edgecolor('red')  # 使用红色突出显示选中元素
                elif hasattr(patch, 'set_color'):
                    patch.set_color('red')  # 使用红色突出显示选中元素

        self.canvas.draw()
        self.stsVar.set(f"已选择 / Selected: {paramName}")

    def calculateGeometry(self):
        # 获取参数
        radius_1 = self.getParam("Radius_1")
        width_r1 = self.getParam("Width_r1")
        length_r1 = self.getParam("Length_r1")

        # 计算Distance_1
        distance_1 = self.getParam("Distance_1")
        radius_2 = self.getParam("Radius_2")
        radius_3 = radius_2 + width_r1  # 直接计算小圆外半径
        radius_4 = self.getParam("Radius_4")
        angle = self.getParam("Angle") / 2
        radius_5 = self.getParam("Radius_5")  # 计算值
        number = int(self.getParam("number"))
        length_r2 = self.getParam("Length_r2")

        # 计算阵列间距
        interval = radius_5*2 + radius_3*2 - 2*width_r1

        # 基本元素位置计算
        circle1_center = (-radius_1, width_r1/2)  # 中心点
        rect1_pos = (-distance_1, 0)  # 左下角
        rect1_width = length_r1 + distance_1
        rect1_height = width_r1

        arc1_center = (length_r1, width_r1)  # 中心点
        arc1_radius = width_r1
        arc1_angle = 90  # 扇形角
        arc1_rotation = 270  # 旋转角 

        # 计算基础单元中心位置
        arc_unit_centers = []
        for i in range(number):
            offset = i * interval

            # 各单元中的圆弧中心位置
            arc2_center = (length_r1 + radius_2 + width_r1 + offset, width_r1)
            arc3_center = (length_r1 + radius_3 + offset, width_r1)

            angle_rad = angle * 2 * math.pi / 360
            arc4_center_x = length_r1 + 2*radius_3 + radius_4 * math.sin(angle_rad) + offset
            arc4_center_y = width_r1 + radius_4 * math.cos(angle_rad)
            arc4_center = (arc4_center_x, arc4_center_y)

            arc5_center = (length_r1 + radius_5 + 2*radius_3 - width_r1 + offset, width_r1)

            # 添加到阵列列表
            arc_unit_centers.append({
                "arc2_center": arc2_center,
                "arc3_center": arc3_center,
                "arc4_center": arc4_center,
                "arc5_center": arc5_center
            })

        # 计算弧6的参数
        arc6_center = (length_r1 + radius_2 + width_r1 + (interval * number), width_r1)
        arc6_radius = radius_2
        arc6_angle = 180
        arc6_rotation = 0  # 旋转180度

        # 计算弧7的参数 - 修正旋转方向为0度
        arc7_center = (length_r1 + radius_3 + (interval * number), width_r1)
        arc7_radius = radius_3
        arc7_angle = 180
        arc7_rotation = 0  # 修正为0度

        # 计算弧8的参数
        arc8_center = (length_r1 + (interval * number) + (radius_3 * 2), width_r1)
        arc8_radius = width_r1
        arc8_angle = 90
        arc8_rotation = 180  # 旋转180度

        # 计算尾部矩形和圆参数
        rect2_pos = (length_r1 + (interval * number) + (radius_3 * 2), 0)
        rect2_width = length_r2 + distance_1
        rect2_height = width_r1

        circle2_center = (length_r1 + (interval * number) + (radius_3 * 2) + length_r2 + radius_1, width_r1 / 2)

        return {
            "circle1_center": circle1_center, "circle1_radius": radius_1,
            "rect1_pos": rect1_pos, "rect1_width": rect1_width, "rect1_height": rect1_height,
            "arc1_center": arc1_center, "arc1_radius": arc1_radius, 
            "arc1_angle": arc1_angle, "arc1_rotation": arc1_rotation,
            "arc2_radius": radius_2, "arc3_radius": radius_3,
            "arc4_radius": radius_4, "arc4_angle": angle * 2,
            "arc4_rotation": 270 - angle,
            "arc5_radius": radius_5, "arc5_angle": 180, "arc5_rotation": 180,
            "arc_unit_centers": arc_unit_centers,
            "number": number, "interval": interval,
            # 新增元素
            "arc6_center": arc6_center, "arc6_radius": arc6_radius,
            "arc6_angle": arc6_angle, "arc6_rotation": arc6_rotation,
            "arc7_center": arc7_center, "arc7_radius": arc7_radius,
            "arc7_angle": arc7_angle, "arc7_rotation": arc7_rotation,
            "arc8_center": arc8_center, "arc8_radius": arc8_radius,
            "arc8_angle": arc8_angle, "arc8_rotation": arc8_rotation,
            "rect2_pos": rect2_pos, "rect2_width": rect2_width, "rect2_height": rect2_height,
            "circle2_center": circle2_center, "circle2_radius": radius_1
        }

    def updateModel(self):
        try:
            # 更新计算参数
            r5 = self.getParam("Radius_5")
            distance_1 = self.getParam("Distance_1")  # 获取计算值

            self.params["Radius_5"].set(str(round(r5, 4)))

            self.ax.clear()
            for key in self.geoPatch:
                self.geoPatch[key] = []

            # 计算几何参数
            geo = self.calculateGeometry()

            # 绘制圆1 (左侧入口)
            circle1 = mpatches.Circle(geo["circle1_center"], geo["circle1_radius"], 
                                     fill=False, edgecolor='blue', lw=2)
            self.ax.add_patch(circle1)
            self.geoPatch["Radius_1"].append(circle1)

            # 绘制矩形1 (左侧通道) - 只绘制上下两条边
            # 下边
            line_bottom1 = plt.Line2D(
                [geo["rect1_pos"][0], geo["rect1_pos"][0] + geo["rect1_width"]],
                [geo["rect1_pos"][1], geo["rect1_pos"][1]],
                color='blue', lw=2
            )
            self.ax.add_line(line_bottom1)
            self.geoPatch["Length_r1"].append(line_bottom1)
            self.geoPatch["Width_r1"].append(line_bottom1)

            # 上边
            line_top1 = plt.Line2D(
                [geo["rect1_pos"][0], geo["rect1_pos"][0] + geo["rect1_width"]],
                [geo["rect1_pos"][1] + geo["rect1_height"], geo["rect1_pos"][1] + geo["rect1_height"]],
                color='blue', lw=2
            )
            self.ax.add_line(line_top1)
            self.geoPatch["Length_r1"].append(line_top1)
            self.geoPatch["Width_r1"].append(line_top1)

            # 绘制弧1 (左侧连接弧)
            arc1 = mpatches.Arc(geo["arc1_center"], 2*geo["arc1_radius"], 2*geo["arc1_radius"],
                               theta1=geo["arc1_rotation"], theta2=geo["arc1_rotation"]+geo["arc1_angle"],
                               edgecolor='blue', lw=2)
            self.ax.add_patch(arc1)
            self.geoPatch["Width_r1"].append(arc1)

            # 绘制阵列单元
            for i, centers in enumerate(geo["arc_unit_centers"]):
                # 绘制弧2 (小圆内弧)
                arc2 = mpatches.Arc(centers["arc2_center"], 2*geo["arc2_radius"], 2*geo["arc2_radius"],
                                   theta1=0, theta2=180, edgecolor='blue', lw=2)
                self.ax.add_patch(arc2)
                self.geoPatch["Radius_2"].append(arc2)
                self.geoPatch["number"].append(arc2)

                # 绘制弧3 (小圆外弧)
                arc3 = mpatches.Arc(centers["arc3_center"], 2*geo["arc3_radius"], 2*geo["arc3_radius"],
                                   theta1=0, theta2=180, edgecolor='blue', lw=2)
                self.ax.add_patch(arc3)
                self.geoPatch["Radius_2"].append(arc3)  # 使用Radius_2替代
                self.geoPatch["Width_r1"].append(arc3)  # 添加宽度依赖
                self.geoPatch["number"].append(arc3)

                # 绘制弧4 (大圆内弧)
                arc4 = mpatches.Arc(centers["arc4_center"], 2*geo["arc4_radius"], 2*geo["arc4_radius"],
                                   theta1=geo["arc4_rotation"], theta2=geo["arc4_rotation"]+geo["arc4_angle"],
                                   edgecolor='blue', lw=2)
                self.ax.add_patch(arc4)
                self.geoPatch["Radius_4"].append(arc4)
                self.geoPatch["Angle"].append(arc4)
                self.geoPatch["number"].append(arc4)

                # 绘制弧5 (大圆外弧)
                arc5 = mpatches.Arc(centers["arc5_center"], 2*geo["arc5_radius"], 2*geo["arc5_radius"],
                                   theta1=geo["arc5_rotation"], theta2=geo["arc5_rotation"]+geo["arc5_angle"],
                                   edgecolor='blue', lw=2)
                self.ax.add_patch(arc5)
                self.geoPatch["Radius_5"].append(arc5)
                self.geoPatch["number"].append(arc5)

            # 绘制弧6 (右侧弧1)
            arc6 = mpatches.Arc(geo["arc6_center"], 2*geo["arc6_radius"], 2*geo["arc6_radius"],
                               theta1=geo["arc6_rotation"], theta2=geo["arc6_rotation"]+geo["arc6_angle"],
                               edgecolor='blue', lw=2)
            self.ax.add_patch(arc6)
            self.geoPatch["Radius_2"].append(arc6)
            self.geoPatch["number"].append(arc6)

            # 绘制弧7 (右侧弧2) - 修正方向
            arc7 = mpatches.Arc(geo["arc7_center"], 2*geo["arc7_radius"], 2*geo["arc7_radius"],
                               theta1=geo["arc7_rotation"], theta2=geo["arc7_rotation"]+geo["arc7_angle"],
                               edgecolor='blue', lw=2)
            self.ax.add_patch(arc7)
            self.geoPatch["Radius_2"].append(arc7)  # 使用Radius_2替代
            self.geoPatch["Width_r1"].append(arc7)  # 添加宽度依赖
            self.geoPatch["number"].append(arc7)

            # 绘制弧8 (右侧弧3)
            arc8 = mpatches.Arc(geo["arc8_center"], 2*geo["arc8_radius"], 2*geo["arc8_radius"],
                               theta1=geo["arc8_rotation"], theta2=geo["arc8_rotation"]+geo["arc8_angle"],
                               edgecolor='blue', lw=2)
            self.ax.add_patch(arc8)
            self.geoPatch["Width_r1"].append(arc8)
            self.geoPatch["number"].append(arc8)

            # 绘制尾部矩形 - 只绘制上下两条边
            # 下边
            line_bottom2 = plt.Line2D(
                [geo["rect2_pos"][0], geo["rect2_pos"][0] + geo["rect2_width"]],
                [geo["rect2_pos"][1], geo["rect2_pos"][1]],
                color='blue', lw=2
            )
            self.ax.add_line(line_bottom2)
            self.geoPatch["Length_r2"].append(line_bottom2)
            self.geoPatch["Width_r1"].append(line_bottom2)

            # 上边
            line_top2 = plt.Line2D(
                [geo["rect2_pos"][0], geo["rect2_pos"][0] + geo["rect2_width"]],
                [geo["rect2_pos"][1] + geo["rect2_height"], geo["rect2_pos"][1] + geo["rect2_height"]],
                color='blue', lw=2
            )
            self.ax.add_line(line_top2)
            self.geoPatch["Length_r2"].append(line_top2)
            self.geoPatch["Width_r1"].append(line_top2)

            # 绘制尾部圆
            circle2 = mpatches.Circle(geo["circle2_center"], geo["circle2_radius"], 
                                     fill=False, edgecolor='blue', lw=2)
            self.ax.add_patch(circle2)
            self.geoPatch["Radius_1"].append(circle2)
            self.geoPatch["Length_r2"].append(circle2)

            # 计算边界和显示区域
            all_centers = [geo["circle1_center"], geo["arc1_center"], geo["arc6_center"], 
                          geo["arc7_center"], geo["arc8_center"], geo["circle2_center"]]

            for centers in geo["arc_unit_centers"]:
                all_centers.extend([centers["arc2_center"], centers["arc3_center"], 
                                   centers["arc4_center"], centers["arc5_center"]])

            # 计算边界
            x_coords = [p[0] for p in all_centers]
            y_coords = [p[1] for p in all_centers]

            # 矩形1的四个角点
            rect1_points = [
                (geo["rect1_pos"][0], geo["rect1_pos"][1]),
                (geo["rect1_pos"][0] + geo["rect1_width"], geo["rect1_pos"][1]),
                (geo["rect1_pos"][0], geo["rect1_pos"][1] + geo["rect1_height"]),
                (geo["rect1_pos"][0] + geo["rect1_width"], geo["rect1_pos"][1] + geo["rect1_height"])
            ]
            x_coords.extend([p[0] for p in rect1_points])
            y_coords.extend([p[1] for p in rect1_points])

            # 矩形2的四个角点
            rect2_points = [
                (geo["rect2_pos"][0], geo["rect2_pos"][1]),
                (geo["rect2_pos"][0] + geo["rect2_width"], geo["rect2_pos"][1]),
                (geo["rect2_pos"][0], geo["rect2_pos"][1] + geo["rect2_height"]),
                (geo["rect2_pos"][0] + geo["rect2_width"], geo["rect2_pos"][1] + geo["rect2_height"])
            ]
            x_coords.extend([p[0] for p in rect2_points])
            y_coords.extend([p[1] for p in rect2_points])

            # 添加半径影响
            max_radius = max(geo["circle1_radius"], geo["arc1_radius"], 
                           geo["arc2_radius"], geo["arc3_radius"], 
                           geo["arc4_radius"], geo["arc5_radius"], geo["circle2_radius"])

            x_min = min(x_coords) - max_radius - 3
            x_max = max(x_coords) + max_radius + 3
            y_min = min(y_coords) - max_radius - 3
            y_max = max(y_coords) + max_radius + 3

            self.ax.set_xlim(x_min, x_max)
            self.ax.set_ylim(y_min, y_max)
            self.ax.set_aspect('equal')
            self.ax.grid(True, linestyle='--', alpha=0.5)

            # 添加标题
            self.ax.set_title("InertialSeparator", fontsize=14)
            self.ax.set_xlabel("")
            self.ax.set_ylabel("")

            self.canvas.draw()
            self.stsVar.set(f"已更新 / Updated - R5={r5:.4f}mm, 阵列间距={geo['interval']:.4f}mm, Distance_1={distance_1:.4f}mm")

            # 如果有选中的参数，重新应用高亮
            if self.curHlt:
                self.highlightComponent(self.curHlt)

        except Exception as e:
            messagebox.showerror("错误 / Error", str(e))
            self.stsVar.set(f"失败 / Failed: {str(e)}")

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

            # 添加圆1 (入口)
            msp.add_circle(geo["circle1_center"], geo["circle1_radius"])

            # 添加矩形1 (左侧通道) - 只绘制上下两条边
            # 下边
            msp.add_line(
                (geo["rect1_pos"][0], geo["rect1_pos"][1]),
                (geo["rect1_pos"][0] + geo["rect1_width"], geo["rect1_pos"][1])
            )

            # 上边
            msp.add_line(
                (geo["rect1_pos"][0], geo["rect1_pos"][1] + geo["rect1_height"]),
                (geo["rect1_pos"][0] + geo["rect1_width"], geo["rect1_pos"][1] + geo["rect1_height"])
            )

            # 添加弧1 (左侧连接弧)
            msp.add_arc(geo["arc1_center"], geo["arc1_radius"],
                       geo["arc1_rotation"], geo["arc1_rotation"] + geo["arc1_angle"])

            # 添加阵列单元
            for centers in geo["arc_unit_centers"]:
                # 弧2 (小圆内弧)
                msp.add_arc(centers["arc2_center"], geo["arc2_radius"], 0, 180)
                # 弧3 (小圆外弧)
                msp.add_arc(centers["arc3_center"], geo["arc3_radius"], 0, 180)
                # 弧4 (大圆内弧)
                msp.add_arc(centers["arc4_center"], geo["arc4_radius"], 
                           geo["arc4_rotation"], geo["arc4_rotation"] + geo["arc4_angle"])
                # 弧5 (大圆外弧)
                msp.add_arc(centers["arc5_center"], geo["arc5_radius"], 
                           geo["arc5_rotation"], geo["arc5_rotation"] + geo["arc5_angle"])

            # 添加弧6 (右侧弧1)
            msp.add_arc(geo["arc6_center"], geo["arc6_radius"],
                       geo["arc6_rotation"], geo["arc6_rotation"] + geo["arc6_angle"])

            # 添加弧7 (右侧弧2)
            msp.add_arc(geo["arc7_center"], geo["arc7_radius"],
                       geo["arc7_rotation"], geo["arc7_rotation"] + geo["arc7_angle"])

            # 添加弧8 (右侧弧3)
            msp.add_arc(geo["arc8_center"], geo["arc8_radius"],
                       geo["arc8_rotation"], geo["arc8_rotation"] + geo["arc8_angle"])

            # 添加尾部矩形 - 只绘制上下两条边
            # 下边
            msp.add_line(
                (geo["rect2_pos"][0], geo["rect2_pos"][1]),
                (geo["rect2_pos"][0] + geo["rect2_width"], geo["rect2_pos"][1])
            )

            # 上边
            msp.add_line(
                (geo["rect2_pos"][0], geo["rect2_pos"][1] + geo["rect2_height"]),
                (geo["rect2_pos"][0] + geo["rect2_width"], geo["rect2_pos"][1] + geo["rect2_height"])
            )

            # 添加尾部圆
            msp.add_circle(geo["circle2_center"], geo["circle2_radius"])

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
