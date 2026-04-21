# Vision API SOP
<!-- aliases: 截图|screenshot|视觉|屏幕识别|屏幕比对|图像识别 -->

## ⚠️ 前置规则（必须遵守）

1. **先枚举窗口**: 调用 vision 前必须先用 `pygetwindow` 枚举窗口标题, 确认目标窗口存在且已激活到前台. 窗口不存在就不要截图.
2. **🚫 禁止全屏截图**: 必须先利用 ljqCtrl 或窗口坐标截取目标窗口区域. 能截局部就不截整窗口, 能截窗口就绝不全屏. 全屏截图在任何场景下都不允许.
3. **能不用 vision 就不用**: 如果窗口标题或本地 OCR `ocr_utils.py` 能获取所需信息, 就不要调用 vision API. Vision 是最后手段.

## 快速用法

```python
from vision_api import ask_vision
result = ask_vision(image, prompt="描述图片内容", backend="claude", timeout=60, max_pixels=1_440_000)
# image: 文件路径(str/Path) 或 PIL Image
# backend: 'claude'(默认) | 'openai' | 'modelscope'
# 返回 str: 成功为模型回复, 失败为 'Error: ...'
```

## 如果没有 `vision_api.py`, 初次构建 vision 能力

1. 复制 `memory/vision_api.template.py` -> `memory/vision_api.py`
2. 只改头部"用户配置区": 去 `mykey.py` 里扫描变量名, 尝试找能用配置名填入 `CLAUDE_CONFIG_KEY` / `OPENAI_CONFIG_KEY`, `DEFAULT_BACKEND` 选后端并测试.
3. 保底: 没有可用 config 时去 `https://modelscope.cn/my/myaccesstoken` 申请 token 填入 `MODELSCOPE_API_KEY`.

## 关键风险与坑点

- **无重试机制**: `vision_api.py` 内部未实现 API 错误重试. 在自动化流程中使用时, 必须在上层代码手动实现重试逻辑, 否则偶发波动会直接中断任务.
- **API Config**: 当前使用 `claude_config141`(ncode.vkm2.com, 已验证). 备选可用: `native_claude_config2/84/5535`. 失效时直接改 `vision_api.py` 中的配置引用.

---
更新: 2025-07-18 | 修复 oai_config 导入 + 返回值统一 str
更新: 2026-02-18 | 默认后端改为 Claude 原生 API | SOP 精简
更新: 2026-04-21 | 合并远端初次构建说明, 保留本地别名与风险提示
