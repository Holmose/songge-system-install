#!/usr/bin/env python3
"""GLM image recognition helper for Minis.

Usage:
  python3 glm_image_identify.py <image_path> [--prompt TEXT]

Requires:
  GLM_API_KEY in environment.
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

API_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'
DEFAULT_MODEL = 'glm-4v-flash'
DEFAULT_PROMPT = '请识别这张图片里的内容，用中文简短回答，并说明关键视觉特征。'


def build_payload(image_path: str, prompt: str, model: str) -> dict:
    mime = mimetypes.guess_type(image_path)[0] or 'image/jpeg'
    with open(image_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('ascii')
    return {
        'model': model,
        'messages': [
            {
                'role': 'user',
                'content': [
                    {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{b64}'}},
                    {'type': 'text', 'text': prompt},
                ],
            }
        ],
        'temperature': 0.1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Recognize an image with GLM vision API.')
    parser.add_argument('image_path')
    parser.add_argument('--prompt', default=DEFAULT_PROMPT)
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument('--raw-json', action='store_true', help='Print raw API JSON response')
    args = parser.parse_args()

    api_key = os.environ.get('GLM_API_KEY')
    if not api_key:
        print('缺少环境变量 GLM_API_KEY。请在 Minis 环境变量里配置。', file=sys.stderr)
        return 3
    if not os.path.exists(args.image_path):
        print(f'图片不存在：{args.image_path}', file=sys.stderr)
        return 2

    payload = build_payload(args.image_path, args.prompt, args.model)
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': 'Bearer ' + api_key,
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print('HTTPError', e.code, e.read().decode('utf-8')[:1000], file=sys.stderr)
        return 1
    except Exception as e:
        print('识图请求失败：' + str(e), file=sys.stderr)
        return 1

    if args.raw_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(data['choices'][0]['message']['content'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
