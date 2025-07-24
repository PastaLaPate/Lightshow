def hsv_to_rgb(h: float, s: float, v: float, a: float) -> tuple:
    if s:
        if h == 1.0:
            h = 0.0
        i = int(h * 6.0)
        f = h * 6.0 - i

        w = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))

        if i == 0:
            return (v, t, w, a)
        if i == 1:
            return (q, v, w, a)
        if i == 2:
            return (w, v, t, a)
        if i == 3:
            return (w, q, v, a)
        if i == 4:
            return (t, w, v, a)
        if i == 5:
            return (v, w, q, a)
    else:
        return (v, v, v, a)
