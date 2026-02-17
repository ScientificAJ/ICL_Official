function clamp(v, lo, hi) {
    if ((v < lo)) {
        return lo;
    } else {
        if ((v > hi)) {
            return hi;
        } else {
            return v;
        }
    }
}
let result = clamp(10, 0, 5);
print(result);
