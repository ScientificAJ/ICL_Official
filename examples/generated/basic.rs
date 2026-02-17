fn add(a: f64, b: f64) -> f64 {
    (a + b)
}

fn main() {
    let mut x = 4;
    let mut y = add(x, 6);
    println!("{:?}", y);
}
