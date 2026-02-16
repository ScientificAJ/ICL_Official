fn clamp(v:Num, lo:Num, hi:Num):Num {
    if v < lo ? {
        ret lo;
    } : {
        if v > hi ? {
            ret hi;
        } : {
            ret v;
        }
    }
}
result := @clamp(10, 0, 5);
@print(result);
