// Empaqueta el simulador (index.html + escena GLB + datos + three.js) en UN solo archivo HTML sin dependencias.
// Uso: npm install three@0.160.0 esbuild  y luego  node build_archivo_unico.js   (ajusta SRC y OUT)
const fs = require("fs");
const path = require("path");
const esbuild = require("esbuild");

const SRC = "C:/Users/Laboratorio/Downloads/tumor_cerebral/vr_quest";
const OUT = "C:/Users/Laboratorio/Downloads/tumor_cerebral/para_quest";
fs.mkdirSync(OUT, { recursive: true });

const html = fs.readFileSync(path.join(SRC, "index.html"), "utf8");
const iMap = html.indexOf('<script type="importmap">');
const iMod = html.indexOf('<script type="module">', iMap);
const iEnd = html.indexOf("</script>", iMod);
if (iMap < 0 || iMod < 0 || iEnd < 0) throw new Error("no se encontraron los scripts");
const prefix = html.slice(0, iMap);
let code = html.slice(iMod + '<script type="module">'.length, iEnd);

// 1) la escena y los datos van incrustados (sin fetch, para que funcione como archivo local)
const glbB64 = fs.readFileSync(path.join(SRC, "vr_escena_tumor.glb")).toString("base64");
const dataJson = fs.readFileSync(path.join(SRC, "vr_data.json"), "utf8");
const oldLoad = code.slice(code.indexOf("async function loadScene()"), code.indexOf("data = json;"));
if (!oldLoad.includes("vr_data.json")) throw new Error("bloque de carga no reconocido");
const newLoad = `
async function loadScene() {
  const bin = Uint8Array.from(atob(GLB_B64), (ch) => ch.charCodeAt(0));
  return await new GLTFLoader().parseAsync(bin.buffer, "");
}
const [gltf, json] = await Promise.all([loadScene(), Promise.resolve(DATA_JSON)]);
`;
code = code.replace(oldLoad, newLoad);
const entry = `const GLB_B64 = "${glbB64}";\nconst DATA_JSON = ${dataJson};\n` + code;
fs.writeFileSync(path.join(__dirname, "entry.mjs"), entry);

// 2) empaquetar three.js y los addons usados
const res = esbuild.buildSync({ entryPoints: [path.join(__dirname, "entry.mjs")], bundle: true, format: "esm", target: "es2022", minify: true, write: false, legalComments: "none", logLevel: "warning" });
let bundle = res.outputFiles[0].text.replace(/<\/script/gi, "<\\/script");

const out = prefix + '<script type="module">\n' + bundle + "\n</script>\n</body>\n</html>\n";
const file = path.join(OUT, "Craniotomy_Trainer_Quest3.html");
fs.writeFileSync(file, out);
console.log("OK", file, (out.length / 1e6).toFixed(2) + " MB", "| bundle", (bundle.length / 1e6).toFixed(2) + " MB", "| imports externos:", /from\s*["']https?:/.test(bundle) || /import\(["']https?:/.test(bundle));
