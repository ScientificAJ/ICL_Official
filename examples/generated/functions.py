def clamp(v, lo, hi):
    if (v < lo):
        return lo
    else:
        if (v > hi):
            return hi
        else:
            return v
result = clamp(10, 0, 5)
print(result)
