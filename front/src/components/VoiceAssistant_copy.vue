<template>
  <div class="voice-assistant">
    <el-card class="assistant-card">
      <template>
        <div class="card-header">
          <h2>语音助手</h2>
          <div class="status" :class="{ 'recording': isRecording, 'speaking': isSpeaking }">
            {{ status }}
          </div>
        </div>
      </template>

      <div class="controls">
        <el-button
          type="primary"
          icon="el-icon-microphone"
          @click="toggleRecording"
         
        >
          {{ isRecording ? '停止录音' : '开始录音' }}
        </el-button>

        <el-button
          v-if="isSpeaking"
          type="warning"
          @click="interruptSpeaking"
        >
          停止回答
        </el-button>
      </div>

      <div class="transcript-container">
        <div class="transcript" ref="transcriptRef">
          <div v-for="(message, index) in messages" :key="index" class="message" :class="message.type">
            <div class="message-content">
              {{ message.content }}
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import io from 'socket.io-client'

export default {
  name: 'VoiceAssistant',
  data () {
    return {
      socket: null,
      isConnected: false,
      isRecording: false,
      isSpeaking: false,
      status: '未连接',
      messages: [],
      mediaRecorder: null,
      audioChunks: [],
      clientId: Date.now().toString(),
      isPlaying: false,
      audioContext: null,
      audioSource: null,
      audioQueue: [],
      isProcessingQueue: false,
      lastPlaybackTime: 0,
      crossfadeDuration: 0.02, // 减少交叉淡入淡出时间到20ms
      minBufferSize: 4096, // 最小缓冲区大小
      maxBufferSize: 16384, // 最大缓冲区大小
      bufferThreshold: 0.1, // 缓冲区阈值（秒）
      audioAnalyser: null,
      silenceTimer: null,
      silenceThreshold: -50, // 静音阈值（dB）
      silenceDuration: 500, // 静音持续时间（毫秒）
      isVoiceActive: false,
      audioWorkletNode: null
    }
  },

  mounted () {
    this.connectSocket()
  },

  beforeDestroy () {
    this.stopAllAudio()
    if (this.audioContext) {
      this.audioContext.close()
    }
    if (this.socket) {
      this.socket.disconnect()
    }
  },

  methods: {
    connectSocket () {
      try {
        console.log('Connecting to Socket.IO...')
        this.socket = io(`http://${window.location.hostname}:8000`, {
          transports: ['websocket'],
          path: '/socket.io',
          reconnection: true,
          reconnectionAttempts: 5,
          reconnectionDelay: 1000
        })

        this.socket.on('connect', () => {
          console.log('Socket.IO connected successfully')
          this.isConnected = true
          this.status = '已连接'
          this.$message({
            message: '已连接到服务器',
            type: 'success'
          })
        })

        this.socket.on('disconnect', () => {
          console.log('Socket.IO disconnected')
          this.isConnected = false
          this.status = '连接已断开'
          this.isRecording = false
          this.isSpeaking = false
          this.$message({
            message: '与服务器的连接已断开',
            type: 'warning'
          })
        })

        this.socket.on('connect_error', (error) => {
          console.error('Socket.IO connection error:', error)
          this.isConnected = false
          this.status = '连接错误'
          this.$message({
            message: '连接出错，请检查服务器是否运行',
            type: 'error'
          })
        })

        this.socket.on('transcript', (data) => {
          console.log('Received transcript:', data)
          if (data.text && data.text.trim()) {
            this.handleTranscript(data.text)
          }
        })

        this.socket.on('audio', (data) => {
          console.log('Received audio data')
          if (data.data) {
            this.isSpeaking = true
            this.handleAudioData(data.data)
          }
        })

        this.socket.on('error', (data) => {
          console.error('Server error:', data.message)
          this.$message({
            message: data.message,
            type: 'error'
          })
          this.status = '出错了'
          this.isSpeaking = false
        })

        this.socket.on('status', (data) => {
          console.log('Server status:', data.message)
          this.status = data.message
        })
      } catch (error) {
        console.error('Error creating Socket.IO connection:', error)
        this.$message({
          message: "创建连接失败: " + error.message,
          type: 'error'
        })
      }
    },

    handleTranscript (text) {
      const lastMessage = this.messages[this.messages.length - 1]

      if (lastMessage && lastMessage.type === 'assistant') {
        lastMessage.content += text
      } else {
        this.messages.push({
          type: 'assistant',
          content: text
        })
      }

      this.scrollToBottom()
    },

    handleAudioData (base64Data) {
      try {
        const binaryString = atob(base64Data)
        const bytes = new Uint8Array(binaryString.length)
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i)
        }

        const int16Array = new Int16Array(bytes.buffer)
        this.audioQueue.push(int16Array)
        
        if (!this.isProcessingQueue) {
          this.processAudioQueue()
        }
      } catch (error) {
        console.error('Error processing audio data:', error)
        this.$message({
          message: '音频处理失败',
          type: 'error'
        })
        this.isSpeaking = false
      }
    },

    async processAudioQueue () {
      if (this.audioQueue.length === 0) {
        this.isProcessingQueue = false
        this.isSpeaking = false
        return
      }

      this.isProcessingQueue = true
      
      try {
        // 确保 AudioContext 已经初始化
        if (!this.audioContext) {
          this.initAudioContext()
        }
        
        // 如果 AudioContext 处于 suspended 状态，需要恢复
        if (this.audioContext.state === 'suspended') {
          await this.audioContext.resume()
        }

        // 计算当前缓冲区大小
        const currentBufferSize = this.audioQueue.reduce((total, chunk) => total + chunk.length, 0)
        const bufferDuration = currentBufferSize / 24000 // 转换为秒

        // 如果缓冲区太小，等待更多数据
        if (bufferDuration < this.bufferThreshold && this.audioQueue.length < 3) {
          await new Promise(resolve => setTimeout(resolve, 50))
          this.processAudioQueue()
          return
        }

        // 合并多个小块以减少播放间隔
        let combinedData = this.audioQueue.shift()
        while (this.audioQueue.length > 0 && combinedData.length < this.maxBufferSize) {
          const nextChunk = this.audioQueue.shift()
          const newLength = combinedData.length + nextChunk.length
          if (newLength <= this.maxBufferSize) {
            const tempArray = new Int16Array(newLength)
            tempArray.set(combinedData)
            tempArray.set(nextChunk, combinedData.length)
            combinedData = tempArray
          } else {
            this.audioQueue.unshift(nextChunk)
            break
          }
        }

        // 创建音频缓冲区
        const audioBuffer = this.audioContext.createBuffer(1, combinedData.length, 24000)
        audioBuffer.getChannelData(0).set(new Float32Array(combinedData).map(x => x / 32768))

        // 创建音频源
        const source = this.audioContext.createBufferSource()
        source.buffer = audioBuffer
        source.connect(this.audioContext.destination)

        // 播放音频
        source.start()
        this.lastPlaybackTime = this.audioContext.currentTime

        // 监听播放结束
        source.onended = () => {
          this.processAudioQueue()
        }
      } catch (error) {
        console.error('Error processing audio queue:', error)
        this.isProcessingQueue = false
        this.isSpeaking = false
      }
    },

    initAudioContext () {
      try {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
          sampleRate: 24000
        })
        
        // 创建音频分析器
        this.audioAnalyser = this.audioContext.createAnalyser()
        this.audioAnalyser.fftSize = 2048
        this.audioAnalyser.smoothingTimeConstant = 0.8
      } catch (error) {
        console.error('Error initializing audio context:', error)
        this.$message({
          message: '音频初始化失败',
          type: 'error'
        })
      }
    },

    async toggleRecording () {
      if (this.isRecording) {
        await this.stopRecording()
      } else {
        await this.startRecording()
      }
    },

    async startRecording () {
      try {
        if (!this.socket || !this.socket.connected) {
          this.$message({
            message: '未连接到服务器，请等待连接...',
            type: 'warning'
          })
          return
        }

        const stream = await navigator.mediaDevices.getUserMedia({ 
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            channelCount: 1,
            sampleRate: 44100,
            latency: 0,
            googEchoCancellation: true,
            googAutoGainControl: true,
            googNoiseSuppression: true,
            googHighpassFilter: true,
            googAudioMirroring: false,  // 禁用音频镜像
            googLeakyBucket: true,      // 启用漏桶算法
            googDucking: true          // 启用音频闪避
          }
        })
        
        // 检查支持的 MIME 类型
        const mimeTypes = [
          'audio/webm;codecs=opus',
          'audio/webm',
          'audio/ogg;codecs=opus',
          'audio/wav',
          'audio/mp4'
        ]
        
        let selectedMimeType = ''
        for (const mimeType of mimeTypes) {
          if (MediaRecorder.isTypeSupported(mimeType)) {
            selectedMimeType = mimeType
            console.log('Selected MIME type:', mimeType)
          }
        }

        if (!selectedMimeType) {
          throw new Error('浏览器不支持任何可用的音频格式')
        }
        
        this.mediaRecorder = new MediaRecorder(stream, {
          mimeType: "audio/webm;codecs=opus",
          audioBitsPerSecond: 256000  // 提高比特率到256kbps
        })
        
        this.audioChunks = []

        this.mediaRecorder.ondataavailable = (event) => {
          console.log('Data available:', event.data.size)
          if (event.data.size > 0) {
            this.audioChunks.push(event.data)
          }
        }

        this.mediaRecorder.onstop = async () => {
          console.log('MediaRecorder stopped')
          try {
            const audioBlob = new Blob(this.audioChunks, { type: "audio/webm;codecs=opus" })
            console.log('Audio blob created:', audioBlob.size)
            
            // 创建音频上下文进行预处理
            const audioContext = new (window.AudioContext || window.webkitAudioContext)({
              sampleRate: 44100
            })
            
            // 读取音频数据
            const arrayBuffer = await audioBlob.arrayBuffer()
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
            
            // 创建新的音频缓冲区
            const processedBuffer = audioContext.createBuffer(
              audioBuffer.numberOfChannels,
              audioBuffer.length,
              audioBuffer.sampleRate
            )
            
            // 处理每个声道
            for (let channel = 0; channel < audioBuffer.numberOfChannels; channel++) {
              const inputData = audioBuffer.getChannelData(channel)
              const outputData = processedBuffer.getChannelData(channel)
              
              // 应用噪声门限
              const noiseGate = 0.01
              // 应用动态范围压缩
              const threshold = 0.5
              const ratio = 0.6
              
              for (let i = 0; i < inputData.length; i++) {
                let sample = inputData[i]
                
                // 噪声门限
                if (Math.abs(sample) < noiseGate) {
                  sample = 0
                }
                
                // 动态范围压缩
                if (Math.abs(sample) > threshold) {
                  const excess = Math.abs(sample) - threshold
                  const compressed = excess * ratio
                  sample = Math.sign(sample) * (threshold + compressed)
                }
                
                // 平滑处理
                if (i > 0 && i < inputData.length - 1) {
                  sample = (inputData[i - 1] + sample + inputData[i + 1]) / 3
                }
                
                outputData[i] = sample
              }
            }
            
            // 将处理后的音频转换回 Blob
            const processedBlob = await this.audioBufferToBlob(processedBuffer)
            const reader = new FileReader()
            
            reader.onload = () => {
              const base64data = reader.result.split(',')[1]
              if (this.socket && this.socket.connected) {
                console.log('Sending audio data to server...')
                this.socket.emit('audio_data', {
                  data: base64data,
                  clientId: this.clientId,
                  mimeType: "audio/webm;codecs=opus"
                }, (response) => {
                  console.log('Server response:', response)
                  if (response && response.error) {
                    this.$message({
                      message: response.error,
                      type: 'error'
                    })
                  }
                })
              } else {
                this.$message({
                  message: '未连接到服务器',
                  type: 'error'
                })
              }
            }

            reader.onerror = (error) => {
              console.error('Error reading audio data:', error)
              this.$message({
                message: '音频数据处理失败',
                type: 'error'
              })
            }

            reader.readAsDataURL(processedBlob)
            
            // 关闭音频上下文
            audioContext.close()
          } catch (error) {
            console.error('Error processing audio data:', error)
            this.$message({
              message: '音频处理失败',
              type: 'error'
            })
          } finally {
            // 停止所有音轨
            stream.getTracks().forEach(track => track.stop())
          }
        }

        // 每50ms触发一次ondataavailable事件，提高采样频率
        this.mediaRecorder.start(50)
        this.isRecording = true
        this.status = '正在录音...'
        this.messages.push({
          type: 'user',
          content: '正在录音...'
        })
      } catch (error) {
        console.error('Error starting recording:', error)
        this.$message({
          message: error.message || '无法访问麦克风',
          type: 'error'
        })
        this.isRecording = false
      }
    },

    // 将 AudioBuffer 转换为 Blob
    async audioBufferToBlob(audioBuffer) {
      const numOfChan = audioBuffer.numberOfChannels
      const length = audioBuffer.length * numOfChan * 2
      const buffer = new ArrayBuffer(44 + length)
      const view = new DataView(buffer)
      const channels = []
      let sample
      let offset = 0
      let pos = 0

      // 写入 WAV 文件头
      this.writeString(view, 0, 'RIFF')
      view.setUint32(4, 36 + length, true)
      this.writeString(view, 8, 'WAVE')
      this.writeString(view, 12, 'fmt ')
      view.setUint32(16, 16, true)
      view.setUint16(20, 1, true)
      view.setUint16(22, numOfChan, true)
      view.setUint32(24, audioBuffer.sampleRate, true)
      view.setUint32(28, audioBuffer.sampleRate * 2 * numOfChan, true)
      view.setUint16(32, numOfChan * 2, true)
      view.setUint16(34, 16, true)
      this.writeString(view, 36, 'data')
      view.setUint32(40, length, true)

      // 写入音频数据
      for (let i = 0; i < numOfChan; i++) {
        channels.push(audioBuffer.getChannelData(i))
      }

      while (pos < audioBuffer.length) {
        for (let i = 0; i < numOfChan; i++) {
          sample = Math.max(-1, Math.min(1, channels[i][pos]))
          sample = (0.5 + sample < 0 ? sample * 32768 : sample * 32767) | 0
          view.setInt16(44 + offset, sample, true)
          offset += 2
        }
        pos++
      }

      return new Blob([buffer], { type: 'audio/wav' })
    },

    // 写入字符串到 DataView
    writeString(view, offset, string) {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i))
      }
    },

    async stopRecording () {
      console.log('Stopping recording...')
      if (this.mediaRecorder) {
        console.log('MediaRecorder state:', this.mediaRecorder.state)
        if (this.mediaRecorder.state === 'recording') {
          try {
            this.mediaRecorder.stop()
            console.log('MediaRecorder stop called')
            this.isRecording = false
            this.status = '处理中...'
            this.messages.push({
              type: 'user',
              content: '录音已停止，正在处理...'
            })
          } catch (error) {
            console.error('Error stopping recording:', error)
            this.$message({
              message: '停止录音时出错',
              type: 'error'
            })
          }
        } else {
          console.log('MediaRecorder is not recording')
          this.isRecording = false
        }
      } else {
        console.log('No MediaRecorder instance')
        this.isRecording = false
      }
    },

    interruptSpeaking () {
      this.stopAllAudio()
      this.isSpeaking = false
      this.status = '已停止'
      this.socket.emit('interrupt', { clientId: this.clientId })
    },

    stopAllAudio () {
      if (this.audioContext) {
        this.audioContext.suspend()
      }
      this.audioQueue = []
      this.isProcessingQueue = false
      this.isSpeaking = false
    },

    scrollToBottom () {
      this.$nextTick(() => {
        const container = this.$refs.transcriptRef
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      })
    }
  }
}
</script>

<style scoped>
.voice-assistant {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.assistant-card {
  background-color: white;
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  color: #409EFF;
}

.status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 14px;
  color: #666;
}

.status.recording {
  color: #F56C6C;
  animation: pulse 1.5s infinite;
}

.status.speaking {
  color: #E6A23C;
  animation: pulse 1.5s infinite;
}

.controls {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin: 20px 0;
}

.transcript-container {
  margin-top: 20px;
  border: 1px solid #EBEEF5;
  border-radius: 4px;
  padding: 10px;
}

.transcript {
  max-height: 400px;
  overflow-y: auto;
  padding: 10px;
}

.message {
  margin-bottom: 10px;
  padding: 8px 12px;
  border-radius: 4px;
  max-width: 80%;
}

.message.user {
  background-color: #ECF5FF;
  margin-left: auto;
}

.message.assistant {
  background-color: #F2F6FC;
  margin-right: auto;
}

.message-content {
  word-break: break-word;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}
</style>