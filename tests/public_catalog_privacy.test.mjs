import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

// Auditoria deterministica dos arquivos publicos da demo; sem backend,
// gabarito, rede, PDF, processamento editorial ou Codespaces.
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dataRoot = resolve(root, "data");
const catalog = JSON.parse(readFileSync(resolve(root, "catalogo.json"), "utf8"));

// Normalizar snake_case, camelCase e hifens evita falsos negativos triviais.
const forbidden = new Set([
  "answer", "answerkey", "officialanswer", "officialanswerkey",
  "correct", "iscorrect", "correctanswer", "correctoption",
  "correctalternative", "rightanswer", "rightoption", "solutionkey",
  "gabarito", "gabaritooficial", "respostacorreta", "alternativacorreta",
  "opcaocorreta", "chavegabarito", "gradingresult",
]);

function rejectAnswerFields(value, source, trace = "$", depth = 0) {
  assert.ok(depth <= 40, source + ": JSON excessivamente profundo");
  if (!value || typeof value !== "object") return;
  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i += 1) {
      rejectAnswerFields(value[i], source, trace + "[]", depth + 1);
    }
    return;
  }
  for (const [key, entry] of Object.entries(value)) {
    const normalized = key.replace(/[^a-zA-Z0-9]/g, "").toLowerCase();
    assert.ok(!forbidden.has(normalized),
      source + ": chave de resposta proibida em " + trace + "." + key);
    rejectAnswerFields(entry, source, trace + "." + key, depth + 1);
  }
}

function sourcePath(relative) {
  assert.equal(typeof relative, "string");
  assert.match(relative, /^data\/[A-Za-z0-9_.-]+\.json$/);
  const full = resolve(root, relative);
  assert.ok(full.startsWith(dataRoot + sep), "Arquivo fora de data/: " + relative);
  return full;
}

// Pastas publicadas em Pages nao precisam estar referenciadas para serem
// acessiveis por URL. Proibir arquivos extras e subpastas em data/.
function requireDataDirectoryClosed(entries, expected) {
  const present = new Set();
  for (const entry of entries) {
    assert.ok(entry.isFile(), "Subpasta ou link proibido em data/: " + entry.name);
    const relative = "data/" + entry.name;
    assert.match(relative, /^data\/[A-Za-z0-9_-][A-Za-z0-9_.-]*\.json$/,
      "Nome de arquivo publico inesperado: " + relative);
    assert.ok(expected.has(relative), "Arquivo publico sem catalogo: " + relative);
    assert.ok(!present.has(relative), "Arquivo repetido: " + relative);
    present.add(relative);
  }
  assert.deepEqual([...present].sort(), [...expected].sort(),
    "JSON catalogado ausente do diretorio publico data/");
}

test("data publica somente JSONs explicitamente referenciados no catalogo", () => {
  const referenced = new Set(catalog.items.map((item) => item.data));
  requireDataDirectoryClosed(readdirSync(dataRoot, { withFileTypes: true }), referenced);
});

test("auditoria recusa arquivo extra, arquivo oculto e subdiretorio", () => {
  const file = (name) => ({ name, isFile: () => true });
  const folder = { name: "backup", isFile: () => false };
  const refs = new Set(["data/questao.json"]);
  assert.doesNotThrow(() => requireDataDirectoryClosed([file("questao.json")], refs));
  for (const extras of [
    [file("questao.json"), file("gabarito.json")],
    [file("questao.json"), file(".secreto.json")],
    [file("questao.json"), folder],
  ]) {
    assert.throws(() => requireDataDirectoryClosed(extras, refs));
  }
});

test("catalogo da demo nao contem campos de gabarito", () => {
  assert.equal(catalog.kind, "sistema-enem.catalogo_publico.v1");
  assert.ok(Array.isArray(catalog.items) && catalog.items.length > 0);
  rejectAnswerFields(catalog, "catalogo.json");
});

test("todo JSON do catalogo existe, e valido e preserva a identidade", () => {
  const paths = new Set();
  for (const item of catalog.items) {
    assert.ok(!paths.has(item.data), "Arquivo duplicado: " + item.data);
    paths.add(item.data);
    const data = JSON.parse(readFileSync(sourcePath(item.data), "utf8"));
    assert.equal(data.question_id, item.question_id,
      "Identidade divergente: " + item.data);
    rejectAnswerFields(data, item.data);
  }
  assert.equal(paths.size, catalog.items.length);
});

test("verificador recusa gabaritos aninhados, independente da grafia", () => {
  for (const field of ["official_answer", "isCorrect", "answer-key", "gabarito"]) {
    assert.throws(
      () => rejectAnswerFields({ metadata: { [field]: "SENTINELA" } }, "teste"),
      /chave de resposta proibida/,
    );
  }
  assert.doesNotThrow(() => rejectAnswerFields(
    { answer_policy: { mode: "server_only" }, options: [{ label: "A" }] },
    "politica",
  ));
});
