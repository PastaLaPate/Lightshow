import queue

ui_queue = queue.Queue()


def post_ui_message(title, message, callback=lambda *a, **k: None):
    ui_queue.put((title, message, callback))
