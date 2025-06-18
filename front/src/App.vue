<template>
  <div id="app">
    <header class="app-header">
      <h1>智能语音助手</h1>
    </header>
    <main class="app-main">
      <VoiceAssistant />
    </main>
  </div>
</template>

<script>
import VoiceAssistant from './components/VoiceAssistant.vue'

export default {
  name: 'App',
  components: {
    VoiceAssistant
  }
}
</script>

<style>
#app {
  font-family: 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  min-height: 100vh;
  background-color: #f5f7fa;
}

.app-header {
  background-color: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 20px 0;
  margin-bottom: 40px;
}

.app-header h1 {
  margin: 0;
  font-size: 24px;
  color: #409EFF;
  text-align: center;
}

.app-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

@media (max-width: 768px) {
  .app-header {
    padding: 15px 0;
    margin-bottom: 20px;
  }

  .app-header h1 {
    font-size: 20px;
  }

  .app-main {
    padding: 0 15px;
  }
}
</style> 