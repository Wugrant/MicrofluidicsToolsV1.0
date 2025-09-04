# MicrofluidicTools
# 微流控工具箱V1.0
一款专为微流控研究和设计人员开发的多功能工具软件，旨在简化微流控设计流程、提高研究效率。

## 功能特性

- **参数化微流控图纸设计**：快速生成和调整微流控芯片设计图纸
    
- **流体阻力计算**：针对不同微通道几何形状的流体阻力计算工具
    
- **液滴尺寸换算**：轻松进行液滴尺寸和液滴体积的转换
    
- **流量换算**：在不同流量流速质量间进行快速转换和计算
    
- **用户友好的图形界面**：基于Tkinter的直观操作界面
    
- **可视化功能**：使用Matplotlib提供数据和结果的可视化展示
    
## 安装方法

### Windows用户

1. 下载本项目的最新版本
    
2. 解压下载的文件
    
3. 打开dist文件夹
    
4. 双击运行.exe文件即可使用软件

### 从源代码运行

如果您希望从源代码运行，请确保安装了所需的依赖：

bash

`pip install numpy matplotlib`

然后运行主程序文件：

bash

`python main.py`

## 使用指南

### 参数化设计模块

输入所需参数，软件将自动生成微流控芯片的设计图纸。

### 流体阻力计算

1. 选择通道形状（矩形、圆形等）
2. 输入几何参数和流体参数
3. 点击"计算"获取结果

### 液滴尺寸换算

在换算界面中输入已知尺寸和单位，选择目标单位后即可获得换算结果。

### 流量换算

支持多种常用流量单位间的互相转换，满足不同实验条件的需求。

## 依赖项

本项目依赖以下Python库：
- numpy - 科学计算库
- matplotlib - 数据可视化库
- tkinter (Python标准库) - GUI界面开发
- ezdxf - DXF文件处理库
- json (Python标准库) - 数据存储和读取
- datetime (Python标准库) - 时间和日期处理
- math (Python标准库) - 数学计算

## 如何贡献

欢迎对本项目进行贡献！您可以通过以下方式参与：
1. 提交Issue报告bug或提出功能建议
2. 提交Pull Request贡献代码
3. 改进文档和使用示例
4. 分享使用经验和案例
    

## 许可证

本项目采用MIT许可证 - 详情请查看 [LICENSE](https://www.westlakechat.com/LICENSE) 文件。

## 联系方式

- 邮箱：914324902@qq.com
- QQ交流群：756934075
    

## 致谢

本项目使用了以下开源库，在此向这些项目的开发者和维护者表示衷心的感谢：

- [NumPy](https://numpy.org/) - 用于科学计算的基础库
    
- [Matplotlib](https://matplotlib.org/) - 用于数据可视化的综合库
    
    - matplotlib.pyplot - 提供类似MATLAB的绘图接口
        
    - matplotlib.backends.backend_tkagg - 提供Matplotlib与Tkinter的集成
        
    - matplotlib.patches - 提供各种形状和图形元素
        
- [Tkinter](https://docs.python.org/3/library/tkinter.html) - Python标准GUI库
    
    - ttk - Themed Tkinter组件
    - filedialog - 文件选择对话框
    - messagebox - 消息对话框
- [JSON](https://docs.python.org/3/library/json.html) - 数据序列化和存储
    
- [datetime](https://docs.python.org/3/library/datetime.html) - 时间处理模块
    

感谢所有使用和支持本项目的研究人员和工程师们！
