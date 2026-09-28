# 模型放置说明 (Model Placement Guide)

请将离线模型文件置于此目录下（确保路径无中文与特殊空格）：

1. Qwen GGUF 翻译模型:
   project/models/translation/qwen2.5-1.5b-instruct-q4_k_m.gguf
   附带同级或子目录 model_info.json

2. CTranslate2 OPUS-MT 翻译模型:
   project/models/translation/opus-mt-en-zh-ct2/
   ├── model_info.json
   ├── model.bin
   ├── config.json
   ├── shared_vocabulary.txt
   └── tokenizer.json

3. 增加新模型：
   仅需新建文件夹并放置对应权重与 model_info.json，程序启动或重载时会自动识别支持的语言，无需修改任何核心代码！
