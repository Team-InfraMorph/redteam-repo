const fs = require('node:fs/promises');
async function readImage(key) {
  return fs.readFile('uploads/' + key);
}
module.exports = { readImage };
