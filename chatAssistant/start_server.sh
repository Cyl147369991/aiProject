#!/bin/bash

# 启动脚本：start_server.sh

# 第一步：激活Conda环境
# 注意：根据你的Conda安装路径调整初始化命令
source ~/miniconda3/etc/profile.d/conda.sh  # 如果使用Anaconda
# 或 source ~/miniconda3/etc/profile.d/conda.sh  # 如果使用Miniconda
conda activate py312

# 第二步：进入工作目录
cd /volume1/homes/evancheng/AI/chatAssistant  # 替换为你的实际项目路径

# 第三步：启动Python服务
python run_server.py