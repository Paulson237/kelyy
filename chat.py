"""Talk to the kely Brain (Malika) interactively.

    uv run python chat.py

Type a question, get Malika's answer from the Company Brain. Commands:
    :recall <q>   show raw memories (which tier each came from)
    :quit         exit
"""

import asyncio
import sys

import cognee

from kely_brain import agent, config


async def main():
    await config.connect_cloud()
    print("\n🧠 kely Brain — chatting with Malika (AngelSitting). Type :quit to exit.\n")
    session = "chat_repl"
    loop = asyncio.get_event_loop()
    while True:
        try:
            q = (await loop.run_in_executor(None, sys.stdin.readline)).strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q in (":quit", ":q", "exit"):
            break
        if q.startswith(":recall "):
            res = await cognee.recall(q[len(":recall ") :], session_id=session, scope="all")
            for r in res:
                print(f"   [{getattr(r, 'source', '?')}] {str(r)[:200]}")
            print()
            continue
        ans = await agent.ask(q, session_id=session)
        print(f"\n💬 Malika: {ans}\n")


if __name__ == "__main__":
    asyncio.run(main())
