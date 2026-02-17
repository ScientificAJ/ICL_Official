fn add(a: f64, b: f64) -> f64 {
    return (a + b);
}

fn main() {
    let mut x: f64 = 4.0;
    let mut y: f64 = add(x, 6.0);
    println!("{:?}", y);
}
