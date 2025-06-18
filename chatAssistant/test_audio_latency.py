#!/usr/bin/env python3
"""
音频延迟测试脚本
用于测试音频流的实时性能
"""

import time
import json
import socketio
import threading
from datetime import datetime

class AudioLatencyTester:
    def __init__(self, server_url="http://127.0.0.1:8000"):
        self.server_url = server_url
        self.sio = socketio.Client()
        self.audio_chunks = []
        self.start_time = None
        self.first_audio_time = None
        self.total_chunks = 0
        self.total_size = 0
        
        self.setup_handlers()
    
    def setup_handlers(self):
        """设置事件处理器"""
        
        @self.sio.event
        def connect():
            print(f"✅ 连接到服务器: {self.server_url}")
        
        @self.sio.event
        def disconnect():
            print("❌ 与服务器断开连接")
        
        @self.sio.event
        def audio(data):
            current_time = time.time()
            chunk_id = data.get('chunk_id', 0)
            timestamp = data.get('timestamp', 0)
            size = data.get('size', 0)
            
            # 计算延迟
            network_delay = current_time - timestamp if timestamp else 0
            
            # 记录第一个音频块
            if self.first_audio_time is None:
                self.first_audio_time = current_time
                first_chunk_delay = current_time - self.start_time
                print(f"🎵 首个音频块延迟: {first_chunk_delay:.3f}秒")
            
            self.total_chunks += 1
            self.total_size += size
            
            print(f"📦 音频块 #{chunk_id}: "
                  f"网络延迟 {network_delay:.3f}s, "
                  f"大小 {size} bytes")
            
            # 存储统计数据
            self.audio_chunks.append({
                'chunk_id': chunk_id,
                'timestamp': timestamp,
                'received_time': current_time,
                'network_delay': network_delay,
                'size': size
            })
        
        @self.sio.event
        def transcript(data):
            print(f"📝 转录: {data.get('text', '')}")
        
        @self.sio.event
        def speaking_start():
            print("🎤 开始说话")
        
        @self.sio.event
        def speaking_end(data):
            print("🔇 结束说话")
            self.print_statistics()
        
        @self.sio.event
        def error(data):
            print(f"❌ 错误: {data.get('message', '')}")
    
    def connect(self):
        """连接到服务器"""
        try:
            self.sio.connect(self.server_url)
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def test_text_input(self, text="你好，请简单介绍一下你自己"):
        """测试文本输入的音频响应延迟"""
        print(f"\n🧪 测试文本输入: '{text}'")
        self.reset_statistics()
        self.start_time = time.time()
        
        # 发送文本消息
        self.sio.emit('text_data', {'text': text})
        
        # 等待响应完成
        time.sleep(10)  # 等待10秒收集数据
    
    def reset_statistics(self):
        """重置统计数据"""
        self.audio_chunks = []
        self.start_time = None
        self.first_audio_time = None
        self.total_chunks = 0
        self.total_size = 0
    
    def print_statistics(self):
        """打印统计信息"""
        if not self.audio_chunks:
            print("📊 没有收到音频数据")
            return
        
        print(f"\n📊 音频延迟统计:")
        print(f"   • 总音频块数: {self.total_chunks}")
        print(f"   • 总数据大小: {self.total_size} bytes")
        
        if self.first_audio_time and self.start_time:
            first_delay = self.first_audio_time - self.start_time
            print(f"   • 首个音频块延迟: {first_delay:.3f}秒")
        
        # 计算网络延迟统计
        network_delays = [chunk['network_delay'] for chunk in self.audio_chunks]
        if network_delays:
            avg_delay = sum(network_delays) / len(network_delays)
            max_delay = max(network_delays)
            min_delay = min(network_delays)
            
            print(f"   • 平均网络延迟: {avg_delay:.3f}秒")
            print(f"   • 最大网络延迟: {max_delay:.3f}秒")
            print(f"   • 最小网络延迟: {min_delay:.3f}秒")
        
        # 计算音频块间隔
        if len(self.audio_chunks) > 1:
            intervals = []
            for i in range(1, len(self.audio_chunks)):
                interval = (self.audio_chunks[i]['received_time'] - 
                           self.audio_chunks[i-1]['received_time'])
                intervals.append(interval)
            
            avg_interval = sum(intervals) / len(intervals)
            print(f"   • 平均音频块间隔: {avg_interval:.3f}秒")
    
    def disconnect(self):
        """断开连接"""
        self.sio.disconnect()

def main():
    """主函数"""
    print("🎵 音频延迟测试工具")
    print("=" * 50)
    
    tester = AudioLatencyTester()
    
    if not tester.connect():
        return
    
    try:
        # 测试不同的输入
        test_cases = [
            "你好",
            "请简单介绍一下你自己",
            "今天天气怎么样？",
        ]
        
        for i, text in enumerate(test_cases, 1):
            print(f"\n🧪 测试用例 {i}/{len(test_cases)}")
            tester.test_text_input(text)
            time.sleep(2)  # 测试间隔
        
        print(f"\n✅ 所有测试完成")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  测试被用户中断")
    finally:
        tester.disconnect()

if __name__ == "__main__":
    main() 