import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys



class ImageLineExtractor:
    def __init__(self, root):
        self.root = root
        self.root.title("图像线条像素提取工具")
        self.root.geometry("1000x700")
        copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 
                             fg="#555555", bg="#f0f0f0")
        copyright_label.pack(side=tk.BOTTOM, fill=tk.X)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 初始化变量
        self.image_path = ""
        self.img_bgr = None
        self.img_rgb = None
        self.height = 0
        self.width = 0
        self.data = None
        
        self.setup_ui()
    
    def setup_ui(self):
        # 主框架
        main = ttk.Frame(self.root, padding="10")
        main.pack(fill=tk.BOTH, expand=True)
        
        # 文件选择
        file_frame = ttk.LabelFrame(main, text="文件选择", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(file_frame, text="选择图像文件", command=self.select_file).pack(side=tk.LEFT, padx=(0, 10))
        self.file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.info_var = tk.StringVar(value="请选择图像文件")
        ttk.Label(file_frame, textvariable=self.info_var).pack(side=tk.RIGHT)
        
        # 控制面板
        control = ttk.LabelFrame(main, text="参数设置", padding="5")
        control.pack(fill=tk.X, pady=(0, 10))
        
        # 方向选择
        ttk.Label(control, text="方向:").grid(row=0, column=0, padx=(0, 5))
        self.direction = tk.StringVar(value="row")
        ttk.Radiobutton(control, text="行", variable=self.direction, value="row", command=self.update_range).grid(row=0, column=1)
        ttk.Radiobutton(control, text="列", variable=self.direction, value="column", command=self.update_range).grid(row=0, column=2)
        
        # 位置选择
        ttk.Label(control, text="位置:").grid(row=0, column=3, padx=(20, 5))
        self.position = tk.IntVar(value=0)
        self.spin = ttk.Spinbox(control, from_=0, to=100, textvariable=self.position, width=8)
        self.spin.grid(row=0, column=4)
        self.range_label = ttk.Label(control, text="(0-0)")
        self.range_label.grid(row=0, column=5, padx=(5, 0))
        
        # 通道选择
        ttk.Label(control, text="通道:").grid(row=0, column=6, padx=(20, 5))
        self.channel = tk.StringVar(value="gray")
        ttk.Combobox(control, textvariable=self.channel, values=["gray", "r", "g", "b", "rgb"], 
                    state="readonly", width=8).grid(row=0, column=7)
        
        # 按钮
        ttk.Button(control, text="预览", command=self.preview).grid(row=0, column=8, padx=(20, 10))
        ttk.Button(control, text="导出Excel", command=self.export).grid(row=0, column=9)
        
        # 显示区域
        display = ttk.Frame(main)
        display.pack(fill=tk.BOTH, expand=True)
        
        # 图像显示
        img_frame = ttk.LabelFrame(display, text="图像预览", padding="5")
        img_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.fig = Figure(figsize=(6, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, img_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 曲线显示
        curve_frame = ttk.LabelFrame(display, text="像素值曲线", padding="5")
        curve_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.curve_fig = Figure(figsize=(4, 5))
        self.curve_canvas = FigureCanvasTkAgg(self.curve_fig, curve_frame)
        self.curve_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="选择图像文件",
            filetypes=[("图像文件", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_var.set(file_path)
            self.image_path = file_path
            self.load_image()
    
    def load_image(self):
        try:
            self.img_bgr = cv2.imread(self.image_path)
            if self.img_bgr is None:
                messagebox.showerror("错误", "无法读取图像")
                return
            
            self.img_rgb = cv2.cvtColor(self.img_bgr, cv2.COLOR_BGR2RGB)
            self.height, self.width = self.img_rgb.shape[:2]
            
            self.info_var.set(f"尺寸: {self.width} x {self.height}")
            self.update_range()
            self.show_image()
            
        except Exception as e:
            messagebox.showerror("错误", f"加载图像失败: {e}")
    
    def update_range(self):
        if self.img_rgb is not None:
            max_pos = (self.height - 1) if self.direction.get() == "row" else (self.width - 1)
            self.range_label.config(text=f"(0-{max_pos})")
            self.spin.config(to=max_pos)
            if self.position.get() > max_pos:
                self.position.set(0)
    
    def show_image(self):
        if self.img_rgb is None:
            return
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.imshow(self.img_rgb)
        ax.axis('off')
        self.canvas.draw()
    
    def preview(self):
        if self.img_rgb is None:
            messagebox.showerror("错误", "请先选择图像")
            return
        
        try:
            pos = self.position.get()
            direction = self.direction.get()
            channel = self.channel.get()
            
            # 显示图像和标记线
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.imshow(self.img_rgb)
            
            if direction == "row":
                ax.axhline(y=pos, color='red', linewidth=3)
                length = self.width
            else:
                ax.axvline(x=pos, color='red', linewidth=3)
                length = self.height
            
            ax.axis('off')
            self.canvas.draw()
            
            # 提取数据
            self.extract_data(pos, direction, length)
            
            # 显示曲线
            self.show_curve(channel, length)
            
        except Exception as e:
            messagebox.showerror("错误", f"预览失败: {e}")
    
    def extract_data(self, pos, direction, length):
        # 获取灰度和BGR数据
        gray = cv2.cvtColor(self.img_rgb, cv2.COLOR_RGB2GRAY)
        
        if direction == 'row':
            gray_vals = gray[pos, :]
            b_vals = self.img_bgr[pos, :, 0]
            g_vals = self.img_bgr[pos, :, 1]
            r_vals = self.img_bgr[pos, :, 2]
        else:
            gray_vals = gray[:, pos]
            b_vals = self.img_bgr[:, pos, 0]
            g_vals = self.img_bgr[:, pos, 1]
            r_vals = self.img_bgr[:, pos, 2]
        
        # 准备Excel数据
        date_col = [''] * length
        date_col[0] = datetime.now().strftime("%Y-%m-%d")
        
        self.data = {
            '坐标': list(range(length)),
            '灰度': gray_vals,
            'G': g_vals,
            'B': b_vals,
            'R': r_vals,
            '日期': date_col
        }
    
    def show_curve(self, channel, length):
        self.curve_fig.clear()
        ax = self.curve_fig.add_subplot(111)
        
        if channel == 'gray':
            ax.plot(self.data['灰度'], 'k-', linewidth=2)
        elif channel == 'r':
            ax.plot(self.data['R'], 'r-', linewidth=2)
        elif channel == 'g':
            ax.plot(self.data['G'], 'g-', linewidth=2)
        elif channel == 'b':
            ax.plot(self.data['B'], 'b-', linewidth=2)
        elif channel == 'rgb':
            ax.plot(self.data['R'], 'r-', linewidth=2)
            ax.plot(self.data['G'], 'g-', linewidth=2)
            ax.plot(self.data['B'], 'b-', linewidth=2)
        
        ax.axis('off')
        ax.grid(True)
        self.curve_canvas.draw()
    
    def export(self):
        if self.data is None:
            messagebox.showerror("错误", "请先预览数据")
            return
        
        try:
            # 生成文件名
            name = Path(self.image_path).stem
            direction = "行" if self.direction.get() == "row" else "列"
            pos = self.position.get()
            
            save_path = Path(self.image_path).parent / f"{name}_{pos}{direction}.xlsx"
            
            # 保存Excel
            df = pd.DataFrame(self.data)
            df.to_excel(save_path, index=False, engine='openpyxl')
            
            messagebox.showinfo("成功", f"已导出到:\n{save_path}")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def on_closing(self):
        try:
            plt.close('all')
            cv2.destroyAllWindows()
            self.root.quit()
            self.root.destroy()
            sys.exit(0)
        except:
            import os
            os._exit(0)




if __name__ == "__main__":
    root = tk.Tk()
    app = ImageLineExtractor(root)
    root.mainloop()