// Synthetic benign arithmetic fixture; no imports, network, mining or dataset code.
// Six constants followed by i32.and, shl, add, xor, shr_u: active counter 0.
var mode = arguments[0];
var iterations = 20000;
var arithmetic = [0,97,115,109,1,0,0,0,1,5,1,96,0,1,127,3,2,1,0,
  7,7,1,3,114,117,110,0,0,10,21,1,19,0,
  65,1,65,1,65,1,65,1,65,1,65,1,113,116,106,115,118,11];
var negative = [0,97,115,109,1,0,0,0,1,5,1,96,0,1,127,3,2,1,0,
  7,7,1,3,114,117,110,0,0,10,6,1,4,0,65,0,11];
if (mode !== 'active' && mode !== 'dormant' && mode !== 'negative') {
  throw new Error('Unknown fixture mode');
}
var bytes = new Uint8Array(mode === 'negative' ? negative : arithmetic);
var instance = new WebAssembly.Instance(new WebAssembly.Module(bytes));
if (mode !== 'dormant') {
  for (var i = 0; i < iterations; ++i) {
    if (instance.exports.run() !== 0) throw new Error('Unexpected arithmetic result');
  }
}
// Keep the instance live and allow the original 50 ms signal timer to sample.
var until = Date.now() + 300;
while (Date.now() < until) {}
print('SMOKE_OK ' + mode + ' ' + iterations);
