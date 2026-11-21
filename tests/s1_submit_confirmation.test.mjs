import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";
import vm from "node:vm";

const base = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(resolve(base, "questao.html"), "utf8");
const code = html.match(/<script>\s*([\s\S]*?)<\/script>/)?.[1];
assert.ok(code, "script embutido da página deve existir");

function createHarness(responses) {
  const questionId = "enem:2024:regular_nacional:d2:q133";
  const key = "sistema_enem_attempt_" + questionId;
  const localData = new Map();
  const sessionData = new Map();
  const elements = new Map();
  const posts = [];
  let uuid = 0;

  function element() {
    return {
      hidden: false, className: "", textContent: "", innerHTML: "",
      disabled: false, style: {}, children: [],
      appendChild(node) { this.children.push(node); },
      setAttribute() {},
      addEventListener(type, fn) { this["on_" + type] = fn; },
    };
  }
  const getElement = (id) => {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  };
  const option = { value: "A" };
  const confidence = { value: "3" };
  const button = element();
  const document = {
    title: "",
    getElementById: getElement,
    createElement: element,
    createTextNode: (v) => ({ textContent: v }),
    querySelector: (selector) => {
      if (selector === 'input[name="alternativa"]:checked') return option;
      if (selector === 'input[name="confianca"]:checked') return confidence;
      if (selector === '#form-resposta button[type="submit"]') return button;
      return null;
    },
  };
  const store = (map) => ({
    getItem(k) { return map.has(k) ? map.get(k) : null; },
    setItem(k, v) { map.set(k, String(v)); },
    removeItem(k) { map.delete(k); },
  });
  const fetch = async (url, init) => {
    if (url === "catalogo.json") return {
      json: async () => ({ items: [{
        id: "q133", question_id: questionId, numero_oficial: 133,
        ano: 2024, prova: "ENEM", pagina: 15, area: "CN",
        fonte: "INEP", imagem: "q133.png", data: "q133.json",
      }] }),
    };
    if (url === "q133.json") return {
      json: async () => ({ options: [{ label: "A", text: "Opção de teste" }] }),
    };
    posts.push(JSON.parse(init.body));
    if (!responses.length) throw new Error("Sem resposta simulada");
    const next = responses.shift();
    if (next instanceof Error) throw next;
    if (typeof next === "function") return next();
    return {
      ok: next.ok ?? true,
      status: next.status ?? 200,
      json: async () => {
        if (next.invalidJson) throw new SyntaxError("Resposta inválida");
        return next.body;
      },
    };
  };

  vm.runInNewContext(code, {
    window: { SISTEMA_ENEM_API: "https://example.invalid/exec" },
    document, location: { search: "?id=q133" }, URLSearchParams,
    fetch, sessionStorage: store(sessionData), localStorage: store(localData),
    crypto: { randomUUID: () => "nonce-" + ++uuid },
    Date, Math, Number, String,
  }, { filename: "questao.html" });

  async function ready() {
    for (let i = 0; i < 8; i++) await Promise.resolve();
    assert.equal(typeof getElement("form-resposta").on_submit, "function");
  }
  async function submit() {
    await ready();
    return getElement("form-resposta").on_submit({ preventDefault() {} });
  }
  return {
    key, posts, sessionData, button, submit, ready,
    result: () => getElement("resultado"),
  };
}

test("HTTP 200 com erro not_found nao confirma e retém nonce para replay", async () => {
  const h = createHarness([
    { body: { error: "not_found" } },
    { body: { persisted: true, correct: true, official_status: "valid" } },
  ]);
  await h.submit();
  assert.equal(h.posts.length, 1);
  assert.equal(h.result().className, "erro");
  assert.equal(h.sessionData.has(h.key), true);
  const nonce = h.posts[0].client_attempt_id;
  await h.submit();
  assert.equal(h.posts[1].client_attempt_id, nonce);
  assert.equal(h.result().className, "ok");
  assert.match(h.result().textContent, /Correta!/);
  assert.equal(h.sessionData.has(h.key), false);
});

test("JSON malformado conserva identificador e nao exibe feedback", async () => {
  const h = createHarness([{ invalidJson: true }, { body: { persisted: true, correct: false } }]);
  await h.submit();
  assert.equal(h.result().className, "erro");
  assert.equal(h.sessionData.has(h.key), true);
  await h.submit();
  assert.equal(h.posts[0].client_attempt_id, h.posts[1].client_attempt_id);
  assert.match(h.result().textContent, /Incorreta/);
  assert.equal(h.sessionData.has(h.key), false);
});

test("HTTP nao-200 nao consome o nonce de idempotencia", async () => {
  const h = createHarness([{ ok: false, status: 503 }]);
  await h.submit();
  assert.equal(h.posts.length, 1);
  assert.match(h.result().textContent, /503/);
  assert.equal(h.sessionData.has(h.key), true);
});

test("persisted falso, corpo vazio e identidade divergente nao confirmam", async () => {
  for (const body of [
    { persisted: false, correct: true },
    {},
    { persisted: true, error: "conflict", correct: true },
    { persisted: true, question_id: "outra", correct: true },
    { persisted: true, client_attempt_id: "outro", correct: true },
    { persisted: true, ok: false, correct: true },
  ]) {
    const h = createHarness([{ body }]);
    await h.submit();
    assert.equal(h.result().className, "erro", JSON.stringify(body));
    assert.equal(h.sessionData.has(h.key), true, JSON.stringify(body));
  }
});

test("recibo persistido de questao anulada libera nonce e confirma registro", async () => {
  const h = createHarness([{ body: { persisted: true, official_status: "annulled", correct: null } }]);
  await h.submit();
  assert.equal(h.result().className, "ok");
  assert.match(h.result().textContent, /anulada pelo INEP/);
  assert.equal(h.sessionData.has(h.key), false);
});

test("duplo clique enquanto a chamada esta pendente faz apenas um POST", async () => {
  let respond;
  const pending = new Promise((resolvePost) => { respond = resolvePost; });
  const h = createHarness([() => pending]);
  await h.ready();
  const first = h.submit();
  await Promise.resolve();
  const second = h.submit();
  assert.equal(h.posts.length, 1);
  assert.equal(h.button.disabled, true);
  respond({ ok: true, status: 200, json: async () => ({ persisted: true, correct: true }) });
  await Promise.all([first, second]);
  assert.equal(h.button.disabled, false);
  assert.equal(h.posts.length, 1);
  assert.equal(h.result().className, "ok");
});
