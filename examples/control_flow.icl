counter := 0;
loop i in 0..5 {
    counter := counter + i;
}
if counter > 5 ? {
    @print(counter);
} : {
    @print(0);
}
