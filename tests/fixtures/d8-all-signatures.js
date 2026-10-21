// Benign independent fixtures for the twelve original active signatures.
var signatures = [[113, 116, 106, 115, 118], [118, 113, 116, 106, 115], [115, 118, 113, 116, 106], [116, 106, 115, 116, 106], [106, 115, 116, 106, 115], [115, 116, 106, 115, 116], [116, 106, 113, 116, 106], [116, 106, 115, 115, 115], [106, 115, 115, 115, 115], [106, 118, 113, 116, 106], [116, 106, 118, 113, 116], [118, 113, 116, 106, 118]];
var match = /^(active|dormant)([0-9]+)$/.exec(arguments[0]);
if (!match || +match[2] >= signatures.length) throw new Error('Invalid case');
var mode = match[1], index = +match[2], iterations = 20000;
var operations = signatures[index];
var body = [0];
var stack = [];
for (var i = 0; i < 6; ++i) { body.push(65, 1); stack.push(1); }
for (var i = 0; i < operations.length; ++i) {
  var opcode = operations[i], b = stack.pop(), a = stack.pop(), value;
  if (opcode === 106) value = (a + b) | 0;
  else if (opcode === 113) value = a & b;
  else if (opcode === 115) value = a ^ b;
  else if (opcode === 116) value = a << (b & 31);
  else if (opcode === 118) value = a >>> (b & 31);
  else throw new Error('Unsupported fixture operation');
  stack.push(value | 0);
  body.push(opcode);
}
body.push(11);
var bytes = [0,97,115,109,1,0,0,0,1,5,1,96,0,1,127,3,2,1,0,
  7,7,1,3,114,117,110,0,0,10,body.length+2,1,body.length].concat(body);
var instance = new WebAssembly.Instance(new WebAssembly.Module(new Uint8Array(bytes)));
if (mode === 'active') {
  for (var i = 0; i < iterations; ++i) {
    if (instance.exports.run() !== stack[0]) throw new Error('Arithmetic mismatch');
  }
}
var until = Date.now() + 300;
while (Date.now() < until) {}
print('SMOKE_OK ' + arguments[0] + ' ' + iterations);
