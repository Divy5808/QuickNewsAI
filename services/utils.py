def calculate_read_time(text):
    if not text:
        return "0 sec"

    words = len(text.split())
    minutes = words / 200

    if minutes < 1:
        return "30 sec"
    else:
        return f"{round(minutes)} min"
