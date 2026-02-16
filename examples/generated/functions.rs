fn clamp(v: f64, lo: f64, hi: f64) -> f64 {
    if (v < lo) {
        return lo;
    } else {
        if (v > hi) {
            return hi;
        } else {
            return v;
        }
    }
}

fn main() {
    let mut result = clamp(10, 0, 5);
    println!("{:?}", result);
}
