fn main() {
    let mut counter = 0;
    for i in (0 as i64)..(5 as i64) {
        counter = (counter + i);
    }
    if (counter > 5) {
        println!("{:?}", counter);
    } else {
        println!("{:?}", 0);
    }
}
