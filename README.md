# VisualAuto - 视觉自动化脚本

基于视觉识别（OpenCV 模板匹配）的桌面自动化点击脚本工具，提供图形化界面进行脚本编排与素材管理。

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.13 |
| GUI 框架 | PySide6（Qt for Python） |
| 视觉识别 | OpenCV（cv2.matchTemplate） |
| 屏幕截图 | MSS |
| 图像处理 | NumPy |
| 输入模拟 | Windows API（ctypes / SendInput / RegisterHotKey） |
| 打包工具 | PyInstaller |

## 基本功能

- **素材管理**：管理视觉素材（图片），支持交互式框选截图、框选检测范围、设定识别阈值
- **脚本编排**：通过可视化界面编排自动化动作序列，支持序号、跳转、条件分支
- **视觉识别**：基于模板匹配在指定屏幕区域检测目标素材，支持自定义相似度阈值
- **鼠标模拟**：模拟鼠标移动（带缓动曲线）和点击（单击/双击，带随机延迟）
- **热键控制**：注册全局热键，一键启动/停止脚本
- **日志输出**：带时间戳的实时日志，保留最近 1000 条
- **数据持久化**：素材和脚本配置以 JSON 文件形式保存

## 支持的动作

| 动作类型 | 说明 |
|----------|------|
| **延时** | 等待指定的毫秒数后继续执行 |
| **视觉判断** | 在指定区域进行模板匹配，根据识别结果（找到/未找到）跳转到不同动作 |
| **鼠标移动** | 移动鼠标到指定坐标（或上一次视觉识别到的位置），支持缓动动画时长 |
| **鼠标点击** | 在鼠标当前位置进行单击或双击（带随机延迟模拟真实操作） |
| **跳转** | 无条件跳转到指定动作序号，或根据当前素材设置条件跳转 |
| **设置素材** | 设置当前素材，用于后续条件跳转的判断依据 |

## 使用方式

### 环境准备

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（Windows PowerShell）
.venv\Scripts\Activate.ps1

# 安装依赖
pip install PySide6 opencv-python mss numpy pyinstaller
```

### 运行

```bash
python main.py
```

### 打包为 exe

```bash
pyinstaller --onefile --noconsole --name VisualAuto --upx-dir "your_upx_dir" --paths="path_to_cv2_package" main.py
```

### 使用流程

1. **添加素材**：在右侧「素材编辑」区域，输入素材名称，通过「截图」按钮框选屏幕区域作为模板图片，通过「框选」按钮设定检测范围，调整识别阈值，点击「添加」保存素材
2. **编排脚本**：在左侧「脚本控制」区域，设置启动/停止热键（如 `Ctrl+Shift+F1`），点击「新增动作」添加动作
3. **配置动作**：在弹出的对话框中设置动作名称、序号、类型，根据类型填写相应参数（延时时间、跳转目标、目标坐标等）
4. **运行脚本**：点击「启动脚本」按钮或按下设定的热键，脚本即按动作列表顺序执行，当前执行的动作会高亮显示
5. **查看日志**：底部日志面板实时显示每条动作的执行情况

## 项目结构

```
VisualAuto/
├── main.py                 # 入口文件
├── core/                   # 核心逻辑
│   ├── data_manager.py     # 数据管理（JSON 读写、素材/脚本 CRUD）
│   ├── vision_engine.py    # 视觉引擎（截屏、模板匹配）
│   ├── input_simulator.py  # 输入模拟（鼠标移动、点击）
│   └── script_engine.py    # 脚本引擎（动作执行、流程控制）
├── models/                 # 数据模型
│   ├── action.py           # 动作模型（ActionType 枚举、Action 数据类）
│   ├── material.py         # 素材模型
│   └── script_config.py    # 脚本配置模型
├── ui/                     # 用户界面
│   ├── main_window.py      # 主窗口
│   ├── script_panel.py     # 脚本控制面板
│   ├── material_panel.py   # 素材管理面板
│   ├── action_dialog.py    # 动作编辑弹窗
│   ├── region_selector.py  # 区域框选组件
│   ├── image_preview.py    # 图片预览弹窗
│   └── detection_overlay.py # 检测结果叠加层
├── data/                   # 数据文件（运行时生成）
│   ├── materials.json      # 素材配置
│   ├── scripts.json        # 脚本配置
│   └── images/             # 素材图片
└── docs/                   # 文档
```

## 开发说明

本项目使用 **TRAE + DeepSeek V4 Pro** 进行开发。