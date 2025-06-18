<template>
  <div class="chat-container">
    <!-- 头部标题 -->
    <div class="chat-header">
      <h1>语音助手</h1>
      <div class="status-indicator" :class="{ 'recording': isRecording, 'speaking': isSpeaking }">
        {{ status }}
      </div>
    </div>

    <!-- 主要聊天区域 -->
    <div class="chat-content">
      <!-- 欢迎界面 - 没有消息时显示 -->
      <div class="welcome-center" v-if="messages.length === 0">
        <div class="welcome-title">
          你好，欢迎使用智能助手
        </div>
        
        <!-- 居中输入框 -->
        <div class="center-input-container">
          <div class="center-input-wrapper">
            <!-- 图片预览区域 -->
            <div v-if="uploadedFiles.length > 0" class="center-image-preview">
              <div class="preview-image-container">
                <img :src="uploadedFiles[0].dataURL" :alt="uploadedFiles[0].name" class="preview-image" />
                <button class="remove-image-btn" @click="removeImage" title="移除图片">×</button>
              </div>
            </div>
            
            <el-input
              v-model="textInput"
              type="textarea"
              :rows="1"
              :autosize="{ minRows: 1, maxRows: 4 }"
              placeholder="发消息、输入 @ 选择技能或 / 选择文件"
              :disabled="isWaitingForResponse"
              @keydown.enter.prevent="handleEnterKey"
              class="center-message-input"
            />
            
            <!-- 工具栏在输入框内 -->
            <div class="center-toolbar">
                             <!-- 文件上传 -->
               <label class="center-tool-button" for="center-file-upload" title="上传文件">
                 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                   <path d="M21.44 11.05L12.25 20.24C11.1242 21.3658 9.59722 21.9983 8.005 21.9983C6.41278 21.9983 4.88583 21.3658 3.76 20.24C2.63417 19.1142 2.00171 17.5872 2.00171 15.995C2.00171 14.4028 2.63417 12.8758 3.76 11.75L12.95 2.56C13.7006 1.80944 14.7186 1.38554 15.78 1.38554C16.8414 1.38554 17.8594 1.80944 18.61 2.56C19.3606 3.31056 19.7845 4.32863 19.7845 5.39C19.7845 6.45137 19.3606 7.46944 18.61 8.22L9.41 17.41C9.03491 17.7851 8.52541 17.9962 7.995 17.9962C7.46459 17.9962 6.95509 17.7851 6.58 17.41C6.20491 17.0349 5.99381 16.5254 5.99381 15.995C5.99381 15.4646 6.20491 14.9551 6.58 14.58L15.07 6.1" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                 </svg>
                 <input
                   id="center-file-upload"
                   type="file"
                   ref="fileInput"
                   @change="handleFileUpload"
                   accept="image/*"
                   style="display: none;"
                 />
               </label>
               
               <!-- 语音按钮 -->
               <button 
                 class="center-voice-button" 
                 :class="{ 'recording': isRecording }"
                 @click="toggleRecording"
                 :title="isRecording ? '停止录音' : '开始录音'"
               >
                 <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                   <path d="M12 1C10.3431 1 9 2.34315 9 4V12C9 13.6569 10.3431 15 12 15C13.6569 15 15 13.6569 15 12V4C15 2.34315 13.6569 1 12 1Z" stroke="currentColor" stroke-width="2"/>
                   <path d="M19 10V12C19 16.4183 15.4183 20 11 20H13C17.4183 20 21 16.4183 21 12V10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                   <path d="M5 10V12C5 16.4183 8.58172 20 13 20H11C6.58172 20 3 16.4183 3 12V10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                   <path d="M12 23V20" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                 </svg>
               </button>
              
              <!-- 发送按钮 -->
              <button
                class="center-send-button"
                @click="sendTextQuestion"
                :disabled="!canSend"
                :title="canSend ? '发送消息' : '请输入内容'"
              >
                ↑
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="messages-container" ref="transcriptRef" v-if="messages.length > 0">
        <div v-for="(message, index) in messages" :key="index" class="message-wrapper" :class="message.type">
          <div class="message-bubble">
            <div class="message-content" v-if="message.type !== 'file'">
              {{ message.content }}
            </div>
            <div class="message-content file-message" v-else>
              <div class="image-preview">
                <img :src="message.fileData" :alt="message.fileName" class="uploaded-image" />
              </div>
              <div class="file-info">
                <div class="file-name">{{ message.fileName }}</div>
                <div class="file-size">{{ formatFileSize(message.fileSize) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 - 只有有消息时才显示 -->
    <div class="input-section" v-if="messages.length > 0">
      <!-- 输入框 -->
      <div class="input-container">
        <div class="input-wrapper">
          <el-input
            v-model="textInput"
            type="textarea"
            :rows="1"
            :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="发消息。输入 @ 选择技能或 / 选择文件"
            :disabled="isWaitingForResponse"
            @keydown.enter.prevent="handleEnterKey"
            class="message-input"
          />
                     <div class="input-actions">
             <button 
               class="voice-button" 
               :class="{ 'recording': isRecording }"
               @click="toggleRecording"
               :title="isRecording ? '停止录音' : '开始录音'"
             >
               <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                 <path d="M12 1C10.3431 1 9 2.34315 9 4V12C9 13.6569 10.3431 15 12 15C13.6569 15 15 13.6569 15 12V4C15 2.34315 13.6569 1 12 1Z" stroke="currentColor" stroke-width="2"/>
                 <path d="M19 10V12C19 16.4183 15.4183 20 11 20H13C17.4183 20 21 16.4183 21 12V10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                 <path d="M5 10V12C5 16.4183 8.58172 20 13 20H11C6.58172 20 3 16.4183 3 12V10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                 <path d="M12 23V20" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
               </svg>
             </button>
           </div>
        </div>
      </div>

      <!-- 底部工具栏 -->
      <div class="toolbar">
        <div class="tool-buttons">
                     <!-- 文件上传 -->
           <label class="tool-button" for="file-upload" title="上传文件">
             <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
               <path d="M21.44 11.05L12.25 20.24C11.1242 21.3658 9.59722 21.9983 8.005 21.9983C6.41278 21.9983 4.88583 21.3658 3.76 20.24C2.63417 19.1142 2.00171 17.5872 2.00171 15.995C2.00171 14.4028 2.63417 12.8758 3.76 11.75L12.95 2.56C13.7006 1.80944 14.7186 1.38554 15.78 1.38554C16.8414 1.38554 17.8594 1.80944 18.61 2.56C19.3606 3.31056 19.7845 4.32863 19.7845 5.39C19.7845 6.45137 19.3606 7.46944 18.61 8.22L9.41 17.41C9.03491 17.7851 8.52541 17.9962 7.995 17.9962C7.46459 17.9962 6.95509 17.7851 6.58 17.41C6.20491 17.0349 5.99381 16.5254 5.99381 15.995C5.99381 15.4646 6.20491 14.9551 6.58 14.58L15.07 6.1" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
             </svg>
                            <input
                 id="file-upload"
                 type="file"
                 ref="fileInput"
                 @change="handleFileUpload"
                 accept="image/*"
                 style="display: none;"
               />
           </label>
        </div>
        
        <div class="send-section">
          <button
            class="send-button"
            @click="sendTextQuestion"
            :disabled="!canSend"
            :title="canSend ? '发送消息' : '请输入内容'"
          >
            ↑
          </button>
        </div>
      </div>
    </div>

    <!-- 停止按钮（仅在AI回答时显示） -->
    <div v-if="isSpeaking" class="stop-button-container">
      <button class="stop-button" @click="interruptSpeaking">
        停止回答
      </button>
    </div>
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
      crossfadeDuration: 0.02,
      minBufferSize: 1024,     // 减小最小缓冲区大小
      maxBufferSize: 4096,     // 减小最大缓冲区大小
      bufferThreshold: 0.03,   // 减小缓冲阈值，更快开始播放
      audioAnalyser: null,
      silenceTimer: null,
      silenceThreshold: -30,
      silenceDuration: 500,
      isVoiceActive: false,
      audioWorkletNode: null,
      voiceActivityDetector: null,
      lastVoiceActivityTime: 0,
      autoStopTimeout: null,
      isContinuousMode: false,
      audioStream: null,
      isWaitingForResponse: false,
      shouldResumeDetection: false,
      isSystemSpeaking: false,
      textInput: '',
      uploadedFiles: []
    }
  },

  computed: {
    canSend() {
      return (this.textInput.trim() || this.uploadedFiles.length > 0) && !this.isWaitingForResponse
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
    if (this.autoStopTimeout) {
      clearTimeout(this.autoStopTimeout)
    }
    if (this.voiceActivityDetector) {
      this.voiceActivityDetector.disconnect()
    }
  },

  methods: {
    connectSocket () {
      try {
        // const url ="http://192.168.137.128:8000"
        const url ="http://127.0.0.1:8000"
        console.log('Connecting to Socket.IO...')
        this.socket = io(url, {
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
          this.isWaitingForResponse = false
          this.$message({
            message: '与服务器的连接已断开',
            type: 'warning'
          })
        })

        this.socket.on('connect_error', (error) => {
          console.error('Socket.IO connection error:', error)
          this.isConnected = false
          this.status = '连接错误'
          this.isWaitingForResponse = false
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
          console.log(`Received audio chunk ${data.chunk_id}, delay: ${(Date.now() / 1000 - data.timestamp).toFixed(3)}s`)
          if (data.data) {
            this.isSpeaking = true
            console.log("Received inputType:", data.inputType)
            this.handleAudioData(data.data, data.inputType)
          }
        })
        this.socket.on('speaking_end', async (data) => {
          console.log('Speaking end')
          this.isSpeaking = true
          if (data.inputType==="audio"){
            await this.startRecording(data.inputType)
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
          this.isWaitingForResponse = false
        })

        this.socket.on('status', (data) => {
          console.log('Server status:', data.message)
          this.status = data.message
        })

        this.socket.on('response_complete', () => {
          console.log('Server response complete')
          this.isSpeaking = false
          this.resetState()
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

    handleAudioData (base64Data, inputType) {
      try {
        this.isSystemSpeaking = true
        
        // 优化：使用更快的base64解码
        const binaryString = atob(base64Data)
        const bytes = new Uint8Array(binaryString.length)
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i)
        }

        const int16Array = new Int16Array(bytes.buffer)
        
        // 检查音频数据有效性
        if (int16Array.length === 0) {
          console.warn('Received empty audio data')
          return
        }
        
        console.log(`Processing audio chunk: ${int16Array.length} samples`)
        this.audioQueue.push(int16Array)
        
        // 立即开始处理，不等待
        if (!this.isProcessingQueue) {
          // 使用setTimeout确保处理是异步的，避免阻塞
          setTimeout(() => this.processAudioQueue(inputType), 0.1)
        }
      } catch (error) {
        console.error('Error processing audio data:', error)
        this.$message({
          message: '音频处理失败',
          type: 'error'
        })
        this.isSpeaking = false
        this.isSystemSpeaking = false
      }
    },

    async processAudioQueue (inputType) {
      if (this.audioQueue.length === 0) {
        this.isProcessingQueue = false
        this.isSpeaking = false
        this.isSystemSpeaking = false
        if (inputType==="text") {
          this.resetState()
        }else{
          this.isWaitingForResponse = false
          this.status = "已完成"
        }
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

        // 立即播放策略：减少等待时间
        const currentBufferSize = this.audioQueue.reduce((total, chunk) => total + chunk.length, 0)
        const bufferDuration = currentBufferSize / 24000 // 转换为秒

        // 更激进的播放策略：有数据就播放，不等待缓冲
        if (this.audioQueue.length === 0) {
          // 如果队列为空，短暂等待
          await new Promise(resolve => setTimeout(resolve, 10))
          this.processAudioQueue(inputType)
          return
        }

        // 立即播放第一个块，不等待更多数据
        let combinedData = this.audioQueue.shift()
        
        // 只有在音频块太小时才合并，避免过度缓冲
        if (combinedData.length < this.minBufferSize && this.audioQueue.length > 0) {
          const nextChunk = this.audioQueue.shift()
          const tempArray = new Int16Array(combinedData.length + nextChunk.length)
          tempArray.set(combinedData)
          tempArray.set(nextChunk, combinedData.length)
          combinedData = tempArray
        }

        // 创建音频缓冲区
        const audioBuffer = this.audioContext.createBuffer(1, combinedData.length, 24000)
        audioBuffer.getChannelData(0).set(new Float32Array(combinedData).map(x => x / 32768))

        // 创建音频源
        const source = this.audioContext.createBufferSource()
        source.buffer = audioBuffer
        source.connect(this.audioContext.destination)

        // 计算播放时间，实现无缝连接
        const playTime = Math.max(this.audioContext.currentTime, this.lastPlaybackTime)
        source.start(playTime)
        this.lastPlaybackTime = playTime + audioBuffer.duration

        // 监听播放结束，立即处理下一个块
        source.onended = () => {
          // 减少延迟，立即处理下一个块
          setTimeout(() => this.processAudioQueue(inputType), 0)
        }
      } catch (error) {
        console.error('Error processing audio queue:', error)
        this.isProcessingQueue = false
        this.isSpeaking = false
        this.isSystemSpeaking = false
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
      if (this.isContinuousMode) {
        await this.stopRecording()
      } else {
        await this.startRecording()
      }
    },

    async startRecording (inputType) {
      try {
        if (!this.socket || !this.socket.connected) {
          this.$message({
            message: '未连接到服务器，请等待连接...',
            type: 'warning'
          })
          return
        }

        // 获取音频流
        this.audioStream = await navigator.mediaDevices.getUserMedia({ 
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
            googAudioMirroring: false,
            googLeakyBucket: true,
            googDucking: true
          }
        })

        // 创建音频上下文和分析器
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
          sampleRate: 44100
        })
        this.audioAnalyser = this.audioContext.createAnalyser()
        this.audioAnalyser.fftSize = 2048
        this.audioAnalyser.smoothingTimeConstant = 0.8

        // 创建音频源
        this.audioSource = this.audioContext.createMediaStreamSource(this.audioStream)
        
        // 创建语音活动检测器
        this.voiceActivityDetector = this.audioContext.createScriptProcessor(2048, 1, 1)
        
        // 正确连接音频处理图
        this.audioSource.connect(this.audioAnalyser)
        this.audioSource.connect(this.voiceActivityDetector)
        this.voiceActivityDetector.connect(this.audioContext.destination)

        console.log("开始设置语音活动检测：")
        // 设置语音活动检测
        this.voiceActivityDetector.onaudioprocess = (e) => {
          const inputData = e.inputBuffer.getChannelData(0)
          const volume = this.calculateVolume(inputData)
          if (this.isContinuousMode && !this.isWaitingForResponse && !this.isSystemSpeaking) {
            if (volume > this.silenceThreshold) {
              this.lastVoiceActivityTime = Date.now()
              if (!this.isVoiceActive) {
                this.isVoiceActive = true
                console.log('检测到语音活动，音量:', volume)
                // 如果不在录音状态，开始新的录音
                if (!this.isRecording) {
                  this.startNewRecording()
                }
              }
            } else {
              if (this.isVoiceActive && Date.now() - this.lastVoiceActivityTime > this.silenceDuration) {
                this.isVoiceActive = false
                console.log('语音活动结束，音量:', volume)
                this.autoStopRecording()
              }
            }
          }
        }
        if (inputType==="text"){
          this.isContinuousMode = false
        }else{
          // 开始持续对话模式
          this.isContinuousMode = true
          this.status = '等待说话...'
          this.messages.push({
            type: 'system',
            content: '已进入持续对话模式，请开始说话...'
          })
        }
        

      } catch (error) {
        console.error('Error starting recording:', error)
        this.$message({
          message: error.message || '无法访问麦克风',
          type: 'error'
        })
        this.isRecording = false
        this.isContinuousMode = false
      }
    },

    async startNewRecording() {
      try {
        if (!this.audioStream) {
          console.error('No audio stream available')
          return
        }

        this.mediaRecorder = new MediaRecorder(this.audioStream, {
          mimeType: "audio/webm;codecs=opus",
          audioBitsPerSecond: 256000
        })
        
        this.audioChunks = []

        this.mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            this.audioChunks.push(event.data)
          }
        }

        this.mediaRecorder.onstop = async () => {
          if (this.audioChunks.length === 0) return

          try {
            const audioBlob = new Blob(this.audioChunks, { type: "audio/webm;codecs=opus" })
            this.audioChunks = []

            const reader = new FileReader()
            reader.onload = () => {
              const base64data = reader.result.split(',')[1]
              if (this.socket && this.socket.connected) {
                console.log('发送音频数据到服务器...')
                this.isWaitingForResponse = true
                this.status = '等待响应...'
                
                // 发送音频数据
                this.socket.emit('audio_data', {
                  data: base64data,
                  clientId: this.clientId,
                  mimeType: "audio/webm;codecs=opus"
                })

                // 设置超时处理
                setTimeout(() => {
                  if (this.isWaitingForResponse) {
                    console.log('响应超时，重置状态')
                    this.resetState()
                  }
                }, 10000) // 10秒超时
              }
            }
            reader.readAsDataURL(audioBlob)
          } catch (error) {
            console.error('Error processing audio data:', error)
            this.resetState()
          }
        }

        this.mediaRecorder.start(50)
        this.isRecording = true
        this.status = '正在录音...'
        this.messages.push({
          type: 'user',
          content: '正在录音...'
        })

      } catch (error) {
        console.error('Error starting new recording:', error)
        this.isRecording = false
      }
    },

    async stopRecording() {
      if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
        this.mediaRecorder.stop()
      }
      this.isRecording = false
      this.isContinuousMode = false
      this.status = '已停止'
      
      // 清理资源
      if (this.voiceActivityDetector) {
        this.voiceActivityDetector.disconnect()
        this.voiceActivityDetector = null
      }
      if (this.audioAnalyser) {
        this.audioAnalyser.disconnect()
      }
      if (this.audioSource) {
        this.audioSource.disconnect()
      }
      if (this.audioContext) {
        this.audioContext.close()
      }
      if (this.audioStream) {
        this.audioStream.getTracks().forEach(track => track.stop())
        this.audioStream = null
      }
    },

    calculateVolume(inputData) {
      let sum = 0
      for (let i = 0; i < inputData.length; i++) {
        sum += inputData[i] * inputData[i]
      }
      const rms = Math.sqrt(sum / inputData.length)
      return 20 * Math.log10(rms)
    },

    autoStopRecording() {
      if (this.isRecording) {
        console.log('Auto stopping recording...')
        this.mediaRecorder.stop()
        this.isRecording = false
        this.status = '处理中...'
        this.messages.push({
          type: 'user',
          content: '录音已停止，正在处理...'
        })
        
        // 清理资源
        if (this.voiceActivityDetector) {
          this.voiceActivityDetector.disconnect()
          this.voiceActivityDetector = null
        }
        if (this.audioAnalyser) {
          this.audioAnalyser.disconnect()
        }
        if (this.autoStopTimeout) {
          clearTimeout(this.autoStopTimeout)
          this.autoStopTimeout = null
        }
      }
    },

    interruptSpeaking() {
      this.stopAllAudio()
      this.isSpeaking = false
      this.status = '已停止'
      this.socket.emit('interrupt', { clientId: this.clientId })
      
      // 如果正在录音，也停止录音
      if (this.isRecording) {
        this.autoStopRecording()
      }
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
    },

    resumeVoiceDetection() {
      if (this.isContinuousMode && !this.isWaitingForResponse && !this.isSystemSpeaking) {
        this.isVoiceActive = false
        this.lastVoiceActivityTime = Date.now()
        console.log('恢复语音检测')
        
        // 确保音频处理图正确连接
        if (this.audioSource && this.voiceActivityDetector) {
          this.audioSource.connect(this.voiceActivityDetector)
          this.voiceActivityDetector.connect(this.audioContext.destination)
        }
      }
    },

    resetState() {
      if (!this.isSystemSpeaking) {
        this.isWaitingForResponse = false
        this.status = '等待说话...'
        this.messages.push({
          type: 'system',
          content: '可以继续说话了...'
        })
        setTimeout(() => {
          this.resumeVoiceDetection()
        }, 1000)
      }
    },

    async sendTextQuestion() {
      if (!this.canSend || !this.socket || !this.socket.connected) {
        return
      }

      const question = this.textInput.trim()
      
      // 构建发送数据，格式为 {"image": xxx, "text": ""}
      const messageData = {
        clientId: this.clientId,
        text: question || "",
        image: this.uploadedFiles.length > 0 ? this.uploadedFiles[0].data : null
      }

      // 显示用户消息
      if (question) {
        this.messages.push({
          type: 'user',
          content: question
        })
      }

      // 显示图片消息
      if (this.uploadedFiles.length > 0) {
        const file = this.uploadedFiles[0]
        this.messages.push({
          type: 'file',
          fileName: file.name,
          fileSize: file.size,
          fileData: file.dataURL // 使用完整的dataURL用于显示
        })
      }
      
      this.isWaitingForResponse = true
      this.status = '等待响应...'

      // 清空输入
      this.textInput = ''
      this.uploadedFiles = []

      try {
        console.log("发送数据到服务器...", {
          clientId: messageData.clientId,
          text: messageData.text,
          hasImage: messageData.image !== null,
          imageLength: messageData.image ? messageData.image.length : 0
        })
        // 如果上传了图片，则是发送图片，否则发送文本
        if (messageData.image) {
          this.socket.emit('image_data', messageData)
        } else {
          this.socket.emit('text_data', messageData)
        }
      } catch (error) {
        console.error('Error sending message:', error)
        this.$message({
          message: '发送消息失败',
          type: 'error'
        })
      }
    },

    handleFileUpload(event) {
      const files = Array.from(event.target.files)
      
      // 限制只能上传一张图片
      if (files.length === 0) return
      
      const file = files[0]
      
      // 检查文件类型
      if (!file.type.startsWith('image/')) {
        this.$message({
          message: '只支持上传图片文件',
          type: 'error'
        })
        return
      }

      // 检查文件大小（限制为5MB）
      if (file.size > 5 * 1024 * 1024) {
        this.$message({
          message: '图片文件太大，请选择小于5MB的图片',
          type: 'error'
        })
        return
      }

      // 读取图片内容为base64
      const reader = new FileReader()
      reader.onload = (e) => {
        // 获取base64数据（去除data:前缀部分）
        const base64Data = e.target.result.split(',')[1] || e.target.result
        
        // 清空之前的文件，只保留最新上传的图片
        this.uploadedFiles = [{
          name: file.name,
          size: file.size,
          type: file.type,
          data: base64Data,
          // 保留完整的dataURL用于显示预览
          dataURL: e.target.result
        }]
        
        this.$message({
          message: `图片 ${file.name} 已选择`,
          type: 'success'
        })
      }
      
      reader.onerror = () => {
        this.$message({
          message: `图片 ${file.name} 读取失败`,
          type: 'error'
        })
      }

      // 使用readAsDataURL读取为base64格式
      reader.readAsDataURL(file)

      // 清空input值，允许重复选择同一文件
      event.target.value = ''
    },



    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },

    handleEnterKey(event) {
      if (event.shiftKey) {
        // Shift+Enter换行，不发送
        return
      }
      // Enter发送消息
      this.sendTextQuestion()
    },

    askQuestion(question) {
      this.textInput = question
      this.sendTextQuestion()
    },

    removeImage() {
      this.uploadedFiles = []
      this.$message({
        message: '图片已移除',
        type: 'info'
      })
    }
  }
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 900px;
  margin: 0 auto;
  background: #f8f9fa;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* 头部样式 */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chat-header h1 {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.status-indicator {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  color: #6b7280;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
}

.status-indicator.recording {
  color: #ef4444;
  background: #fef2f2;
  border-color: #fecaca;
  animation: pulse 1.5s infinite;
}

.status-indicator.speaking {
  color: #f59e0b;
  background: #fffbeb;
  border-color: #fed7aa;
  animation: pulse 1.5s infinite;
}

/* 主要内容区域 */
.chat-content {
  flex: 1;
  overflow-y: auto;
  /* padding: 24px; */
  display: flex;
  flex-direction: column;
}

/* 居中欢迎界面 */
.welcome-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  max-width: 900px;
  width: 900px;
  /* margin: 0 auto; */
  /* padding: 40px 20px; */
}

.welcome-title {
  font-size: 28px;
  font-weight: 400;
  color: #1f2937;
  margin-bottom: 40px;
  text-align: center;
}

.center-input-container {
  width: 100%;
  max-width: 900px;
}

.center-input-wrapper {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
}

.center-input-wrapper:focus-within {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.center-image-preview {
  margin-bottom: 12px;
}

.preview-image-container {
  position: relative;
  display: inline-block;
}

.preview-image {
  max-width: 150px;
  max-height: 150px;
  border-radius: 8px;
  object-fit: cover;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.remove-image-btn {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 24px;
  height: 24px;
  border: none;
  background: #ef4444;
  color: white;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: bold;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);
}

.remove-image-btn:hover {
  background: #dc2626;
  transform: scale(1.1);
}

.center-message-input {
  width: 100%;
  margin-bottom: 12px;
}

.center-message-input ::v-deep .el-textarea__inner {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
  resize: none !important;
  font-size: 16px;
  line-height: 1.5;
  color: #374151;
}

.center-message-input ::v-deep .el-textarea__inner::placeholder {
  color: #9ca3af;
}

.center-toolbar {
  display: flex;
  align-items: center;
  justify-content: right;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.center-tool-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #6b7280;
  transition: all 0.2s;
}

.center-tool-button:hover {
  background: #f9fafb;
  color: #374151;
}

.center-voice-button {
  width: 36px;
  height: 36px;
  border: none;
  background: #f3f4f6;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  transition: all 0.2s;
  color: #6b7280;
}

.center-voice-button:hover {
  background: #e5e7eb;
  color: #374151;
}

.center-voice-button.recording {
  background: #ef4444;
  color: white;
  animation: pulse 1.5s infinite;
}

.center-send-button {
  width: 36px;
  height: 36px;
  border: none;
  background: #2563eb;
  color: white;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: bold;
  transition: all 0.2s;
}

.center-send-button:hover:not(:disabled) {
  background: #1d4ed8;
  transform: scale(1.05);
}

.center-send-button:disabled {
  background: #d1d5db;
  cursor: not-allowed;
  transform: none;
}

/* 消息容器 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 20px;
  margin:15px
}

.message-wrapper {
  display: flex;
  width: 100%;
  /* padding: 10px; */
}

.message-wrapper.user {
  justify-content: flex-end;
}

.message-wrapper.assistant,
.message-wrapper.system {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 16px;
  word-break: break-word;
  line-height: 1.4;
  font-size: 14px;
}

.message-wrapper.user .message-bubble {
  background: #2563eb;
  color: white;
  border-bottom-right-radius: 4px;
}

.message-wrapper.assistant .message-bubble {
  background: white;
  color: #374151;
  border: 1px solid #e5e7eb;
  border-bottom-left-radius: 4px;
}

.message-wrapper.system .message-bubble {
  background: #f3f4f6;
  color: #6b7280;
  font-size: 12px;
  border-radius: 12px;
  align-self: center;
  max-width: none;
}

.file-message {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.image-preview {
  flex-shrink: 0;
}

.uploaded-image {
  max-width: 200px;
  max-height: 200px;
  border-radius: 8px;
  object-fit: cover;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.file-info {
  flex: 1;
}

.file-name {
  font-weight: 500;
  color: #1e293b;
  margin-bottom: 4px;
}

.file-size {
  font-size: 12px;
  color: #64748b;
}

/* 输入区域 */
.input-section {
  background: white;
  border-top: 1px solid #e5e7eb;
  padding: 16px 24px;
}

.input-container {
  margin-bottom: 12px;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 24px;
  padding: 8px 16px;
  transition: all 0.2s;
}

.input-wrapper:focus-within {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.message-input {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  outline: none;
  font-size: 14px;
  line-height: 1.4;
}

.message-input ::v-deep .el-textarea__inner {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
  resize: none !important;
  font-size: 14px;
  line-height: 1.4;
}

.input-actions {
  display: flex;
  align-items: center;
}

.voice-button {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: all 0.2s;
}

.voice-button:hover {
  background: #f3f4f6;
}

.voice-button.recording {
  background: #ef4444;
  color: white;
  animation: pulse 1.5s infinite;
}

/* 工具栏 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tool-buttons {
  display: flex;
  gap: 8px;
}

.tool-button {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: all 0.2s;
  color: #6b7280;
}

.tool-button:hover {
  background: #f3f4f6;
  color: #374151;
}

.send-section {
  display: flex;
  align-items: center;
}

.send-button {
  width: 32px;
  height: 32px;
  border: none;
  background: #2563eb;
  color: white;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: bold;
  transition: all 0.2s;
}

.send-button:hover:not(:disabled) {
  background: #1d4ed8;
  transform: scale(1.05);
}

.send-button:disabled {
  background: #d1d5db;
  cursor: not-allowed;
  transform: none;
}

/* 停止按钮 */
.stop-button-container {
  position: fixed;
  bottom: 100px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
}

.stop-button {
  padding: 12px 24px;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 24px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
  transition: all 0.2s;
}

.stop-button:hover {
  background: #dc2626;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(239, 68, 68, 0.4);
}

/* 动画 */
@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.6; }
  100% { opacity: 1; }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chat-container {
    height: 100vh;
  }
  
  .chat-header {
    padding: 16px 20px;
  }
  
  .chat-content {
    padding: 16px 20px;
  }
  
  .input-section {
    padding: 12px 20px;
  }
  
  .message-bubble {
    max-width: 85%;
  }
  
  .welcome-center {
    padding: 20px 16px;
  }
  
  .welcome-title {
    font-size: 24px;
    margin-bottom: 30px;
  }
  
  .center-input-container {
    max-width: 100%;
  }
  
  .center-toolbar {
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .center-tool-button {
    font-size: 12px;
    padding: 6px 8px;
  }
}

/* 滚动条样式 */
.messages-container::-webkit-scrollbar,
.chat-content::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track,
.chat-content::-webkit-scrollbar-track {
  background: transparent;
}

.messages-container::-webkit-scrollbar-thumb,
.chat-content::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb:hover,
.chat-content::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}
</style>