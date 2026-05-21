"""
艺术品鉴赏智能体 API
"""
import base64
import json
import os

from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask_login import current_user
from dotenv import load_dotenv


assistant_bp = Blueprint('assistant', __name__, url_prefix='/api/assistant')

ALLOWED_IMAGE_MIMES = {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}
MAX_IMAGES = 5
MAX_IMAGE_BYTES = 8 * 1024 * 1024
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_openai_client():
    load_dotenv(os.path.join(BASE_DIR, '.env'))

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError('缺少 openai SDK，请先安装 openai>=1.0') from exc

    api_key = (os.getenv('ARK_API_KEY') or '').strip()
    if not api_key:
        raise RuntimeError('未配置 ARK_API_KEY 环境变量')

    return OpenAI(
        base_url=os.getenv('ARK_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3'),
        api_key=api_key,
    )


def _response_text(response):
    text = getattr(response, 'output_text', None)
    if text:
        return text

    chunks = []
    for item in getattr(response, 'output', []) or []:
        for content in getattr(item, 'content', []) or []:
            value = getattr(content, 'text', None)
            if value:
                chunks.append(value)
    return '\n'.join(chunks).strip()


def _image_inputs(files):
    image_parts = []
    for file_storage in files[:MAX_IMAGES]:
        if not file_storage or not file_storage.filename:
            continue
        if file_storage.mimetype not in ALLOWED_IMAGE_MIMES:
            raise ValueError('仅支持 png、jpg、jpeg、webp、gif 图片')

        payload = file_storage.read()
        if len(payload) > MAX_IMAGE_BYTES:
            raise ValueError('单张图片不能超过 8MB')

        encoded = base64.b64encode(payload).decode('ascii')
        image_parts.append({
            'type': 'input_image',
            'image_url': f'data:{file_storage.mimetype};base64,{encoded}',
        })

    return image_parts


def _event_to_dict(event):
    if isinstance(event, dict):
        return event
    if hasattr(event, 'model_dump'):
        return event.model_dump()
    if hasattr(event, 'dict'):
        return event.dict()
    return {}


def _find_string_by_keys(value, key_names):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in key_names and isinstance(item, str):
                return item
        for item in value.values():
            found = _find_string_by_keys(item, key_names)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_string_by_keys(item, key_names)
            if found:
                return found
    return ''


def _stream_piece(event):
    data = _event_to_dict(event)
    event_type = data.get('type') or getattr(event, 'type', '')
    event_type = str(event_type)
    delta = data.get('delta') or getattr(event, 'delta', '') or ''

    if 'thinking' in event_type or 'reasoning' in event_type:
        if isinstance(delta, str):
            return 'thinking', delta
        found = _find_string_by_keys(data, {'delta', 'text', 'content', 'summary'})
        return ('thinking', found) if found else (None, '')

    if event_type == 'response.output_text.delta':
        return ('answer', delta) if isinstance(delta, str) else (None, '')

    if event_type.endswith('.delta'):
        if isinstance(delta, str):
            return 'answer', delta

    return None, ''


def _stream_model(client, model, text, image_parts):
    stream = client.responses.create(
        model=model,
        input=[
            {
                'role': 'user',
                'content': [
                    *image_parts,
                    {'type': 'input_text', 'text': text},
                ],
            }
        ],
        stream=True,
        extra_body={'thinking': {'type': 'enabled'}},
    )
    for event in stream:
        part, delta = _stream_piece(event)
        if delta:
            yield part, delta


def _sse(event, payload):
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _domain_guard_prompt(message, conversation_context=''):
    return f"""
你是 ArtMarket 的艺术品鉴赏智能体，只回答与艺术品鉴赏、艺术史风格、图像分析、材料技法、收藏登记、藏品描述写作、展陈与收藏建议相关的问题。
如果用户问题与上述领域无关，请礼貌拒绝，并简短说明你只能协助艺术品鉴赏相关问题。
不要回答政治、编程、医疗、法律、金融投资、闲聊、作业代写等无关问题。
不要虚构作者、真伪、价格、确定年代；如果信息不足，要明确说明。

最近对话上下文：
{conversation_context or '无'}

用户问题：
{message or '无'}
"""


def _appraisal_prompt(message, conversation_context='', has_images=False):
    image_context = '用户本次上传了一张或多张图片，请结合图片内容进行艺术品鉴赏。' if has_images else '用户本次没有上传图片，请基于文字问题和对话上下文回答。'
    return f"""
你是 ArtMarket 的艺术品鉴赏智能体，只回答与艺术品鉴赏、艺术史风格、图像分析、材料技法、收藏登记、藏品描述写作、展陈与收藏建议相关的问题。
如果用户问题与上述领域无关，请礼貌拒绝，并简短说明你只能协助艺术品鉴赏相关问题。
不要回答政治、编程、医疗、法律、金融投资、闲聊、作业代写等无关问题。
不要虚构作者、真伪、价格、确定年代；如果信息不足，要明确说明。

{image_context}

最近对话上下文：
{conversation_context or '无'}

用户问题：
{message or '无'}

回答要求：
1. 如果是图片鉴赏，尽量按“整体印象、题材与图像内容、构图与色彩、材料技法、风格关联、收藏与登记建议、风险提示”组织。
2. 如果是追问，直接围绕艺术品鉴赏问题回答。
3. 所有不确定信息都要标明“不确定”或“需要补充资料”。
"""


@assistant_bp.route('/appraise', methods=['POST'])
def appraise():
    """根据一张或多张图片生成艺术品鉴赏意见。"""
    if not current_user.is_authenticated:
        return jsonify({'error': '请先登录后使用艺术品鉴赏智能体'}), 401

    message = request.form.get('message', '').strip()
    files = request.files.getlist('images')
    conversation_context = request.form.get('context', '').strip()

    try:
        image_parts = _image_inputs(files)

        if not image_parts:
            if not message:
                return jsonify({'error': '请输入问题，或上传图片进行鉴赏'}), 400

        client = _get_openai_client()
        model = os.getenv('ARK_MODEL', 'doubao-seed-2-0-pro-260215')

        prompt = _appraisal_prompt(message, conversation_context, bool(image_parts))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 500
    except Exception as exc:
        return jsonify({'error': f'智能体调用失败：{exc}'}), 502

    @stream_with_context
    def generate():
        try:
            thinking_done = False
            for part, delta in _stream_model(client, model, prompt, image_parts):
                if part == 'thinking':
                    yield _sse('thinking_delta', {'delta': delta})
                    continue
                if part == 'answer':
                    if not thinking_done:
                        yield _sse('thinking_done', {})
                        thinking_done = True
                    yield _sse('answer_delta', {'delta': delta})
            if not thinking_done:
                yield _sse('thinking_done', {})
            yield _sse('done', {})
        except Exception as exc:
            yield _sse('error', {'error': f'智能体调用失败：{exc}'})

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )
