<div align="center">

# 🚀 SSH Simple
### 让 SSH 操作变得 **简单**、**优雅**、**高效**

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?style=for-the-badge&logo=windows)
---


</div>

## ✨ 项目简介

**SSH Simple GUI** 是一个专为 Windows 用户打造的轻量级 SSH 客户端。告别繁琐的命令行参数，加入工具箱，拥抱现代化的图形界面！
本项目由 **Python** 驱动，结合了 `paramiko` 的强大功能与 `tkinter` 的原生体验！

> **"像adb一样，繁琐的命令，留给机器；优雅的操作，留给自己。"**

---

## 🌈 核心功能 (Features)

### 🖥️ **可视化连接 & 端口映射**
- **一键连接**：输入 IP、端口、用户密码，点击即连。
- **端口映射神器**：支持图形化添加 `Local -> Remote` 端口映射，甚至支持 **端口范围** (e.g., `8000-8005`)！
- **状态监控**：实时显示的连接状态指示灯 (🟢/🔴)。

### 💻 **独立终端体验**
- **原生 GUI 终端**：不再是黑乎乎的 CMD 窗口！我们重写了基于 Tkinter 的独立终端窗口。
- **多开支持**：同时管理多个会话，互不干扰。
- **主题适配**：完美适配深色/浅色模式。

### 📂 **全能文件管理器**
- **可视化操作**：像在本地一样管理远程文件。
- **在线编辑**：双击文本文件直接编辑、保存，即刻生效！
- **文件操作**：复制、剪切、粘贴、删除，一应俱全。

### 🚀 **极客工具箱**
- **3x-ui 一键安装**：内置脚本，点击按钮即可自动在终端中安装/管理 3x-ui 面板，小白也能轻松上手。
- **更多功能**：持续更新中...



## 🛠️ 安装与运行

### 环境要求
- Windows 10/11
- Python 3.8+

### 📦 依赖安装

#### 方法一：使用虚拟环境（推荐）
```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
.venv\Scripts\activate

# 3. 安装依赖
pip install paramiko matplotlib
```

#### 方法二：直接安装
```bash
pip install paramiko matplotlib
```

> ℹ️ **提示**：Tkinter 通常随 Python 一起安装，无需单独安装。

### ▶️ 启动
```bash
python gui.py
```

---

## 📸 界面预览

| **主界面 (深色模式)** | **文件管理** |
|:---:|:---:|
| *简洁直观的连接面板* | *强大的远程文件浏览* |

| **独立终端** | **工具箱** |
|:---:|:---:|
| *支持命令交互的 GUI 终端* | *一键安装脚本集成* |

---

## 📝 更新日志

- **v1.2 (new)** - 2025-11-24
    - ✨ **终端交互优化**：
        - 重写终端，提升视觉体验
        - 支持鼠标点击定位光标
        - 完善箭头键导航功能
        - 修复删除键行为，正确模拟 VT100 终端
    - 🐛 **Bug 修复**：
        - 修复光标消失问题
        - 修复字符覆盖与重复显示问题
    - 📊 **增加监控**：(独立monitoring_panel.py文件显示性能趋势😎)
        - 增加cpu、网络、硬盘、内存趋势图
        - 实现差分计算，展示真实的服务器统计数据
        - 动态识别最活跃网络接口
    - 😋 **问题检测**：开放log方便检测问题
    - 🛡️ **安全检测**：加入安全检测功能，会检测异常指令
- **v1.1 (old)** - 2025-11-23
    - 🔄 **重构后端**：完全移除 C 语言依赖，纯 Python 实现，无需编译！
    - 💻 **独立终端**：新增 `terminal.py`，提供独立的 GUI 终端体验。
    - 📂 **文件管理**：新增可视化文件管理器与文本编辑器。
    - 🚀 **工具箱**：集成 3x-ui 一键安装功能。
- **v1.0 (old)** - 2025-11-23
    - 💻 **独立终端**：提供独立的 GUI 终端体验。
    - 🚀 **工具箱**：新增工具箱功能。
---

<div align="center">

### 💖 Star This Project!

本项目是高粱NexT第一个项目

**By 高粱NexT**

</div>

## 📈 趋势图 (Star History)

[![Star History Chart](https://api.star-history.com/svg?repos=drgtdrgtgsd/SSH-is-simple&type=Date)](https://star-history.com/#drgtdrgtgsd/SSH-is-simple&Date)