import asyncio
import aiosqlite

async def clear():
    async with aiosqlite.connect('data/chat.db') as db:
        # 删除所有导入的消息
        await db.execute("DELETE FROM messages WHERE id LIKE 'msg_import_%'")
        # 删除所有导入的对话
        await db.execute("DELETE FROM conversations WHERE model = 'imported'")
        await db.commit()
        print("✅ 已清空所有导入的聊天记录，可以重新导入了。")

asyncio.run(clear())