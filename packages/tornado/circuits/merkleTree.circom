pragma circom 2.0.0;

include "../../../node_modules/circomlib/circuits/poseidon.circom";


// if s == 0 return in[0], in[1]
// if s == 1 return in[1], in[0]
template DaulMux() {
  signal input in[2];
  signal input s;
  signal output out[2];
  s * (1 - s) === 0;
  out[0] <== (in[1] - in[0])*s + in[0];
  out[1] <== (in[0] - in[1])*s + in[1];
}

// Verify merkle proof
template MerkleProofValidator(levels) {
  signal input leaf;
  signal input root;
  signal input pathElements[levels];
  signal input pathIndices[levels];

  component selectors[levels];
  component hashers[levels];

  for (var i = 0; i < levels; i++) {
    selectors[i] = DaulMux();
    selectors[i].in[0] <== i == 0 ? leaf : hashers[i-1].out;
    selectors[i].in[1] <== pathElements[i];
    selectors[i].s <== pathIndices[i];

    hashers[i] = Poseidon(2);
    hashers[i].inputs[0] <== selectors[i].out[0];
    hashers[i].inputs[1] <== selectors[i].out[1];
  }

  root === hashers[levels - 1].out;
}