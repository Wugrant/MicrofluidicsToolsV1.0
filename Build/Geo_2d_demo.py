# Copyright (c) 2025 [Grant]
# Licensed under the MIT License.
# See LICENSE in the project root for license information.
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import math
from datetime import datetime
import numpy as np
import sys

# 增加对中文的支持
if sys.platform == "win32":
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)

class FluidChannelCalculator:
    def __init__(self):
        self.config = [
            {'name': 'M', 'label': '主入口流道的高宽长 (um)', 'num_fields': 3, 'default': [360, 2000, 51300], 'type': 'double'},
            {'name': 'M_eq', 'label': '主出口流道的高宽长 (um)', 'num_fields': 3, 'default': [360, 2000, 51300], 'type': 'double'},
            {'name': 'S', 'label': '分配入口流道的高宽长 (um)', 'num_fields': 3, 'default': [360, 360, 51300], 'type': 'double'},
            {'name': 'S_eq', 'label': '分配出口流道的高宽长 (um)', 'num_fields': 3, 'default': [360, 360, 51300], 'type': 'double'},
            {'name': 'Trd', 'label': '分散相通孔支撑流道 [r,l]', 'num_fields': 3, 'default': [0, 0, 0], 'type': 'double'},
            {'name': 'Trc', 'label': '连续相通孔支撑流道 [r,l]', 'num_fields': 3, 'default': [0, 0, 0], 'type': 'double'},
            {'name': 'UPd', 'label': '分散相连接流道的高宽长 (um)', 'num_fields': 3, 'default': [26, 2025, 5835], 'type': 'double'},
            {'name': 'UPc', 'label': '连续相连接流道的高宽长 (um)', 'num_fields': 3, 'default': [0, 0, 0], 'type': 'double'},
            {'name': 'DFUd', 'label': '分散相液滴流道入口的高宽长', 'num_fields': 3, 'default': [22.5, 40, 236], 'type': 'double'},
            {'name': 'DFUc', 'label': '连续相液滴流道入口的高宽长', 'num_fields': 3, 'default': [22.5, 40, 236], 'type': 'double'},
            {'name': 'Or', 'label': '缩口', 'num_fields': 3, 'default': [22.5, 20, 20], 'type': 'double'},
            {'name': 'Rd', 'label': '分散相上游流阻管的高宽长', 'num_fields': 3, 'default': [22.5, 10, 1024], 'type': 'double'},
            {'name': 'Rc1', 'label': '连续相上游流阻管1的高宽长', 'num_fields': 3, 'default': [22.5, 20, 1024], 'type': 'double'},
            {'name': 'Rc2', 'label': '连续相上游流阻管2的高宽长', 'num_fields': 3, 'default': [22.5, 10, 1024], 'type': 'double'},
            {'name': 'Rc', 'label': '连续相上游流阻管2并联的高宽长', 'num_fields': 3, 'default': [22.5, 10, 1024], 'type': 'double'},
            {'name': 'Viad', 'label': '通孔分散相的直径长', 'num_fields': 2, 'default': [40, 130], 'type': 'double'},
            {'name': 'Viac', 'label': '通孔连续相的直径长', 'num_fields': 2, 'default': [60, 130], 'type': 'double'},
            {'name': 'Via', 'label': '通孔出口的直径长', 'num_fields': 2, 'default': [40, 130], 'type': 'double'},
            {'name': 'li', 'label': '支路上的液滴生成器数量', 'num_fields': 1, 'default': [285], 'type': 'int'},
            {'name': 'lj', 'label': '主路上的支路数量', 'num_fields': 1, 'default': [36], 'type': 'int'}
        ]
        copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 
                             fg="#555555", bg="#f0f0f0")
        copyright_label.pack(side=tk.BOTTOM, fill=tk.X)
        self.params = {}
        for param in self.config:
            self.params[param['name']] = param['default'].copy()

        self.calculate_fluid_dynamics()

    def set_param(self, name, value):
        """设置参数值"""
        if name in self.params:
            self.params[name] = value
        else:
            raise ValueError(f"Unknown parameter: {name}")

    def resistance_factor_cyl(self, cir):
        """计算圆柱流阻因子"""
        if all([d == 0 for d in cir]):
            return 0

        d = cir[0]  # 直径
        l = cir[1]  # 长度
        return 128 * l / (math.pi * d**4)

    def resistance_factor_rect_mod(self, m):
        """计算矩形流阻因子（修正公式）"""
        if all([d == 0 for d in m]):
            return 0

        w = m[0]  # 宽度
        h = m[1]  # 高度
        l = m[2]  # 长度

        a = max(w, h)
        b = min(w, h)

        if a > 1.3 * b:
            return 12 * l / (a * b**3 * (1 - 0.63 * (b/a)))
        else:
            a = (a + b) / 2
            return 28 * l / a**4

    def calculate_fluid_dynamics(self):
        """计算流体动力学参数"""
        # 获取参数
        M = self.params['M']
        M_eq = self.params['M_eq']
        S = self.params['S']
        S_eq = self.params['S_eq']
        Trd = self.params['Trd']
        Trc = self.params['Trc']
        UPd = self.params['UPd']
        UPc = self.params['UPc']
        DFUd = self.params['DFUd']
        DFUc = self.params['DFUc']
        Or = self.params['Or']
        Rd = self.params['Rd']
        Rc = self.params['Rc']
        Viad = self.params['Viad']
        Viac = self.params['Viac']
        Via = self.params['Via']
        li = self.params['li'][0]  # int value
        lj = self.params['lj'][0]  # int value

        # 计算各部分的流阻因子
        self.params['R_M'] = self.resistance_factor_rect_mod(M)
        self.params['R_M_eq'] = self.resistance_factor_rect_mod(M_eq)
        self.params['R_S'] = self.resistance_factor_rect_mod(S)
        self.params['R_S_eq'] = self.resistance_factor_rect_mod(S_eq)

        # 计算面积
        self.params['A_M'] = M[0] * M[1]
        self.params['A_M_eq'] = M_eq[0] * M_eq[1]
        self.params['A_S'] = S[0] * S[1]
        self.params['A_S_eq'] = S_eq[0] * S_eq[1]

        # 计算流速比
        self.params['u_M'] = 1
        self.params['u_M_eq'] = 1
        self.params['u_S'] = self.params['A_M'] / (self.params['A_S'] * lj) if self.params['A_S'] != 0 else 0

        # 处理其他参数
        self.params['R_Trd'] = self.resistance_factor_rect_mod(Trd)
        self.params['A_Trd'] = Trd[0] * Trd[1] if all([d != 0 for d in Trd]) else 0
        self.params['u_Trd'] = self.params['A_M'] / (self.params['A_Trd'] * lj) if self.params['A_Trd'] != 0 else 0

        self.params['R_Trc'] = self.resistance_factor_rect_mod(Trc)
        self.params['A_Trc'] = Trc[0] * Trc[1] if all([d != 0 for d in Trc]) else 0
        self.params['u_Trc'] = self.params['A_M'] / (self.params['A_Trc'] * lj) if self.params['A_Trc'] != 0 else 0

        self.params['R_UPd'] = self.resistance_factor_rect_mod(UPd)
        self.params['A_UPd'] = UPd[0] * UPd[1] if all([d != 0 for d in UPd]) else 0
        self.params['u_UPd'] = self.params['A_M'] / (self.params['A_UPd'] * lj) if self.params['A_UPd'] != 0 else 0

        self.params['R_UPc'] = self.resistance_factor_rect_mod(UPc)
        self.params['A_UPc'] = UPc[0] * UPc[1] if all([d != 0 for d in UPc]) else 0
        self.params['u_UPc'] = self.params['A_M'] / (self.params['A_UPc'] * 2 * lj) if self.params['A_UPc'] != 0 else 0

        self.params['R_DFUd'] = self.resistance_factor_rect_mod(DFUd)
        self.params['A_DFUd'] = DFUd[0] * DFUd[1] if all([d != 0 for d in DFUd]) else 0
        self.params['u_DFUd'] = self.params['A_M'] / (self.params['A_DFUd'] * lj * li) if self.params['A_DFUd'] != 0 else 0

        self.params['R_DFUc'] = self.resistance_factor_rect_mod(DFUc)
        self.params['A_DFUc'] = DFUc[0] * DFUc[1] if all([d != 0 for d in DFUc]) else 0
        self.params['u_DFUc'] = self.params['A_M'] / (self.params['A_DFUc'] * 2 * lj * li) if self.params['A_DFUc'] != 0 else 0

        self.params['R_Or'] = self.resistance_factor_rect_mod(Or)
        self.params['A_Or'] = Or[0] * Or[1] if all([d != 0 for d in Or]) else 0
        self.params['u_Or'] = self.params['A_M'] / (self.params['A_Or'] * lj * li) if self.params['A_Or'] != 0 else 0

        self.params['R_Rd'] = self.resistance_factor_rect_mod(Rd)
        self.params['A_Rd'] = Rd[0] * Rd[1] if all([d != 0 for d in Rd]) else 0
        self.params['u_Rd'] = self.params['A_M'] / (self.params['A_Rd'] * lj * li) if self.params['A_Rd'] != 0 else 0

        # 处理Rc
        if all([d != 0 for d in self.params['Rc']]):
            Rc1 = self.params['Rc1'] = self.params['Rc']
            Rc2 = self.params['Rc2'] = self.params['Rc']
            self.params['R_Rc'] = self.resistance_factor_rect_mod(Rc1) * 2 + self.resistance_factor_rect_mod(Rc2)
            self.params['A_Rc'] = Rc2[0] * Rc2[1] if all([d != 0 for d in Rc2]) else 0
            self.params['u_Rc'] = self.params['A_M'] / (self.params['A_Rc'] * 2 * lj * li) if self.params['A_Rc'] != 0 else 0
        else:
            self.params['R_Rc'] = 0
            self.params['A_Rc'] = 0
            self.params['u_Rc'] = 0

        self.params['R_Viad'] = self.resistance_factor_cyl(Viad)
        self.params['A_Viad'] = math.pi * Viad[0]**2 / 4 if Viad[0] != 0 else 0
        self.params['u_Viad'] = self.params['A_M'] / (self.params['A_Viad'] * lj * li) if self.params['A_Viad'] != 0 else 0

        self.params['R_Viac'] = self.resistance_factor_cyl(Viac)
        self.params['A_Viac'] = math.pi * Viac[0]**2 / 4 if Viac[0] != 0 else 0
        self.params['u_Viac'] = self.params['A_M'] / (self.params['A_Viac'] * 2 * lj * li) if self.params['A_Viac'] != 0 else 0

        self.params['R_Via'] = self.resistance_factor_cyl(Via)
        self.params['A_Via'] = math.pi * Via[0]**2 / 4 if Via[0] != 0 else 0
        self.params['u_Via'] = self.params['A_M'] / (self.params['A_Via'] * lj * li) if self.params['A_Via'] != 0 else 0

        # 计算RX参数
        RX_mind = 0
        for lk in range(1, li+1):
            denominator = self.params['R_Rd'] + self.params['R_Or'] + self.params['R_DFUd'] + self.params['R_Viad'] + (self.params['R_S_eq'] + self.params['R_Trd'] * self.params['R_S_eq'] / self.params['R_S']) / li * (lk-1)
            if denominator != 0:
                RX_mind += 1 / denominator
        self.params['RX_mind'] = 1 / RX_mind if RX_mind != 0 else 0

        RX_minc = 0
        for lk in range(1, li+1):
            denominator = self.params['R_Rc']/2 + self.params['R_Or'] + self.params['R_DFUc']/2 + self.params['R_Viac'] + (self.params['R_S_eq'] + self.params['R_Trc'] * self.params['R_S_eq'] / self.params['R_S']) / li * (lk-1)
            if denominator != 0:
                RX_minc += 1 / denominator
        self.params['RX_minc'] = 1 / RX_minc if RX_minc != 0 else 0

        RX_maxd = 0
        for lk in range(1, lj+1):
            denominator = self.params['RX_mind'] + self.params['R_UPd'] + self.params['R_M_eq']/lj * (lk-1)
            if denominator != 0:
                RX_maxd += 1 / denominator
        self.params['RX_maxd'] = 1 / RX_maxd if RX_maxd != 0 else 0

        RX_maxc = 0
        for lk in range(1, lj+1):
            denominator = self.params['RX_minc'] + self.params['R_UPc'] + self.params['R_M_eq']/lj * (lk-1)
            if denominator != 0:
                RX_maxc += 1 / denominator
        self.params['RX_maxc'] = 1 / RX_maxc if RX_maxc != 0 else 0

        # 计算2D流分布
        if self.params['R_S'] != 0:
            fdmin = 1 + (self.params['R_S_eq'] + self.params['R_Trd'] * self.params['R_S_eq'] / self.params['R_S']) / (self.params['R_DFUd'] + self.params['R_Rd'] + self.params['R_Or'] + self.params['R_Viad'])
        else:
            fdmin = 0

        if self.params['R_S'] != 0:
            fcmin = 1 + (self.params['R_S_eq'] + self.params['R_Trc'] * self.params['R_S_eq'] / self.params['R_S']) / (self.params['R_DFUc']/2 + self.params['R_Rc']/2 + self.params['R_Or'] + self.params['R_Viac'])
        else:
            fcmin = 0

        if self.params['R_S'] != 0:
            fdmax = 1 + self.params['R_M_eq'] / (self.params['R_S'] - self.params['R_S_eq'] + self.params['RX_mind'] + self.params['R_UPd']) 
        else:
            fdmax = 0

        if self.params['R_S'] != 0:
            fcmax = 1 + self.params['R_M_eq'] / (self.params['R_S'] - self.params['R_S_eq'] + self.params['RX_minc'] + self.params['R_UPc'])
        else:
            fcmax = 0

        self.params['fdmin'] = fdmin
        self.params['fcmin'] = fcmin
        self.params['fdmax'] = fdmax
        self.params['fcmax'] = fcmax

        # 创建向量分布
        U_dmax = np.linspace(1, fdmax, lj) if lj > 1 else [fdmax]
        U_dmin = np.linspace(1, fdmin, li) if li > 1 else [fdmin]
        U_cmax = np.linspace(1, fcmax, lj) if lj > 1 else [fcmax]
        U_cmin = np.linspace(1, fcmin, li) if li > 1 else [fcmin]

        U_d = np.outer(U_dmax, U_dmin)
        U_c1 = np.outer(U_dmax, U_dmin)

        if np.any(U_c1 != 0):
            phi_1 = U_d / U_c1
        else:
            phi_1 = np.zeros_like(U_d)

        if np.min(phi_1) != 0:
            phi_1 = phi_1 / np.min(phi_1)

        if phi_1.size > 0:
            max1 = np.max(phi_1)
            idx = np.unravel_index(np.argmax(phi_1), phi_1.shape)
        else:
            max1 = 0
            idx = (0, 0)

        self.params['phi_1'] = phi_1
        self.params['max_phi_1'] = max1
        self.params['phi_1_max_index'] = idx

        # 计算CV (dripping)
        if phi_1.size > 0 and np.mean(1/phi_1) != 0:
            CV_dripping = np.std(1/phi_1) / np.mean(1/phi_1)
        else:
            CV_dripping = 0

        self.params['CV_dripping'] = CV_dripping

        # 计算CV (squeezing)
        if phi_1.size > 0 and np.mean(phi_1**(-1/3)) != 0:
            CV_squeezing = np.std(phi_1**(-1/3)) / np.mean(phi_1**(-1/3))
        else:
            CV_squeezing = 0

        self.params['CV_squeezing'] = CV_squeezing

class FluidChannelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("流体通道参数设置与计算")
        self.root.geometry("800x600")

        # 设置应用默认风格
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#4CAF50", foreground="black")
        style.configure("TLabel", background="#f5f5f5", foreground="#333", font=("Arial", 10))

        self.calculator = FluidChannelCalculator()

        # 创建主框架
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=1)

        # 创建画布
        self.canvas = tk.Canvas(self.main_frame, background="#f5f5f5")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        # 添加滚动条
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 配置画布
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # 创建在画布上的框架
        self.frame = ttk.Frame(self.canvas, padding=10)
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")

        # 创建输入区域
        self.create_input_fields()

        # 绑定画布区域更新
        self.frame.bind("<Configure>", self.on_frame_configure)

        # 添加按钮
        self.button_frame = ttk.Frame(root, padding=10)
        self.button_frame.pack(pady=10, fill=tk.X)

        self.calculate_button = ttk.Button(self.button_frame, text="计算", command=self.calculate)
        self.calculate_button.grid(row=0, column=0, padx=5)

        self.export_button = ttk.Button(self.button_frame, text="导出CSV", command=self.export_csv)
        self.export_button.grid(row=0, column=1, padx=5)

    def create_input_fields(self):
        # 创建表单标题
        title = ttk.Label(self.frame, text="流体通道参数设置", font=("Arial", 16, "bold"))
        title.grid(row=0, column=0, columnspan=3, pady=10, sticky="n")

        # 创建列标题
        header_style = ttk.Style()
        header_style.configure("Header.TLabel", background="#e5e5e5", font=("Arial", 10, "bold"))

        ttk.Label(self.frame, text="参数名称", style="Header.TLabel").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(self.frame, text="值 1", style="Header.TLabel").grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(self.frame, text="值 2", style="Header.TLabel").grid(row=1, column=2, padx=5, pady=5)

        # 创建输入框
        self.entry_vars = {}
        self.entries = {}

        row = 3
        for param in self.calculator.config:
            # 标签
            label = ttk.Label(self.frame, text=param['label'])
            label.grid(row=row, column=0, padx=10, pady=5, sticky="w")

            # 输入框
            param_entries = []
            for i in range(param['num_fields']):
                if i < 3:  # 只显示最多3列
                    var = tk.StringVar()
                    var.set(str(param['default'][i]))
                    entry = ttk.Entry(self.frame, textvariable=var, width=10)
                    if param['type'] == 'int':
                        entry.config(justify="center", font=("Arial", 9))
                    else:
                        entry.config(justify="center", font=("Arial", 9))
                    entry.grid(row=row, column=i+1, padx=5, pady=5)
                    param_entries.append(var)

            self.entry_vars[param['name']] = param_entries
            self.entries[param['name']] = param_entries
            row += 3  # 增加行距

        # 添加数据类型的提示
        tip = ttk.Label(self.frame, text="提示: li 和 lj 为整数, 其他均为浮点数", font=("Arial", 9), foreground="gray")
        tip.grid(row=row+1, column=0, columnspan=3, padx=5, pady=10, sticky="w")

    def on_frame_configure(self, event):
        """更新画布区域"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def get_param_value(self, name):
        """获取参数的数值，根据配置中的类型进行转换"""
        if name not in self.entry_vars:
            return self.calculator.params.get(name, [])

        # 查找参数的配置
        param_config = next((item for item in self.calculator.config if item['name'] == name), None)

        if param_config is None:
            return self.calculator.params.get(name, [])

        values = []
        for var in self.entry_vars[name]:
            value = var.get()
            if value.strip() == '':
                values.append(param_config['default'][0] if values else 0)
                continue

            try:
                if param_config['type'] == 'int':
                    values.append(int(value))
                else:  # double
                    values.append(float(value))
            except ValueError:
                messagebox.showerror("输入错误", f"{param_config['label']}的值必须是{'整型' if param_config['type']=='int' else '浮点型'}")
                # 使用默认值
                values.append(param_config['default'][0] if values else 0)

        return values

    def calculate(self):
        """计算流体通道参数"""
        try:
            # 更新计算器的用户配置参数
            for param in self.calculator.config:
                name = param['name']
                values = self.get_param_value(name)
                if values:
                    self.calculator.params[name] = values

            # 执行计算
            self.calculator.calculate_fluid_dynamics()

            # 显示计算结果
            messagebox.showinfo("成功", "计算完成！点击导出CSV保存结果。")

        except ValueError as e:
            messagebox.showerror("输入错误", f"请输入有效的数字: {str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"计算失败: {str(e)}\n请检查输入参数是否正确。")

    def export_csv(self):
        """导出计算结果为CSV文件"""
        try:
            # 打开保存对话框
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="保存计算结果"
            )

            if not file_path:
                return

            # 使用utf-8-sig编码以解决中文乱码问题
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)

                # 写入头部
                header = ["参数名称", "参数1", "参数2", "参数3", "几何流阻系数", "横截面积", "流速比"]
                writer.writerow(header)

                # 写入数据
                params = self.calculator.params
                config = self.calculator.config

                # 写入用户配置的参数
                for param in config:
                    name = param['name']
                    if name in params:
                        values = params[name]
                        # 获取关联的计算结果
                        flow_res = params.get(f"R_{name}", 0)
                        area = params.get(f"A_{name}", 0)
                        flow_rate = params.get(f"u_{name}", 0)

                        # 确保关联值是数值类型
                        if not isinstance(flow_res, (int, float)):
                            flow_res = 0

                        if not isinstance(area, (int, float)):
                            area = 0

                        if not isinstance(flow_rate, (int, float)):
                            flow_rate = 0

                        # 根据参数个数调整输出
                        if isinstance(values, list):
                            if len(values) >= 3:
                                writer.writerow([param['label'], values[0], values[1], values[2], flow_res, area, flow_rate])
                            elif len(values) == 2:
                                writer.writerow([param['label'], values[0], values[1], "", flow_res, area, flow_rate])
                            elif len(values) == 1:
                                if param['type'] == 'int':
                                    # 对于单值参数，只输出在第一列
                                    writer.writerow([param['label'], values[0], "", "", flow_res, area, flow_rate])
                                else:
                                    writer.writerow([param['label'], values[0], "", "", flow_res, area, flow_rate])
                        else:
                            # 单值参数
                            if param['type'] == 'int':
                                # 对于单值参数，只输出在第一列
                                writer.writerow([param['label'], values, "", "", flow_res, area, flow_rate])
                            else:
                                writer.writerow([param['label'], values, "", "", flow_res, area, flow_rate])

                # 写入计算结果
                # 写入流速比
                writer.writerow(["支路分散相流速比", params['fdmin'], "", "", "", "", ""])
                writer.writerow(["支路连续相流速比", params['fcmin'], "", "", "", "", ""])
                writer.writerow(["主路分散相流速比", params['fdmax'], "", "", "", "", ""])
                writer.writerow(["主路连续相流速比", params['fcmax'], "", "", "", "", ""])

                # 最大流比系数
                if params['max_phi_1'] != 0:
                    # 格式化输出，保留6位小数
                    max_phi = f"{params['max_phi_1']:.6f}"
                    writer.writerow(["最大流比系数", max_phi, "", "", "", "", ""])

                # 写入液滴CV值和挤压流CV值，使用科学计数法
                if params['CV_dripping'] != 0:
                    cv_drip = f"{params['CV_dripping']:.6e}"
                    writer.writerow(["液滴CV值", cv_drip, "", "", "", "", ""])

                if params['CV_squeezing'] != 0:
                    cv_squeeze = f"{params['CV_squeezing']:.6e}"
                    writer.writerow(["挤压流CV值", cv_squeeze, "", "", "", "", ""])

                # 写入元数据
                writer.writerow(["作者", "Grant", "", "", "", "", ""])
                writer.writerow(["日期", datetime.now().strftime("%Y-%m-%d"), "", "", "", "", ""])

                messagebox.showinfo("成功", f"数据已成功导出到 {file_path}")

        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

# 运行应用
if __name__ == "__main__":
    root = tk.Tk()
    app = FluidChannelApp(root)
    root.mainloop()