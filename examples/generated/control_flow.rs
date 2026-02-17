fn main() {
    let mut counter: f64 = 0.0;
    for i in ((0.0 as i64))..((5.0 as i64)) {
        counter = (counter + (i as f64));
    }
    if (counter > 5.0) {
        println!("{:?}", counter);
    } else {
        println!("{:?}", 0.0);
    }
}
