import asyncio
from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager,
    GlobalSystemMediaTransportControlsSession,
)

loop = None  # global loop reference


async def aplayback_handler(session: GlobalSystemMediaTransportControlsSession, event):
    pb_infos = session.get_playback_info()
    l = ["closed", "opened", "changing", "stopped", "playing", "paused"]
    infos = await session.try_get_media_properties_async()
    if not infos:
        print(l[pb_infos.playback_status])
    else:
        print(f"NOW {l[pb_infos.playback_status]} ({infos.title or ''})")


def playback_handler(session: GlobalSystemMediaTransportControlsSession, event):
    # schedule the coroutine onto the main asyncio loop
    asyncio.run_coroutine_threadsafe(aplayback_handler(session, event), loop)


def handler(manager: GlobalSystemMediaTransportControlsSessionManager, session):
    ses = manager.get_current_session()
    if ses:
        ses.add_playback_info_changed(playback_handler)


async def main():
    manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
    manager.add_current_session_changed(handler)
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
