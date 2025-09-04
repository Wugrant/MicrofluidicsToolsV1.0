# Copyright (c) 2025 [Grant]
# Licensed under the MIT License.
# See LICENSE in the project root for license information.
import tkinter as tk
from tkinter import ttk

import math

#---------- 1. 液滴转换器函数 ----------

def droplet_d_to_v(d):
    """直径(μm) -> 体积(nL)"""

    return 4/3e6 * math.pi * (d/2)**3

def droplet_v_to_d(v):

    """体积(nL) -> 直径(μm)"""
    return 100 * (3/4/math.pi*v)**(1/3) * 2

#---------- 2. 流量转换计算器函数 ----------

def mass_to_quantity(mass, time, density=1e6):
    """质量转流量"""
    Q = mass / time / density / 60  # m³/s
    q = Q * 60 * 1e9  # μL/min

    return Q, q

def quantity_to_velocity(Q, w, h=None, d=None, shape="rect"):

    """流量转速度"""

    if shape == "rect":

        v = Q / 60 / w / h * 1000

    else:  # 圆柱

        v = Q / 60 / (math.pi * (d/2)**2) * 1000

    return v

def velocity_to_quantity(v, w, h=None, d=None, shape="rect"):
    """速度转流量"""
    if shape == "rect":
        Q = v * w * h * 60 / 1000  # μL/min

    else:  # 圆柱
        Q = v * math.pi * (d/2)**2 * 60 / 1000  # μL/min

    return Q

def quantity_to_mass(Q, time, density=1e6):

    """流量转质量"""

    Q_m3_s = Q / 60 / 1e9  # μL/min → m³/s

    mass = Q_m3_s * density * 60 * time  # g

    return mass

def resistance_to_pressure(Q, resistance_factor, mu=1.005):
    """几何流阻系数转压力"""

    P = Q * resistance_factor * mu * 1e-6 * (1/60) * 1e-9 * 1e18 /100000
    return P

def pressure_to_resistance(P, Q, mu=1.005):
    """压力转几何流阻系数"""

    resistance_factor = P / (Q * mu * 1e-6 * (1/60) * 1e-9 * 1e18 * 1e-3)*100

    return resistance_factor

#---------- 3. 几何流阻计算器函数 ----------
def resistance_factor_cyl(d, l):
    """计算圆柱体(CYL)的几何流阻系数"""
    return 128 * l / (math.pi * d**4)

def resistance_factor_rect(w, h, l):
    """计算矩形(RECT)的几何流阻系数"""
    a = max(w, h)
    b = min(w, h)

    return 12 * l / (a * b**3) / (1 - 0.63 * (b/a))

def resistance_factor_squa(w, h, l):
    """计算方形(SQUA)的几何流阻系数"""

    a = max(w, h)
    b = min(w, h)

    a = (a + b) / 2

    return 28 * l * a**(-4)

def resistance_factor_rect_mod(w, h, l):

    """计算改进矩形(RECT_MOD)的几何流阻系数"""
    a = max(w, h)

    b = min(w, h)
    if a > 1.3 * b:

        return 12 * l / (a * b**3) / (1 - 0.63 * (b/a))

    else:
        a = (a + b) / 2
        return 28 * l * a**(-4)

def channel_v_cyl(d, l):
    """计算圆柱体微通道体积(μL)"""

    return d * d * l * math.pi * 0.25 * 1e-9

def channel_v_cub(w, h, l):
    """计算立方体微通道体积(μL)"""

    return w * h * l * 1e-9

class MicrofluidCalculatorApp:
    def __init__(self, root):
        self.root = root

        self.root.title("微流体计算工具集Microfluidic Tools")
        self.root.geometry("550x550")
        
        # 历史记录存储
        self.history = {tab: [] for tab in ["tab1", "tab2", "tab3", "tab4", "tab5", "tab6", "tab7", "tab8"]}
        
        # 创建选项卡

        self.tab_control = ttk.Notebook(root)
        
        # 创建八个选项卡
        self.tabs = []

        for i in range(8):
            self.tabs.append(ttk.Frame(self.tab_control))

        
        tab_names = ["质量→流量", 
                    "流量→质量", 
                    "流量→速度", 
                    "速度→流量", 
                    "流阻→压力", 
                    "压力→流阻", 
                    "液滴转换器", 
                    "几何流阻计算"]

        
        for i, name in enumerate(tab_names):

            self.tab_control.add(self.tabs[i], text=name)
        
        self.tab_control.pack(expand=1, fill="both")
        
        # 设置各选项卡

        self.setup_tabs()

        # 添加版权标签 - 在这里添加

        copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 

                             fg="#555555", bg="#f0f0f0", font=("Arial", 8))
        copyright_label.pack(side=tk.BOTTOM, fill=tk.X, pady=1)

    def create_input_field(self, parent, label, default, row, column=0, width=10):

        """创建输入字段"""
        ttk.Label(parent, text=label).grid(column=column, row=row, sticky=tk.W, pady=5)

        entry = ttk.Entry(parent, width=width)
        entry.grid(column=column+1, row=row, sticky=tk.W, pady=5)
        entry.insert(0, default)
        return entry
    
    def create_history_frame(self, parent, row, column=0, columnspan=2):
        """创建历史记录框架"""
        history_frame = ttk.LabelFrame(parent, text="历史记录Log", padding="5")
        history_frame.grid(column=column, row=row, columnspan=columnspan, sticky="ew", pady=5)

        
        history_labels = []

        for i in range(5):
            label = ttk.Label(history_frame, text="", wraplength=450)
            label.grid(column=0, row=i, sticky=tk.W, pady=2)
            history_labels.append(label)

        return history_labels

    
    def add_to_history(self, tab, entry):
        """添加记录到历史列表"""
        self.history[tab].insert(0, entry)  # 在列表开头插入

        self.history[tab] = self.history[tab][:5]  # 保留最近5条

        
        # 更新对应标签
        history_labels = getattr(self, f"history_labels_{tab}")

        for i, record in enumerate(self.history[tab]):
            history_labels[i].config(text=f"{i+1}. {record}")

    
    def setup_tabs(self):
        """设置所有选项卡"""

        self.setup_tab1()  # 质量→流量

        self.setup_tab2()  # 流量→质量

        self.setup_tab3()  # 流量→速度
        self.setup_tab4()  # 速度→流量
        self.setup_tab5()  # 流阻→压力

        self.setup_tab6()  # 压力→流阻
        self.setup_tab7()  # 液滴转换器

        self.setup_tab8()  # 几何流阻计算

    
    def setup_tab1(self):

        """质量→流量"""
        frame = ttk.Frame(self.tabs[0], padding="10")
        frame.pack(fill="both", expand=True)

        
        # 添加中英文标题

        title_label = ttk.Label(frame, text="质量→流量 (Mass→Flow Rate)", 

                            font=("Arial", 12, "bold"))
        title_label.grid(column=0, row=0, columnspan=2, pady=(0, 10))
        
        # 输入
        self.mass_entry = self.create_input_field(frame, "质量Mass (g):", "5.48", 1)

        self.time_m2q_entry = self.create_input_field(frame, "时间Time (min):", "5", 2)

        self.density_m2q_entry = self.create_input_field(frame, "流体密度Density (g/m³):", "1e6", 3)

        
        # 计算按钮
        ttk.Button(frame, text="计算Calculate", command=self.calculate_quantity).grid(column=0, row=4, columnspan=2, pady=5)

        
        # 结果

        result_frame = ttk.LabelFrame(frame, text="结果Result", padding="5")
        result_frame.grid(column=0, row=5, columnspan=2, sticky="ew", pady=5)

        
        ttk.Label(result_frame, text="流量Volumetric Flow Rate (m³/s):").grid(column=0, row=0, sticky=tk.W)
        self.Q_var = tk.StringVar()
        ttk.Label(result_frame, textvariable=self.Q_var, width=15).grid(column=1, row=0, sticky=tk.W)

        
        ttk.Label(result_frame, text="流量Volumetric Flow Rate (μL/min):").grid(column=0, row=1, sticky=tk.W)
        self.q_var = tk.StringVar()

        ttk.Label(result_frame, textvariable=self.q_var, width=15).grid(column=1, row=1, sticky=tk.W)
        
        # 历史记录

        self.history_labels_tab1 = self.create_history_frame(frame, 6)

        
        # 初始计算
        self.calculate_quantity()

    def setup_tab2(self):

        """流量→质量"""
        frame = ttk.Frame(self.tabs[1], padding="10")

        frame.pack(fill="both", expand=True)
        
        # 添加中英文标题

        title_label = ttk.Label(frame, text="流量→质量 (Flow Rate→Mass)", 

                            font=("Arial", 12, "bold"))
        title_label.grid(column=0, row=0, columnspan=2, pady=(0, 10))
        
        # 输入
        self.Q_q2m_entry = self.create_input_field(frame, "流量Volumetric Flow Rate (μL/min):", "10", 1)
        self.time_q2m_entry = self.create_input_field(frame, "时间Time (min):", "5", 2)
        self.density_q2m_entry = self.create_input_field(frame, "流体密度Density (g/m³):", "1e6", 3)
        
        # 计算按钮

        ttk.Button(frame, text="计算Calculate", command=self.calculate_mass).grid(column=0, row=4, columnspan=2, pady=5)
        
        # 结果
        result_frame = ttk.LabelFrame(frame, text="结果Result", padding="5")

        result_frame.grid(column=0, row=5, columnspan=2, sticky="ew", pady=5)
        
        ttk.Label(result_frame, text="质量Mass (g):").grid(column=0, row=0, sticky=tk.W)

        self.mass_var = tk.StringVar()

        ttk.Label(result_frame, textvariable=self.mass_var, width=15).grid(column=1, row=0, sticky=tk.W)
        
        # 历史记录
        self.history_labels_tab2 = self.create_history_frame(frame, 6)
        
        # 初始计算

        self.calculate_mass()

    def setup_tab3(self):

        """流量→速度"""
        frame = ttk.Frame(self.tabs[2], padding="10")
        frame.pack(fill="both", expand=True)

        
        # 添加中英文标题

        title_label = ttk.Label(frame, text="流量→速度 (Flow Rate→Velocity)", 

                            font=("Arial", 12, "bold"))
        title_label.grid(column=0, row=0, columnspan=2, pady=(0, 10))
        
        # 形状选择
        ttk.Label(frame, text="通道形状Shape:").grid(column=0, row=1, sticky=tk.W, pady=5)

        self.q2v_shape_var = tk.StringVar(value="rect")
        shape_frame = ttk.Frame(frame)

        shape_frame.grid(column=1, row=1, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(shape_frame, text="矩形rect", variable=self.q2v_shape_var, 

                    value="rect", command=self.toggle_q2v_shape).pack(side=tk.LEFT)

        ttk.Radiobutton(shape_frame, text="圆柱cyl", variable=self.q2v_shape_var, 

                    value="cyl", command=self.toggle_q2v_shape).pack(side=tk.LEFT)

        
        # 输入

        self.Q_entry = self.create_input_field(frame, "流量Volumetric Flow Rate (μL/min):", "10", 2)
        
        # 矩形参数框架

        self.q2v_rect_frame = ttk.Frame(frame)
        self.q2v_rect_frame.grid(column=0, row=3, columnspan=2, sticky="ew")

        self.width_q2v_entry = self.create_input_field(self.q2v_rect_frame, "流道宽度Width (μm):", "200", 0)
        self.height_q2v_entry = self.create_input_field(self.q2v_rect_frame, "流道高度Height (μm):", "160", 1)

        
        # 圆柱参数框架

        self.q2v_cyl_frame = ttk.Frame(frame)

        self.diameter_q2v_entry = self.create_input_field(self.q2v_cyl_frame, "流道内直径Inner Diameter (μm):", "100", 0)
        
        # 计算按钮

        ttk.Button(frame, text="计算Calculate", command=self.calculate_velocity).grid(column=0, row=4, columnspan=2, pady=5)
        
        # 结果
        result_frame = ttk.LabelFrame(frame, text="结果Result", padding="5")

        result_frame.grid(column=0, row=5, columnspan=2, sticky="ew", pady=5)
        
        ttk.Label(result_frame, text="平均速度Average Velocity (m/s):").grid(column=0, row=0, sticky=tk.W)

        self.v_var = tk.StringVar()
        ttk.Label(result_frame, textvariable=self.v_var, width=15).grid(column=1, row=0, sticky=tk.W)

        
        # 历史记录
        self.history_labels_tab3 = self.create_history_frame(frame, 6)
        
        # 初始设置显示矩形
        self.toggle_q2v_shape()

    def setup_tab4(self):
        """速度→流量"""
        frame = ttk.Frame(self.tabs[3], padding="10")
        frame.pack(fill="both", expand=True)

        
        # 添加中英文标题

        title_label = ttk.Label(frame, text="速度→流量 (Velocity→Flow Rate)", 
                            font=("Arial", 12, "bold"))

        title_label.grid(column=0, row=0, columnspan=2, pady=(0, 10))

        
        # 形状选择
        ttk.Label(frame, text="通道形状Shape:").grid(column=0, row=1, sticky=tk.W, pady=5)

        self.v2q_shape_var = tk.StringVar(value="rect")

        shape_frame = ttk.Frame(frame)
        shape_frame.grid(column=1, row=1, sticky=tk.W, pady=5)

        
        ttk.Radiobutton(shape_frame, text="矩形Rect", variable=self.v2q_shape_var, 

                    value="rect", command=self.toggle_v2q_shape).pack(side=tk.LEFT)
        ttk.Radiobutton(shape_frame, text="圆柱Cyl", variable=self.v2q_shape_var, 

                    value="cyl", command=self.toggle_v2q_shape).pack(side=tk.LEFT)

        
        # 输入

        self.v_entry = self.create_input_field(frame, "平均速度Average Velocity (m/s):", "0.005", 2)

        
        # 矩形参数框架
        self.v2q_rect_frame = ttk.Frame(frame)

        self.v2q_rect_frame.grid(column=0, row=3, columnspan=2, sticky="ew")

        self.width_v2q_entry = self.create_input_field(self.v2q_rect_frame, "流道宽度Width (μm):", "200", 0)

        self.height_v2q_entry = self.create_input_field(self.v2q_rect_frame, "流道高度Height (μm):", "160", 1)

        
        # 圆柱参数框架
        self.v2q_cyl_frame = ttk.Frame(frame)
        self.diameter_v2q_entry = self.create_input_field(self.v2q_cyl_frame, "流道内直径Inner Diameter (μm):", "100", 0)
        
        # 计算按钮
        ttk.Button(frame, text="计算Calculate", command=self.calculate_flow_from_velocity).grid(column=0, row=4, columnspan=2, pady=5)
        
        # 结果
        result_frame = ttk.LabelFrame(frame, text="结果Result", padding="5")

        result_frame.grid(column=0, row=5, columnspan=2, sticky="ew", pady=5)
        
        ttk.Label(result_frame, text="流量Volumetric Flow Rate (μL/min):").grid(column=0, row=0, sticky=tk.W)

        self.flow_var = tk.StringVar()

        ttk.Label(result_frame, textvariable=self.flow_var, width=15).grid(column=1, row=0, sticky=tk.W)
        
        # 历史记录

        self.history_labels_tab4 = self.create_history_frame(frame, 6)
        
        # 初始设置

        self.toggle_v2q_shape()

    def setup_tab5(self):

        """几何流阻系数→压力"""
        frame = ttk.Frame(self.tabs[4], padding="10")
        frame.pack(fill="both", expand=True)

        
        # 添加中英文标题

        title_label = ttk.Label(frame, text="流阻→压力 (Flow Resistance→Pressure)", 

                            font=("Arial", 12, "bold"))
        title_label.grid(column=0, row=0, columnspan=2, pady=(0, 10))
        
        # 输入
        self.Q_r2p_entry = self.create_input_field(frame, "流量Volumetric Flow Rate (μL/min):", "660", 1)

        self.resistance_entry = self.create_input_field(frame, "几何流阻系数Geometric Flow Resistance Coefficient (1e16 m^-3):", "0.001", 2)
        self.mu_r2p_entry = self.create_input_field(frame, "流体动力黏度Dynamic Viscosity (10^-3 Pa·s):", "1.005", 3)
        
        # 计算按钮

        ttk.Button(frame, text="计算Calculate", command=self.calculate_pressure).grid(column=0, row=4, columnspan=2, pady=5)
        
        # 结果
        result_frame = ttk.LabelFrame(frame, text="结果Result", padding="5")

        result_frame.grid(column=0, row=5, columnspan=2, sticky="ew", pady=5)
        
        ttk.Label(result_frame, text="压力 (MPa):").grid(column=0, row=0, sticky=tk.W)

        self.pressure_var = tk.StringVar()

        ttk.Label(result_frame, textvariable=self.pressure_var, width=15).grid(column=1, row=0, sticky=tk.W)
        
        # 历史记录

        self.history_labels_tab5 = self.create_history_frame(frame, 6)
        
        # 初始计算
        self.calculate_pressure()

    def setup_tab6(self):
        """压力→几何流阻系数"""

        frame = ttk.Frame(self.tabs[5], padding="10")
        frame.pack(fill="both", expand=True)

        
        # 添加中英文标题
        title_label = ttk.Label(frame, text="压力→流阻 (Pressure→Flow Resistance)", 

                            font=("Arial", 12, "bold"))
        title_label.grid(column=0, row=0, columnspan=2, pady=(0, 10))
        
        # 输入
        self.pressure_p2r_entry = self.create_input_field(frame, "压力Pressure (MPa):", "0.0111", 1)
        self.Q_p2r_entry = self.create_input_field(frame, "流量Volumetric Flow Rate (μL/min):", "660", 2)
        self.mu_p2r_entry = self.create_input_field(frame, "流体黏度 (10^-3 Pa·s):", "1.005", 3)
        
        # 计算按钮
        ttk.Button(frame, text="计算Calculate", command=self.calculate_resistance_factor).grid(column=0, row=4, columnspan=2, pady=5)

        
        # 结果

        result_frame = ttk.LabelFrame(frame, text="结果Result", padding="5")
        result_frame.grid(column=0, row=5, columnspan=2, sticky="ew", pady=5)

        
        ttk.Label(result_frame, text="几何流阻系数 (1e16 m^-3):").grid(column=0, row=0, sticky=tk.W)

        self.resistance_factor_var = tk.StringVar()

        ttk.Label(result_frame, textvariable=self.resistance_factor_var, width=15).grid(column=1, row=0, sticky=tk.W)

        
        # 历史记录
        self.history_labels_tab6 = self.create_history_frame(frame, 6)
        
        # 初始计算

        self.calculate_resistance_factor()

            
    def setup_tab7(self):
        """液滴转换器"""
        frame = ttk.Frame(self.tabs[6], padding="10")

        frame.pack(fill="both", expand=True)
        
        # 添加中英文标题
        title_label = ttk.Label(frame, text="液滴转换器 (Droplet Converter)", 

                            font=("Arial", 12, "bold"))
        title_label.grid(column=0, row=0, columnspan=3, pady=(0, 10))

        
        # 当前转换模式 - 默认为直径转体积
        self.current_mode = "d_to_v"

        
        # 模式切换按钮

        self.mode_button = ttk.Button(frame, text="切换到：体积→直径", 

                                    command=self.switch_mode)

        self.mode_button.grid(column=0, row=1, columnspan=3, pady=5)
        
        # 转换区域标题

        self.title_label = ttk.Label(frame, text="直径到体积转换", 
                                    font=("Arial", 11, "bold"))

        self.title_label.grid(column=0, row=2, columnspan=3, pady=5)
        
        # 输入部分
        self.input_label = ttk.Label(frame, text="直径Droplet Diameter (μm):")

        self.input_label.grid(column=0, row=3, sticky=tk.W, pady=5)
        
        self.input_entry = ttk.Entry(frame, width=10)
        self.input_entry.grid(column=1, row=3, sticky=tk.W, pady=5)
        self.input_entry.insert(0, "100")  # 直径模式默认值100

        
        ttk.Button(frame, text="计算Calculate", command=self.calculate_droplet).grid(column=2, row=3, padx=5)

        
        # 输出结果框架

        self.result_frame = ttk.LabelFrame(frame, text="结果Result", padding="5")
        self.result_frame.grid(column=0, row=4, columnspan=3, sticky="ew", pady=5)
        
        # 结果标签和值

        self.output_label = ttk.Label(self.result_frame, text="体积(nL):")

        self.output_label.grid(column=0, row=0, sticky=tk.W)

        
        self.result_label = ttk.Label(self.result_frame, text="")

        self.result_label.grid(column=1, row=0, sticky=tk.W)

        
        # 历史记录
        ttk.Label(frame, text="历史记录Log", font=("Arial", 11, "bold")).grid(

            column=0, row=6, columnspan=3, pady=5)
        
        # 历史记录标签

        self.history_labels_tab7 = []

        for i in range(5):
            label = ttk.Label(frame, text="", width=40)
            label.grid(column=0, row=7+i, columnspan=3, sticky=tk.W, pady=2)
            self.history_labels_tab7.append(label)

        
        # 初始计算
        self.calculate_droplet()

    def setup_tab8(self):

        """几何流阻系数计算器"""
        frame = ttk.Frame(self.tabs[7], padding="10")

        frame.pack(fill="both", expand=True)
        
        # 添加中英文标题

        title_label = ttk.Label(frame, text="几何流阻计算 (Geometric Flow Resistance Calculator)", 
                            font=("Arial", 12, "bold"))

        title_label.grid(column=0, row=0, columnspan=3, pady=(0, 10))

    
        # 预填充默认值
        self.default_values = {

            "CYL": {"d": 100, "l": 1000},

            "RECT": {"w": 100, "h": 50, "l": 1000},

            "SQUA": {"w": 100, "h": 100, "l": 1000},

            "RECT_MOD": {"w": 100, "h": 70, "l": 1000}

        }
        
        # 形状选择

        ttk.Label(frame, text="选择形状:").grid(column=0, row=1, sticky=tk.W, pady=5)
        
        self.shape_var = tk.StringVar()
        self.shape_combo = ttk.Combobox(frame, textvariable=self.shape_var, width=15, state="readonly")

        self.shape_combo['values'] = ('CYL (圆柱体)', 'RECT (矩形)', 'SQUA (方形)', 'RECT_MOD (改进矩形)')

        self.shape_combo.grid(column=1, row=1, columnspan=2, sticky=tk.W, pady=5)
        self.shape_combo.bind('<<ComboboxSelected>>', self.on_shape_select)
        self.shape_combo.current(0)
        
        # 参数框架
        self.input_frame = ttk.LabelFrame(frame, text="参数Factors (μm)", padding="10")
        self.input_frame.grid(column=0, row=2, columnspan=3, sticky="ew", pady=5)

        
        # 圆柱体参数 - 修改变量名避免冲突

        self.cyl_frame = ttk.Frame(self.input_frame)

        ttk.Label(self.cyl_frame, text="直径Inner Diameter (d):").grid(column=0, row=0, sticky=tk.W, pady=5)

        self.diameter_geo_entry = ttk.Entry(self.cyl_frame, width=10)

        self.diameter_geo_entry.grid(column=1, row=0, sticky=tk.W, pady=5)
        
        ttk.Label(self.cyl_frame, text="长度Length (l):").grid(column=0, row=1, sticky=tk.W, pady=5)
        self.length_cyl_geo_entry = ttk.Entry(self.cyl_frame, width=10)

        self.length_cyl_geo_entry.grid(column=1, row=1, sticky=tk.W, pady=5)

        
        # 其他形状参数 - 修改变量名避免冲突

        self.rect_frame = ttk.Frame(self.input_frame)

        ttk.Label(self.rect_frame, text="宽度Width (w):").grid(column=0, row=0, sticky=tk.W, pady=5)

        self.width_geo_entry = ttk.Entry(self.rect_frame, width=10)
        self.width_geo_entry.grid(column=1, row=0, sticky=tk.W, pady=5)

        
        ttk.Label(self.rect_frame, text="高度Height (h):").grid(column=0, row=1, sticky=tk.W, pady=5)

        self.height_geo_entry = ttk.Entry(self.rect_frame, width=10)
        self.height_geo_entry.grid(column=1, row=1, sticky=tk.W, pady=5)

        
        ttk.Label(self.rect_frame, text="长度Length (l):").grid(column=0, row=2, sticky=tk.W, pady=5)

        self.length_rect_geo_entry = ttk.Entry(self.rect_frame, width=10)
        self.length_rect_geo_entry.grid(column=1, row=2, sticky=tk.W, pady=5)
        
        # 计算按钮
        ttk.Button(frame, text="计算Calculate", command=self.calculate_resistance_factor_geo).grid(column=0, row=3, columnspan=3, pady=5)

        
        # 结果显示

        result_frame = ttk.LabelFrame(frame, text="结果Result", padding="10")
        result_frame.grid(column=0, row=4, columnspan=3, sticky="ew", pady=5)

        
        # 体积结果
        ttk.Label(result_frame, text="流道体积Microchannel Volume (μL):").grid(column=0, row=0, sticky=tk.W, pady=5)

        self.volume_var = tk.StringVar()
        self.volume_label = ttk.Label(result_frame, textvariable=self.volume_var, width=20)
        self.volume_label.grid(column=1, row=0, sticky=tk.W, pady=5)
        
        # 几何流阻系数结果

        ttk.Label(result_frame, text="几何流阻系数Geometric Flow Resistance Coefficient (R'):").grid(column=0, row=1, sticky=tk.W, pady=5)
        self.r_result_var = tk.StringVar()

        self.r_result_label = ttk.Label(result_frame, textvariable=self.r_result_var, width=20)

        self.r_result_label.grid(column=1, row=1, sticky=tk.W, pady=5)
        
        ttk.Label(frame, text="单位: × 10^18 m^-1", font=("Arial", 9)).grid(column=0, row=5, columnspan=3, sticky=tk.W)

        
        # 历史记录
        self.history_labels_tab8 = self.create_history_frame(frame, 6, columnspan=3)

        
        # 初始化默认选择
        self.on_shape_select(None)
    
    def toggle_q2v_shape(self):
        """切换流量→速度选项卡中的形状参数"""
        if self.q2v_shape_var.get() == "rect":
            self.q2v_cyl_frame.grid_remove()
            self.q2v_rect_frame.grid(column=0, row=2, columnspan=2, sticky="ew")
        else:
            self.q2v_rect_frame.grid_remove()

            self.q2v_cyl_frame.grid(column=0, row=2, columnspan=2, sticky="ew")

        
        self.calculate_velocity()

    def toggle_v2q_shape(self):

        """切换速度→流量选项卡中的形状参数"""
        if self.v2q_shape_var.get() == "rect":
            self.v2q_cyl_frame.grid_remove()
            self.v2q_rect_frame.grid(column=0, row=2, columnspan=2, sticky="ew")
        else:
            self.v2q_rect_frame.grid_remove()
            self.v2q_cyl_frame.grid(column=0, row=2, columnspan=2, sticky="ew")

        
        self.calculate_flow_from_velocity()
    
    def on_shape_select(self, event):
        """处理形状选择"""
        shape_full = self.shape_var.get()

        shape = shape_full.split()[0] if shape_full else "CYL"

        
        # 切换输入框

        for frame in [self.cyl_frame, self.rect_frame]:
            frame.pack_forget()

        
        # 预填充数值

        if shape == 'CYL':
            self.cyl_frame.pack(fill=tk.X)
            self.diameter_geo_entry.delete(0, tk.END)  # 更改变量名

            self.length_cyl_geo_entry.delete(0, tk.END)  # 更改变量名

            self.diameter_geo_entry.insert(0, str(self.default_values[shape]["d"]))

            self.length_cyl_geo_entry.insert(0, str(self.default_values[shape]["l"]))
        else:
            self.rect_frame.pack(fill=tk.X)
            self.width_geo_entry.delete(0, tk.END)  # 更改变量名

            self.height_geo_entry.delete(0, tk.END)  # 更改变量名
            self.length_rect_geo_entry.delete(0, tk.END)  # 更改变量名

            self.width_geo_entry.insert(0, str(self.default_values[shape]["w"]))
            self.height_geo_entry.insert(0, str(self.default_values[shape]["h"]))
            self.length_rect_geo_entry.insert(0, str(self.default_values[shape]["l"]))
        
        # 自动计算
        self.calculate_resistance_factor_geo()
    
    def switch_mode(self):

        """切换液滴转换模式"""

        if self.current_mode == "d_to_v":
            # 切换到体积转直径模式

            self.current_mode = "v_to_d"
            self.mode_button.config(text="切换到：直径→体积")

            self.title_label.config(text="体积到直径转换")
            self.input_label.config(text="体积 (nL):")
            self.output_label.config(text="直径(μm):")

            
            # 重置输入框为体积模式默认值1

            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, "1")
        else:
            # 切换到直径转体积模式
            self.current_mode = "d_to_v"
            self.mode_button.config(text="切换到：体积→直径")
            self.title_label.config(text="直径到体积转换")
            self.input_label.config(text="直径 (μm):")
            
            # 重置输入框为直径模式默认值100

            self.input_entry.delete(0, tk.END)

            self.input_entry.insert(0, "100")

        
        # 计算并显示结果
        self.calculate_droplet()

    
    def format_volume_result(self, volume_nl):
        """格式化体积结果，小于1nL时转为pL"""
        if volume_nl < 1:
            # 转换为pL
            volume_pl = volume_nl * 1000
            self.result_label.config(text=f"{volume_pl:.4f}")

            self.output_label.config(text="体积Volume(pL):")

        else:
            self.result_label.config(text=f"{volume_nl:.4f}")
            self.output_label.config(text="体积Volume(nL):")
    
    def calculate_droplet(self):

        """执行液滴转换计算"""
        try:
            input_value = float(self.input_entry.get())
            
            if self.current_mode == "d_to_v":
                result = droplet_d_to_v(input_value)
                self.format_volume_result(result)
                
                # 添加到历史记录

                if result < 1:
                    record = f"直径 {input_value:.2f} μm → 体积 {result*1000:.4f} pL"
                else:
                    record = f"直径 {input_value:.2f} μm → 体积 {result:.4f} nL"

            else:
                result = droplet_v_to_d(input_value)

                self.result_label.config(text=f"{result:.4f}")
                
                # 添加到历史记录
                record = f"体积 {input_value:.4f} nL → 直径 {result:.2f} μm"
            
            # 更新历史记录
            self.history["tab7"].insert(0, record)

            if len(self.history["tab7"]) > 5:
                self.history["tab7"].pop()

            
            for i, label in enumerate(self.history_labels_tab7):
                if i < len(self.history["tab7"]):
                    label.config(text=self.history["tab7"][i])

                else:
                    label.config(text="")
                    
        except ValueError:
            self.result_label.config(text="输入错误")
    
    def calculate_quantity(self):
        """计算流量"""
        try:
            mass = float(self.mass_entry.get())
            time = float(self.time_m2q_entry.get())
            density = float(self.density_m2q_entry.get())

            
            if mass <= 0 or time <= 0 or density <= 0:

                raise ValueError()
                
            Q, q = mass_to_quantity(mass, time, density)

            
            self.Q_var.set(f"{Q:.6e}")
            self.q_var.set(f"{q:.4f}")
            
            # 添加到历史记录
            history_entry = f"质量: {mass}g, 时间: {time}min → 流量: {q:.4f}μL/min"
            self.add_to_history("tab1", history_entry)
            
        except ValueError:
            self.Q_var.set("输入错误")

            self.q_var.set("输入错误")

    
    def calculate_velocity(self):

        """计算流速"""
        try:
            Q = float(self.Q_entry.get())

            shape = self.q2v_shape_var.get()
            
            if Q <= 0:

                raise ValueError()
                
            if shape == "rect":
                # 修改变量引用以使用新的变量名
                w = float(self.width_q2v_entry.get())
                h = float(self.height_q2v_entry.get())

                if w <= 0 or h <= 0:

                    raise ValueError()
                v = quantity_to_velocity(Q, w, h, shape="rect")
                
                # 添加到历史记录
                history_entry = f"流量: {Q}μL/min, 矩形 {w}×{h}μm → 速度: {v:.6f}m/s"

            else:
                d = float(self.diameter_q2v_entry.get())

                if d <= 0:

                    raise ValueError()
                v = quantity_to_velocity(Q, None, None, d, shape="cyl")
                
                # 添加到历史记录

                history_entry = f"流量: {Q}μL/min, 圆柱 Φ{d}μm → 速度: {v:.6f}m/s"
            
            self.v_var.set(f"{v:.6f}")

            self.add_to_history("tab3", history_entry)
            
        except ValueError:
            self.v_var.set("输入错误")

    
    def calculate_flow_from_velocity(self):

        """计算速度→流量"""

        try:
            v = float(self.v_entry.get())

            shape = self.v2q_shape_var.get()
            
            if v <= 0:

                raise ValueError()
                
            if shape == "rect":

                w = float(self.width_v2q_entry.get())

                h = float(self.height_v2q_entry.get())
                if w <= 0 or h <= 0:

                    raise ValueError()
                Q = velocity_to_quantity(v, w, h, shape="rect")

                
                # 添加到历史记录

                history_entry = f"速度: {v}m/s, 矩形 {w}×{h}μm → 流量: {Q:.4f}μL/min"

            else:
                d = float(self.diameter_v2q_entry.get())
                if d <= 0:
                    raise ValueError()

                Q = velocity_to_quantity(v, None, None, d, shape="cyl")
                
                # 添加到历史记录

                history_entry = f"速度: {v}m/s, 圆柱 Φ{d}μm → 流量: {Q:.4f}μL/min"

            
            self.flow_var.set(f"{Q:.4f}")

            self.add_to_history("tab4", history_entry)
            
        except ValueError:
            self.flow_var.set("输入错误")

    
    def calculate_mass(self):
        """计算质量"""
        try:
            Q = float(self.Q_q2m_entry.get())
            time = float(self.time_q2m_entry.get())

            density = float(self.density_q2m_entry.get())
            
            if Q <= 0 or time <= 0 or density <= 0:

                raise ValueError()
                
            mass = quantity_to_mass(Q, time, density)
            
            self.mass_var.set(f"{mass:.4f}")
            
            # 添加到历史记录
            history_entry = f"流量: {Q}μL/min, 时间: {time}min → 质量: {mass:.4f}g"
            self.add_to_history("tab2", history_entry)
            
        except ValueError:
            self.mass_var.set("输入错误")

    
    def calculate_pressure(self):

        """计算压力"""

        try:
            Q = float(self.Q_r2p_entry.get())
            resistance_factor = float(self.resistance_entry.get())

            mu = float(self.mu_r2p_entry.get())

            
            if Q <= 0 or resistance_factor <= 0 or mu <= 0:

                raise ValueError()
                
            P = resistance_to_pressure(Q, resistance_factor, mu)

            
            self.pressure_var.set(f"{P:.6f}")
            
            # 添加到历史记录

            history_entry = f"流量: {Q}μL/min, 几何流阻系数: {resistance_factor} → 压力: {P:.6f}MPa"
            self.add_to_history("tab5", history_entry)

            
        except ValueError:
            self.pressure_var.set("输入错误")
    
    def calculate_resistance_factor(self):
        """计算几何流阻系数"""

        try:
            P = float(self.pressure_p2r_entry.get())

            Q = float(self.Q_p2r_entry.get())

            mu = float(self.mu_p2r_entry.get())

            
            if P <= 0 or Q <= 0 or mu <= 0:
                raise ValueError()
                
            resistance_factor = pressure_to_resistance(P, Q, mu)

            
            self.resistance_factor_var.set(f"{resistance_factor:.6f}")
            
            # 添加到历史记录

            history_entry = f"压力: {P}MPa, 流量: {Q}μL/min → 几何流阻: {resistance_factor:.6f}"

            self.add_to_history("tab6", history_entry)

            
        except ValueError:

            self.resistance_factor_var.set("输入错误")

    
    def calculate_resistance_factor_geo(self):

        """计算几何形状的流阻系数"""
        shape_full = self.shape_var.get()
        shape = shape_full.split()[0] if shape_full else "CYL"
        
        try:
            if shape == 'CYL':
                # 修改变量引用以使用新的变量名
                d = float(self.diameter_geo_entry.get())
                l = float(self.length_cyl_geo_entry.get())

                
                if d <= 0 or l <= 0:

                    raise ValueError("参数必须为正数")
                    
                r = resistance_factor_cyl(d, l)
                v = channel_v_cyl(d, l)
                
                # 添加到历史记录

                history_entry = f"圆柱体: Φ{d}μm × {l}μm → 几何流阻: {r:.6e}"

                
            else:
                # 修改变量引用以使用新的变量名

                w = float(self.width_geo_entry.get())

                h = float(self.height_geo_entry.get())

                l = float(self.length_rect_geo_entry.get())

                
                if w <= 0 or h <= 0 or l <= 0:
                    raise ValueError("参数必须为正数")

                
                v = channel_v_cub(w, h, l)

                
                if shape == 'RECT':

                    r = resistance_factor_rect(w, h, l)

                    history_entry = f"矩形: {w}×{h}×{l}μm → 几何流阻: {r:.6e}"

                elif shape == 'SQUA':
                    r = resistance_factor_squa(w, h, l)

                    history_entry = f"方形: {w}×{h}×{l}μm → 几何流阻: {r:.6e}"

                elif shape == 'RECT_MOD':
                    r = resistance_factor_rect_mod(w, h, l)
                    history_entry = f"改进矩形: {w}×{h}×{l}μm → 几何流阻: {r:.6e}"

            
            # 显示结果
            self.r_result_var.set(f"{r:.6e}")
            self.volume_var.set(f"{v:.6f}")
            
            self.add_to_history("tab8", history_entry)
            
        except ValueError:
            self.r_result_var.set("输入错误")

            self.volume_var.set("输入错误")

# 运行应用

if __name__ == "__main__":

    root = tk.Tk()

    app = MicrofluidCalculatorApp(root)

    root.mainloop()
