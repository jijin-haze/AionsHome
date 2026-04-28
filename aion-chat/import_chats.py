"""
聊天记录导入脚本（清洗版 + 附件信息保留）
使用方法：python import_chats.py 你的聊天记录.json
"""

import json
import time
import sys
import re
import asyncio
from datetime import datetime
import aiosqlite

DB_PATH = "data/chat.db"


def parse_timestamp(ts) -> float:
    if isinstance(ts, (int, float)):
        if ts > 1e12:
            return ts / 1000.0
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts).timestamp()
        except Exception:
            return time.time()
    return time.time()


def clean_content(text: str) -> str:
    """
    清洗消息内容（威力加强版）：
    1. 移除 <think>...</think> 思维链（完全隐藏）
    2. 移除 <attachment ...>...</attachment> 系统注入信息（完全隐藏）
    3. 移除 [HEART:xxx] 指令（完全隐藏）
    4. 保留 [MEMORY:xxx] 指令（改为可点击标签）
    5. 保留 [MUSIC:xxx] 指令（改为可点击标签）
    6. 替换图片引用为纯文本表情标签
    """
    # 1. 移除 <think>...</think> 思维链
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    # 2. 移除 <attachment ...>...</attachment> 系统注入信息
    text = re.sub(r'<attachment[^>]*>.*?</attachment>', '', text, flags=re.DOTALL)

    # 3. 移除 [HEART:xxx] 指令
    text = re.sub(r'\[HEART:[^\]]+\]', '', text)

    # 4. 保留 [MEMORY:xxx] 指令（改为可点击的记忆标签）
    text = re.sub(r'\[MEMORY:([^\]]+)\]', r'💭[记忆: \1]', text)

    # 5. 保留 [MUSIC:xxx] 指令（改为可点击的音乐标签）
    text = re.sub(r'\[MUSIC:([^\]]+)\]', r'🎵[点歌: \1]', text)

    # 6. 替换图片引用为纯文本表情标签
    text = re.sub(r'!\[([^\]]*)\]\(file://[^\)]+\)', r'[表情: \1]', text)

    # 7. 清理多余空白
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text
async def import_chats(json_path: str):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    chats = data.get("chats", [])
    if not chats:
        print("❌ 没有找到对话数据")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        total_conv = 0
        total_msg = 0
        skipped_empty = 0
        skipped_heart = 0

        for chat in chats:
            messages = chat.get("messages", [])
            if not messages:
                print(f"⏭️ 跳过空对话: {chat.get('title', '无标题')}")
                continue

            conv_id = chat.get("id", f"conv_import_{int(time.time()*1000)}")
            title = chat.get("title", "导入对话")
            created_at = parse_timestamp(chat.get("createdAt", time.time()))
            updated_at = parse_timestamp(chat.get("updatedAt", time.time()))

            await db.execute(
                "INSERT OR REPLACE INTO conversations (id, title, model, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (conv_id, title, "imported", created_at, updated_at),
            )

            for msg in messages:
                base = msg.get("baseMessage", {})
                sender = base.get("sender", "user")
                role = "user" if sender == "user" else "assistant"
                content = base.get("content", "")
                timestamp = parse_timestamp(base.get("timestamp", time.time()))

                if not content.strip():
                    skipped_empty += 1
                    continue

                cleaned = clean_content(content)
                if not cleaned:
                    skipped_heart += 1
                    continue

                # 拼接附加信息（时间、模型、角色名）
                meta_parts = []
                dt = datetime.fromtimestamp(timestamp)
                meta_parts.append(f"发送时间：{dt.month}月{dt.day}日 {dt.strftime('%H:%M')}")

                if role == "assistant":
                    model_name = base.get("modelName", "")
                    if model_name:
                        meta_parts.append(f"模型：{model_name}")

                role_name = base.get("roleName", "")
                if role_name and role_name not in ("用户", "user"):
                    meta_parts.append(f"角色：{role_name}")

                if meta_parts:
                    cleaned += f"\n<meta>{' | '.join(meta_parts)}</meta>"

                msg_id = f"msg_import_{int(timestamp*1000)}_{total_msg}"
                await db.execute(
                    "INSERT OR REPLACE INTO messages (id, conv_id, role, content, created_at, attachments) VALUES (?, ?, ?, ?, ?, ?)",
                    (msg_id, conv_id, role, cleaned, timestamp, "[]"),
                )
                total_msg += 1

            total_conv += 1
            print(f"✅ {title}: {len(messages)} 条 → 导入 {len(messages) - skipped_empty - skipped_heart} 条")

        await db.commit()

    print(f"\n🎉 完成！{total_conv} 个对话，{total_msg} 条消息。")
    if skipped_heart > 0:
        print(f"   (已自动隐藏 {skipped_heart} 条思维链内心独白)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python import_chats.py 文件名.json")
        sys.exit(1)

    json_file = sys.argv[1]
    asyncio.run(import_chats(json_file))