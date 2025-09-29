import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
from pathlib import Path
from scipy.spatial.distance import pdist, squareform




# Matplotlib 设置
plt.rcParams['font.sans-serif'] = ['Arial']
plt.rcParams['axes.unicode_minus'] = False




class DropletAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Droplet Size Analyzer / 液滴分析工具")
        self.root.geometry("1400x900")  # 更宽，适合横向布局


        # 图像数据
        self.img_bgr = None
        self.img_rgb = None
        self.droplet_data = None


        # 绘图对象
        self.rect = None  # ROI 矩形
        self.line = None  # 标尺线段
        self.drawing_roi = False
        self.drawing_line = False
        self.start_x = self.start_y = 0


        # 参数
        self.pixel_size = tk.DoubleVar(value=1.0)        # μm/pixel
        self.min_diameter = tk.DoubleVar(value=5.0)      # 最小直径 (μm)
        self.channel = tk.StringVar(value="gray")        # 通道
        self.droplet_type = tk.StringVar(value="dark")   # 类型
        self.use_manual_thresh = tk.BooleanVar(value=False)
        self.thresh_value = tk.IntVar(value=127)
        self.min_circularity = tk.DoubleVar(value=0.8)
        self.merge_threshold_px = tk.DoubleVar(value=2.0)  # 去重距离


        # ROI 控制
        self.use_roi = tk.BooleanVar(value=False)
        self.lock_roi = tk.BooleanVar(value=False)
        self.roi_x = tk.IntVar(value=0)
        self.roi_y = tk.IntVar(value=0)
        self.roi_w = tk.IntVar(value=100)
        self.roi_h = tk.IntVar(value=100)


        # 标尺工具
        self.use_ruler = tk.BooleanVar(value=False)
        self.ruler_start = None
        self.ruler_line = None


        self.setup_ui()


    def setup_ui(self):
        main = ttk.Frame(self.root, padding="10")
        main.pack(fill=tk.BOTH, expand=True)


        # --- 图像加载 ---
        load_frame = ttk.LabelFrame(main, text="Image Input / 图像输入", padding="5")
        load_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(load_frame, text="Load Image / 点击加载图像", command=self.load_image).pack(side=tk.LEFT, padx=(0, 10))
        self.file_var = tk.StringVar()
        ttk.Entry(load_frame, textvariable=self.file_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)

        # === 控件区：三列横向布局 ===
        control_frame = ttk.Frame(main)
        control_frame.pack(fill=tk.X, pady=(0, 10))


        # 1. 左侧：参数设置（多列网格）
        param_frame = ttk.LabelFrame(control_frame, text="Parameters / 参数设置", padding="10")
        param_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), expand=False)


        # 使用网格布局，2列
        ttk.Label(param_frame, text="像素尺寸/Pixel Size (μm):").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        ttk.Entry(param_frame, textvariable=self.pixel_size, width=8).grid(row=0, column=1, sticky=tk.W)


        ttk.Label(param_frame, text="最小液滴直径/Min Diam (μm):").grid(row=0, column=2, sticky=tk.W, padx=(20, 10), pady=5)
        ttk.Entry(param_frame, textvariable=self.min_diameter, width=8).grid(row=0, column=3, sticky=tk.W)


        ttk.Label(param_frame, text="色彩通道/Channel:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        ttk.Combobox(param_frame, textvariable=self.channel, values=["gray", "r", "g", "b"], state="readonly", width=8).grid(row=1, column=1, sticky=tk.W)


        ttk.Label(param_frame, text="模式/Type:").grid(row=1, column=2, sticky=tk.W, padx=(20, 10), pady=5)
        ttk.Radiobutton(param_frame, text="暗场/Dark", variable=self.droplet_type, value="dark").grid(row=1, column=3)
        ttk.Radiobutton(param_frame, text="明场/Bright", variable=self.droplet_type, value="bright").grid(row=1, column=4)


        ttk.Checkbutton(param_frame, text="手动阈值/Manual Threshold", variable=self.use_manual_thresh,
                        command=self.toggle_threshold).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.thresh_slider = tk.Scale(param_frame, from_=0, to=255, orient=tk.HORIZONTAL,
                                      variable=self.thresh_value, label="Threshold", length=180)
        self.thresh_slider.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)
        self.thresh_slider.config(state='disabled')


        ttk.Label(param_frame, text="最小圆度/Min Circularity:").grid(row=2, column=3, sticky=tk.W, padx=(20, 10), pady=5)
        ttk.Entry(param_frame, textvariable=self.min_circularity, width=8).grid(row=2, column=4, sticky=tk.W)


        ttk.Label(param_frame, text="防重叠距离/Merge Dist (px):").grid(row=3, column=3, sticky=tk.W, padx=(20, 10), pady=5)
        ttk.Entry(param_frame, textvariable=self.merge_threshold_px, width=8).grid(row=3, column=4, sticky=tk.W)


        # ROI 设置（单行紧凑）
        roi_frame = ttk.Frame(param_frame)
        roi_frame.grid(row=4, column=0, columnspan=5, pady=(10, 0), sticky=tk.W)


        ttk.Checkbutton(roi_frame, text="Use ROI", variable=self.use_roi).pack(side=tk.LEFT)
        ttk.Checkbutton(roi_frame, text="Lock ROI", variable=self.lock_roi).pack(side=tk.LEFT, padx=(10, 10))


        # X
        ttk.Label(roi_frame, text="X:").pack(side=tk.LEFT)
        x_entry = ttk.Entry(roi_frame, textvariable=self.roi_x, width=6)
        x_entry.pack(side=tk.LEFT)
        x_entry.bind('<Return>', lambda e: self.apply_roi())  # 按回车更新


        # Y
        ttk.Label(roi_frame, text="Y:").pack(side=tk.LEFT, padx=(10, 0))
        y_entry = ttk.Entry(roi_frame, textvariable=self.roi_y, width=6)
        y_entry.pack(side=tk.LEFT)
        y_entry.bind('<Return>', lambda e: self.apply_roi())


        # W
        ttk.Label(roi_frame, text="W:").pack(side=tk.LEFT, padx=(10, 0))
        w_entry = ttk.Entry(roi_frame, textvariable=self.roi_w, width=6)
        w_entry.pack(side=tk.LEFT)
        w_entry.bind('<Return>', lambda e: self.apply_roi())


        # H
        ttk.Label(roi_frame, text="H:").pack(side=tk.LEFT, padx=(10, 0))
        h_entry = ttk.Entry(roi_frame, textvariable=self.roi_h, width=6)
        h_entry.pack(side=tk.LEFT)
        h_entry.bind('<Return>', lambda e: self.apply_roi())


        # Apply ROI 按钮
        ttk.Button(roi_frame, text="Apply ROI", command=self.apply_roi).pack(side=tk.LEFT, padx=(15, 0))


        self.roi_info = tk.StringVar(value="Current ROI: Full Image")
        ttk.Label(param_frame, textvariable=self.roi_info, foreground="gray").grid(row=5, column=0, columnspan=5, pady=(5, 0), sticky=tk.W)


        # 按钮行
        btn_frame = ttk.Frame(param_frame)
        btn_frame.grid(row=6, column=0, columnspan=5, pady=(10, 0), sticky=tk.W)
        ttk.Button(btn_frame, text="Analyze / 分析", command=self.analyze_droplets).pack(side=tk.LEFT, padx=(0, 10))
        self.export_btn = ttk.Button(btn_frame, text="Export Results / 导出结果", command=self.export_results, state=tk.DISABLED)
        self.export_btn.pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Clear All / 清除", command=self.clear_all).pack(side=tk.RIGHT)


        # 2. 中间：标尺
        ruler_frame = ttk.LabelFrame(control_frame, text="Ruler / 标尺", padding="10")
        ruler_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        ttk.Checkbutton(ruler_frame, text="Enable Ruler", variable=self.use_ruler).pack(anchor=tk.W)
        ttk.Button(ruler_frame, text="Clear Line", command=self.clear_ruler).pack(pady=5)
        self.ruler_info = tk.StringVar(value="Length: -- px\nDistance: -- μm")
        ttk.Label(ruler_frame, textvariable=self.ruler_info, foreground="blue").pack()


        # 3. 右侧：统计
        stats_frame = ttk.LabelFrame(control_frame, text="Statistics / 统计", padding="10")
        stats_frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.count_var = tk.StringVar(value="Total: 0")
        ttk.Label(stats_frame, textvariable=self.count_var, font=("Arial", 10, "bold"), foreground="blue").pack(anchor=tk.W)
        self.mean_var = tk.StringVar(value="Mean: -- μm")
        self.std_var = tk.StringVar(value="Std: -- μm")
        self.cv_var = tk.StringVar(value="CV: --%")
        self.median_var = tk.StringVar(value="Median: -- μm")
        self.range_var = tk.StringVar(value="Range: -- → -- μm")
        ttk.Label(stats_frame, textvariable=self.mean_var).pack(anchor=tk.W)
        ttk.Label(stats_frame, textvariable=self.std_var).pack(anchor=tk.W)
        ttk.Label(stats_frame, textvariable=self.cv_var).pack(anchor=tk.W)
        ttk.Label(stats_frame, textvariable=self.median_var).pack(anchor=tk.W)
        ttk.Label(stats_frame, textvariable=self.range_var).pack(anchor=tk.W)


        # === 图像显示区（最大化）===
        display_frame = ttk.LabelFrame(main, text="Visualization / 可视化", padding="5")
        display_frame.pack(fill=tk.BOTH, expand=True)


        self.fig_img = Figure(figsize=(7.5, 5), dpi=100)  # 增大
        self.canvas_img = FigureCanvasTkAgg(self.fig_img, display_frame)
        self.canvas_img.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))


        self.fig_hist = Figure(figsize=(5, 5), dpi=100)
        self.canvas_hist = FigureCanvasTkAgg(self.fig_hist, display_frame)
        self.canvas_hist.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)


        # 事件绑定
        self.canvas_img.mpl_connect('button_press_event', self.on_press)
        self.canvas_img.mpl_connect('motion_notify_event', self.on_drag)
        self.canvas_img.mpl_connect('button_release_event', self.on_release)


    def toggle_threshold(self):
        state = 'normal' if self.use_manual_thresh.get() else 'disabled'
        self.thresh_slider.config(state=state)


    def load_image(self):
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp"), ("All", "*.*")]
        )
        if not path: return
        self.file_var.set(Path(path).name)
        try:
            self.img_bgr = cv2.imread(path)
            self.img_rgb = cv2.cvtColor(self.img_bgr, cv2.COLOR_BGR2RGB)
            self.reset_roi()
        except Exception as e:
            messagebox.showerror("Error", f"Load failed:\n{e}")


    def show_original(self):
        self.fig_img.clear()
        ax = self.fig_img.add_subplot(111)
        ax.imshow(self.img_rgb)
        ax.set_title("Original Image")
        ax.axis('off')
        self.fig_img.tight_layout()
        self.canvas_img.draw()


    def on_press(self, event):
        if event.inaxes != self.fig_img.axes[0]: return
        if self.use_ruler.get() and not self.use_roi.get():
            self.drawing_line = True
            self.ruler_start = (event.xdata, event.ydata)
            return
        if self.use_roi.get() and not self.lock_roi.get():
            self.drawing_roi = True
            self.start_x, self.start_y = int(event.xdata), int(event.ydata)


    def on_drag(self, event):
        if not event.inaxes: return
        ax = self.fig_img.axes[0]
        if self.drawing_roi and self.use_roi.get() and not self.lock_roi.get():
            if self.rect: self.rect.remove()
            x, y = int(event.xdata), int(event.ydata)
            x1, y1 = min(self.start_x, x), min(self.start_y, y)
            w, h = abs(x - self.start_x), abs(y - self.start_y)
            self.rect = ax.add_patch(plt.Rectangle((x1, y1), w, h, fill=False, color='red', linewidth=2))
            self.canvas_img.draw()
        elif self.drawing_line and self.use_ruler.get():
            if self.ruler_line: self.ruler_line.remove()
            x0, y0 = self.ruler_start
            x1, y1 = event.xdata, event.ydata
            self.ruler_line = ax.plot([x0, x1], [y0, y1], 'r-', linewidth=2)[0]
            px_len = np.hypot(x1 - x0, y1 - y0)
            um_len = px_len * self.pixel_size.get()
            self.ruler_info.set(f"Length: {px_len:.1f} px\nDistance: {um_len:.2f} μm")
            self.canvas_img.draw()


    def on_release(self, event):
        if not event.inaxes: return
        if self.drawing_roi and self.use_roi.get() and not self.lock_roi.get():
            self.drawing_roi = False
            x, y = int(event.xdata), int(event.ydata)
            x1, y1 = min(self.start_x, x), min(self.start_y, y)
            w, h = abs(x - self.start_x), abs(y - self.start_y)
            self.roi_x.set(x1); self.roi_y.set(y1); self.roi_w.set(w); self.roi_h.set(h)
            self.update_roi_display()
        elif self.drawing_line and self.use_ruler.get():
            self.drawing_line = False


    def apply_roi(self):
        x, y, w, h = self.roi_x.get(), self.roi_y.get(), self.roi_w.get(), self.roi_h.get()
        if self.img_rgb is None: return
        ih, iw = self.img_rgb.shape[:2]
        if x < 0 or y < 0 or x + w > iw or y + h > ih:
            messagebox.showerror("Error", "ROI out of bounds.")
            return
        self.update_roi_display()


    def reset_roi(self):
        if self.img_rgb is None: return
        self.roi_x.set(0)
        self.roi_y.set(0)
        self.roi_w.set(self.img_rgb.shape[1])
        self.roi_h.set(self.img_rgb.shape[0])
        self.update_roi_display()


    def update_roi_display(self):
        self.show_original()
        if self.use_roi.get():
            x, y, w, h = self.roi_x.get(), self.roi_y.get(), self.roi_w.get(), self.roi_h.get()
            ax = self.fig_img.axes[0]
            self.rect = ax.add_patch(plt.Rectangle((x, y), w, h, fill=False, color='red', linewidth=2))
            self.roi_info.set(f"Current ROI: (X={x}, Y={y}, W={w}, H={h})")
        else:
            self.roi_info.set("Current ROI: Full Image")
        self.canvas_img.draw()


    def clear_ruler(self):
        self.ruler_info.set("Length: -- px\nDistance: -- μm")
        if self.ruler_line:
            self.ruler_line.remove()
            self.ruler_line = None
            self.canvas_img.draw()


    def analyze_droplets(self):
        if self.img_rgb is None:
            messagebox.showwarning("Warning", "Load image first.")
            return
        try:
            px_size = self.pixel_size.get()
            if px_size <= 0: raise ValueError("Pixel size > 0")
            min_circ = self.min_circularity.get()
            if not 0 < min_circ <= 1: raise ValueError("Circularity in (0,1]")
            min_diam = self.min_diameter.get()
            if min_diam <= 0: raise ValueError("Min diam > 0")
            min_area_px = np.pi * (min_diam / 2 / px_size) ** 2


            if self.use_roi.get():
                x, y, w, h = self.roi_x.get(), self.roi_y.get(), self.roi_w.get(), self.roi_h.get()
                ih, iw = self.img_rgb.shape[:2]
                if x + w > iw or y + h > ih:
                    messagebox.showerror("Error", "ROI out of bounds.")
                    return
                img_crop_bgr = self.img_bgr[y:y+h, x:x+w]
                img_crop_rgb = self.img_rgb[y:y+h, x:x+w]
                offset_x, offset_y = x, y
            else:
                img_crop_bgr = self.img_bgr
                img_crop_rgb = self.img_rgb
                offset_x, offset_y = 0, 0


            channel = self.channel.get()
            if channel == "r": work_img = img_crop_bgr[:, :, 2]
            elif channel == "g": work_img = img_crop_bgr[:, :, 1]
            elif channel == "b": work_img = img_crop_bgr[:, :, 0]
            else: work_img = cv2.cvtColor(img_crop_rgb, cv2.COLOR_RGB2GRAY)


            blurred = cv2.GaussianBlur(work_img, (7, 7), 1.0)
            if self.use_manual_thresh.get():
                _, binary = cv2.threshold(blurred, self.thresh_value.get(), 255, cv2.THRESH_BINARY)
            else:
                _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if self.droplet_type.get() == "dark":
                binary = cv2.bitwise_not(binary)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=2)


            dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
            _, sure_fg = cv2.threshold(dist, 0.7 * dist.max(), 255, 0)
            sure_fg = np.uint8(sure_fg)
            _, markers = cv2.connectedComponents(sure_fg)
            markers = markers + 1
            sure_bg = cv2.dilate(binary, kernel, iterations=3)
            markers[sure_bg == 0] = 0
            markers = cv2.watershed(img_crop_bgr, markers)
            binary[markers == -1] = 0


            contours, _ = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
            droplets = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < min_area_px: continue
                perimeter = cv2.arcLength(cnt, True)
                if perimeter == 0: continue
                circ = 4 * np.pi * area / (perimeter ** 2)
                if circ < min_circ: continue


                if len(cnt) >= 5:
                    ellipse = cv2.fitEllipse(cnt)
                    major = ellipse[1][0]
                    minor = ellipse[1][1]
                    diam_um = (major + minor) / 2 * px_size
                else:
                    diam_um = 2 * np.sqrt(area) * px_size / np.sqrt(np.pi)


                mask = np.zeros_like(work_img)
                cv2.drawContours(mask, [cnt], -1, 255, -1)
                dist_mask = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
                _, _, _, center_px = cv2.minMaxLoc(dist_mask)
                cx = int(center_px[0]) + offset_x
                cy = int(center_px[1]) + offset_y


                droplets.append({
                    'Area (px²)': area,
                    'Diameter (μm)': diam_um,
                    'Circularity': circ,
                    'Center': (cx, cy)
                })


            if not droplets:
                messagebox.showinfo("Result", "No droplets found.")
                return


            merge_thresh = self.merge_threshold_px.get()
            if merge_thresh <= 0: merge_thresh = 2.0


            centers = np.array([d['Center'] for d in droplets])
            if len(centers) > 1:
                dist_mat = squareform(pdist(centers))
                np.fill_diagonal(dist_mat, np.inf)
                close_pairs = np.where(dist_mat < merge_thresh)
                to_remove = set()
                for i, j in zip(*close_pairs):
                    if i in to_remove or j in to_remove: continue
                    if droplets[i]['Area (px²)'] >= droplets[j]['Area (px²)']:
                        to_remove.add(j)
                    else:
                        to_remove.add(i)
                droplets = [d for i, d in enumerate(droplets) if i not in to_remove]


            self.droplet_data = pd.DataFrame(droplets)
            self.update_statistics(len(droplets))
            self.plot_results(droplets)
            self.export_btn.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Analysis failed:\n{e}")


    def update_statistics(self, count):
        self.count_var.set(f"Total: {count}")
        diam = self.droplet_data['Diameter (μm)']
        self.mean_var.set(f"Mean: {diam.mean():.2f} μm")
        self.std_var.set(f"Std: {diam.std():.2f} μm")
        self.cv_var.set(f"CV: {diam.std()/diam.mean()*100:.1f}%")
        self.median_var.set(f"Median: {diam.median():.2f} μm")
        self.range_var.set(f"Range: {diam.min():.2f} → {diam.max():.2f} μm")


    def plot_results(self, droplets):
        self.fig_img.clear()
        ax1 = self.fig_img.add_subplot(111)
        overlay = self.img_rgb.copy()
        centers = np.array([d['Center'] for d in droplets])
        diameters = np.array([d['Diameter (μm)'] for d in droplets])
        if len(diameters) > 1:
            hist, bins = np.histogram(diameters, bins=20)
            mode_diam = (bins[np.argmax(hist)] + bins[np.argmax(hist)+1]) / 2
        else:
            mode_diam = diameters[0] if len(diameters) == 1 else 1.0
        threshold_px = (mode_diam / 6) / self.pixel_size.get()
        if len(centers) > 1:
            dist_mat = squareform(pdist(centers))
            np.fill_diagonal(dist_mat, np.inf)
            close_idx = set(np.where(dist_mat < threshold_px)[0])
        else:
            close_idx = set()
        for i, d in enumerate(droplets):
            cx, cy = d['Center']
            color = (255, 0, 0) if i in close_idx else (0, 0, 255)
            cv2.circle(overlay, (cx, cy), 5, color, -1)
        ax1.imshow(overlay)
        ax1.set_title("Droplets (red=clustered)")
        ax1.axis('off')
        self.fig_img.tight_layout()
        self.canvas_img.draw()


        self.fig_hist.clear()
        ax2 = self.fig_hist.add_subplot(111)
        ax2.hist(diameters, bins=20, color='lightgreen', edgecolor='black', alpha=0.8)
        ax2.set_title("Size Distribution")
        ax2.set_xlabel("Diameter (μm)")
        ax2.set_ylabel("Count")
        ax2.grid(True, alpha=0.5)
        self.fig_hist.tight_layout()
        self.canvas_hist.draw()


    def export_results(self):
        if self.droplet_data is None: return
        path = filedialog.asksaveasfilename(
            title="Save Results", defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")]
        )
        if not path: return
        try:
            meta = {
                'Parameter': [
                    'Pixel Size (μm/pixel)', 'Min Diameter (μm)', 'Channel', 'Droplet Type',
                    'Manual Threshold', 'Threshold Value', 'Min Circularity', 'Merge Threshold (px)',
                    'Use ROI', 'ROI X', 'ROI Y', 'ROI Width', 'ROI Height'
                ],
                'Value': [
                    self.pixel_size.get(), self.min_diameter.get(), self.channel.get(), self.droplet_type.get(),
                    self.use_manual_thresh.get(), self.thresh_value.get() if self.use_manual_thresh.get() else 'Otsu',
                    self.min_circularity.get(), self.merge_threshold_px.get(),
                    self.use_roi.get(),
                    self.roi_x.get() if self.use_roi.get() else 'Full',
                    self.roi_y.get() if self.use_roi.get() else 'Full',
                    self.roi_w.get() if self.use_roi.get() else 'Full',
                    self.roi_h.get() if self.use_roi.get() else 'Full'
                ]
            }
            df_meta = pd.DataFrame(meta)
            df_combined = pd.concat([df_meta, self.droplet_data.reset_index(drop=True)], axis=1)


            ext = Path(path).suffix.lower()
            if ext == ".xlsx":
                df_combined.to_excel(path, index=False, engine='openpyxl')
            else:
                df_combined.to_csv(path, index=False)
            messagebox.showinfo("Success", f"Saved to:\n{Path(path).name}")
        except Exception as e:
            messagebox.showerror("Fail", f"Save error:\n{e}")


    def clear_all(self):
        self.file_var.set("")
        self.count_var.set("Total: 0")
        self.mean_var.set("Mean: -- μm"); self.std_var.set("Std: -- μm"); self.cv_var.set("CV: --%")
        self.median_var.set("Median: -- μm"); self.range_var.set("Range: -- → -- μm")
        self.droplet_data = None
        self.export_btn.config(state=tk.DISABLED)
        self.fig_img.clear(); self.canvas_img.draw()
        self.fig_hist.clear(); self.canvas_hist.draw()
        self.clear_ruler()




if __name__ == "__main__":
    root = tk.Tk()
    # ===版权信息===
    copyright_label = tk.Label(root, text="© 2025 Grant. Licensed under the MIT License.", 
                             fg="#555555", bg="#f0f0f0")
    copyright_label.pack(side=tk.BOTTOM, fill=tk.X)
    app = DropletAnalyzer(root)

    root.mainloop()