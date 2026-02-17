const __icl_output = document.getElementById('icl-output');
function print(value) {
  if (__icl_output) {
    __icl_output.textContent += String(value) + '\n';
  }
  console.log(value);
}

print(1);
