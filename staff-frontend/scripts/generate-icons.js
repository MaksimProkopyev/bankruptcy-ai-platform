const sharp = require('sharp');
const path = require('path');

async function generate() {
  const src = path.join(__dirname, '../public/icons/icon.svg');
  await sharp(src).resize(192, 192).png().toFile(
    path.join(__dirname, '../public/icons/icon-192.png')
  );
  await sharp(src).resize(512, 512).png().toFile(
    path.join(__dirname, '../public/icons/icon-512.png')
  );
  console.log('Icons generated');
}
generate();
