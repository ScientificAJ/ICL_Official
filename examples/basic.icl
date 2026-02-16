fn add(a:Num, b:Num):Num => a + b;
x:Num := 4;
y := @add(x, 6);
@print(y);
